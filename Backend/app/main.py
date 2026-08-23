import os
from dotenv import load_dotenv

from fastapi import FastAPI
from .db.postgres import connectPostgres
from .db.postgres_models import Base, User

# Getting ENV variables 
load_dotenv()
postgres_connectionURL = os.getenv("DATABASE_URL")
if not postgres_connectionURL:
    raise RuntimeError("DATABASE_URL is not set.")

async def lifespan(app: FastAPI):
    print("Connecting to PostgreSQL...")
    engine, sessionLocal = connectPostgres(postgres_connectionURL)
    Base.metadata.create_all(bind=engine)
    print("PostgreSQL connected.")

    app.state.engine = engine
    app.state.sessionLocal = sessionLocal

    yield

    print("Shutting down...")
    engine.dispose()

app = FastAPI(lifespan=lifespan)

@app.get("/")
async def root():
    return {
        "message": "Backend is running"
    }