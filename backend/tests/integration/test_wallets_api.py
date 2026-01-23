"""
Integration tests for Wallets API endpoints.

Tests the following routes:
- GET /wallets/{address}
- GET /wallets/{address}/axies
- GET /wallets/{address}/trades
- GET /wallets/{address}/portfolio
- GET /wallets/{address}/portfolio/holdings
- POST /wallets/{address}/portfolio/refresh
- PATCH /wallets/{address}/holdings/{axie_id}/cost-basis
"""

import pytest
from datetime import datetime, timedelta
from decimal import Decimal
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.models import Axie, AxieClass, Sale, Wallet, WalletHolding


@pytest.fixture
async def wallet_data(db: AsyncSession) -> dict:
    """Create test data for wallet tests."""
    # Create a tracked wallet
    wallet_address = "0x" + "a" * 40
    wallet = Wallet(
        address=wallet_address,
        alias="Test Whale",
        first_seen=datetime.utcnow() - timedelta(days=90),
        last_active=datetime.utcnow() - timedelta(hours=2),
        total_trades=50,
        total_buy_volume_eth=Decimal("5.0"),
        total_sell_volume_eth=Decimal("4.5"),
        is_whale=True,
    )
    db.add(wallet)

    # Create axies owned by the wallet
    axies = []
    for i in range(5):
        axie = Axie(
            id=6000 + i,
            name=f"Wallet Axie {i}",
            class_=AxieClass.BEAST if i < 3 else AxieClass.AQUATIC,
            genes="0x" + "b" * 64,
            breed_count=i % 3,
            purity_score=4 + (i % 3),
            owner_address=wallet_address,
        )
        db.add(axie)
        axies.append(axie)

    # Create wallet holdings with P&L data
    holdings = []
    for i, axie in enumerate(axies):
        holding = WalletHolding(
            wallet_address=wallet_address,
            axie_id=axie.id,
            acquired_at=datetime.utcnow() - timedelta(days=30 - i),
            acquisition_type="purchase",
            cost_basis_eth=Decimal(f"0.0{i+1}") if i < 3 else None,
            current_value_eth=Decimal(f"0.0{i+2}") if i < 4 else None,
            last_valued_at=datetime.utcnow() - timedelta(hours=1) if i < 4 else None,
        )
        db.add(holding)
        holdings.append(holding)

    # Create sales history
    sales = []
    for i in range(6):
        is_buy = i % 2 == 0
        sale = Sale(
            axie_id=6000 + (i % 5),
            seller_address="0x" + "c" * 40 if is_buy else wallet_address,
            buyer_address=wallet_address if is_buy else "0x" + "d" * 40,
            price_eth=Decimal(f"0.0{i+1}"),
            price_usd=Decimal(f"{(i+1)*20}"),
            sold_at=datetime.utcnow() - timedelta(days=i * 5),
            tx_hash=f"0x{'tx'[i % 2]}" + "0" * 62,
        )
        db.add(sale)
        sales.append(sale)

    await db.commit()

    return {
        "wallet": wallet,
        "wallet_address": wallet_address,
        "axies": axies,
        "holdings": holdings,
        "sales": sales,
    }


class TestGetWallet:
    """Tests for GET /wallets/{address} endpoint."""

    async def test_get_tracked_wallet(
        self, client: AsyncClient, wallet_data: dict
    ):
        """Should return tracked wallet info."""
        address = wallet_data["wallet_address"]
        response = await client.get(f"/wallets/{address}")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["address"] == address.lower()
        assert data["data"]["is_whale"] is True
        assert data["data"]["alias"] == "Test Whale"

    async def test_get_untracked_wallet(
        self, client: AsyncClient, wallet_data: dict
    ):
        """Should return basic info for untracked wallet."""
        address = "0x" + "e" * 40
        response = await client.get(f"/wallets/{address}")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["address"] == address.lower()

    async def test_get_wallet_normalizes_address(
        self, client: AsyncClient, wallet_data: dict
    ):
        """Should normalize address to lowercase."""
        address = wallet_data["wallet_address"].upper()
        response = await client.get(f"/wallets/{address}")

        assert response.status_code == 200
        data = response.json()
        assert data["data"]["address"] == address.lower()


class TestGetWalletAxies:
    """Tests for GET /wallets/{address}/axies endpoint."""

    async def test_get_wallet_axies(
        self, client: AsyncClient, wallet_data: dict
    ):
        """Should return axies owned by wallet."""
        address = wallet_data["wallet_address"]
        response = await client.get(f"/wallets/{address}/axies")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert len(data["data"]) == len(wallet_data["axies"])

    async def test_get_wallet_axies_by_class(
        self, client: AsyncClient, wallet_data: dict
    ):
        """Should filter axies by class."""
        address = wallet_data["wallet_address"]
        response = await client.get(f"/wallets/{address}/axies?class=beast")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        for axie in data["data"]:
            assert axie["class"] == "beast"

    async def test_get_wallet_axies_by_purity(
        self, client: AsyncClient, wallet_data: dict
    ):
        """Should filter axies by minimum purity."""
        address = wallet_data["wallet_address"]
        response = await client.get(f"/wallets/{address}/axies?purity=5")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        for axie in data["data"]:
            assert axie["purity_score"] >= 5

    async def test_get_wallet_axies_pagination(
        self, client: AsyncClient, wallet_data: dict
    ):
        """Should paginate results."""
        address = wallet_data["wallet_address"]
        response = await client.get(
            f"/wallets/{address}/axies?page=1&per_page=2"
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert len(data["data"]) == 2
        assert data["meta"]["total"] == len(wallet_data["axies"])


class TestGetWalletTrades:
    """Tests for GET /wallets/{address}/trades endpoint."""

    async def test_get_wallet_trades(
        self, client: AsyncClient, wallet_data: dict
    ):
        """Should return all trades for wallet."""
        address = wallet_data["wallet_address"]
        response = await client.get(f"/wallets/{address}/trades")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert len(data["data"]) == len(wallet_data["sales"])

    async def test_get_wallet_trades_buys_only(
        self, client: AsyncClient, wallet_data: dict
    ):
        """Should filter to buy trades only."""
        address = wallet_data["wallet_address"]
        response = await client.get(f"/wallets/{address}/trades?type=buy")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        for trade in data["data"]:
            assert trade["type"] == "buy"

    async def test_get_wallet_trades_sells_only(
        self, client: AsyncClient, wallet_data: dict
    ):
        """Should filter to sell trades only."""
        address = wallet_data["wallet_address"]
        response = await client.get(f"/wallets/{address}/trades?type=sell")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        for trade in data["data"]:
            assert trade["type"] == "sell"

    async def test_get_wallet_trades_date_filter(
        self, client: AsyncClient, wallet_data: dict
    ):
        """Should filter by date range."""
        address = wallet_data["wallet_address"]
        from_date = (datetime.utcnow() - timedelta(days=10)).isoformat()
        response = await client.get(
            f"/wallets/{address}/trades?from_date={from_date}"
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True


class TestGetPortfolioSummary:
    """Tests for GET /wallets/{address}/portfolio endpoint."""

    async def test_get_portfolio_summary(
        self, client: AsyncClient, wallet_data: dict
    ):
        """Should return portfolio P&L summary."""
        address = wallet_data["wallet_address"]
        response = await client.get(f"/wallets/{address}/portfolio")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "holdings_count" in data["data"]
        assert "total_cost_basis_eth" in data["data"]

    async def test_get_portfolio_summary_not_found(self, client: AsyncClient):
        """Should return 404 for untracked wallet."""
        address = "0x" + "f" * 40
        response = await client.get(f"/wallets/{address}/portfolio")

        assert response.status_code == 404


class TestGetPortfolioHoldings:
    """Tests for GET /wallets/{address}/portfolio/holdings endpoint."""

    async def test_get_portfolio_holdings(
        self, client: AsyncClient, wallet_data: dict
    ):
        """Should return detailed holdings."""
        address = wallet_data["wallet_address"]
        response = await client.get(f"/wallets/{address}/portfolio/holdings")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert len(data["data"]) == len(wallet_data["holdings"])

    async def test_get_portfolio_holdings_with_pnl_only(
        self, client: AsyncClient, wallet_data: dict
    ):
        """Should filter to holdings with cost basis."""
        address = wallet_data["wallet_address"]
        response = await client.get(
            f"/wallets/{address}/portfolio/holdings?only_with_pnl=true"
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        for holding in data["data"]:
            assert holding["has_cost_basis"] is True

    async def test_get_portfolio_holdings_sorting(
        self, client: AsyncClient, wallet_data: dict
    ):
        """Should sort holdings."""
        address = wallet_data["wallet_address"]
        response = await client.get(
            f"/wallets/{address}/portfolio/holdings?sort_by=cost_basis&sort_order=desc"
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    async def test_get_portfolio_holdings_pagination(
        self, client: AsyncClient, wallet_data: dict
    ):
        """Should paginate results."""
        address = wallet_data["wallet_address"]
        response = await client.get(
            f"/wallets/{address}/portfolio/holdings?per_page=2"
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert len(data["data"]) <= 2


class TestRefreshPortfolioValuations:
    """Tests for POST /wallets/{address}/portfolio/refresh endpoint."""

    async def test_refresh_portfolio(
        self, client: AsyncClient, wallet_data: dict
    ):
        """Should trigger portfolio refresh."""
        address = wallet_data["wallet_address"]
        response = await client.post(f"/wallets/{address}/portfolio/refresh")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["wallet_address"] == address.lower()

    async def test_refresh_portfolio_not_found(self, client: AsyncClient):
        """Should return 404 for unknown wallet."""
        address = "0x" + "f" * 40
        response = await client.post(f"/wallets/{address}/portfolio/refresh")

        assert response.status_code == 404
