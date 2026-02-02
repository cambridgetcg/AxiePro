"""
Market API endpoints.

Provides routes for:
- Active listings
- Sales history
- Floor prices
- Market statistics
- Price analytics and time-series data
"""

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Optional, Literal
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func, and_, desc
from sqlalchemy.ext.asyncio import AsyncSession

from src.models import Listing, Sale, Axie, AxieClass, get_db
from src.services.skymavis_client import SkyMavisClient
from src.services.market_aggregator import (
    MarketAggregatorService,
    get_market_aggregator,
)
from src.services.sales_aggregator import (
    SalesAggregatorService,
    get_sales_aggregator,
)
from src.services.cache import get_cache_manager

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
        query = query.where(Sale.price_token >= min_price)
    if max_price is not None:
        query = query.where(Sale.price_token <= max_price)
    if from_date:
        query = query.where(Sale.block_timestamp >= from_date)
    if to_date:
        query = query.where(Sale.block_timestamp <= to_date)
    if seller:
        query = query.where(Sale.seller == seller.lower())
    if buyer:
        query = query.where(Sale.buyer == buyer.lower())

    # Sorting
    sort_column = {
        "date": Sale.block_timestamp,
        "price": Sale.price_token,
    }.get(sort, Sale.block_timestamp)

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
    class_: Optional[str] = Query(None, alias="class"),
    use_cache: bool = Query(True, description="Whether to use cached results"),
    db: AsyncSession = Depends(get_db),
):
    """
    Get market-wide statistics for 24h, 7d, 30d periods.

    Uses the MarketAggregatorService for efficient querying with caching.
    Now includes floor_price_eth, max_price_eth, and active_listings.
    """
    try:
        aggregator = await get_market_aggregator(db)
        stats = await aggregator.get_market_stats(use_cache=use_cache)

        return {
            "success": True,
            "data": stats,
            "cached": use_cache,
        }
    except Exception as e:
        # Fallback to direct query if aggregator fails
        stats = {}

        for period_name, days in [("24h", 1), ("7d", 7), ("30d", 30)]:
            since = datetime.now(timezone.utc) - timedelta(days=days)

            # Sales stats
            sales_query = select(
                func.count(Sale.id).label("sales_count"),
                func.coalesce(func.sum(Sale.price_token), 0).label("volume_eth"),
                func.coalesce(func.avg(Sale.price_token), 0).label("avg_price"),
                func.count(func.distinct(Sale.buyer)).label("unique_buyers"),
                func.count(func.distinct(Sale.seller)).label("unique_sellers"),
            ).where(Sale.block_timestamp >= since)

            result = await db.execute(sales_query)
            row = result.one()

            # Calculate median
            median_query = (
                select(Sale.price_token)
                .where(Sale.block_timestamp >= since)
                .order_by(Sale.price_token)
            )
            median_result = await db.execute(median_query)
            prices = [float(p[0]) for p in median_result.all()]
            median_price = prices[len(prices) // 2] if prices else 0

            # Get floor price from listings
            floor_query = select(func.min(Listing.price_eth)).where(
                Listing.status == "active"
            )
            floor_result = await db.execute(floor_query)
            floor_price = floor_result.scalar()

            # Get active listings count
            listings_query = select(func.count(Listing.id)).where(
                Listing.status == "active"
            )
            listings_result = await db.execute(listings_query)
            active_listings = listings_result.scalar() or 0

            stats[period_name] = {
                "volume_eth": float(row.volume_eth or 0),
                "sales_count": row.sales_count or 0,
                "avg_price_eth": float(row.avg_price or 0),
                "median_price_eth": median_price,
                "floor_price_eth": float(floor_price) if floor_price else None,
                "unique_buyers": row.unique_buyers or 0,
                "unique_sellers": row.unique_sellers or 0,
                "active_listings": active_listings,
            }

        return {
            "success": True,
            "data": stats,
            "cached": False,
        }


# =============================================================================
# Analytics Endpoints - Time-series and aggregated data
# =============================================================================

@router.get("/analytics/summary")
async def get_market_summary(
    use_cache: bool = Query(True),
    db: AsyncSession = Depends(get_db),
):
    """
    Get complete market summary for the analytics dashboard.

    Returns:
    - Market statistics for all periods (24h, 7d, 30d)
    - Floor prices by class with 24h change
    - Volume trends
    """
    aggregator = await get_market_aggregator(db)
    summary = await aggregator.get_market_summary()

    return {
        "success": True,
        "data": summary,
    }


@router.get("/analytics/floor-prices")
async def get_analytics_floor_prices(
    use_cache: bool = Query(True),
    db: AsyncSession = Depends(get_db),
):
    """
    Get floor prices by class with 24h change percentage.

    Uses cached data from price_snapshots for historical comparison.
    """
    aggregator = await get_market_aggregator(db)
    floors = await aggregator.get_floor_prices_by_class(use_cache=use_cache)

    return {
        "success": True,
        "data": {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "floors": floors,
        },
    }


@router.get("/analytics/price-history")
async def get_price_history(
    trait_key: str = Query(..., description="Trait key (e.g., 'class:beast', 'part:eyes:kotaro')"),
    interval: str = Query("1h", description="Time bucket interval: 5m, 1h, 1d"),
    limit: int = Query(100, ge=1, le=500, description="Max data points"),
    use_cache: bool = Query(True),
    db: AsyncSession = Depends(get_db),
):
    """
    Get price history time-series for a specific trait.

    Returns floor price, average price, and volume over time.
    Data comes from the price_snapshots table populated by price_ingestion lambda.
    """
    aggregator = await get_market_aggregator(db)
    history = await aggregator.get_price_history(
        trait_key=trait_key,
        interval=interval,
        limit=limit,
        use_cache=use_cache,
    )

    return {
        "success": True,
        "data": {
            "trait_key": trait_key,
            "interval": interval,
            "points": history,
        },
    }


@router.get("/analytics/class-history/{axie_class}")
async def get_class_price_history(
    axie_class: str,
    interval: str = Query("1h"),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
):
    """
    Get price history for a specific Axie class.

    Convenience endpoint that wraps /analytics/price-history.
    """
    # Validate class
    try:
        AxieClass(axie_class.lower())
    except ValueError:
        raise HTTPException(400, f"Invalid class: {axie_class}")

    aggregator = await get_market_aggregator(db)
    history = await aggregator.get_class_price_history(
        axie_class=axie_class,
        interval=interval,
        limit=limit,
    )

    return {
        "success": True,
        "data": {
            "class": axie_class.lower(),
            "interval": interval,
            "points": history,
        },
    }


# =============================================================================
# Sales Activity Endpoints - Recent sales and activity statistics
# =============================================================================

@router.get("/sales/recent")
async def get_recent_sales(
    hours: int = Query(24, ge=1, le=168, description="Hours to look back (max 7 days)"),
    class_: Optional[str] = Query(None, alias="class"),
    limit: int = Query(50, ge=1, le=200, description="Maximum number of sales"),
    use_cache: bool = Query(True),
    db: AsyncSession = Depends(get_db),
):
    """
    Get recent sales with optional class filter.

    Optimized endpoint for dashboard recent sales display.
    Uses Redis caching for fast repeated access.
    """
    # Validate class if provided
    if class_:
        try:
            AxieClass(class_.lower())
        except ValueError:
            raise HTTPException(400, f"Invalid class: {class_}")

    aggregator = await get_sales_aggregator(db)
    sales = await aggregator.get_recent_sales(
        hours=hours,
        axie_class=class_,
        limit=limit,
        use_cache=use_cache,
    )

    return {
        "success": True,
        "data": sales,
        "meta": {
            "hours": hours,
            "class_filter": class_,
            "count": len(sales),
            "source": "cache" if use_cache else "database",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
    }


@router.get("/sales/activity")
async def get_sales_activity(
    hours: int = Query(24, ge=1, le=168, description="Hours to analyze"),
    class_: Optional[str] = Query(None, alias="class"),
    use_cache: bool = Query(True),
    db: AsyncSession = Depends(get_db),
):
    """
    Get aggregated sales activity statistics.

    Returns volume, average price, unique traders, and breakdown by class.
    """
    if class_:
        try:
            AxieClass(class_.lower())
        except ValueError:
            raise HTTPException(400, f"Invalid class: {class_}")

    aggregator = await get_sales_aggregator(db)
    activity = await aggregator.get_sales_activity(
        hours=hours,
        axie_class=class_,
        use_cache=use_cache,
    )

    return {
        "success": True,
        "data": activity,
        "meta": {
            "hours": hours,
            "class_filter": class_,
            "source": "cache" if use_cache else "database",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
    }


@router.get("/sales/class/{axie_class}")
async def get_class_sales(
    axie_class: str,
    hours: int = Query(24, ge=1, le=168),
    limit: int = Query(20, ge=1, le=100),
    use_cache: bool = Query(True),
    db: AsyncSession = Depends(get_db),
):
    """
    Get detailed sales data for a specific Axie class.

    Includes aggregated stats and recent sales for the class.
    """
    try:
        AxieClass(axie_class.lower())
    except ValueError:
        raise HTTPException(400, f"Invalid class: {axie_class}")

    aggregator = await get_sales_aggregator(db)
    class_data = await aggregator.get_class_sales(
        axie_class=axie_class,
        hours=hours,
        limit=limit,
        use_cache=use_cache,
    )

    return {
        "success": True,
        "data": class_data,
        "meta": {
            "class": axie_class.lower(),
            "hours": hours,
            "source": "cache" if use_cache else "database",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
    }


@router.get("/sales/hourly")
async def get_hourly_sales_distribution(
    hours: int = Query(24, ge=1, le=168),
    use_cache: bool = Query(True),
    db: AsyncSession = Depends(get_db),
):
    """
    Get hourly distribution of sales for time-series visualization.

    Returns sales count and volume per hour for charting.
    """
    aggregator = await get_sales_aggregator(db)
    distribution = await aggregator.get_hourly_sales_distribution(
        hours=hours,
        use_cache=use_cache,
    )

    return {
        "success": True,
        "data": {
            "hours": hours,
            "distribution": distribution,
        },
        "meta": {
            "source": "cache" if use_cache else "database",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
    }
