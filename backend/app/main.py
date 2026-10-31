
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from app.api.product_routes import router as product_router
from app.api.customer_routes import router as customer_router
from app.api.order_routes import router as order_router
from app.api.support_ticket_routes import (
    router as support_ticket_router,
)
from app.api.chat_routes import router as chat_router
from app.api.rag_routes import router as rag_router
from app.api.support_graph_routes import (
    router as support_graph_router,
)

from app.api.admin_dashboard_routes import (
    router as admin_dashboard_router,
)

from app.api.auth_routes import router as auth_router
from app.api.conversation_routes import router as conversation_router
from app.api.refund_routes import router as refund_router
from app.core.request_id import RequestIdMiddleware
from app.core.structured_logging import configure_logging

from app.core.config import APP_NAME, APP_VERSION, FRONTEND_ORIGIN

configure_logging()

# Create the application using centralized settings.
app = FastAPI(
    title=APP_NAME,
    description="Backend API for our multi-agent GenAI project",
    version=APP_VERSION,
)

# Allow the local React development server to call the API.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONTEND_ORIGIN],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID"],
)
app.add_middleware(RequestIdMiddleware)

# Register the API endpoints.
app.include_router(router)
app.include_router(auth_router)
app.include_router(product_router)
app.include_router(customer_router)
app.include_router(order_router)
app.include_router(support_ticket_router)
app.include_router(admin_dashboard_router)
app.include_router(chat_router)
app.include_router(rag_router)
app.include_router(support_graph_router)
app.include_router(conversation_router)
app.include_router(refund_router)
