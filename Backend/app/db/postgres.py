from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

def connectPostgres(connectionString: str):
    engine = create_engine(connectionString)
    sessionLocal =  sessionmaker(
        bind=engine, 
        autocommit=False, autoflush=False
    )
    return engine, sessionLocal
