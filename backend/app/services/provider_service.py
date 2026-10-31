from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_groq import ChatGroq

from app.core.config import (
    GEMINI_EMBEDDING_MODEL,
    GOOGLE_API_KEY,
    GROQ_API_KEY,
    GROQ_MODEL,
)


def create_groq_chat_model(
    *,
    temperature: float = 0,
    max_tokens: int = 500,
    timeout: int = 30,
    max_retries: int = 1,
) -> ChatGroq:
    """Create the configured Groq chat client in one swappable boundary."""
    if not GROQ_API_KEY:
        raise RuntimeError("GROQ_API_KEY is not configured")
    return ChatGroq(
        model=GROQ_MODEL,
        temperature=temperature,
        max_tokens=max_tokens,
        api_key=GROQ_API_KEY,
        timeout=timeout,
        max_retries=max_retries,
    )


def create_gemini_embeddings() -> GoogleGenerativeAIEmbeddings:
    """Create the configured Gemini embedding client."""
    if not GOOGLE_API_KEY:
        raise RuntimeError("GOOGLE_API_KEY is not configured")
    return GoogleGenerativeAIEmbeddings(
        model=GEMINI_EMBEDDING_MODEL,
        google_api_key=GOOGLE_API_KEY,
    )
