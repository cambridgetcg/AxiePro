"""
Market API endpoints.

Provides routes for:
- Active listings
- Sales history
- Floor prices
- Market statistics
"""

from datetime import datetime, timedelta
from decimal import Decimal
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func, and_, desc
from sqlalchemy.ext.asyncio import AsyncSession

from src.models import Listing, Sale, Axie, AxieClass, get_db
from src.services.skymavis_client import SkyMavisClient

router = APIRouter(prefix="/market", tags=["market"])


@router.get("/listings")
async def get_listings(
    # Class filter
    class_: Optional[str] = Query(None, alias="class"),

    # Price filters
    min_price: Optional[float] = Query(None),
    max_price: Optional[float] = Query(None),

    # Purity filter
    purity: Optional[int] = Query(None, ge=0, le=6),

    # Pagination and sorting
    sort: str = Query("price", description="Sort: price, listed_at"),
    order: str = Query("asc"),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),

    db: AsyncSession = Depends(get_db),
):
    """
    Get active marketplace listings.
    """
    query = (
        select(Listing, Axie)
        .join(Axie, Listing.axie_id == Axie.id)
        .where(Listing.status == "active")
    )

    # Apply filters
    if class_:
        try:
            axie_class = AxieClass(class_.lower())
            query = query.where(Axie.class_ == axie_class)
        except ValueError:
            raise HTTPException(400, f"Invalid class: {class_}")

    if min_price is not None:
        query = query.where(Listing.price_eth >= min_price)
    if max_price is not None:
        query = query.where(Listing.price_eth <= max_price)
    if purity is not None:
        query = query.where(Axie.purity_score >= purity)

    # Sorting
    sort_column = {
        "price": Listing.price_eth,
        "listed_at": Listing.listed_at,
    }.get(sort, Listing.price_eth)

    if order == "desc":
        query = query.order_by(sort_column.desc())
    else:
        query = query.order_by(sort_column.asc())

    # Count
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Paginate
    offset = (page - 1) * per_page
    query = query.offset(offset).limit(per_page)

    result = await db.execute(query)
    rows = result.all()

    listings = []
    for listing, axie in rows:
        listings.append({
            "id": listing.id,
            "axie_id": listing.axie_id,
            "seller": listing.seller_address,
            "price_eth": float(listing.price_eth),
            "price_usd": float(listing.price_usd) if listing.price_usd else None,
            "listed_at": listing.listed_at.isoformat(),
            "axie": {
                "class": axie.class_.value,
                "purity": axie.purity_score,
                "breed_count": axie.breed_count,
            }
        })

    return {
        "success": True,
        "data": listings,
        "meta": {
            "total": total,
            "page": page,
            "per_page": per_page,
            "total_pages": (total + per_page - 1) // per_page,
        }
    }


@router.get("/sales")
async def get_sales(
    # Filters
    class_: Optional[str] = Query(None, alias="class"),
    min_price: Optional[float] = Query(None),
    max_price: Optional[float] = Query(None),
    from_date: Optional[datetime] = Query(None),
    to_date: Optional[datetime] = Query(None),
    seller: Optional[str] = Query(None),
    buyer: Optional[str] = Query(None),

    # Pagination and sorting
    sort: str = Query("date", description="Sort: date, price"),
    order: str = Query("desc"),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),

    db: AsyncSession = Depends(get_db),
):
    """
    Get sales history.
    """
    query = (
        select(Sale, Axie)
        .outerjoin(Axie, Sale.axie_id == Axie.id)
    )

    # Apply filters
    if class_:
        try:
            axie_class = AxieClass(class_.lower())
            query = query.where(Axie.class_ == axie_class)
        except ValueError:
            raise HTTPException(400, f"Invalid class: {class_}")

    if min_price is not None:
        query = query.where(Sale.price_eth >= min_price)
    if max_price is not None:
        query = query.where(Sale.price_eth <= max_price)
    if from_date:
        query = query.where(Sale.sold_at >= from_date)
    if to_date:
        query = query.where(Sale.sold_at <= to_date)
    if seller:
        query = query.where(Sale.seller_address == seller.lower())
    if buyer:
        query = query.where(Sale.buyer_address == buyer.lower())

    # Sorting
    sort_column = {
        "date": Sale.sold_at,
        "price": Sale.price_eth,
    }.get(sort, Sale.sold_at)

    if order == "desc":
        query = query.order_by(sort_column.desc())
    else:
        query = query.order_by(sort_column.asc())

    # Count
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Paginate
    offset = (page - 1) * per_page
    query = query.offset(offset).limit(per_page)

    result = await db.execute(query)
    rows = result.all()

    sales = []
    for sale, axie in rows:
        sale_data = {
            "id": sale.id,
            "axie_id": sale.axie_id,
            "seller": sale.seller_address,
            "buyer": sale.buyer_address,
            "price_eth": float(sale.price_eth),
            "price_usd": float(sale.price_usd) if sale.price_usd else None,
            "sold_at": sale.sold_at.isoformat(),
            "tx_hash": sale.tx_hash,
        }
        if axie:
            sale_data["axie"] = {
                "class": axie.class_.value,
                "purity": axie.purity_score,
            }
        sales.append(sale_data)

    return {
        "success": True,
        "data": sales,
        "meta": {
            "total": total,
            "page": page,
            "per_page": per_page,
            "total_pages": (total + per_page - 1) // per_page,
        }
    }


@router.get("/floor-prices")
async def get_floor_prices(
    class_: Optional[str] = Query(None, alias="class"),
    group_by: str = Query("class", description="Group by: class, purity"),
    db: AsyncSession = Depends(get_db),
):
    """
    Get current floor prices by class or purity.
    """
    if group_by == "class":
        # Floor price by class
        query = (
            select(
                Axie.class_,
                func.min(Listing.price_eth).label("floor_eth"),
                func.count(Listing.id).label("count"),
            )
            .join(Listing, and_(
                Listing.axie_id == Axie.id,
                Listing.status == "active"
            ))
            .group_by(Axie.class_)
        )

        if class_:
            try:
                axie_class = AxieClass(class_.lower())
                query = query.where(Axie.class_ == axie_class)
            except ValueError:
                pass

        result = await db.execute(query)
        rows = result.all()

        floors = [
            {
                "class": row.class_.value,
                "floor_eth": float(row.floor_eth),
                "count": row.count,
            }
            for row in rows
        ]

    elif group_by == "purity":
        # Floor price by purity (within a class)
        query = (
            select(
                Axie.class_,
                Axie.purity_score,
                func.min(Listing.price_eth).label("floor_eth"),
                func.count(Listing.id).label("count"),
            )
            .join(Listing, and_(
                Listing.axie_id == Axie.id,
                Listing.status == "active"
            ))
            .group_by(Axie.class_, Axie.purity_score)
        )

        if class_:
            try:
                axie_class = AxieClass(class_.lower())
                query = query.where(Axie.class_ == axie_class)
            except ValueError:
                pass

        result = await db.execute(query)
        rows = result.all()

        floors = [
            {
                "class": row.class_.value,
                "purity": row.purity_score,
                "floor_eth": float(row.floor_eth),
                "count": row.count,
            }
            for row in rows
        ]

    else:
        raise HTTPException(400, "Invalid group_by value")

    return {
        "success": True,
        "data": {
            "timestamp": datetime.utcnow().isoformat(),
            "floors": floors,
        }
    }


@router.get("/stats")
async def get_market_stats(
    db: AsyncSession = Depends(get_db),
):
    """
    Get market-wide statistics for 24h, 7d, 30d periods.
    """
    stats = {}

    for period_name, days in [("24h", 1), ("7d", 7), ("30d", 30)]:
        since = datetime.utcnow() - timedelta(days=days)

        # Sales stats
        sales_query = select(
            func.count(Sale.id).label("sales_count"),
            func.sum(Sale.price_eth).label("volume_eth"),
            func.avg(Sale.price_eth).label("avg_price"),
            func.count(func.distinct(Sale.buyer_address)).label("unique_buyers"),
            func.count(func.distinct(Sale.seller_address)).label("unique_sellers"),
        ).where(Sale.sold_at >= since)

        result = await db.execute(sales_query)
        row = result.one()

        # Calculate median (simplified - would need window function for exact)
        median_query = (
            select(Sale.price_eth)
            .where(Sale.sold_at >= since)
            .order_by(Sale.price_eth)
        )
        median_result = await db.execute(median_query)
        prices = [float(p[0]) for p in median_result.all()]
        median_price = prices[len(prices) // 2] if prices else 0

        stats[period_name] = {
            "volume_eth": float(row.volume_eth or 0),
            "sales_count": row.sales_count or 0,
            "avg_price_eth": float(row.avg_price or 0),
            "median_price_eth": median_price,
            "unique_buyers": row.unique_buyers or 0,
            "unique_sellers": row.unique_sellers or 0,
        }

    return {
        "success": True,
        "data": stats,
    }
