# ByteGenie Python API

This repository contains the backend API for my ByteGenie FullStack Developer Test application. The API allows users to interact with events, company, and people data through natural language queries.

## Technology Stack

- Python 3.9+
- FastAPI
- SQLAlchemy
- PostgreSQL
- Langchain
- Anthropic Claude API

## Installation and Setup

1. Clone the repository:

   ```
   git clone https://github.com/Huvinesh-Rajendran-12/bytegenie-python-api.git
   cd bytegenie-python-api
   ```

2. Create and activate a virtual environment:

   ```
   python -m venv venv
   source venv/bin/activate  # On Windows, use `venv\Scripts\activate`
   ```

3. Install dependencies:

   ```
   pip install -r requirements.txt
   ```

4. Set up environment variables:
   Create a `.env` file in the root directory and add the following:

   ```
   export DB_USERNAME=bytegenie_user
   export DB_PASSWORD=bytegenie_pass
   export DB_HOST=localhost
   export DB_PORT=5432
   export DB_NAME=bytegenie_db
   export ANTHROPIC_API_KEY=your-api-key
   export ANTHROPIC_LLM_MODEL=claude-3-5-sonnet-20240620
   export ANTHROPIC_LLM_TEMPERATURE=0
   export ANTHROPIC_LLM_MAX_TOKENS=4096
   export API_HOST=0.0.0.0
   export API_PORT=8000
   export ENABLE_CACHE=true
   export TOKENIZERS_PARALLELISM=true
   export EMBEDDING_MODEL=mixedbread-ai/mxbai-embed-large-v1
   ```

5. Initialize the database:
   Assuming database is intialized already, if not please visit the bytegenie-db repository for further instructions.

6. Run the API:
   ```
   uvicorn src.api.main:app
   ```

The API should now be running on `http://localhost:8000`.

## Data Engineering and Processing

Before making the data available to the API, I performed the following steps:

### Data cleaning and normalization

Note : The data analysis and augmentation were handled by GPT4o. In an ideal world, I would prefer to handle it through Claude 3.5 Sonnet but as of now it cannot handle large datasets.

#### company_info data

1. Any special characters from the company_name column was removed. Row 595 with company_name #XcelerAI was cleaned to be just XcelerAI.
2. The null values in company_industry were filled by analysing the company_name and company_overview columns but even then there were some additonal rows that couldn't be filled, those were filled with 'Unknown' value.
3. Then the n_employees column were standardized to use a range of numbers. Any additonal wordings such as 'employees' were found and removed. The single value rows were also converted to any standard range of numbers. The empty values were filled with 'Unknown' value.
4. The company_revenue data was standardized to be only in million dollar value, because there were some rows with billion dollar value which was converted to be reflected in millions. The empty rows are filled with 'Unknown' value.
5. The company_founding_year was converted into a string instead of floating values, and the values were converted to reflect integer values, and the missing rows were filled with 'Unknown' value.
6. The homepage_url was filled by analysing the homepage_base_url.
7. The rest of the missing values in this dataset was filled with 'Unknown' value.

### event_info data

1. The null values in the event_end_date column (only 2 null-values) were filled by me visiting the event url and finding those event end dates.
2. The null values in the event_venue column (only 3 null-values) were filled by me visiting the event url and finding the event venues.
3. The null value in the event_description column (only 1 null-value) were filled by me asking Perplexity.ai about the event information and description.
4. The null values in the event_country column (22 null-values) were filled by analysing the event_venue column.
5. Finally, derived an additional column called event_industry based on event_name and event_description columns.
6. There are no null values remaining.

### people_info data

1. This dataset was the hardest to engineer and augment.
2. The null values in person_city, person_state, and person_country columns were filled with 'Unknown' value.
3. The null values in email_pattern were filled with 'Unknown' values.
4. An additional column was derived from email_pattern called email_address by analysing the person's name, email_pattern and homepage_base_url.
5. Finally, the duration_in_current_job was standardized and any redundant value which was also present in duration_in_current_job was removed. The null values in both of these columns were filled with 'Unknown' value.

## Main Functionalities

The API provides the following key functionalities:

1. Natural language query processing
2. SQL query generation based on user input
3. Data retrieval from the database
4. Response formatting and optimization

## Key Challenges I Faced

During the development of the API, particularly the SQLAgent component, I encountered several significant challenges:

#### Accurately interpreting natural language queries:

Dealing with ambiguity in user queries was a major hurdle. For example, a query like "Find recent events" could be interpreted in multiple ways (e.g., last week, last month, or last year).
Maintaining context across multi-turn conversations proved complex, especially when users referred to previous queries or results.

#### Generating efficient SQL queries for complex user requests:

Translating natural language into optimized SQL queries was challenging, especially for complex requests involving multiple joins, subqueries, or aggregations.
Ensuring that generated queries were efficient and didn't overload the database required careful consideration of query plans and index usage.
Handling edge cases, such as queries that could potentially return very large result sets, needed special attention to prevent performance issues.

#### Handling edge cases and ambiguous queries:

Dealing with queries that had no clear SQL equivalent or required data not present in the database was challenging.
Providing meaningful responses to overly broad or vague queries while still offering useful information was a delicate balance.
Implementing fallback mechanisms for when the primary query generation failed, without compromising the quality of results.

#### Optimizing response times for large datasets:

Implementing efficient caching strategies that balanced fresh data with quick responses was complex.
Optimizing database queries and result processing for datasets with millions of records required careful tuning and indexing strategies.
Managing memory efficiently, especially when dealing with large result sets that needed to be processed before returning to the user.

#### Ensuring data consistency across different tables:

Maintaining referential integrity across the events, companies, and people tables, especially with derived data, was challenging.
Implementing strategies to handle inconsistencies in the source data without breaking the system or producing incorrect results required careful error handling and data cleaning processes.

#### Implementing effective context management for multi-turn conversations:

Designing a system that could effectively store and retrieve relevant context from previous queries in a conversation was complex.
Balancing the amount of context to retain versus the computational and storage overhead it introduced required careful consideration.
Determining when to use context and when to treat a query as a new conversation added another layer of complexity.

#### Balancing accuracy with response time:

Finding the right trade-off between the accuracy of natural language understanding and query generation, and the speed of response was a constant challenge.
Implementing a system that could provide quick responses for simple queries while still being capable of handling complex requests required a multi-tiered approach.

## Future Improvements

If I had more time, I would improve the backend in the following ways:

1. Implement query caching for faster response times
2. Add more sophisticated error handling and query validation
3. Develop a feedback loop to improve natural language understanding over time
4. Optimize database queries further using advanced indexing techniques
5. Implement rate limiting and authentication for production use
6. Add support for more complex queries involving multiple data sources
7. Develop a comprehensive test suite for all API endpoints and edge cases
