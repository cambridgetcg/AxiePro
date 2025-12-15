"""
Wallet API endpoints.

Provides routes for:
- Wallet overview and stats
- Holdings
- Trade history
"""

from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.models import Wallet, WalletHolding, Axie, Sale, get_db
from src.services.moralis_client import MoralisClient

router = APIRouter(prefix="/wallets", tags=["wallets"])


@router.get("/{address}")
async def get_wallet(
    address: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Get wallet overview with trading statistics.
    """
    address = address.lower()

    # Get wallet from DB
    result = await db.execute(
        select(Wallet)
        .where(Wallet.address == address)
        .options(selectinload(Wallet.holdings))
    )
    wallet = result.scalar_one_or_none()

    if wallet:
        # Calculate current holdings value (would need price data)
        holdings_count = len(wallet.holdings)

        return {
            "success": True,
            "data": {
                "address": wallet.address,
                "alias": wallet.alias,
                "first_seen": wallet.first_seen.isoformat() if wallet.first_seen else None,
                "last_active": wallet.last_active.isoformat() if wallet.last_active else None,
                "holdings": {
                    "axie_count": holdings_count,
                },
                "trading_stats": {
                    "total_buys": wallet.total_trades // 2,  # Approximation
                    "total_sells": wallet.total_trades // 2,
                    "total_buy_volume_eth": float(wallet.total_buy_volume_eth),
                    "total_sell_volume_eth": float(wallet.total_sell_volume_eth),
                },
                "is_whale": wallet.is_whale,
            }
        }

    # If not tracked, try to get basic info from sales
    buy_stats = await db.execute(
        select(
            func.count(Sale.id),
            func.sum(Sale.price_eth),
        ).where(Sale.buyer_address == address)
    )
    buy_row = buy_stats.one()

    sell_stats = await db.execute(
        select(
            func.count(Sale.id),
            func.sum(Sale.price_eth),
        ).where(Sale.seller_address == address)
    )
    sell_row = sell_stats.one()

    # Count current holdings from Axie table
    holdings_result = await db.execute(
        select(func.count(Axie.id)).where(Axie.owner_address == address)
    )
    axie_count = holdings_result.scalar() or 0

    return {
        "success": True,
        "data": {
            "address": address,
            "alias": None,
            "first_seen": None,
            "last_active": None,
            "holdings": {
                "axie_count": axie_count,
            },
            "trading_stats": {
                "total_buys": buy_row[0] or 0,
                "total_sells": sell_row[0] or 0,
                "total_buy_volume_eth": float(buy_row[1] or 0),
                "total_sell_volume_eth": float(sell_row[1] or 0),
            },
            "is_whale": False,
        },
        "tracked": False,
    }


@router.get("/{address}/axies")
async def get_wallet_axies(
    address: str,
    # Filters (same as /axies endpoint)
    class_: Optional[str] = Query(None, alias="class"),
    purity: Optional[int] = Query(None, ge=0, le=6),

    # Pagination
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),

    db: AsyncSession = Depends(get_db),
):
    """
    Get Axies owned by a wallet.
    """
    address = address.lower()

    query = select(Axie).where(Axie.owner_address == address)

    # Apply filters
    if class_:
        try:
            from src.models import AxieClass
            query = query.where(Axie.class_ == AxieClass(class_.lower()))
        except ValueError:
            pass

    if purity is not None:
        query = query.where(Axie.purity_score >= purity)

    # Count
    count_result = await db.execute(select(func.count()).select_from(query.subquery()))
    total = count_result.scalar() or 0

    # Paginate
    offset = (page - 1) * per_page
    query = query.offset(offset).limit(per_page)

    result = await db.execute(query)
    axies = result.scalars().all()

    return {
        "success": True,
        "data": [axie.to_dict() for axie in axies],
        "meta": {
            "total": total,
            "page": page,
            "per_page": per_page,
            "total_pages": (total + per_page - 1) // per_page,
        }
    }


@router.get("/{address}/trades")
async def get_wallet_trades(
    address: str,
    type_: str = Query("all", alias="type", description="Trade type: buy, sell, all"),
    from_date: Optional[datetime] = Query(None),
    to_date: Optional[datetime] = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """
    Get trading history for a wallet.
    """
    address = address.lower()

    if type_ == "buy":
        query = select(Sale).where(Sale.buyer_address == address)
    elif type_ == "sell":
        query = select(Sale).where(Sale.seller_address == address)
    else:
        query = select(Sale).where(
            or_(Sale.buyer_address == address, Sale.seller_address == address)
        )

    if from_date:
        query = query.where(Sale.sold_at >= from_date)
    if to_date:
        query = query.where(Sale.sold_at <= to_date)

    query = query.order_by(Sale.sold_at.desc())

    # Count
    count_result = await db.execute(select(func.count()).select_from(query.subquery()))
    total = count_result.scalar() or 0

    # Paginate
    offset = (page - 1) * per_page
    query = query.offset(offset).limit(per_page)

    result = await db.execute(query)
    sales = result.scalars().all()

    trades = []
    for sale in sales:
        trade_type = "buy" if sale.buyer_address == address else "sell"
        trades.append({
            "id": sale.id,
            "type": trade_type,
            "axie_id": sale.axie_id,
            "counterparty": sale.seller_address if trade_type == "buy" else sale.buyer_address,
            "price_eth": float(sale.price_eth),
            "price_usd": float(sale.price_usd) if sale.price_usd else None,
            "timestamp": sale.sold_at.isoformat(),
            "tx_hash": sale.tx_hash,
        })

    return {
        "success": True,
        "data": trades,
        "meta": {
            "total": total,
            "page": page,
            "per_page": per_page,
            "total_pages": (total + per_page - 1) // per_page,
        }
    }
