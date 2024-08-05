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
   git clone https://github.com/your-username/bytegenie-api.git
   cd bytegenie-api
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
   export DB_NAME=bytegenie2
   export ANTHROPIC_API_KEY=your_anthropic_api_key
   ```

5. Initialize the database:

   ```
   python scripts/init_db.py
   ```

6. Run the API:
   ```
   uvicorn src.main:app --reload
   ```

The API should now be running on `http://localhost:8000`.

> > > > > > > 1d58fb0 (updated README.md file, added context-awareness)

## Data Engineering and Processing

Before making the data available to the API, I performed the following steps:

1. Data cleaning and normalization
2. Index creation for frequently queried columns
3. Derived additional columns using LLM for enhanced querying capabilities:
   - Tagged events with industries based on event name and description
   - Created standardized email addresses for people based on email patterns and names
4. Standardized columns like company_industry, company_revenue, and number of employees for consistent querying

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
Handling domain-specific jargon and acronyms required extensive training data and fine-tuning of the language model.
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

#### Handling data privacy and security concerns:

Implementing measures to prevent SQL injection and other security vulnerabilities without limiting the flexibility of the query system was challenging.
Ensuring that sensitive data was not inadvertently exposed through query results or error messages required careful consideration of data access patterns.

## Future Improvements

If I had more time, I would improve the backend in the following ways:

1. Implement query caching for faster response times
2. Add more sophisticated error handling and query validation
3. Develop a feedback loop to improve natural language understanding over time
4. Optimize database queries further using advanced indexing techniques
5. Implement rate limiting and authentication for production use
6. Add support for more complex queries involving multiple data sources
7. Develop a comprehensive test suite for all API endpoints and edge cases
