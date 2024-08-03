import os
import json
import hashlib
import sqlite3
from typing_extensions import TypedDict
from datetime import datetime
from functools import lru_cache
from dotenv import load_dotenv
from langchain_community.utilities import SQLDatabase
from langchain_core.messages import ToolMessage, AIMessage, HumanMessage
from langchain_core.runnables import RunnableLambda, RunnableWithFallbacks
from langgraph.prebuilt import ToolNode
from langchain_community.agent_toolkits import SQLDatabaseToolkit
from langchain_anthropic import ChatAnthropic
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.pydantic_v1 import BaseModel, Field
from typing import Any, List, Dict, Literal
from langgraph.graph import END, StateGraph, START
from langgraph.graph.message import AnyMessage, add_messages

# Load environment variables
load_dotenv()

# Database connection setup
db_url = f"postgresql://{os.getenv('DB_USERNAME')}:{os.getenv('DB_PASSWORD')}@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}"
anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")
db = SQLDatabase.from_uri(db_url)

# SQLite database for caching and feedback
conn = sqlite3.connect('sql_agent_cache.db')
cursor = conn.cursor()
cursor.execute('''
    CREATE TABLE IF NOT EXISTS query_cache (
        query_hash TEXT PRIMARY KEY,
        query TEXT,
        result TEXT,
        timestamp DATETIME
    )
''')
cursor.execute('''
    CREATE TABLE IF NOT EXISTS query_feedback (
        query_hash TEXT PRIMARY KEY,
        query TEXT,
        success_count INTEGER,
        failure_count INTEGER,
        last_used DATETIME
    )
''')
conn.commit()

# Caching decorator
def cache_query(func):
    @lru_cache(maxsize=100)
    def wrapper(query: str) -> str:
        query_hash = hashlib.md5(query.encode()).hexdigest()
        cursor.execute("SELECT result FROM query_cache WHERE query_hash = ?", (query_hash,))
        cached_result = cursor.fetchone()
        if cached_result:
            return cached_result[0]
        result = func(query)
        cursor.execute(
            "INSERT OR REPLACE INTO query_cache (query_hash, query, result, timestamp) VALUES (?, ?, ?, ?)",
            (query_hash, query, result, datetime.now())
        )
        conn.commit()
        return result
    return wrapper

# Feedback loop functions
def record_query_success(query: str):
    query_hash = hashlib.md5(query.encode()).hexdigest()
    cursor.execute('''
        INSERT INTO query_feedback (query_hash, query, success_count, failure_count, last_used)
        VALUES (?, ?, 1, 0, ?) ON CONFLICT(query_hash) DO UPDATE SET success_count = success_count + 1, last_used = ?
    ''', (query_hash, query, datetime.now(), datetime.now()))
    conn.commit()

def record_query_failure(query: str):
    query_hash = hashlib.md5(query.encode()).hexdigest()
    cursor.execute('''
        INSERT INTO query_feedback (query_hash, query, success_count, failure_count, last_used)
        VALUES (?, ?, 0, 1, ?) ON CONFLICT(query_hash) DO UPDATE SET failure_count = failure_count + 1, last_used = ?
    ''', (query_hash, query, datetime.now(), datetime.now()))
    conn.commit()

# Define utility functions
def create_tool_node_with_fallback(tools: list) -> RunnableWithFallbacks[Any, Dict]:
    return ToolNode(tools).with_fallbacks([RunnableLambda(handle_tool_error)], exception_key="error")

def handle_tool_error(state) -> Dict:
    error = state.get("error")
    tool_calls = state["messages"][-1].tool_calls
    return {
        "messages": [
            ToolMessage(
                content=f"Error: {repr(error)}. Please fix your mistakes and try again.",
                tool_call_id=tc["id"]
            ) for tc in tool_calls
        ]
    }

# Define the LLM model
llm = ChatAnthropic(model="claude-3-opus-20240229", temperature=0, api_key=anthropic_api_key)

# Define tools for SQL agent usage
sqltoolkit = SQLDatabaseToolkit(db=db, llm=llm)
sqltools = sqltoolkit.get_tools()
list_tables_tool = next(tool for tool in sqltools if tool.name == "sql_db_list_tables")
get_schema_tool = next(tool for tool in sqltools if tool.name == "sql_db_schema")

# Define the db query tool with caching
@cache_query
def db_query_tool(query: str) -> str:
    result = db.run_no_throw(query)
    if not result:
        record_query_failure(query)
        return "Error: Query failed. Please rewrite your query and try again."
    record_query_success(query)
    return result

# Improved query check system prompt
query_check_system = """You are a PostgreSQL expert with a strong attention to detail. Thoroughly check the query for common mistakes and optimizations..."""

query_check_prompt = ChatPromptTemplate.from_messages([
    ("system", query_check_system),
    ("placeholder", "{messages}")
])
query_check = query_check_prompt | llm.bind_tools([db_query_tool], tool_choice="required")

# Define the state of the agent
class State(TypedDict):
    messages: List[AnyMessage]

# Define the graph
workflow = StateGraph(State)

def first_tool_call(state: State) -> Dict[str, List[AIMessage]]:
    return {
        "messages": [
            AIMessage(
                content="To answer your question, I first need to understand the database structure. Let me list the available tables.",
                tool_calls=[{"name": "sql_db_list_tables", "args": {}, "id": "tool_list_tables"}]
            )
        ]
    }

def model_check_query(state: State) -> Dict[str, List[AIMessage]]:
    return {
        "messages": [query_check.invoke({"messages": [state["messages"][-1]]})]
    }

# Define the workflow nodes
workflow.add_node("first_tool_call", first_tool_call)
workflow.add_node("list_tables_tool", create_tool_node_with_fallback([list_tables_tool]))
workflow.add_node("get_schema_tool", create_tool_node_with_fallback([get_schema_tool]))

# Improved query generation system prompt
query_gen_system = """You are a PostgreSQL expert tasked with answering user questions by generating and executing SQL queries..."""

query_gen_prompt = ChatPromptTemplate.from_messages([
    ("system", query_gen_system),
    ("placeholder", "{messages}")
])
query_gen = query_gen_prompt | llm.bind_tools([SubmitFinalAnswer])

def query_gen_node(state: State):
    message = query_gen.invoke(state)
    tool_messages = []
    if message.tool_calls:
        for tc in message.tool_calls:
            if tc["name"] != "SubmitFinalAnswer":
                tool_messages.append(
                    ToolMessage(
                        content=f"Error: The wrong tool was called: {tc['name']}. Please fix your mistakes.",
                        tool_call_id=tc["id"]
                    )
                )
    return {"messages": [message] + tool_messages}

workflow.add_node("query_gen", query_gen_node)
workflow.add_node("correct_query", model_check_query)
workflow.add_node("execute_query", create_tool_node_with_fallback([db_query_tool]))

def agent_should_continue(state: State) -> Literal[END, "correct_query", "query_gen"]:
    messages = state["messages"]
    last_message = messages[-1]
    if getattr(last_message, "tool_calls", None):
        return END
    return "query_gen" if last_message.content.startswith("Error:") else "correct_query"

# Define the workflow edges
workflow.add_edge(START, "first_tool_call")
workflow.add_edge("first_tool_call", "list_tables_tool")
workflow.add_edge("list_tables_tool", "get_schema_tool")
workflow.add_edge("get_schema_tool", "query_gen")
workflow.add_conditional_edges("query_gen", agent_should_continue)
workflow.add_edge("correct_query", "execute_query")
workflow.add_edge("execute_query", "query_gen")

app = workflow.compile()

def process_user_query(user_query: str) -> str:
    messages = app.invoke({"messages": [HumanMessage(content=user_query)]}, {"recursion_limit": 100})
    final_message = messages["messages"][-1]
    if isinstance(final_message, AIMessage) and final_message.tool_calls:
        for tool_call in final_message.tool_calls:
            if tool_call["name"] == "SubmitFinalAnswer":
                return json.loads(tool_call["args"])["final_answer"]
    return "I apologize, but I couldn't generate a proper answer to your query."

# Example usage
user_question = "Find me events that will occur in the next 3 months."
answer = process_user_query(user_question)
print(f"User Question: {user_question}")
print(f"Answer: {answer}")

# Close the SQLite connection when done
conn.close()
