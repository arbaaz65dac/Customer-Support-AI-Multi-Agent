from warnings import filterwarnings
filterwarnings('ignore')
from fastapi import FastAPI

# Create the FastAPI application instance.
app = FastAPI(
    title="Customer Support AI Assistant",
    description="Backend API for our multi-agent GenAI project",
    version="0.1.0",
)


# Health-check endpoint to verify that the backend is running.
@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "message": "Customer Support AI backend is running!"
    }


# Root endpoint to provide basic API information.
@app.get("/")
def root():
    return {
        "message": "Welcome to the Customer Support AI Assistant API"
    }
