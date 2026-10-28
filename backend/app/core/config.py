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