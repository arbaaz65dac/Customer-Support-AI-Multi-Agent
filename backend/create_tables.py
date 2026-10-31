from sqlalchemy import inspect, text

from app.database import Base, engine

# Import all models so SQLAlchemy registers their tables.
from app.models import (
    Customer,
    Product,
    Order,
    OrderItem,
    SupportTicket,
)

def ensure_schema(target_engine=engine):
    """Create missing tables and safely add Phase 2 columns to older schemas."""
    identifier = target_engine.dialect.identifier_preparer.quote
    inspector = inspect(target_engine)
    existing_tables = set(inspector.get_table_names())

    additions = {
        "customers": {
            "active": "BOOLEAN NOT NULL DEFAULT 1",
        },
        "support_tickets": {
            "priority": "VARCHAR(20) NOT NULL DEFAULT 'normal'",
            "order_id": "INTEGER NULL",
            "assigned_admin_id": "INTEGER NULL",
        },
        "orders": {
            "delivered_at": "DATETIME NULL",
        },
    }

    with target_engine.begin() as connection:
        for table_name, columns in additions.items():
            if table_name not in existing_tables:
                continue
            existing_columns = {
                column["name"]
                for column in inspect(connection).get_columns(table_name)
            }
            for column_name, definition in columns.items():
                if column_name not in existing_columns:
                    connection.execute(
                        text(
                            f"ALTER TABLE {identifier(table_name)} "
                            f"ADD COLUMN {identifier(column_name)} {definition}"
                        )
                    )

        if target_engine.dialect.name == "mysql" and (
            "support_tickets" in existing_tables
        ):
            constraints = inspect(connection).get_foreign_keys("support_tickets")
            constrained_columns = {
                column
                for constraint in constraints
                for column in constraint.get("constrained_columns", [])
            }
            foreign_keys = {
                "order_id": ("orders", "fk_support_tickets_order_id"),
                "assigned_admin_id": (
                    "customers",
                    "fk_support_tickets_assigned_admin_id",
                ),
            }
            for column_name, (target_table, constraint_name) in foreign_keys.items():
                if column_name not in constrained_columns:
                    connection.execute(
                        text(
                            f"ALTER TABLE {identifier('support_tickets')} "
                            f"ADD CONSTRAINT {identifier(constraint_name)} "
                            f"FOREIGN KEY ({identifier(column_name)}) "
                            f"REFERENCES {identifier(target_table)} "
                            f"({identifier('id')})"
                        )
                    )

    Base.metadata.create_all(bind=target_engine)

    # create_all skips indexes on pre-existing tables, so add model indexes
    # separately after any required columns have been added.
    with target_engine.begin() as connection:
        for table in Base.metadata.sorted_tables:
            for index in table.indexes:
                index.create(bind=connection, checkfirst=True)


if __name__ == "__main__":
    ensure_schema()
    print("Database schema created or upgraded successfully.")