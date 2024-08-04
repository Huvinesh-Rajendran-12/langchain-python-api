import os
from typing import Optional, Dict
from dotenv import load_dotenv
from sqlalchemy import create_engine
from langchain_anthropic import ChatAnthropic
from langchain_community.utilities import SQLDatabase
from langchain_community.agent_toolkits import create_sql_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_community.cache import InMemoryCache
from langchain.globals import set_llm_cache
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings
from langchain.schema import Document
import time
import zlib
import json
from collections import deque
from typing import AsyncGenerator, Tuple
from src.config import settings

class SQLAgent:
    def __init__(self) -> None:
        if settings.ENABLE_CACHE:
            set_llm_cache(InMemoryCache())

        self.db = SQLDatabase.from_uri(settings.DATABASE_URL)

        self.llm = ChatAnthropic(
            model=settings.ANTHROPIC_LLM_MODEL,
            temperature=settings.ANTHROPIC_LLM_TEMPERATURE,
            api_key=settings.ANTHROPIC_API_KEY,
            cache=settings.ENABLE_CACHE,
            max_tokens_to_sample=settings.ANTHROPIC_LLM_MAX_TOKENS
        )

        self.embeddings = HuggingFaceEmbeddings()
        self.country_vector_store = self.initialize_vector_stores()

        self.system_prompt = """You are a precise SQL expert. Given a question:
        1. Create an efficient {dialect} query using only these tables: {table_names}
        2. Execute the query and analyze results
        3. Provide a concise, informative answer to the user
        Guidelines:
        - Use indexes, avoid full table scans
        - Limit to 10 results unless specified
        - No DML statements
        - For proper noun filters, use search_proper_nouns tool
        - Join tables: event_url for event & company, homepage_base_url for company & people
        - When dealing with queries related to country, only use values you get from using the search_country tool.
        - If unrelated to the database, briefly explain why
        - Prioritize clarity and brevity in your response
        - Include only essential information and key insights
        - Use bullet points for multiple items
        - Offer to provide more details if needed"""

        self.prompt = ChatPromptTemplate.from_messages([
            ("system", self.system_prompt),
            ("human", "{input}"),
            MessagesPlaceholder("agent_scratchpad")
        ])

        self.tools = [self.search_country, self.search_proper_nouns]

        self.agent = create_sql_agent(
            llm=self.llm,
            db=self.db,
            prompt=self.prompt,
            agent_type="tool-calling",
            verbose=True,
            additional_tools=self.tools
        )

        self.vector_store = self.initialize_table_vector_store()
        self.query_cache = {}
        self.final_answer: Optional[str] = None

    def initialize_vector_stores(self):
            return FAISS.from_texts(
                [row[0] for row in self.db.run("SELECT DISTINCT person_country FROM people")],
                self.embeddings
            )

    def initialize_table_vector_store(self):
        docs = [Document(page_content=table) for table in self.db.get_usable_table_names()]
        return FAISS.from_documents(docs, self.embeddings)

    def search_country(self, query, top_k=5):
        results = self.country_vector_store.similarity_search(query, k=top_k)
        return [doc.page_content for doc in results]

    def search_proper_nouns(self, query):
        results = self.vector_store.similarity_search(query, k=1)
        return results[0].page_content if results else None

    async def process_query(self, question: str) -> AsyncGenerator[Tuple[str, str], None]:
        yield "Initializing", "Starting to process your query"

        try:
            compressed_input = zlib.compress(question.encode())
            result = self.agent.invoke({"input": zlib.decompress(compressed_input).decode()})

            yield "Processing", "Analyzing the query results"

            self.query_cache[question] = result
            self.final_answer = self.extract_final_answer(result)

            yield "Finalizing", "Preparing the final answer"

        except Exception as e:
            yield "Error", f"An error occurred: {str(e)}"


    def extract_final_answer(self, result: Dict) -> str:
            # Extract the final answer from the agent's response
            # This method may need to be adjusted based on the exact structure of the agent's output
            if 'output' in result:
                return result['output']
            elif 'intermediate_steps' in result:
                # If the result contains intermediate steps, take the last one as the final answer
                return result['intermediate_steps'][-1][1]
            else:
                return "Unable to extract a final answer from the agent's response."

    async def get_final_answer(self) -> str:
            if self.final_answer is None:
                return "No query has been processed yet."
            if isinstance(self.final_answer, list):
                return self.final_answer[0]['text'] if self.final_answer else "No result"
            return str(self.final_answer)
