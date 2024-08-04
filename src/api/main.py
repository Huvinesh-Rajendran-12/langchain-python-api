# src/api/main.py

from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import json
from src.sql_agent.model import SQLAgent
from typing import Union, List, Dict

app = FastAPI()

class Query(BaseModel):
    question: str

class StatusUpdate(BaseModel):
    step: str
    message: Union[str, List[Dict[str, Union[str, int]]]]

sql_agent = SQLAgent()

async def process_query_with_updates(question: str):
    updates_received = False
    async for step, message in sql_agent.process_query(question):
        updates_received = True
        status_update = StatusUpdate(step=step, message=message)
        yield json.dumps(status_update.model_dump()) + "\n"

    # Final answer
    result = await sql_agent.get_final_answer()
    if isinstance(result, list):
        result = result[0]['text'] if result else "No result"
    final_update = StatusUpdate(step="Final Answer", message=result)
    yield json.dumps(final_update.model_dump()) + "\n"

    # If no updates were received, yield an error message
    if not updates_received:
        error_update = StatusUpdate(step="Error", message="No updates received from the SQL agent")
        yield json.dumps(error_update.model_dump()) + "\n"

@app.post("/query")
async def query_endpoint(query: Query):
    return StreamingResponse(process_query_with_updates(query.question), media_type="text/event-stream")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
