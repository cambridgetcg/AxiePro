"""
Wallet API endpoints.

Provides routes for:
- Wallet overview and stats
- Holdings with P&L tracking
- Portfolio valuation and analytics
- Trade history
"""

from datetime import datetime
from decimal import Decimal
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from pydantic import BaseModel, Field
from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.models import Wallet, WalletHolding, Axie, Sale, get_db
from src.services.moralis_client import MoralisClient
from src.services.wallet_balance_service import WalletBalanceService, get_wallet_balance_service
from src.api.deps import get_authenticated_wallet

router = APIRouter(prefix="/wallets", tags=["wallets"])


# =========================================================================
# Pydantic Models for Portfolio P&L
# =========================================================================

class HoldingPnL(BaseModel):
    """Individual holding with P&L data."""
    axie_id: int
    acquired_at: Optional[str]
    acquisition_type: Optional[str]
    cost_basis_eth: Optional[float]
    current_value_eth: Optional[float]
    last_valued_at: Optional[str]
    unrealized_pnl_eth: Optional[float]
    unrealized_pnl_percent: Optional[float]
    has_cost_basis: bool


class PortfolioSummary(BaseModel):
    """Aggregated portfolio P&L summary."""
    wallet_address: str
    holdings_count: int
    total_cost_basis_eth: Optional[float]
    total_current_value_eth: Optional[float]
    total_unrealized_pnl_eth: Optional[float]
    total_unrealized_pnl_percent: Optional[float]
    holdings_with_cost_basis: int
    holdings_missing_cost_basis: int
    last_valuation_at: Optional[str]


class PortfolioResponse(BaseModel):
    """Response for portfolio endpoints."""
    success: bool
    data: dict
    meta: dict


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


# =========================================================================
# Portfolio P&L Endpoints
# =========================================================================

@router.get("/{address}/portfolio", response_model=PortfolioResponse)
async def get_portfolio_summary(
    address: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Get portfolio P&L summary for a wallet.

    Returns aggregated portfolio metrics:
    - Total holdings value (using hedonic valuations)
    - Total cost basis (from acquisition prices)
    - Unrealized P&L (absolute and percentage)
    - Coverage stats (how many holdings have cost basis)
    """
    address = address.lower()

    # Get wallet with holdings
    result = await db.execute(
        select(Wallet)
        .where(Wallet.address == address)
        .options(selectinload(Wallet.holdings))
    )
    wallet = result.scalar_one_or_none()

    if not wallet:
        raise HTTPException(
            status_code=404,
            detail=f"Wallet {address} not found or not tracked"
        )

    # Aggregate P&L metrics
    holdings = wallet.holdings
    total_cost_basis = Decimal(0)
    total_current_value = Decimal(0)
    holdings_with_basis = 0
    holdings_missing_basis = 0
    last_valued = None

    for holding in holdings:
        # Recompute P&L for each holding
        holding.compute_unrealized_pnl()

        if holding.has_cost_basis:
            total_cost_basis += holding.cost_basis_eth or Decimal(0)
            holdings_with_basis += 1
        else:
            holdings_missing_basis += 1

        if holding.current_value_eth:
            total_current_value += holding.current_value_eth

        if holding.last_valued_at:
            if last_valued is None or holding.last_valued_at > last_valued:
                last_valued = holding.last_valued_at

    # Calculate total unrealized P&L
    total_pnl = None
    total_pnl_percent = None

    if total_cost_basis > 0 and total_current_value > 0:
        total_pnl = total_current_value - total_cost_basis
        total_pnl_percent = (total_pnl / total_cost_basis) * 100

    summary = PortfolioSummary(
        wallet_address=address,
        holdings_count=len(holdings),
        total_cost_basis_eth=float(total_cost_basis) if total_cost_basis else None,
        total_current_value_eth=float(total_current_value) if total_current_value else None,
        total_unrealized_pnl_eth=float(total_pnl) if total_pnl else None,
        total_unrealized_pnl_percent=float(total_pnl_percent) if total_pnl_percent else None,
        holdings_with_cost_basis=holdings_with_basis,
        holdings_missing_cost_basis=holdings_missing_basis,
        last_valuation_at=last_valued.isoformat() if last_valued else None,
    )

    return {
        "success": True,
        "data": summary.model_dump(),
        "meta": {
            "timestamp": datetime.utcnow().isoformat(),
            "coverage_percent": round(
                (holdings_with_basis / len(holdings) * 100) if holdings else 0, 1
            ),
        }
    }


@router.get("/{address}/portfolio/holdings")
async def get_portfolio_holdings(
    address: str,
    include_valuation: bool = Query(True, description="Include current valuation"),
    only_with_pnl: bool = Query(False, description="Only return holdings with cost basis"),
    sort_by: str = Query(
        "unrealized_pnl",
        description="Sort by: unrealized_pnl, cost_basis, current_value, acquired_at"
    ),
    sort_order: str = Query("desc", description="Sort order: asc, desc"),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """
    Get detailed holdings with P&L for each Axie.

    Returns individual holding-level P&L data for portfolio analysis.
    Use `only_with_pnl=true` to filter for holdings that have cost basis.
    """
    address = address.lower()

    # Get wallet with holdings
    result = await db.execute(
        select(Wallet)
        .where(Wallet.address == address)
        .options(selectinload(Wallet.holdings))
    )
    wallet = result.scalar_one_or_none()

    if not wallet:
        raise HTTPException(
            status_code=404,
            detail=f"Wallet {address} not found or not tracked"
        )

    holdings_data = []

    for holding in wallet.holdings:
        # Recompute P&L
        holding.compute_unrealized_pnl()

        # Filter if needed
        if only_with_pnl and not holding.has_cost_basis:
            continue

        holdings_data.append(HoldingPnL(
            axie_id=holding.axie_id,
            acquired_at=holding.acquired_at.isoformat() if holding.acquired_at else None,
            acquisition_type=holding.acquisition_type,
            cost_basis_eth=float(holding.cost_basis_eth) if holding.cost_basis_eth else None,
            current_value_eth=float(holding.current_value_eth) if holding.current_value_eth else None,
            last_valued_at=holding.last_valued_at.isoformat() if holding.last_valued_at else None,
            unrealized_pnl_eth=float(holding.unrealized_pnl_eth) if holding.unrealized_pnl_eth else None,
            unrealized_pnl_percent=float(holding.unrealized_pnl_percent) if holding.unrealized_pnl_percent else None,
            has_cost_basis=holding.has_cost_basis,
        ))

    # Sort
    def sort_key(h):
        if sort_by == "unrealized_pnl":
            return h.unrealized_pnl_eth or 0
        elif sort_by == "cost_basis":
            return h.cost_basis_eth or 0
        elif sort_by == "current_value":
            return h.current_value_eth or 0
        elif sort_by == "acquired_at":
            return h.acquired_at or ""
        return 0

    reverse = sort_order == "desc"
    holdings_data.sort(key=sort_key, reverse=reverse)

    # Paginate
    total = len(holdings_data)
    offset = (page - 1) * per_page
    holdings_data = holdings_data[offset:offset + per_page]

    return {
        "success": True,
        "data": [h.model_dump() for h in holdings_data],
        "meta": {
            "total": total,
            "page": page,
            "per_page": per_page,
            "total_pages": (total + per_page - 1) // per_page if total > 0 else 0,
            "sort_by": sort_by,
            "sort_order": sort_order,
        }
    }


@router.post("/{address}/portfolio/refresh")
async def refresh_portfolio_valuations(
    address: str,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """
    Trigger refresh of portfolio valuations.

    Updates current_value_eth for all holdings using the hedonic
    valuation model. Runs in the background.
    """
    address = address.lower()

    # Verify wallet exists
    result = await db.execute(
        select(Wallet).where(Wallet.address == address)
    )
    wallet = result.scalar_one_or_none()

    if not wallet:
        raise HTTPException(
            status_code=404,
            detail=f"Wallet {address} not found"
        )

    async def refresh_task():
        """Background task to refresh valuations."""
        from src.services.valuation import HedonicValuationService

        # Get holdings
        holdings_result = await db.execute(
            select(WalletHolding)
            .where(WalletHolding.wallet_address == address)
        )
        holdings = holdings_result.scalars().all()

        if not holdings:
            return

        # Get Axie IDs
        axie_ids = [h.axie_id for h in holdings]

        # Batch valuate
        service = HedonicValuationService(db)
        valuations = await service.batch_valuate(axie_ids)

        # Update holdings with valuations
        valuation_map = {v.axie_id: v for v in valuations}
        now = datetime.utcnow()

        for holding in holdings:
            val = valuation_map.get(holding.axie_id)
            if val and val.ensemble_value_eth:
                holding.current_value_eth = val.ensemble_value_eth
                holding.last_valued_at = now
                holding.compute_unrealized_pnl()

        await db.commit()

    background_tasks.add_task(refresh_task)

    return {
        "success": True,
        "message": "Portfolio valuation refresh started",
        "wallet_address": address,
    }


@router.patch("/{address}/holdings/{axie_id}/cost-basis")
async def update_holding_cost_basis(
    address: str,
    axie_id: int,
    cost_basis_eth: float = Query(..., description="Cost basis in ETH"),
    acquisition_type: Optional[str] = Query(
        None, description="Acquisition type: purchase, breeding, gift, transfer"
    ),
    acquired_at: Optional[datetime] = Query(None, description="Acquisition date"),
    authenticated_wallet: str = Depends(get_authenticated_wallet),
    db: AsyncSession = Depends(get_db),
):
    """
    Manually update cost basis for a holding.

    **Requires authentication**: Must sign a challenge with your wallet.
    You can only update cost basis for your own wallet.

    Use this for:
    - Holdings acquired before tracking began
    - Breeding offspring (set cost to parent+SLP cost)
    - Gifts/airdrops (set cost to 0 or FMV at acquisition)
    """
    address = address.lower()

    # Verify the authenticated wallet matches the target address
    if authenticated_wallet != address:
        raise HTTPException(
            status_code=403,
            detail="You can only update cost basis for your own wallet",
        )

    # Get holding
    result = await db.execute(
        select(WalletHolding)
        .where(WalletHolding.wallet_address == address)
        .where(WalletHolding.axie_id == axie_id)
    )
    holding = result.scalar_one_or_none()

    if not holding:
        raise HTTPException(
            status_code=404,
            detail=f"Holding not found for wallet {address}, axie {axie_id}"
        )

    # Update fields
    holding.cost_basis_eth = Decimal(str(cost_basis_eth))
    if acquisition_type:
        holding.acquisition_type = acquisition_type
    if acquired_at:
        holding.acquired_at = acquired_at

    # Recompute P&L
    holding.compute_unrealized_pnl()

    await db.commit()
    await db.refresh(holding)

    return {
        "success": True,
        "data": {
            "axie_id": holding.axie_id,
            "cost_basis_eth": float(holding.cost_basis_eth) if holding.cost_basis_eth else None,
            "acquisition_type": holding.acquisition_type,
            "acquired_at": holding.acquired_at.isoformat() if holding.acquired_at else None,
            "unrealized_pnl_eth": float(holding.unrealized_pnl_eth) if holding.unrealized_pnl_eth else None,
            "unrealized_pnl_percent": float(holding.unrealized_pnl_percent) if holding.unrealized_pnl_percent else None,
        },
        "message": "Cost basis updated successfully",
    }


# =========================================================================
# Wallet Token Balance Endpoints
# =========================================================================

class TokenBalance(BaseModel):
    """Individual token balance data."""
    token: str
    balance: float
    balance_usd: Optional[float]
    token_price_usd: Optional[float]
    last_updated: str


class WalletBalancesResponse(BaseModel):
    """Response for wallet balance endpoints."""
    success: bool
    data: dict[str, TokenBalance]
    meta: dict


@router.get("/{address}/balances", response_model=WalletBalancesResponse)
async def get_wallet_balances(
    address: str,
    force_refresh: bool = Query(
        False,
        description="Force refresh from blockchain (skip cache)"
    ),
    balance_service: WalletBalanceService = Depends(get_wallet_balance_service),
):
    """
    Get token balances for a wallet.

    Returns current balances for all supported tokens:
    - RON (Native Ronin token)
    - WETH (Wrapped ETH - Axie marketplace currency)
    - WRON (Wrapped RON)
    - AXS (Axie Infinity Shards)
    - SLP (Smooth Love Potion)

    **Caching**: Balances are cached for 5 minutes by default.
    Use `force_refresh=true` to bypass cache and fetch directly from blockchain.

    **USD Values**: Token prices are currently from config (future: price oracle).
    """
    address = address.lower()

    # Fetch balances via service (handles caching)
    balances = await balance_service.get_balances(
        wallet_address=address,
        force_refresh=force_refresh,
    )

    # Convert BalanceData to API response format
    balance_responses = {}
    for token, balance_data in balances.items():
        balance_responses[token] = TokenBalance(
            token=balance_data.token,
            balance=float(balance_data.balance),
            balance_usd=float(balance_data.balance_usd) if balance_data.balance_usd else None,
            token_price_usd=float(balance_data.token_price_usd) if balance_data.token_price_usd else None,
            last_updated=balance_data.last_updated.isoformat(),
        )

    # Calculate total portfolio value in USD
    total_usd = sum(
        float(b.balance_usd) if b.balance_usd else 0
        for b in balances.values()
    )

    return {
        "success": True,
        "data": balance_responses,
        "meta": {
            "wallet_address": address,
            "total_usd": round(total_usd, 2),
            "token_count": len(balances),
            "timestamp": datetime.utcnow().isoformat(),
            "from_cache": not force_refresh,
        }
    }


@router.post("/{address}/balances/refresh")
async def refresh_wallet_balances(
    address: str,
    balance_service: WalletBalanceService = Depends(get_wallet_balance_service),
):
    """
    Force refresh wallet balances from blockchain.

    Bypasses all caches and fetches fresh balance data directly from
    Ronin RPC. Updates database and Redis cache with new values.

    Use this endpoint:
    - After making a transaction
    - When real-time accuracy is needed
    - To verify cached balances

    **Rate Limits**: Calls Ronin RPC directly (5 calls per wallet).
    Cached for 5 minutes after refresh.
    """
    address = address.lower()

    # Force refresh from blockchain
    balances = await balance_service.refresh_balances(wallet_address=address)

    # Convert to response format
    balance_responses = {}
    for token, balance_data in balances.items():
        balance_responses[token] = TokenBalance(
            token=balance_data.token,
            balance=float(balance_data.balance),
            balance_usd=float(balance_data.balance_usd) if balance_data.balance_usd else None,
            token_price_usd=float(balance_data.token_price_usd) if balance_data.token_price_usd else None,
            last_updated=balance_data.last_updated.isoformat(),
        )

    total_usd = sum(
        float(b.balance_usd) if b.balance_usd else 0
        for b in balances.values()
    )

    return {
        "success": True,
        "data": balance_responses,
        "meta": {
            "wallet_address": address,
            "total_usd": round(total_usd, 2),
            "token_count": len(balances),
            "timestamp": datetime.utcnow().isoformat(),
            "refreshed_from_blockchain": True,
        },
        "message": "Balances refreshed successfully from blockchain",
    }
