from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import asyncio
import json
from src.sql_agent.model import SQLAgent
from src.config import settings

app = FastAPI()

class Query(BaseModel):
    question: str

class StatusUpdate(BaseModel):
    step: str
    message: str

# Initialize the SQLAgent
sql_agent = SQLAgent()

async def process_query_with_updates(question: str):
    async for step, message in sql_agent.process_query(question):
        status_update = StatusUpdate(step=step, message=message)
        yield json.dumps(status_update.dict()) + "\n"

    # Final answer
    result = await sql_agent.get_final_answer()
    final_update = StatusUpdate(step="Final Answer", message=result)
    yield json.dumps(final_update.dict()) + "\n"

@app.post("/query")
async def query_endpoint(query: Query):
    return StreamingResponse(process_query_with_updates(query.question), media_type="text/event-stream")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=settings.API_HOST, port=settings.API_PORT)
