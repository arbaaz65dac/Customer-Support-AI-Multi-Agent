
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Product
from app.schemas.product import ProductCreate, ProductResponse, ProductUpdate

from decimal import Decimal

from app.services.product_service import search_products
from app.core.security import require_admin

router = APIRouter(prefix="/api/products", tags=["Products"])



@router.get("", response_model=list[ProductResponse])
def list_products(
    query: str | None = None,
    category: str | None = None,
    min_price: Decimal | None = Query(default=None, gt=0),
    max_price: Decimal | None = Query(default=None, gt=0),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    """Search active products through the reusable service layer."""
    if (
        min_price is not None
        and max_price is not None
        and min_price > max_price
    ):
        raise HTTPException(
            status_code=422,
            detail="Minimum price cannot exceed maximum price.",
        )
    return search_products(
        db=db,
        query=query,
        category=category,
        min_price=min_price,
        max_price=max_price,
        limit=limit,
        offset=offset,
    )


@router.get("/categories", response_model=list[str])
def list_product_categories(db: Session = Depends(get_db)):
    return db.scalars(
        select(Product.category)
        .where(Product.active.is_(True))
        .distinct()
        .order_by(Product.category)
    ).all()


@router.get("/admin/all", response_model=list[ProductResponse])
def list_admin_products(
    query: str | None = None,
    category: str | None = None,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    admin_customer=Depends(require_admin),
):
    statement = select(Product).order_by(Product.id)
    if query:
        search_term = f"%{query.strip()}%"
        statement = statement.where(
            Product.name.ilike(search_term)
            | Product.description.ilike(search_term)
        )
    if category:
        statement = statement.where(Product.category == category)
    return db.scalars(statement.offset(offset).limit(limit)).all()



@router.get("/{product_id}", response_model=ProductResponse)
def get_product(product_id: int, db: Session = Depends(get_db)):
    """Return one active product."""
    product = db.get(Product, product_id)

    if product is None or not product.active:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found",
        )

    return product


@router.post(
    "",
    response_model=ProductResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_product(
    product_data: ProductCreate,
    db: Session = Depends(get_db),
    admin_customer=Depends(require_admin),
):
    """Create a product for an administrator."""
    product = Product(**product_data.model_dump())

    db.add(product)
    db.commit()
    db.refresh(product)

    return product


@router.patch("/{product_id}", response_model=ProductResponse)
def update_product(
    product_id: int,
    product_data: ProductUpdate,
    db: Session = Depends(get_db),
    admin_customer=Depends(require_admin),
):
    product = db.get(Product, product_id)
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")

    for field, value in product_data.model_dump().items():
        setattr(product, field, value)
    db.commit()
    db.refresh(product)
    return product


@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_product(
    product_id: int,
    db: Session = Depends(get_db),
    admin_customer=Depends(require_admin),
):
    product = db.get(Product, product_id)
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")

    # Keep historical order-item references intact.
    product.active = False
    db.commit()
