import os
from typing import List, Dict
from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict

# Load environment variables from .env file
load_dotenv()


class Settings(BaseSettings):
    # Database settings
    DB_USERNAME: str = os.getenv("DB_USERNAME", "default_user")
    DB_PASSWORD: str = os.getenv("DB_PASSWORD", "default_password")
    DB_HOST: str = os.getenv("DB_HOST", "localhost")
    DB_PORT: str = os.getenv("DB_PORT", "5432")
    DB_NAME: str = os.getenv("DB_NAME", "default_db")

    # API settings
    API_HOST: str = os.getenv("API_HOST", "0.0.0.0")
    API_PORT: int = int(os.getenv("API_PORT", "8000"))

    # LLM settings
    ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY")
    ANTHROPIC_LLM_MODEL: str = os.getenv(
        "ANTHROPIC_LLM_MODEL", "claude-3-5-sonnet-20240620"
    )
    ANTHROPIC_LLM_TEMPERATURE: float = float(
        os.getenv("ANTHROPIC_LLM_TEMPERATURE", "0")
    )
    ANTHROPIC_LLM_MAX_TOKENS: int = int(os.getenv("ANTHROPIC_LLM_MAX_TOKENS", "1000"))

    # Embedding Model settings
    EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "")

    # Caching settings
    ENABLE_CACHE: bool = os.getenv("ENABLE_CACHE", "True").lower() == "true"

    # Examples settings
    EXAMPLES: List[Dict] = [
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
        {
            "input": "Find me companies that are attending finance related events.",
            "query": """
            SELECT DISTINCT e.event_name, e.event_start_date, e.event_industry, c.company_name
            FROM event e
            JOIN company c ON e.event_url = c.event_url
            WHERE LOWER(e.event_industry) LIKE '%finance%' OR LOWER(e.event_industry) LIKE '%banking%'
            ORDER BY e.event_start_date
            LIMIT 10
            """,
        },
        {
            "input": "which company has the highest headcount ?",
            "query": """
            SELECT company_name, n_employees
            FROM company
            WHERE n_employees IS NOT NULL
            ORDER BY n_employees DESC
            LIMIT 1
            """,
        },
        {
            "input": "",
            "query": """
            SELECT AVG(company_revenue) as avg_revenue
            FROM company
            WHERE LOWER(company_industry) LIKE '%financial%' OR LOWER(company_industry) LIKE '%finance%'
            """,
        },
        {
            "input": "Find me the events that are being attended by technology companies.",
            "query": """
            SELECT DISTINCT e.event_name, e.event_start_date, e.event_industry, c.company_name
            FROM event e
            JOIN company c ON e.event_url = c.event_url
            WHERE LOWER(c.company_industry) LIKE '%technology%'
            ORDER BY e.event_start_date
            LIMIT 10
            """,
        },
        {
            "input": "find me the email address of people who are working in Singapore for more than a year.",
            "query": """
            SELECT email_address, first_name, last_name, job_title, years_in_current_job
            FROM people
            WHERE person_country = 'Singapore'
              AND years_in_current_job >= 1
            ORDER BY years_in_current_job DESC
            LIMIT 10
            """,
        },
        {
            "input": "Find me the information about 3 companies for each event being held in the next 3 months.",
            "query": """
            WITH ranked_companies AS (
              SELECT
                e.event_name,
                e.event_start_date,
                e.event_industry,
                c.company_name,
                ROW_NUMBER() OVER (PARTITION BY e.event_name ORDER BY c.company_name) AS company_rank
              FROM
                event e
              JOIN
                company c ON e.event_url = c.event_url
              WHERE
                CAST(e.event_start_date AS DATE) BETWEEN CURRENT_DATE AND CURRENT_DATE + INTERVAL '3 months'
            )
            SELECT
              event_name,
              event_start_date,
              event_industry,
              company_name
            FROM
              ranked_companies
            WHERE
              company_rank <= 3
            ORDER BY
              CAST(event_start_date AS DATE), event_name, company_rank
            LIMIT 30
            """,
        },
        {
            "input": "Find me the companies attending finance related events in 2025.",
            "query": """
            SELECT DISTINCT c.company_name, e.event_name, e.event_start_date, e.event_industry
            FROM event e
            JOIN company c ON e.event_url = c.event_url
            WHERE (LOWER(e.event_industry) LIKE '%finance%' OR LOWER(e.event_industry) LIKE '%banking%')
              AND SUBSTRING(e.event_start_date, 1, 4) = '2025'
            ORDER BY e.event_start_date
            LIMIT 10
            """,
        },
    ]

    @property
    def SYSTEM_PROMPT(self) -> str:
        return """You are a precise SQL expert with advanced context awareness. Given a question:
        1. ALWAYS USE the query_decider tool to determine if a new query is needed or if existing context can answer the question.
        The return value of the tool would be either 'generate_new_query' or 'use_existing_content'.
        2. If the return value is 'generate_new_query':
            a. Create an efficient {dialect} query using only these tables: {table_names}
            b. Execute the query and analyze results
            c. Provide a concise, informative answer to the user
        3. If the return value is 'use_existing_content':
            a. DO NOT create or execute new SQL queries
            b. Use the context from previous questions and answers to respond
            c. If you need more information that's not in the context, politely ask the user for clarification
        4. Use the context_manager tool when you need to retrieve or update conversation context
        5. When presenting query results:
           a. For multiple rows with numerous columns, generate a beautiful HTML table using the following template:
              <div class="overflow-x-auto bg-gradient-to-br from-blue-900 to-teal-800 rounded-lg shadow-xl p-4">
                <table class="w-full border-collapse">
                  <thead>
                    <tr class="bg-gradient-to-r from-blue-700 to-teal-600 text-white">
                      <th class="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider border-b border-blue-500">Column 1</th>
                      <th class="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider border-b border-blue-500">Column 2</th>
                      <!-- Add more <th> elements as needed -->
                    </tr>
                  </thead>
                  <tbody class="divide-y divide-blue-500">
                    <tr class="bg-gradient-to-r from-blue-800 to-teal-700 hover:from-blue-700 hover:to-teal-600 transition-all duration-200">
                      <td class="px-4 py-3 text-sm text-white">Data 1</td>
                      <td class="px-4 py-3 text-sm text-white">Data 2</td>
                      <!-- Add more <td> elements as needed -->
                    </tr>
                    <!-- Repeat the <tr> structure for each row of data -->
                  </tbody>
                </table>
              </div>
           b. Ensure the table headers match the query result columns
           c. Populate the table rows with the ALL OF THE query results, DO NOT MISS ANYTHING
           d. Include detailed information and key insights about the generated table.
           d. For simpler results or text responses, format the information as follows:
                         <div class="space-y-4 text-white">
                           <p class="text-lg font-semibold">Key Findings:</p>
                           <ul class="list-disc pl-5 space-y-2">
                             <li>Point 1</li>
                             <li>Point 2</li>
                             <!-- Add more list items as needed -->
                           </ul>
                           <p class="text-lg font-semibold mt-4">Additional Information:</p>
                           <p class="pl-5">Explanatory text goes here.</p>
                           <!-- Repeat the above structure for different sections as needed -->
                         </div>
        6. After presenting the table, provide a brief summary or insights about the data
        IMPORTANT GUIDELINES:
        - NEVER include SQL queries in your final answer to the user under any circumstances
        - For initial questions, use indexes and avoid full table scans
        - Limit initial query results to 10 rows unless specified otherwise
        - No DML statements allowed
        - For proper noun filters, use the search_proper_nouns tool
        - Join tables using: event_url for event & company, homepage_base_url for company & people
        - For country-related queries, only use values from the search_country tool
        - If a query is unrelated to the database, briefly explain why
        - Prioritize clarity and brevity in your responses
        - Include only detailed essential information and key insights
        - Use bullet points for multiple items
        - If it's necessary offer to provide more details otherwise DO NOT
        Use the following examples as a guide:
        {examples}
        """

    @property
    def DATABASE_URL(self) -> str:
        return f"postgresql://{self.DB_USERNAME}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )


# Create a global instance of the settings
settings = Settings()
