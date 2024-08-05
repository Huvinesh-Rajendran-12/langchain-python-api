from typing import Optional, Dict, List, Tuple, AsyncGenerator, Any
from langchain_anthropic import ChatAnthropic
from langchain_community.utilities import SQLDatabase
from langchain_community.agent_toolkits import create_sql_agent
from langchain.tools import StructuredTool
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

        self.embeddings = HuggingFaceEmbeddings(model_name=settings.EMBEDDING_MODEL)
        self.country_vector_store = self.initialize_vector_stores()

        self.example_selector = self._initialize_example_selector()

        self.conversation_history = []
        self.last_query_result = None

        self.context_tool = StructuredTool.from_function(
            name="context_manager",
            func=self.manage_context,
            description="Use this tool to retrieve or update the conversation context. Input should be 'get' to retrieve context or 'update: <new_context>' to update it.",
        )

        self.query_decider = StructuredTool.from_function(
                    name="query_decider",
                    func=self.decide_query_generation,
                    description="Use this tool to decide whether to generate a new SQL query or use existing context."
                )

        self.search_country_tool = StructuredTool.from_function(
            name="search_country",
            func=self.search_country,
            description="Search for countries in the database.",
        )
        self.search_proper_nouns_tool = StructuredTool.from_function(
            name="search_proper_nouns",
            func=self.search_proper_nouns,
            description="Search for proper nouns in the database.",
        )

        self.prompt = ChatPromptTemplate.from_messages(
            [
                ("system", settings.SYSTEM_PROMPT),
                ("human", "{input}"),
                MessagesPlaceholder("agent_scratchpad"),
            ]
        )

        self.custom_tools = [
            self.context_tool,
            self.search_country_tool,
            self.search_proper_nouns_tool,
        ]

        self.agent = create_sql_agent(
            llm=self.llm,
            db=self.db,
            prompt=self.prompt,
            agent_type="tool-calling",
            verbose=True,
            extra_tools=self.custom_tools,
        )

        self.vector_store = self.initialize_table_vector_store()
        self.query_cache = {}
        self.final_answer: Optional[str] = None

    def _initialize_example_selector(self):
        return SemanticSimilarityExampleSelector.from_examples(
            settings.EXAMPLES, self.embeddings, FAISS, k=2, input_keys=["input"]
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

    async def process_query(self, question: str) -> AsyncGenerator[Tuple[str, str], None]:
        yield "Initializing", "Starting to process your query"

        try:
            similar_examples = self.get_similar_examples(question)
            formatted_examples = self._format_examples(similar_examples)

            context = self._get_context()

            enhanced_question = f"""User query: {question}

            Similar examples:
            {formatted_examples}

            Current context:
            {context}

            Remember: For follow-up questions, do not create or execute new SQL queries. Use the existing context to answer."""

            compressed_input = zlib.compress(enhanced_question.encode())

            yield "Processing", "Analyzing the query and formulating a response"

            query_results = None
            full_response = ""

            async for chunk in self.agent.astream({
                "input": zlib.decompress(compressed_input).decode(),
                "examples": formatted_examples,
            }):
                if 'actions' in chunk:
                    for action in chunk['actions']:
                        if action.tool == "sql_db_query":
                            query_results = action.tool_input
                        yield "Executing", f"Running action: {action.tool}"
                elif 'intermediate_steps' in chunk:
                    for step in chunk['intermediate_steps']:
                        yield "Intermediate Step", str(step)
                elif 'output' in chunk:
                    try:
                        if query_results and isinstance(query_results, list) and len(query_results) > 0:
                            formatted_results = self._format_results(query_results)
                            full_response += f"Here are the relevant results:\n\n{formatted_results}\n\n"
                    except Exception as e:
                        print(f"Debug: Error in formatting results: {str(e)}")

                    if isinstance(chunk['output'], list):
                        for item in chunk['output']:
                            if isinstance(item, dict) and 'text' in item:
                                full_response += item['text']
                            else:
                                full_response += str(item)
                    else:
                        full_response += str(chunk['output'])

                    yield "Finalizing", "Preparing the final answer"

            # Remove any SQL queries from the final answer
            final_answer = self._remove_sql_queries(full_response)
            self.final_answer = final_answer
            self.last_query_result = final_answer
            self._update_conversation_history(question, final_answer)

        except Exception as e:
            print(f"Debug: Error in process_query: {str(e)}")
            yield "Error", f"An error occurred: {str(e)}"

    def _remove_sql_queries(self, text: str) -> str:
        # Simple function to remove anything that looks like an SQL query
        lines = text.split('\n')
        filtered_lines = [line for line in lines if not line.strip().upper().startswith(('SELECT', 'INSERT', 'UPDATE', 'DELETE', 'CREATE', 'ALTER', 'DROP', 'SQL', 'FROM', 'WHERE', 'LIMIT', 'LIKE', 'AND', 'OR', 'JOIN'))]
        return '\n'.join(filtered_lines)


    def _format_results(self, results: List[Dict]) -> str:
        if not results or len(results) == 0:
            return "No data available."

        # Convert results to JSON string
        table_data = json.dumps(results[:10])  # Limit to 10 rows

        # Create a message with the table data and total count
        message = f"<TableData>{table_data}</TableData>"
        if len(results) > 10:
            message += f"\n\n*Showing 10 out of {len(results)} rows*"

        return message

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


    def decide_query_generation(self, question: str) -> str:
        context = json.loads(self.manage_context("get"))
        decision_prompt = f"""Given the following question and conversation context, decide if a new SQL query should be generated or if the existing context is sufficient to answer the question.

        Question: {question}

        Conversation Context:
        {json.dumps(context, indent=2)}

        Respond with either "generate_new_query" or "use_existing_context", followed by a brief explanation of your decision."""

        decision = self.llm.predict(decision_prompt)
        return decision

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
