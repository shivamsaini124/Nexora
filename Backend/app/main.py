import os
from dotenv import load_dotenv

from fastapi import FastAPI
from .db.postgres import connectPostgres

load_dotenv()

app = FastAPI()
postgres_connectionURL = os.getenv("DATABASE_URL")
postgres_session = connectPostgres(postgres_connectionURL)

@app.get("/")
async def root():
    return {
        "message": "Backend is running"
    }

