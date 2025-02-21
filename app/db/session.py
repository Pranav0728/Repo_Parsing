# app/db/session.py
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Replace this with your actual database URL (e.g., PostgreSQL, MySQL, etc.)
SQLALCHEMY_DATABASE_URL = "postgresql://postgres:12345@localhost:5432/momentum"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
