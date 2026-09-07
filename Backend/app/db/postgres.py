from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

class Postgres:
    def __init__(self, connectionString: str, Base):
        self.engine = create_engine(connectionString)
        self.sessionLocal =  sessionmaker(
            bind=self.engine,
            autocommit=False, autoflush=False
        )

        Base.metadata.create_all(bind=self.engine)

    def get_session(self):
        return self.sessionLocal()

    def dispose(self) -> None:
        self.engine.dispose()
