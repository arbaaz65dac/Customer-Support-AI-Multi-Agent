from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from app.core.config import APP_NAME, APP_VERSION, FRONTEND_ORIGIN

from app.api.product_routes import router as product_router
from app.api.customer_routes import router as customer_router
from app.api.order_routes import router as order_router
from app.api.support_ticket_routes import (
    router as support_ticket_router,
)
from app.api.chat_routes import router as chat_router

# Create the application using centralized settings.
app = FastAPI(
    title=APP_NAME,
    description="Backend API for our multi-agent GenAI project",
    version=APP_VERSION,
)

# Allow the local React development server to call the API.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        FRONTEND_ORIGIN,
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register the API endpoints.
app.include_router(router)
app.include_router(product_router)
app.include_router(customer_router)
app.include_router(order_router)
app.include_router(support_ticket_router)
app.include_router(chat_router)