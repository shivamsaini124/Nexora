import os
from dotenv import load_dotenv

from fastapi import FastAPI
from .db.postgres import connectPostgres
from .db.postgres_models import Base
from .db.qdrant import connectQdrant

# Getting ENV variables 
load_dotenv()

POSTGRES_URL = os.getenv("POSTGRES_URL")
QDRANT_URL = os.getenv("QDRANT_URL")

if not POSTGRES_URL:
    raise RuntimeError("POSTGRES_URL is not set.")
if not QDRANT_URL:
    raise RuntimeError("QDRANT_URL is not set.")


# Define lifespan of fastapi app (basically what runs before starting the app and what runs after closing the app)
async def lifespan(app: FastAPI):
    print("Connecting to PostgreSQL...")
    # Connecting to postgres and initializing the tables if not done already (it does not automatically recreate tables if schema is changed)
    engine, sessionLocal = connectPostgres(POSTGRES_URL)
    Base.metadata.create_all(bind=engine)
    print("PostgreSQL connected.")

    print("Connecting to Qdrant...")
    # Connecting to Qdrant and initializing the collections(if not initilized already)
    qdrant = connectQdrant(QDRANT_URL)
    print("Qdrant connected.")

    app.state.engine = engine
    app.state.sessionLocal = sessionLocal
    app.state.qdrant = qdrant

    yield

    print("Shutting down...")
    engine.dispose()
    qdrant.close()

app = FastAPI(lifespan=lifespan)

@app.get("/")
async def root():
    return {
        "message": "Backend is running"
    }