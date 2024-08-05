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
   DATABASE_URL=postgresql://username:password@localhost/bytegenie
   ANTHROPIC_API_KEY=your_anthropic_api_key
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

During the development of the API, I faced the following challenges:

1. Accurately interpreting natural language queries
2. Generating efficient SQL queries for complex user requests
3. Handling edge cases and ambiguous queries
4. Optimizing response times for large datasets
5. Ensuring data consistency across different tables

## Future Improvements

If I had more time, I would improve the backend in the following ways:

1. Implement query caching for faster response times
2. Add more sophisticated error handling and query validation
3. Develop a feedback loop to improve natural language understanding over time
4. Optimize database queries further using advanced indexing techniques
5. Implement rate limiting and authentication for production use
6. Add support for more complex queries involving multiple data sources
7. Develop a comprehensive test suite for all API endpoints and edge cases
