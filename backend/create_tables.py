from app.database import Base, engine

# Import all models so SQLAlchemy registers their tables.
from app.models import (
    Customer,
    Product,
    Order,
    OrderItem,
    SupportTicket,
)

if __name__ == "__main__":
    # Creates tables that do not yet exist.
    Base.metadata.create_all(bind=engine)
    print("Database tables created successfully!")