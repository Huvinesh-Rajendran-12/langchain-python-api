import os
from dotenv import load_dotenv
from langchain_community.utilities import SQLDatabase
from langchain_core.prompts import (
    ChatPromptTemplate,
    MessagesPlaceholder,
)
from langchain_mistralai import ChatMistralAI
from langchain_community.agent_toolkits import create_sql_agent
import pprint
import asyncio

# Load environment variables
load_dotenv()

# Set up API keys and database connection
mistral_api_key = os.getenv("MISTRAL_API_KEY")
print(mistral_api_key)

db_username = os.getenv('DB_USERNAME')
db_password = os.getenv('DB_PASSWORD')
db_host = os.getenv('DB_HOST')
db_port = os.getenv('DB_PORT')
db_name = os.getenv('DB_NAME')

db_url = f'postgresql://{db_username}:{db_password}@{db_host}:{db_port}/{db_name}'
db = SQLDatabase.from_uri(db_url)

# Set up language model
llm = ChatMistralAI(model="open-mixtral-8x22b", api_key=mistral_api_key)

# Define system prompt
system = """You are an agent designed to interact with a SQL database.
Given an input question, create a syntactically correct {dialect} query to run, then look at the results of the query and return the answer.
You can order the results by a relevant column to return the most interesting examples in the database.
Never query for all the columns from a specific table, only ask for the relevant columns given the question.
You have access to tools for interacting with the database.
Only use the given tools. Only use the information returned by the tools to construct your final answer.
You MUST double check your query before executing it. If you get an error while executing a query, rewrite the query and try again.

DO NOT make any DML statements (INSERT, UPDATE, DELETE, DROP etc.) to the database.

If you need to filter on a proper noun, you must ALWAYS first look up the filter value using the "search_proper_nouns" tool!

You have access to the following tables: {table_names}

If the question does not seem related to the database, explain to the user why you can't find the answer.

Return the response in a nice format and visualize it if possible.

Use the following information about the tables to retrieve accurate answers.

[Table information here...]
"""

# Create prompt and agent
prompt = ChatPromptTemplate.from_messages(
    [("system", system), ("human", "{input}"), MessagesPlaceholder("agent_scratchpad")]
)
agent = create_sql_agent(
    llm=llm,
    db=db,
    prompt=prompt,
    agent_type="tool-calling",
    verbose=True,
)

# Async function to stream agent responses
async def stream_agent_response(input_text):
    chunks = []
    async for chunk in agent.astream({"input": input_text}):
        chunks.append(chunk)
        print("------")
        pprint.pprint(chunk, depth=5)
    return chunks

# Function to run agent queries
def run_agent_query(input_text):
    return agent.invoke({"input": input_text})

# Example usage
if __name__ == "__main__":
    # Async streaming example
    asyncio.run(stream_agent_response("Find all sales people working in Singapore"))

    # Regular query examples
    queries = [
        "Identify companies that are attending finance related events.",
        "Identify companies that are attending banking related events.",
        "Identify companies that are attending Oil & Gas related events.",
        "Find all sales people working in Singapore",
        "Find sales people working for over a year in Singapore.",
        "Find the people working the longest in their current company.",
        "Find me the events happening in the next 6 months.",
        "Find me the events happening in the next 12 months.",
        "Find me the companies that are attending events in the next 3 months.",
        "Find events that already over."
    ]

    for query in queries:
        print(f"\nQuery: {query}")
        result = run_agent_query(query)
        print("Result:", result)
