import os
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

RAW_DSN = os.getenv(
    "URBAN_LENS_POSTGRES_DSN", 
    "postgresql://admin:senha_segura_db@localhost:5433/urban_lens"
)
POSTGRES_DSN = RAW_DSN.replace("postgresql://", "postgresql+psycopg://")

engine = create_engine(POSTGRES_DSN)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()