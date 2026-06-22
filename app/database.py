from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker
import os

# SQLite para desenvolvimento. Para produção, troque pela variável DATABASE_URL.
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./studyai.db")

# connect_args apenas necessário para SQLite (thread safety)
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(DATABASE_URL, connect_args=connect_args)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    """Dependency para injetar sessão do banco nas rotas FastAPI."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
