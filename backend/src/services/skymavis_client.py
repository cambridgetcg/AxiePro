"""
Sky Mavis GraphQL Client for Axie Infinity data.

Provides access to:
- Axie metadata and genes
- Marketplace listings and sales
- Breeding data
- Battle statistics
"""

import asyncio
import logging
from datetime import datetime
from typing import Any, Optional
from dataclasses import dataclass, field
from enum import Enum

import httpx

from src.config import get_settings
from src.utils.gene_parser import GeneParser, AxieGenes

logger = logging.getLogger(__name__)


class AxieClass(str, Enum):
    BEAST = "Beast"
    BUG = "Bug"
    BIRD = "Bird"
    PLANT = "Plant"
    AQUATIC = "Aquatic"
    REPTILE = "Reptile"
    MECH = "Mech"
    DAWN = "Dawn"
    DUSK = "Dusk"


class ListingStatus(str, Enum):
    ACTIVE = "active"
    SOLD = "sold"
    CANCELLED = "cancelled"


@dataclass
class AxiePart:
    """Single body part data."""
    id: str
    name: str
    class_: str
    type: str
    specialGenes: Optional[str] = None
    abilities: list[dict] = field(default_factory=list)


@dataclass
class AxieData:
    """Complete Axie data from Sky Mavis API."""
    id: int
    name: str
    class_: str
    stage: int
    breedCount: int
    genes: str
    image: str
    owner: str
    birthDate: Optional[datetime]
    matronId: Optional[int]
    sireId: Optional[int]
    parts: list[AxiePart]
    stats: dict
    title: Optional[str] = None
    auction: Optional[dict] = None  # Current listing if any

    # Parsed genes (lazy loaded)
    _parsed_genes: Optional[AxieGenes] = field(default=None, repr=False)

    @property
    def parsed_genes(self) -> Optional[AxieGenes]:
        """Get parsed gene data."""
        if self._parsed_genes is None and self.genes:
            parser = GeneParser()
            self._parsed_genes = parser.parse(self.genes)
        return self._parsed_genes

    @property
    def purity_score(self) -> int:
        """Get purity score (dominant parts matching class)."""
        if self.parsed_genes:
            return self.parsed_genes.purity_score
        return 0

    @classmethod
    def from_graphql(cls, data: dict) -> "AxieData":
        """Create from GraphQL response."""
        parts = []
        for part_data in data.get("parts", []):
            parts.append(AxiePart(
                id=part_data.get("id", ""),
                name=part_data.get("name", ""),
                class_=part_data.get("class", ""),
                type=part_data.get("type", ""),
                specialGenes=part_data.get("specialGenes"),
                abilities=part_data.get("abilities", []),
            ))

        birth_date = None
        if data.get("birthDate"):
            try:
                birth_date = datetime.fromtimestamp(data["birthDate"])
            except (ValueError, TypeError):
                pass

        return cls(
            id=int(data.get("id", 0)),
            name=data.get("name", ""),
            class_=data.get("class", "Unknown"),
            stage=data.get("stage", 0),
            breedCount=data.get("breedCount", 0),
            genes=data.get("genes", ""),
            image=data.get("image", ""),
            owner=data.get("owner", ""),
            birthDate=birth_date,
            matronId=int(data["matronId"]) if data.get("matronId") else None,
            sireId=int(data["sireId"]) if data.get("sireId") else None,
            parts=parts,
            stats=data.get("stats", {}),
            title=data.get("title"),
            auction=data.get("auction"),
        )


@dataclass
class MarketplaceListing:
    """Marketplace listing data."""
    axie_id: int
    seller: str
    current_price: str  # In wei
    current_price_usd: Optional[float]
    started_at: datetime
    expires_at: Optional[datetime]
    axie: Optional[AxieData] = None

    @classmethod
    def from_graphql(cls, data: dict) -> "MarketplaceListing":
        """Create from GraphQL response."""
        auction = data.get("auction", {})

        started_at = datetime.now()
        if auction.get("startedAt"):
            try:
                started_at = datetime.fromtimestamp(int(auction["startedAt"]))
            except (ValueError, TypeError):
                pass

        expires_at = None
        if auction.get("duration"):
            try:
                expires_at = datetime.fromtimestamp(
                    int(auction["startedAt"]) + int(auction["duration"])
                )
            except (ValueError, TypeError):
                pass

        axie = None
        if data.get("id"):
            axie = AxieData.from_graphql(data)

        return cls(
            axie_id=int(data.get("id", 0)),
            seller=auction.get("seller", ""),
            current_price=auction.get("currentPrice", "0"),
            current_price_usd=auction.get("currentPriceUSD"),
            started_at=started_at,
            expires_at=expires_at,
            axie=axie,
        )


@dataclass
class SaleRecord:
    """Historical sale record."""
    axie_id: int
    seller: str
    buyer: str
    price: str  # In wei
    price_usd: Optional[float]
    timestamp: datetime
    tx_hash: str


class SkyMavisAPIError(Exception):
    """Raised when Sky Mavis API returns an error."""
    def __init__(self, message: str, errors: Optional[list] = None):
        self.message = message
        self.errors = errors or []
        super().__init__(message)


class SkyMavisClient:
    """
    Async GraphQL client for Sky Mavis APIs.

    Usage:
        async with SkyMavisClient() as client:
            axie = await client.get_axie(12345)
    """

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize Sky Mavis client.

        Args:
            api_key: Sky Mavis API key. If not provided, uses settings.
        """
        settings = get_settings()
        self.api_key = api_key or settings.skymavis_api_key
        self.graphql_url = settings.skymavis_graphql_url
        self.marketplace_url = settings.skymavis_marketplace_url
        self.rate_limit = settings.skymavis_rate_limit
        self._client: Optional[httpx.AsyncClient] = None
        self._request_count = 0
        self._last_reset = datetime.now()

    async def __aenter__(self) -> "SkyMavisClient":
        """Async context manager entry."""
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        self._client = httpx.AsyncClient(
            timeout=30.0,
            headers=headers,
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self._client:
            await self._client.aclose()
            self._client = None

    async def _graphql_request(
        self,
        query: str,
        variables: Optional[dict] = None,
        use_marketplace: bool = False,
    ) -> dict[str, Any]:
        """
        Execute a GraphQL query.

        Args:
            query: GraphQL query string
            variables: Query variables
            use_marketplace: Use marketplace endpoint instead of main

        Returns:
            Query response data
        """
        if not self._client:
            raise RuntimeError("Client not initialized. Use async context manager.")

        await self._check_rate_limit()

        url = self.marketplace_url if use_marketplace else self.graphql_url

        payload = {"query": query}
        if variables:
            payload["variables"] = variables

        try:
            response = await self._client.post(url, json=payload)

            if response.status_code == 429:
                retry_after = int(response.headers.get("Retry-After", 60))
                logger.warning(f"Rate limited, waiting {retry_after}s")
                await asyncio.sleep(retry_after)
                return await self._graphql_request(query, variables, use_marketplace)

            if response.status_code >= 400:
                raise SkyMavisAPIError(
                    f"HTTP {response.status_code}: {response.text}"
                )

            data = response.json()

            if "errors" in data:
                error_msg = data["errors"][0].get("message", "Unknown error")
                raise SkyMavisAPIError(error_msg, data["errors"])

            return data.get("data", {})

        except httpx.RequestError as e:
            logger.error(f"Request error: {e}")
            raise SkyMavisAPIError(str(e))

    async def _check_rate_limit(self):
        """Check and enforce rate limiting."""
        now = datetime.now()
        elapsed = (now - self._last_reset).total_seconds()

        if elapsed >= 60:
            self._request_count = 0
            self._last_reset = now

        if self._request_count >= self.rate_limit:
            wait_time = 60 - elapsed
            if wait_time > 0:
                logger.info(f"Rate limit reached, waiting {wait_time:.1f}s")
                await asyncio.sleep(wait_time)
                self._request_count = 0
                self._last_reset = datetime.now()

        self._request_count += 1

    # =========================================================================
    # Axie Queries
    # =========================================================================

    async def get_axie(self, axie_id: int) -> Optional[AxieData]:
        """
        Get detailed data for a single Axie.

        Args:
            axie_id: Axie ID number

        Returns:
            AxieData or None if not found
        """
        query = """
        query GetAxie($axieId: ID!) {
            axie(axieId: $axieId) {
                id
                name
                class
                stage
                breedCount
                genes
                image
                owner
                birthDate
                matronId
                sireId
                title
                parts {
                    id
                    name
                    class
                    type
                    specialGenes
                    abilities {
                        id
                        name
                        attack
                        defense
                        energy
                        description
                    }
                }
                stats {
                    hp
                    speed
                    skill
                    morale
                }
                auction {
                    currentPrice
                    currentPriceUSD
                    startedAt
                    duration
                    seller
                }
            }
        }
        """

        data = await self._graphql_request(query, {"axieId": str(axie_id)})
        axie_data = data.get("axie")

        if not axie_data:
            return None

        return AxieData.from_graphql(axie_data)

    async def get_axies_brief(self, axie_ids: list[int]) -> list[AxieData]:
        """
        Get brief data for multiple Axies.

        Args:
            axie_ids: List of Axie IDs

        Returns:
            List of AxieData
        """
        # Build query for multiple axies
        query_parts = []
        for i, axie_id in enumerate(axie_ids):
            query_parts.append(f"""
                axie{i}: axie(axieId: "{axie_id}") {{
                    id
                    name
                    class
                    breedCount
                    genes
                    image
                    owner
                    parts {{
                        id
                        name
                        class
                        type
                    }}
                    stats {{
                        hp
                        speed
                        skill
                        morale
                    }}
                    auction {{
                        currentPrice
                        currentPriceUSD
                    }}
                }}
            """)

        query = "query GetAxies {\n" + "\n".join(query_parts) + "\n}"

        data = await self._graphql_request(query)

        axies = []
        for i in range(len(axie_ids)):
            axie_data = data.get(f"axie{i}")
            if axie_data:
                axies.append(AxieData.from_graphql(axie_data))

        return axies

    async def search_axies(
        self,
        owner: Optional[str] = None,
        classes: Optional[list[str]] = None,
        breed_count: Optional[tuple[int, int]] = None,  # (min, max)
        parts: Optional[list[str]] = None,
        purity: Optional[tuple[int, int]] = None,  # (min, max)
        price_range: Optional[tuple[float, float]] = None,  # (min, max) in ETH
        sort_by: str = "PriceAsc",
        size: int = 20,
        offset: int = 0,
        auction_type: str = "Sale",  # Sale, All, NotForSale
    ) -> tuple[list[AxieData], int]:
        """
        Search for Axies with filters.

        Args:
            owner: Filter by owner address
            classes: Filter by classes
            breed_count: (min, max) breed count range
            parts: Filter by part IDs
            purity: (min, max) purity score range
            price_range: (min, max) price in ETH
            sort_by: Sort order (PriceAsc, PriceDesc, IdAsc, IdDesc, etc.)
            size: Results per page
            offset: Pagination offset
            auction_type: Filter by listing status

        Returns:
            Tuple of (Axie list, total count)
        """
        query = """
        query SearchAxies($criteria: AxieSearchCriteria!, $sort: SortBy!, $size: Int!, $from: Int!) {
            axies(criteria: $criteria, sort: $sort, size: $size, from: $from) {
                total
                results {
                    id
                    name
                    class
                    breedCount
                    genes
                    image
                    owner
                    parts {
                        id
                        name
                        class
                        type
                    }
                    stats {
                        hp
                        speed
                        skill
                        morale
                    }
                    auction {
                        currentPrice
                        currentPriceUSD
                        startedAt
                        seller
                    }
                }
            }
        }
        """

        criteria: dict[str, Any] = {"auctionType": auction_type}

        if owner:
            criteria["owner"] = owner

        if classes:
            criteria["classes"] = classes

        if breed_count:
            criteria["breedCount"] = list(breed_count)

        if parts:
            criteria["parts"] = parts

        if purity:
            criteria["pureness"] = list(purity)

        if price_range:
            # Convert ETH to wei
            criteria["priceRange"] = [
                str(int(price_range[0] * 10**18)) if price_range[0] else None,
                str(int(price_range[1] * 10**18)) if price_range[1] else None,
            ]

        variables = {
            "criteria": criteria,
            "sort": sort_by,
            "size": size,
            "from": offset,
        }

        data = await self._graphql_request(query, variables)
        axies_data = data.get("axies", {})

        axies = [
            AxieData.from_graphql(item)
            for item in axies_data.get("results", [])
        ]
        total = axies_data.get("total", 0)

        return axies, total

    # =========================================================================
    # Marketplace Queries
    # =========================================================================

    async def get_recent_listings(
        self,
        classes: Optional[list[str]] = None,
        size: int = 20,
        offset: int = 0,
    ) -> tuple[list[MarketplaceListing], int]:
        """
        Get recently listed Axies.

        Args:
            classes: Filter by classes
            size: Results per page
            offset: Pagination offset

        Returns:
            Tuple of (listings, total count)
        """
        axies, total = await self.search_axies(
            classes=classes,
            sort_by="Latest",
            size=size,
            offset=offset,
            auction_type="Sale",
        )

        listings = []
        for axie in axies:
            if axie.auction:
                listings.append(MarketplaceListing(
                    axie_id=axie.id,
                    seller=axie.auction.get("seller", ""),
                    current_price=axie.auction.get("currentPrice", "0"),
                    current_price_usd=axie.auction.get("currentPriceUSD"),
                    started_at=datetime.now(),  # Would need to parse from auction data
                    expires_at=None,
                    axie=axie,
                ))

        return listings, total

    async def get_floor_prices(
        self,
        classes: Optional[list[str]] = None,
    ) -> dict[str, dict]:
        """
        Get current floor prices by class.

        Args:
            classes: Classes to check (defaults to all)

        Returns:
            Dict mapping class to floor price data
        """
        if classes is None:
            classes = ["Beast", "Bug", "Bird", "Plant", "Aquatic", "Reptile"]

        results = {}

        for axie_class in classes:
            axies, _ = await self.search_axies(
                classes=[axie_class],
                sort_by="PriceAsc",
                size=1,
                auction_type="Sale",
            )

            if axies and axies[0].auction:
                results[axie_class.lower()] = {
                    "floor_price_wei": axies[0].auction.get("currentPrice", "0"),
                    "floor_price_usd": axies[0].auction.get("currentPriceUSD"),
                    "axie_id": axies[0].id,
                }
            else:
                results[axie_class.lower()] = {
                    "floor_price_wei": None,
                    "floor_price_usd": None,
                    "axie_id": None,
                }

        return results

    # =========================================================================
    # Breeding Queries
    # =========================================================================

    async def get_axie_children(
        self,
        axie_id: int,
        size: int = 20,
        offset: int = 0,
    ) -> tuple[list[AxieData], int]:
        """
        Get children of an Axie.

        Args:
            axie_id: Parent Axie ID
            size: Results per page
            offset: Pagination offset

        Returns:
            Tuple of (children list, total count)
        """
        query = """
        query GetAxieChildren($axieId: ID!, $size: Int!, $from: Int!) {
            axie(axieId: $axieId) {
                children(size: $size, from: $from) {
                    total
                    results {
                        id
                        name
                        class
                        breedCount
                        genes
                        image
                        owner
                        birthDate
                        parts {
                            id
                            name
                            class
                            type
                        }
                        stats {
                            hp
                            speed
                            skill
                            morale
                        }
                    }
                }
            }
        }
        """

        data = await self._graphql_request(query, {
            "axieId": str(axie_id),
            "size": size,
            "from": offset,
        })

        axie_data = data.get("axie", {})
        children_data = axie_data.get("children", {})

        children = [
            AxieData.from_graphql(item)
            for item in children_data.get("results", [])
        ]
        total = children_data.get("total", 0)

        return children, total

    async def get_axie_siblings(
        self,
        axie_id: int,
    ) -> list[AxieData]:
        """
        Get siblings of an Axie (same parents).

        Args:
            axie_id: Axie ID

        Returns:
            List of sibling Axies
        """
        # First get the axie's parents
        axie = await self.get_axie(axie_id)
        if not axie or not axie.matronId or not axie.sireId:
            return []

        # Then search for axies with same parents
        # Note: This is simplified - a more complete implementation
        # would use a dedicated siblings query if available
        matron_children, _ = await self.get_axie_children(axie.matronId, size=100)

        # Filter to only those that also have the same sire
        siblings = [
            child for child in matron_children
            if child.id != axie_id and child.sireId == axie.sireId
        ]

        return siblings


# Convenience functions
async def get_axie_quick(axie_id: int) -> Optional[AxieData]:
    """Quick function to get an Axie's data."""
    async with SkyMavisClient() as client:
        return await client.get_axie(axie_id)
