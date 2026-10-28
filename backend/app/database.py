
import os

from sqlalchemy import URL, create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.core.config import BACKEND_DIR

# Load database settings from backend/.env.
# config.py already loads this file; these lookups read its values.
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", "3306"))
DB_NAME = os.getenv("DB_NAME", "customer_support_ai")
DB_USER = os.getenv("DB_USER", "root")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")

# Build the connection URL safely.
# URL.create handles special characters in passwords.
DATABASE_URL = URL.create(
    drivername="mysql+pymysql",
    username=DB_USER,
    password=DB_PASSWORD,
    host=DB_HOST,
    port=DB_PORT,
    database=DB_NAME,
    query={"charset": "utf8mb4"},
)

# Create the SQLAlchemy engine.
# pool_pre_ping checks connections before reusing them.
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
)

# Each request can create its own database session.
SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    expire_on_commit=False,
)


# Base class for all our database models.
class Base(DeclarativeBase):
    pass


# Dependency for FastAPI endpoints.
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
