# ByteGenie Python API

This repository contains the backend API for my ByteGenie FullStack Developer Test application. The API allows users to interact with events, company, and people data through natural language queries.

## 🚀 Technology Stack

- Python 3.9+
- FastAPI
- SQLAlchemy
- PostgreSQL
- Langchain
- Anthropic Claude API

## 🛠️ Installation and Setup

1. **Clone the repository:**

   ```bash
   git clone https://github.com/Huvinesh-Rajendran-12/bytegenie-python-api.git
   cd bytegenie-python-api
   ```

2. **Create and activate a virtual environment:**

   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows, use `venv\Scripts\activate`
   ```

3. **Install dependencies:**

   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables:**
   Create a `.env` file in the root directory with the following content:

   ```env
   DB_USERNAME=bytegenie_user
   DB_PASSWORD=bytegenie_pass
   DB_HOST=localhost
   DB_PORT=5432
   DB_NAME=bytegenie_db
   ANTHROPIC_API_KEY=your-api-key
   ANTHROPIC_LLM_MODEL=claude-3-5-sonnet-20240620
   ANTHROPIC_LLM_TEMPERATURE=0
   ANTHROPIC_LLM_MAX_TOKENS=4096
   API_HOST=0.0.0.0
   API_PORT=8000
   ENABLE_CACHE=true
   TOKENIZERS_PARALLELISM=true
   EMBEDDING_MODEL=mixedbread-ai/mxbai-embed-large-v1
   ```

5. **Initialize the database:**
   Assuming the database is initialized already. If not, please visit the bytegenie-db repository for further instructions.

6. **Run the API:**
   ```bash
   uvicorn src.api.main:app
   ```

The API should now be running on `http://localhost:8000`.

## 🧹 Data Engineering and Processing

Before making the data available to the API, I performed the following steps:

### Data Cleaning and Normalization

> Note: The data analysis and augmentation were handled by GPT4o. Ideally, I would prefer to handle it through Claude 3.5 Sonnet, but it currently cannot handle large datasets.

#### Company Info Data

- Removed special characters from company names
- Filled null values in company_industry
- Standardized n_employees column
- Normalized company_revenue data
- Converted company_founding_year to string format
- Filled missing homepage_url values

#### Event Info Data

- Filled null values in event_end_date, event_venue, and event_description
- Derived event_country from event_venue where missing
- Added event_industry column based on event_name and event_description

#### People Info Data

- Filled null values in location columns with 'Unknown'
- Derived email_address from email_pattern, person's name, and homepage_base_url
- Standardized duration_in_current_job and duration_in_current_company

## 🔍 Main Functionalities

1. Natural language query processing
2. SQL query generation based on user input
3. Data retrieval from the database
4. Response formatting and optimization

## 🏋️ Key Challenges I Faced

During the development of the API, particularly the SQLAgent component, I encountered several significant challenges:

### 1. Choosing the Right AI Model

The selection of an appropriate AI model was crucial for the success of this project. I conducted extensive experiments with various proprietary and open-source AI models to find the best fit for function calling and SQL query generation.

- **Models Tested**:

  - Claude 3.5 Sonnet
  - Command R+
  - GPT4o
  - Mistral 8x22

- **Evaluation Criteria**:

  - Accuracy in understanding natural language queries
  - Ability to generate correct SQL queries
  - Handling of complex and ambiguous requests
  - Performance with large datasets

- **Outcome**: After rigorous testing, Claude 3.5 Sonnet emerged as the most capable model for handling sophisticated and complex tasks in our specific use case.

### 2. Addressing Hallucinations

Even with advanced models like Claude 3.5 Sonnet, hallucinations posed a significant challenge in the early stages of development.

- **Problem**: The model would sometimes generate incorrect or non-existent information, especially for ambiguous queries.

- **Solution**:

  1. Engineered a well-defined prompt to restrict hallucinations and focus the model on the given tasks.
  2. Developed custom tools (e.g., search_country) to provide verified information to the model.
  3. Implemented strict validation of model outputs against the actual database schema and content.

- **Outcome**: Significantly reduced hallucinations, improving the reliability and accuracy of the API responses.

### 3. Generating Correct SQL Queries for Complex User Requests

Translating natural language into accurate and efficient SQL queries, especially for complex requests, was a major hurdle.

- **Challenges**:

  - Handling multi-table joins
  - Correctly interpreting user intent for ambiguous queries
  - Generating optimized queries for large datasets

- **Solution**:

  1. Created a comprehensive set of example SQL queries paired with natural language inputs.
  2. Implemented a vector database (FAISS) to store and quickly retrieve relevant query examples.
  3. Developed a system where the model uses retrieved similar queries as a reference for generating new queries.

- **Outcome**: Improved accuracy and consistency in SQL query generation, even for complex and unusual requests.

### 4. Optimizing Response Times for Large Datasets

Balancing query accuracy with performance, especially for large datasets, required significant optimization efforts.

- **Challenges**:

  - Long processing times for complex queries
  - High memory usage when dealing with large result sets
  - Maintaining responsiveness under varying load conditions

- **Solutions**:

  1. Implemented an efficient caching strategy to balance data freshness with quick responses.
  2. Developed a tiered approach to handle queries of varying complexity.

- **Outcome**: Significantly improved response times while maintaining the ability to handle complex queries on large datasets. But, in some cases the response time is still quite slow.

### 5. Balancing Accuracy with Response Time

Finding the right trade-off between the accuracy of natural language understanding, query generation, and the speed of response was a constant challenge.

- **Challenges**:

  - Longer processing times for more accurate results
  - User expectation for quick responses
  - Varying complexity of user queries

- **Solutions**:

  1. Implemented a multi-tiered approach to handle queries of different complexities.
  2. Optimized the AI model's performance through prompt engineering.

- **Outcome**: Achieved a balance between accuracy and speed, providing quick responses for simple queries while maintaining the capability to handle complex requests accurately.

These challenges required a combination of creative problem-solving, advanced natural language processing techniques, efficient database design, and a deep understanding of the domain. Overcoming them involved continuous testing, refinement, and learning from real-world usage patterns and edge cases encountered during development.

## 🚀 Future Improvements

1. Implement multi-turn conversation capabilities
2. Explore the 'astream_events' v2 of the API to further include streaming tokens from particular events such as 'on_chat_model_stream' to improve the response time. Currently the response time is too slow.
3. Enhance query caching for faster response times
4. Add more sophisticated error handling and query validation
5. Develop a feedback loop to improve natural language understanding
6. Further optimize database queries using advanced indexing techniques
7. Implement rate limiting and authentication for production use
8. Add support for more complex queries involving multiple data sources
9. Develop a comprehensive test suite for all API endpoints and edge cases
