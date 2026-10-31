import os
from datetime import datetime, timedelta, timezone

from pwdlib import PasswordHash
from sqlalchemy import Engine, select
from sqlalchemy.orm import Session, sessionmaker

from app.database import Base, SessionLocal, engine
from app.models import (
    Customer,
    Order,
    OrderItem,
    Product,
    SupportTicket,
)


PRODUCTS = [
    ("AeroTune Wireless Headphones", "Electronics", "2799.00", 24),
    ("BassLite Bluetooth Earbuds", "Electronics", "1499.00", 42),
    ("SoundArc Over-Ear Headphones", "Electronics", "3499.00", 16),
    ("PulseFit Smartwatch", "Wearables", "4299.00", 18),
    ("Everyday Fitness Band", "Wearables", "1899.00", 32),
    ("Nova 20W USB-C Charger", "Accessories", "699.00", 60),
    ("Braided USB-C Cable 2m", "Accessories", "299.00", 90),
    ("Wireless Charging Pad", "Accessories", "999.00", 35),
    ("ClickPro Wireless Mouse", "Computer Accessories", "799.00", 50),
    ("MechKey Compact Keyboard", "Computer Accessories", "2499.00", 21),
    ("Ergo Office Keyboard", "Computer Accessories", "1299.00", 28),
    ("ViewBright 24-inch Monitor", "Computers", "8999.00", 12),
    ("ViewBright 27-inch Monitor", "Computers", "13999.00", 9),
    ("SwiftBook Laptop Stand", "Computer Accessories", "1199.00", 33),
    ("Full HD Web Camera", "Computer Accessories", "2199.00", 19),
    ("HomeSound Smart Speaker", "Home", "3299.00", 17),
    ("RoomGlow LED Desk Lamp", "Home", "1499.00", 27),
    ("AirPure Mini Air Purifier", "Home", "5999.00", 8),
    ("BrewMate Electric Kettle", "Kitchen", "1799.00", 22),
    ("FreshPress Mixer Grinder", "Kitchen", "3499.00", 13),
    ("DailySip Insulated Bottle", "Lifestyle", "599.00", 48),
    ("TrailPack Day Backpack", "Lifestyle", "1899.00", 25),
    ("SoftWeave Cotton Towel Set", "Home", "999.00", 40),
    ("ComfortCloud Pillow Pair", "Home", "1599.00", 20),
    ("CleanSweep Hand Vacuum", "Home", "2799.00", 11),
    ("PowerBank 10000mAh", "Accessories", "1599.00", 30),
    ("PowerBank 20000mAh", "Accessories", "2499.00", 18),
    ("TabMate Tablet Cover", "Accessories", "899.00", 36),
    ("GripSafe Phone Case", "Accessories", "499.00", 65),
    ("ClearView Screen Protector", "Accessories", "249.00", 100),
]


def seed_data(
    target_engine: Engine = engine,
    session_factory: sessionmaker[Session] = SessionLocal,
) -> None:
    admin_password = os.getenv("SEED_ADMIN_PASSWORD")
    customer_password = os.getenv("SEED_CUSTOMER_PASSWORD")
    if (
        not admin_password
        or not customer_password
        or len(admin_password) < 12
        or len(customer_password) < 12
    ):
        raise RuntimeError(
            "Set SEED_ADMIN_PASSWORD and SEED_CUSTOMER_PASSWORD to values "
            "of at least 12 characters before seeding."
        )

    Base.metadata.create_all(bind=target_engine)
    password_hasher = PasswordHash.recommended()

    with session_factory.begin() as db:
        customers = []
        for index in range(1, 3):
            email = f"admin{index}@support.local"
            customer = db.scalar(
                select(Customer).where(Customer.email == email)
            )
            if customer is None:
                customer = Customer(
                    name=f"Support Admin {index}",
                    email=email,
                    password_hash=password_hasher.hash(admin_password),
                    role="admin",
                )
                db.add(customer)
            customers.append(customer)

        for index in range(1, 13):
            email = f"customer{index:02d}@example.in"
            customer = db.scalar(
                select(Customer).where(Customer.email == email)
            )
            if customer is None:
                customer = Customer(
                    name=f"Demo Customer {index}",
                    email=email,
                    password_hash=password_hasher.hash(customer_password),
                    role="customer",
                )
                db.add(customer)
            customers.append(customer)

        db.flush()

        products = []
        for name, category, price, stock in PRODUCTS:
            product = db.scalar(
                select(Product).where(Product.name == name)
            )
            if product is None:
                product = Product(
                    name=name,
                    description=f"{name} from our curated {category.lower()} range.",
                    category=category,
                    price=price,
                    stock=stock,
                    active=True,
                )
                db.add(product)
            products.append(product)

        db.flush()

        existing_orders = db.scalar(select(Order.id).limit(1))
        if existing_orders is None:
            for index in range(12):
                customer = customers[2 + index]
                order = Order(
                    customer_id=customer.id,
                    status=(
                        "delivered"
                        if index < 8
                        else "processing" if index < 10 else "shipped"
                    ),
                    delivered_at=(
                        datetime.now(timezone.utc).replace(tzinfo=None)
                        - timedelta(days=2)
                        if index < 8
                        else None
                    ),
                )
                for product_index in (index, (index + 7) % len(products)):
                    product = products[product_index]
                    order.items.append(
                        OrderItem(
                            product_id=product.id,
                            quantity=1,
                            unit_price=product.price,
                        )
                    )
                db.add(order)

        db.flush()
        if not db.scalar(select(SupportTicket.id).limit(1)):
            for index, customer in enumerate(customers[2:7], start=1):
                db.add(
                    SupportTicket(
                        customer_id=customer.id,
                        subject=f"Demo support request {index}",
                        description=(
                            "Please help me with a question about my recent "
                            "order and the available support options."
                        ),
                        status="open" if index % 2 else "in_progress",
                        priority="normal",
                    )
                )


if __name__ == "__main__":
    seed_data()
    print("Seed data created or already present.")
