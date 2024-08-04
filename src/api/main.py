from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import AsyncGenerator
import json
from src.sql_agent.model import SQLAgent

app = FastAPI()

origins = [
    "http://localhost:3000",  # React default port
    "http://localhost:8000",  # Another common development port
    "https://yourdomain.com",  # Your production domain
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class Query(BaseModel):
    question: str


async def process_query_with_updates(question: str) -> AsyncGenerator[str, None]:
    agent = SQLAgent()

    try:
        async for step, message in agent.process_query(question):
            yield json.dumps({"step": step, "message": message}) + "\n"

        final_answer = await agent.get_final_answer()
        yield json.dumps({"step": "Final Answer", "message": final_answer}) + "\n"
    except Exception as e:
        yield json.dumps({"step": "Error", "message": str(e)}) + "\n"


@app.post("/query")
async def query_endpoint(query: Query):
    return StreamingResponse(
        process_query_with_updates(query.question), media_type="text/event-stream"
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
