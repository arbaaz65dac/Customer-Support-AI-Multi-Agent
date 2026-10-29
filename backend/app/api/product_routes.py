
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Product
from app.schemas.product import ProductCreate, ProductResponse

from decimal import Decimal

from app.services.product_service import search_products
from app.core.security import require_admin

router = APIRouter(prefix="/api/products", tags=["Products"])



@router.get("", response_model=list[ProductResponse])
def list_products(
    query: str | None = None,
    category: str | None = None,
    max_price: Decimal | None = Query(default=None, gt=0),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    """Search active products through the reusable service layer."""
    return search_products(
        db=db,
        query=query,
        category=category,
        max_price=max_price,
        limit=limit,
        offset=offset,
    )



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
    """Create a product. Restrict this endpoint to admins before production."""
    product = Product(**product_data.model_dump())

    db.add(product)
    db.commit()
    db.refresh(product)

    return product
