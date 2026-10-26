from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
def health_check():
    """Verify that the backend API is responding."""
    return {
        "status": "healthy",
        "message": "Customer Support AI backend is running!",
    }


@router.get("/")
def root():
    """Return basic information about the API."""
    return {
        "message": "Welcome to the Customer Support AI Assistant API"
    }