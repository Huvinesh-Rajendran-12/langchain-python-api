# tests/test_api.py

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock, MagicMock
import json
import asyncio

# Mock the settings
mock_settings = MagicMock()
mock_settings.ANTHROPIC_LLM_MODEL = "claude-3-5-sonnet-20240620"
mock_settings.ANTHROPIC_LLM_TEMPERATURE = 0
mock_settings.ANTHROPIC_LLM_MAX_TOKENS = 1000
mock_settings.DATABASE_URL = "mock_db_url"

# Patch the settings
@pytest.fixture(autouse=True)
def mock_dependencies():
    with patch('src.config.settings', mock_settings):
        yield

# Now import the app
from src.api.main import app, process_query_with_updates

client = TestClient(app)

def test_query_endpoint_success():
    async def mock_process_query(question):
        yield "Initializing", "Starting to process your query"
        yield "Processing", "Analyzing the query results"
        yield "Finalizing", "Preparing the final answer"

    with patch('src.api.main.sql_agent') as mock_sql_agent:
        mock_sql_agent.process_query = mock_process_query
        mock_sql_agent.get_final_answer = AsyncMock(return_value="This is the final answer")

        response = client.post("/query", json={"question": "Test question"})

        assert response.status_code == 200
        content = response.content.decode().strip().split('\n')
        assert len(content) == 4  # 3 status updates + 1 final answer
        assert json.loads(content[0])["step"] == "Initializing"
        assert json.loads(content[1])["step"] == "Processing"
        assert json.loads(content[2])["step"] == "Finalizing"
        assert json.loads(content[3])["step"] == "Final Answer"

def test_query_endpoint_error():
    async def mock_process_query(question):
        # This generator will not yield any values
        if False:
            yield

    with patch('src.api.main.sql_agent') as mock_sql_agent:
        mock_sql_agent.process_query = mock_process_query
        mock_sql_agent.get_final_answer = AsyncMock(return_value="Error occurred")

        response = client.post("/query", json={"question": "Test question"})

        assert response.status_code == 200
        content = response.content.decode().strip().split('\n')
        assert len(content) == 2  # Final answer + Error message
        assert json.loads(content[0])["step"] == "Final Answer"
        assert json.loads(content[0])["message"] == "Error occurred"
        assert json.loads(content[1])["step"] == "Error"
        assert json.loads(content[1])["message"] == "No updates received from the SQL agent"

def test_query_endpoint_invalid_input():
    response = client.post("/query", json={})
    assert response.status_code == 422  # Unprocessable Entity

@pytest.mark.asyncio
async def test_process_query_with_updates():
    async def mock_process_query(question):
        yield "Initializing", "Starting to process your query"
        yield "Processing", "Analyzing the query results"
        yield "Finalizing", "Preparing the final answer"

    with patch('src.api.main.sql_agent') as mock_sql_agent:
        mock_sql_agent.process_query = mock_process_query
        mock_sql_agent.get_final_answer = AsyncMock(return_value="This is the final answer")

        updates = [update async for update in process_query_with_updates("Test question")]

        assert len(updates) == 4  # 3 status updates + 1 final answer
        assert all(isinstance(update, str) for update in updates)
        assert json.loads(updates[0].strip())["step"] == "Initializing"
        assert json.loads(updates[1].strip())["step"] == "Processing"
        assert json.loads(updates[2].strip())["step"] == "Finalizing"
        assert json.loads(updates[3].strip())["step"] == "Final Answer"

if __name__ == "__main__":
    pytest.main()
