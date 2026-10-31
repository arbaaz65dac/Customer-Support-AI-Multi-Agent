from sqlalchemy import create_engine, func, inspect, select, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.models import Customer, Order, OrderItem, Product, SupportTicket
from create_tables import ensure_schema
from seed_data import PRODUCTS, seed_data


def test_seed_data_creates_expected_demo_records_and_is_repeatable(
    monkeypatch,
):
    monkeypatch.setenv("SEED_ADMIN_PASSWORD", "test-admin-password")
    monkeypatch.setenv("SEED_CUSTOMER_PASSWORD", "test-customer-password")

    test_engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    test_sessions = sessionmaker(bind=test_engine, expire_on_commit=False)

    try:
        seed_data(target_engine=test_engine, session_factory=test_sessions)
        seed_data(target_engine=test_engine, session_factory=test_sessions)

        with test_sessions() as db:
            assert db.scalar(
                select(func.count(Customer.id)).where(Customer.role == "admin")
            ) == 2
            assert db.scalar(
                select(func.count(Customer.id)).where(
                    Customer.role == "customer"
                )
            ) == 12
            assert db.scalar(select(func.count(Product.id))) == len(PRODUCTS)
            assert db.scalar(select(func.count(Order.id))) == 12
            assert db.scalar(select(func.count(OrderItem.id))) == 24
            assert db.scalar(select(func.count(SupportTicket.id))) == 5
    finally:
        Base.metadata.drop_all(bind=test_engine)
        test_engine.dispose()


def test_schema_initializer_upgrades_existing_tables_without_dropping_data():
    test_engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    legacy_schema = [
        "CREATE TABLE customers (id INTEGER PRIMARY KEY, name VARCHAR(100) NOT NULL, "
        "email VARCHAR(255) NOT NULL, password_hash VARCHAR(255) NOT NULL, "
        "role VARCHAR(20) NOT NULL DEFAULT 'customer', "
        "created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP)",
        "CREATE TABLE products (id INTEGER PRIMARY KEY, name VARCHAR(150) NOT NULL, "
        "description TEXT, category VARCHAR(100) NOT NULL, price NUMERIC(10, 2) "
        "NOT NULL, stock INTEGER NOT NULL, active BOOLEAN NOT NULL)",
        "CREATE TABLE orders (id INTEGER PRIMARY KEY, customer_id INTEGER NOT NULL, "
        "status VARCHAR(30) NOT NULL, created_at DATETIME NOT NULL "
        "DEFAULT CURRENT_TIMESTAMP)",
        "CREATE TABLE order_items (id INTEGER PRIMARY KEY, order_id INTEGER NOT NULL, "
        "product_id INTEGER NOT NULL, quantity INTEGER NOT NULL, "
        "unit_price NUMERIC(10, 2) NOT NULL)",
        "CREATE TABLE support_tickets (id INTEGER PRIMARY KEY, customer_id INTEGER "
        "NOT NULL, subject VARCHAR(200) NOT NULL, description TEXT NOT NULL, "
        "status VARCHAR(30) NOT NULL, created_at DATETIME NOT NULL "
        "DEFAULT CURRENT_TIMESTAMP)",
    ]

    try:
        with test_engine.begin() as connection:
            for statement in legacy_schema:
                connection.execute(text(statement))
            connection.execute(
                text(
                    "INSERT INTO customers "
                    "(id, name, email, password_hash, role) "
                    "VALUES (1, 'Existing', 'existing@example.com', 'hash', 'customer')"
                )
            )

        ensure_schema(target_engine=test_engine)

        inspector = inspect(test_engine)
        customer_columns = {
            column["name"] for column in inspector.get_columns("customers")
        }
        ticket_columns = {
            column["name"] for column in inspector.get_columns("support_tickets")
        }
        assert "active" in customer_columns
        assert {"priority", "order_id", "assigned_admin_id"} <= ticket_columns
        assert {
            "conversations",
            "messages",
            "refund_requests",
            "ticket_replies",
        } <= set(inspector.get_table_names())
        with test_engine.connect() as connection:
            assert connection.scalar(
                text("SELECT COUNT(*) FROM customers")
            ) == 1
    finally:
        Base.metadata.drop_all(bind=test_engine)
        test_engine.dispose()
