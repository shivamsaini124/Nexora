from sqlalchemy import create_engine
from sqlalchemy.orm import Session

def connectPostgres(connectionString):
    engine = create_engine(connectionString)
    return Session(engine, autocommit=False, autoflush=False)
