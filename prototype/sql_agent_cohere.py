import os
from sqlalchemy import create_engine
from dotenv import load_dotenv
from langchain_community.utilities import SQLDatabase
from langchain_core.prompts import (
    ChatPromptTemplate,
    FewShotPromptTemplate,
    MessagesPlaceholder,
    PromptTemplate,
    SystemMessagePromptTemplate,
)
from langchain_cohere import ChatCohere
from langchain_community.agent_toolkits import create_sql_agent
import pprint

# Load environment variables
load_dotenv()

cohere_api_key = os.getenv("COHERE_API_KEY")
print(cohere_api_key)

db_username = os.getenv("DB_USERNAME")
db_password = os.getenv("DB_PASSWORD")
db_host = os.getenv("DB_HOST")
db_port = os.getenv("DB_PORT")
db_name = os.getenv("DB_NAME")

db_url = f"postgresql://{db_username}:{db_password}@{db_host}:{db_port}/{db_name}"

db = SQLDatabase.from_uri(db_url)

llm = ChatCohere(model="command-r-plus", cohere_api_key=cohere_api_key)

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


CREATE TABLE event_company (
	company_logo_url TEXT,
	company_logo_text TEXT,
	company_name TEXT,
	relation_to_event TEXT,
	event_url TEXT,
	company_revenue TEXT,
	n_employees TEXT,
	company_phone TEXT,
	company_founding_year DOUBLE PRECISION,
	company_address TEXT,
	company_industry TEXT,
	company_overview TEXT,
	homepage_url TEXT,
	linkedin_company_url TEXT,
	homepage_base_url TEXT,
	company_logo_url_on_event_page TEXT,
	company_logo_match_flag TEXT,
	event_logo_url TEXT,
	event_name TEXT,
	event_start_date TEXT,
	event_end_date TEXT,
	event_venue TEXT,
	event_country TEXT,
	event_description TEXT,
	event_industry TEXT
)

/*
3 rows from event_company table:
company_logo_url	company_logo_text	company_name	relation_to_event	event_url	company_revenue	n_employees	company_phone	company_founding_year	company_address	company_industry	company_overview	homepage_url	linkedin_company_url	homepage_base_url	company_logo_url_on_event_page	company_logo_match_flag	event_logo_url	event_name	event_start_date	event_end_date	event_venue	event_country	event_description	event_industry
https://d1hbpr09pwz0sk.cloudfront.net/logo_url/100-women-in-finance-6a062f47	Women in Finance	100 Women In Finance	partner	https://apac.commoditytradingweek.com/	None	11-50	None	2001.0	None	Financial Services	100 Women in Finance strengthens the global finance industry by empowering women to achieve their pr	https://100women.org/events/	https://www.linkedin.com/company/100-women-in-finance/about	100women.org	https://apac.commoditytradingweek.com/wp-content/uploads/2022/03/100wif_web-1.png	yes	https://apac.commoditytradingweek.com/wp-content/uploads/2024/02/cropped-ctw-apac-main-2.png	Commodity Trading Week APAC	2025-02-25	2025-02-26	Marina Bay Sands	None	Commodity Trading Week APAC is the premier event in the Asia Pacific region for the commodity indust	Finance
https://media.licdn.com/dms/image/C4D0BAQHlTYAmrCwYOw/company-logo_200_200/0/1671349864369/bbgc_serv	BBGC	BBGC	sponsor	https://apac.commoditytradingweek.com/	None	51-200	None	None	None	IT Services and IT Consulting	Business Benefits Global Consulting (BBGC) is a multinational consultancy firm with offices in Middl	www.bbgcservices.com	https://it.linkedin.com/company/bbgcservices/about	bbgcservices.com	https://apac.commoditytradingweek.com/wp-content/uploads/2022/03/BBGC_WEB_logo-1.png	yes	https://apac.commoditytradingweek.com/wp-content/uploads/2024/02/cropped-ctw-apac-main-2.png	Commodity Trading Week APAC	2025-02-25	2025-02-26	Marina Bay Sands	None	Commodity Trading Week APAC is the premier event in the Asia Pacific region for the commodity indust	Finance
https://d1hbpr09pwz0sk.cloudfront.net/logo_url/hr-maritime-c13714f3	HR MARITIME	HR Maritime	partner	https://apac.commoditytradingweek.com/	$2 million	2-10	+41 22 732 57 00	2008.0	1-3 Rue De Chantepoulet, Geneva, Geneva 1201, CH	Maritime Transportation	HR Maritime is a Geneva based company providing services to the International Trading and Shipping i	http://www.hr-maritime.com	https://ch.linkedin.com/company/hr-maritime/about	hr-maritime.com	https://apac.commoditytradingweek.com/wp-content/uploads/2022/03/HR_logo-2.png	yes	https://apac.commoditytradingweek.com/wp-content/uploads/2024/02/cropped-ctw-apac-main-2.png	Commodity Trading Week APAC	2025-02-25	2025-02-26	Marina Bay Sands	None	Commodity Trading Week APAC is the premier event in the Asia Pacific region for the commodity indust	Finance
*/


CREATE TABLE people_company (
	first_name TEXT,
	middle_name TEXT,
	last_name TEXT,
	job_title TEXT,
	person_city TEXT,
	person_state TEXT,
	person_country TEXT,
	email_pattern TEXT,
	homepage_base_url TEXT,
	duration_in_current_job TEXT,
	duration_in_current_company TEXT,
	company_logo_url TEXT,
	company_logo_text TEXT,
	company_name TEXT,
	relation_to_event TEXT,
	event_url TEXT,
	company_revenue TEXT,
	n_employees TEXT,
	company_phone TEXT,
	company_founding_year DOUBLE PRECISION,
	company_address TEXT,
	company_industry TEXT,
	company_overview TEXT,
	homepage_url TEXT,
	linkedin_company_url TEXT,
	company_logo_url_on_event_page TEXT,
	company_logo_match_flag TEXT,
	email_address TEXT
)

/*
3 rows from people_company table:
first_name	middle_name	last_name	job_title	person_city	person_state	person_country	email_pattern	homepage_base_url	duration_in_current_job	duration_in_current_company	company_logo_url	company_logo_text	company_name	relation_to_event	event_url	company_revenue	n_employees	company_phone	company_founding_year	company_address	company_industry	company_overview	homepage_url	linkedin_company_url	company_logo_url_on_event_page	company_logo_match_flag	email_address
Cynthia	None	Battini	Indirect Buyer	None	None	France	None	ariane.group	None	None	https://d1hbpr09pwz0sk.cloudfront.net/logo_url/arianegroup-6d9a19a5	arianespace	ArianeGroup	sponsor	https://www.space.org.sg/gstc/	$4.38 billion	5,001-10,000 employees	+33 5 57 20 86 25	2015.0	51-61 Route de Verneuil, Les Mureaux, Île-de-France 78130, FR	Aviation and Aerospace Component Manufacturing	With roots reaching back more than 70 years into the history of space activity in Europe, ArianeGrou	http://www.ariane.group	https://www.linkedin.com/company/arianegroup/about	https://www.space.org.sg/gstc/wp-content/uploads/2022/12/Arianespace-300x300.png	yes	None
Alexander	None	McClure	Public Relations	Austin	TX	US	None	amazon.com	None	None	https://d1hbpr09pwz0sk.cloudfront.net/logo_url/amazon-b6f77c2b	G8	Amazon Web Services (AWS)	sponsor	https://www.terrapinn.com/conference/submarine-networks-world/index.stm	$280.52 billion	10,001+	(206) 266-1000	2006.0	2127 7th Ave., Seattle, Washington 98109, US	IT Services and IT Consulting	Launched in 2006, Amazon Web Services (AWS) began exposing key infrastructure services to businesses	http://aws.amazon.com	https://www.linkedin.com/company/amazon-web-services/about	https://terrapinn-cdn.com/tres/pa-images/10817/a0AN2000001GQFhMAO_org.png?20231018033746	yes	None
Alexander	None	McClure	Public Relations	Austin	TX	US	None	amazon.com	None	None	https://d1hbpr09pwz0sk.cloudfront.net/logo_url/amazon-b6f77c2b	4	Amazon Web Services (AWS)	speaker	https://www.cloudexpoasia.com/	$280.52 billion	10,001+	(206) 266-1000	2006.0	2127 7th Ave., Seattle, Washington 98109, US	IT Services and IT Consulting	Launched in 2006, Amazon Web Services (AWS) began exposing key infrastructure services to businesses	http://aws.amazon.com	https://www.linkedin.com/company/amazon-web-services/about	https://taskfilescsm.s3.amazonaws.com:443/uploads/speaker_thumb/2023-09-2011%253A08%253A44120429-Jag	yes	None
*/
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

# Example usage
chunks = []

async for chunk in agent.astream(
    {"input": "Find all sales people working in Singapore"}
):
    chunks.append(chunk)
    print("------")
    pprint.pprint(chunk, depth=5)

# More example queries
print(
    agent.invoke(
        {"input": "Identify companies that are attending finance related events."}
    )
)
print(
    agent.invoke(
        {"input": "Identify companies that are attending banking related events."}
    )
)
print(
    agent.invoke(
        {"input": "Identify companies that are attending Oil & Gas related events."}
    )
)
print(agent.invoke({"input": "Find all sales people working in Singapore"}))
print(
    agent.invoke({"input": "Find sales people working for over a year in Singapore."})
)
print(
    agent.invoke(
        {"input": "Find the people working the longest in their current company."}
    )
)
print(agent.invoke({"input": "Find me the events happening in the next 6 months."}))
print(agent.invoke({"input": "Find me the events happening in the next 12 months."}))
print(
    agent.invoke(
        {
            "input": "Find me the companies that are attending events in the next 3 months."
        }
    )
)
print(agent.invoke({"input": "Find events that already over."}))
