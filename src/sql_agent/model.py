from typing import Optional, Dict, List, Tuple, AsyncGenerator
from langchain_anthropic import ChatAnthropic
from langchain_community.utilities import SQLDatabase
from langchain_community.agent_toolkits import create_sql_agent
from langchain.tools import Tool
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.example_selectors.semantic_similarity import (
    SemanticSimilarityExampleSelector,
)
from langchain_community.cache import InMemoryCache
from langchain.globals import set_llm_cache
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings
from langchain.schema import Document
import zlib
from src.config import settings
import json


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
            max_tokens_to_sample=settings.ANTHROPIC_LLM_MAX_TOKENS,
        )

        self.embeddings = HuggingFaceEmbeddings()
        self.country_vector_store = self.initialize_vector_stores()

        self.example_selector = self._initialize_example_selector()

        self.conversation_history = []
        self.last_query_result = None

        self.context_tool = Tool(
            name="context_manager",
            func=self.manage_context,
            description="Use this tool to retrieve or update the conversation context. Input should be 'get' to retrieve context or 'update: <new_context>' to update it.",
        )

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
        - When dealing with queries related to country such as person_country, only use values you get from using the search_country tool.
        - If unrelated to the database, briefly explain why
        - Prioritize clarity and brevity in your response
        - Include only essential information and key insights
        - Create a table or list accordingly when handling multiple results from a query.

        Use the following examples as a guide:
        {examples}
        """

        self.prompt = ChatPromptTemplate.from_messages(
            [
                ("system", self.system_prompt),
                ("human", "{input}"),
                MessagesPlaceholder("agent_scratchpad"),
            ]
        )

        self.tools = [self.search_country, self.search_proper_nouns]

        self.agent = create_sql_agent(
            llm=self.llm,
            db=self.db,
            prompt=self.prompt,
            agent_type="tool-calling",
            verbose=True,
            additional_tools=self.tools,
        )

        self.vector_store = self.initialize_table_vector_store()
        self.query_cache = {}
        self.final_answer: Optional[str] = None

    def _initialize_example_selector(self):
        examples = [
            {
                "input": "Find companies attending Oil & Gas related events over the next 12 months",
                "query": """
                SELECT DISTINCT ec.company_name
                FROM event_company ec
                JOIN (SELECT event_url FROM event_company WHERE event_industry = 'Oil & Gas') oe ON ec.event_url = oe.event_url
                WHERE ec.event_start_date BETWEEN CURRENT_DATE AND CURRENT_DATE + INTERVAL '12 months'
                LIMIT 10
                """,
            },
            {
                "input": "Find sales people for companies attending events in Singapore over the next 9 months",
                "query": """
                SELECT DISTINCT pc.first_name, pc.last_name, pc.email_address
                FROM people_company pc
                JOIN event_company ec ON pc.company_name = ec.company_name
                WHERE ec.event_country = 'Singapore'
                  AND ec.event_start_date BETWEEN CURRENT_DATE AND CURRENT_DATE + INTERVAL '9 months'
                  AND pc.job_title ILIKE '%sales%'
                LIMIT 10
                """,
            },
            {
                "input": "Find events that companies in Pharmaceuticals sector are attending",
                "query": """
                SELECT DISTINCT e.event_name, e.event_start_date, e.event_country
                FROM event_company e
                JOIN (SELECT DISTINCT company_name FROM people_company WHERE company_industry = 'Pharmaceuticals') p
                ON e.company_name = p.company_name
                ORDER BY e.event_start_date
                LIMIT 10
                """,
            },
            {
                "input": "Get email addresses of people working for companies attending finance and banking events",
                "query": """
                SELECT DISTINCT pc.email_address
                FROM people_company pc
                JOIN event_company ec ON pc.company_name = ec.company_name
                WHERE ec.event_industry IN ('Finance', 'Banking')
                LIMIT 10
                """,
            },
            {
                "input": "List companies with revenue above $1 billion attending technology events",
                "query": """
                SELECT DISTINCT pc.company_name, pc.company_revenue
                FROM people_company pc
                JOIN event_company ec ON pc.company_name = ec.company_name
                WHERE ec.event_industry = 'Technology'
                  AND pc.company_revenue > 1000000000
                ORDER BY pc.company_revenue DESC
                LIMIT 10
                """,
            },
            {
                "input": "Find me people working in Singapore",
                "query": """"
                SELECT first_name, last_name, job_title, email_address, person_city
                FROM people
                WHERE person_country = 'Singapore'
                LIMIT 10
                """,
            },
        ]

        return SemanticSimilarityExampleSelector.from_examples(
            examples, self.embeddings, FAISS, k=2, input_keys=["input"]
        )

    def initialize_vector_stores(self):
        return FAISS.from_texts(
            [
                row[0]
                for row in self.db.run("SELECT DISTINCT person_country FROM people")
            ],
            self.embeddings,
        )

    def initialize_table_vector_store(self):
        docs = [
            Document(page_content=table) for table in self.db.get_usable_table_names()
        ]
        return FAISS.from_documents(docs, self.embeddings)

    def search_country(self, query, top_k=5):
        results = self.country_vector_store.similarity_search(query, k=top_k)
        return [doc.page_content for doc in results]

    def search_proper_nouns(self, query):
        results = self.vector_store.similarity_search(query, k=1)
        return results[0].page_content if results else None

    def get_similar_examples(self, query: str) -> List[Dict[str, str]]:
        return self.example_selector.select_examples({"input": query})

    def _format_examples(self, examples: List[Dict[str, str]]) -> str:
        formatted = ""
        for i, example in enumerate(examples, 1):
            formatted += f"Example {i}:\nInput: {example['input']}\nQuery: {example['query']}\n\n"
        return formatted.strip()

    async def process_query(
        self, question: str
    ) -> AsyncGenerator[Tuple[str, str], None]:
        yield "Initializing", "Starting to process your query"

        try:
            similar_examples = self.get_similar_examples(question)
            formatted_examples = self._format_examples(similar_examples)

            enhanced_question = f"""User query: {question}

            Similar examples:
            {formatted_examples}

            Generate a new SQL query based on the user query and the similar examples."""

            compressed_input = zlib.compress(enhanced_question.encode())

            yield "Processing", "Analyzing the query and generating SQL"

            async for chunk in self.agent.astream(
                {
                    "input": zlib.decompress(compressed_input).decode(),
                    "examples": formatted_examples,
                }
            ):
                if "actions" in chunk:
                    for action in chunk["actions"]:
                        yield "Executing", f"Running action: {action.tool}"
                elif "intermediate_steps" in chunk:
                    for step in chunk["intermediate_steps"]:
                        yield "Intermediate Step", str(step)
                elif "output" in chunk:
                    self.final_answer = chunk["output"]
                    yield "Finalizing", "Preparing the final answer"

        except Exception as e:
            yield "Error", f"An error occurred: {str(e)}"

    def extract_final_answer(self, result: Dict) -> str:
        if "output" in result:
            return result["output"]
        elif "intermediate_steps" in result:
            return result["intermediate_steps"][-1][1]
        else:
            return "Unable to extract a final answer from the agent's response."

    def manage_context(self, action: str) -> str:
        if action == "get":
            return self._get_context()
        elif action.startswith("update:"):
            new_context = action[7:].strip()
            return self._update_context(new_context)
        else:
            return "Invalid action. Use 'get' to retrieve context or 'update: <new_context>' to update it."

    def _get_context(self) -> str:
        context = {
            "conversation_history": self.conversation_history,
            "last_query_result": self.last_query_result,
        }
        return json.dumps(context)

    def _update_context(self, new_context: str) -> str:
        try:
            context_dict = json.loads(new_context)
            self.conversation_history = context_dict.get(
                "conversation_history", self.conversation_history
            )
            self.last_query_result = context_dict.get(
                "last_query_result", self.last_query_result
            )
            return "Context updated successfully"
        except json.JSONDecodeError:
            return "Error: Invalid JSON format for context update"

    def _update_conversation_history(self, question: str, answer: str) -> None:
        self.conversation_history.append({"human": question, "ai": answer})
        if len(self.conversation_history) > 10:  # Limit history to last 10 exchanges
            self.conversation_history.pop(0)

    async def get_final_answer(self) -> str:
        if self.final_answer is None:
            return "No query has been processed yet."
        if isinstance(self.final_answer, list):
            return self.final_answer[0]["text"] if self.final_answer else "No result"
        return str(self.final_answer)
