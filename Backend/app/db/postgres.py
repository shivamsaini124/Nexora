from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# import os
# from dotenv import load_dotenv
# load_dotenv()
# connectionString = os.getenv("DATABASE_URL")

def connectPostgres(connectionString):
    engine = create_engine(connectionString)
    sessionLocal =  sessionmaker(
        bind=engine, 
        autocommit=False, autoflush=False
    )
    return engine, sessionLocal
