import os
from pathlib import Path

from dotenv import load_dotenv

# Locate the backend/.env file independently of the terminal directory.
BACKEND_DIR = Path(__file__).resolve().parents[2]
load_dotenv(BACKEND_DIR / ".env")

# Read application settings from environment variables.
APP_NAME = os.getenv(
    "APP_NAME",
    "Customer Support AI Assistant",
)
APP_VERSION = os.getenv("APP_VERSION", "0.1.0")
FRONTEND_ORIGIN = os.getenv(
    "FRONTEND_ORIGIN",
    "http://localhost:5173",
)

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL = os.getenv(
    "GROQ_MODEL",
    "llama-3.3-70b-versatile",
)

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "")
GEMINI_EMBEDDING_MODEL = os.getenv(
    "GEMINI_EMBEDDING_MODEL",
    "gemini-embedding-001",
)

RAG_TOP_K = int(os.getenv("RAG_TOP_K", "3"))

# This is a provisional setting. Calibrate it using Step 2.
RAG_MAX_DISTANCE = float(
    os.getenv("RAG_MAX_DISTANCE", "1.5")
)

# Authentication settings.
# Set a long, random secret in backend/.env before running the app.
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "")
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(
    os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30")
)