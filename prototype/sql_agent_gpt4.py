import os
from dotenv import load_dotenv
from langchain_community.utilities import SQLDatabase
from langchain_core.prompts import (
    ChatPromptTemplate,
    MessagesPlaceholder,
)
from langchain_community.agent_toolkits import create_sql_agent
from langchain_openai import ChatOpenAI
import ast
import re

# Load environment variables
load_dotenv()

# Get the database credentials from environment variables
db_username = os.getenv('DB_USERNAME')
db_password = os.getenv('DB_PASSWORD')
db_host = os.getenv('DB_HOST')
db_port = os.getenv('DB_PORT')
db_name = os.getenv('DB_NAME')

# Create database connection
db_url = f'postgresql://{db_username}:{db_password}@{db_host}:{db_port}/{db_name}'
db = SQLDatabase.from_uri(db_url)

# Set up OpenAI API
openai_api_key = os.getenv("OPENAI_API_KEY")
print(openai_api_key)

# Create language model
llm = ChatOpenAI(model="gpt-4o-mini", temperature=0, api_key=openai_api_key)

# Get database context
context = db.get_context()
print(context["table_info"])

def query_as_list(db, query):
    res = db.run(query)
    res = [el for sub in ast.literal_eval(res) for el in sub if el]
    res = [re.sub(r"\b\d+\b", "", string).strip() for string in res]
    return list(set(res))

# Define system prompt
system = """You are an agent designed to interact with a SQL database.
Given an input question, create a syntactically correct {dialect} query to run, then look at the results of the query and return the answer.
Try more advacned queries if the normal query does not result in any responses.
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

event and company tables can be merged using 'event_url' column.
company and people data can be merged using 'homepage_base_url' column.
Each event_url corresponds to a unique event, and each homepage_base_url can
be interpreted as a unique company.
 """

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

# Example usage of the agent
print(agent.invoke({"input": "Find all sales people working in Singapore"}))
print(agent.invoke({"input": "Identify companies that are attending finance related events."}))
print(agent.invoke({"input": "Identify companies that are attending banking related events."}))
print(agent.invoke({"input": "Identify companies that are attending Oil & Gas related events."}))
print(agent.invoke({"input": "Find sales people working for over a year in Singapore."}))
print(agent.invoke({"input": "Find the people working the longest in their current company."}))
print(agent.invoke({"input": "Find me the events happening in the next 6 months."}))
print(agent.invoke({"input": "Find me the events happening in the next 12 months."}))
print(agent.invoke({"input": "Find me the companies that are attending events in the next 3 months."}))
print(agent.invoke({"input": "Find events that already over."}))

# Async example (uncomment to use)
# async def run_async_query():
#     chunks = []
#     async for chunk in agent.astream(
#         {"input": "Find all sales people working in Singapore"}
#     ):
#         chunks.append(chunk)
#         print("------")
#         pprint.pprint(chunk, depth=5)
#
# import asyncio
# asyncio.run(run_async_query())
