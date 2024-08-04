import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
from langchain_anthropic import ChatAnthropic
from langchain_community.utilities import SQLDatabase
from langchain_community.agent_toolkits import create_sql_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.cache import InMemoryCache
from langchain.globals import set_llm_cache
from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain.schema import Document
import time
import zlib
import json
from collections import deque

load_dotenv()

# Environment variables
anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")
db_url = f'postgresql://{os.getenv("DB_USERNAME")}:{os.getenv("DB_PASSWORD")}@{os.getenv("DB_HOST")}:{os.getenv("DB_PORT")}/{os.getenv("DB_NAME")}'

# Set up caching
set_llm_cache(InMemoryCache())

# Database connection
db = SQLDatabase.from_uri(db_url)

# LLM setup with lower temperature and caching
llm = ChatAnthropic(
    model="claude-3-5-sonnet-20240620",
    temperature=0,
    api_key=anthropic_api_key,
    cache=True,
    max_tokens_to_sample=1000
)

embeddings = HuggingFaceEmbeddings()

def initialize_vector_stores(db):
    country_vector_store = FAISS.from_texts(
        [row[0] for row in db.run("SELECT DISTINCT person_country FROM people")],
        embeddings
    )
    return country_vector_store

country_vector_store = initialize_vector_stores(db)

# Function to search countries
def search_country(query, top_k=5):
    results = country_vector_store.similarity_search(query, k=top_k)
    return [doc.page_content for doc in results]

# Optimized system prompt
system = """You are a precise SQL expert. Given a question:
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

prompt = ChatPromptTemplate.from_messages([
    ("system", system),
    ("human", "{input}"),
    MessagesPlaceholder("agent_scratchpad")
])

tools = [
    search_country,
]

# Create SQL agent
agent = create_sql_agent(
    llm=llm,
    db=db,
    prompt=prompt,
    agent_type="tool-calling",
    verbose=True,
    additional_tools=tools
)

# Set up vector store for semantic search
embeddings = HuggingFaceEmbeddings()
docs = [Document(page_content=table) for table in db.get_table_names()]
vector_store = FAISS.from_documents(docs, embeddings)

def search_proper_nouns(query):
    results = vector_store.similarity_search(query, k=1)
    return results[0].page_content if results else None

# Client-side caching
query_cache = {}
table_schemas = {
    'company': 'clu,clt,cn,rte,eu,cr,ne,cp,cfy,ca,ci,co,hu,lcu,hbu,clue,clmf,cc',
    'event': 'elu,en,esd,eed,ev,ec,ed,eu,ei',
    'people': 'i,fn,mn,ln,jt,pc,ps,pco,ep,hbu,dcj,dcc,ea,ev,fn,ycj'
}

# Query batching
query_queue = deque()
MAX_BATCH_SIZE = 5
BATCH_TIMEOUT = 60  # seconds

def enqueue_query(query):
    query_queue.append((query, time.time()))

def process_query_batch():
    batch = []
    current_time = time.time()
    while query_queue and len(batch) < MAX_BATCH_SIZE:
        query, enqueue_time = query_queue.popleft()
        if current_time - enqueue_time > BATCH_TIMEOUT:
            continue  # Skip expired queries
        batch.append(query)

    if batch:
        combined_query = " ".join(batch)
        return rate_limited_agent_invoke(combined_query)
    return None

# Compression
def compress_input(input_text):
    return zlib.compress(input_text.encode())

def decompress_output(compressed_output):
    return zlib.decompress(compressed_output).decode()

# Progressive loading
def get_summary_results(full_results, limit=3):
    return full_results[:limit]

# Rate limiting
last_call_time = 0
min_delay = 1  # Minimum delay between API calls in seconds

def rate_limited_agent_invoke(input_text):
    global last_call_time
    current_time = time.time()
    if current_time - last_call_time < min_delay:
        time.sleep(min_delay - (current_time - last_call_time))

    try:
        # Check cache first
        if input_text in query_cache:
            return query_cache[input_text]

        # Compress input
        compressed_input = compress_input(input_text)

        # Make API call
        result = agent.invoke({"input": decompress_output(compressed_input)})
        last_call_time = time.time()

        # Cache result
        query_cache[input_text] = result

        return result
    except Exception as e:
        print(f"Error occurred: {e}")
        return None

# Example usage
user_input = "List the email address for the people working in Singapore for more than a year."
enqueue_query(user_input)
message = process_query_batch()

if message:
    full_results = message['output']
    summary_results = get_summary_results(full_results)
    print("Summary results:", summary_results)
    print("To see full results, request more details.")
else:
    print("Failed to get a response from the agent.")

# Monitoring and analysis
def log_token_usage(query, tokens_in, tokens_out):
    with open('token_usage.log', 'a') as f:
        f.write(f"{time.time()},{query},{tokens_in},{tokens_out}\n")
