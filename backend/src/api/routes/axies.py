"""
Axie API endpoints.

Provides routes for:
- Searching and filtering Axies
- Getting Axie details
- Family relationships (siblings, children)
"""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.models import Axie, AxiePart, Part, Listing, AxieClass, get_db
from src.utils.gene_parser import GeneParser
from src.services.skymavis_client import SkyMavisClient

router = APIRouter(prefix="/axies", tags=["axies"])


@router.get("")
async def search_axies(
    # Class filters
    class_: Optional[str] = Query(None, alias="class", description="Filter by class"),
    classes: Optional[str] = Query(None, description="Multiple classes, comma-separated"),

    # Purity filters
    purity: Optional[int] = Query(None, ge=0, le=6, description="Minimum purity score"),
    max_purity: Optional[int] = Query(None, ge=0, le=6, description="Maximum purity score"),

    # Breed count filter
    breed_count: Optional[int] = Query(None, ge=0, le=7, description="Maximum breed count"),
    min_breed_count: Optional[int] = Query(None, ge=0, le=7, description="Minimum breed count"),

    # Part filters
    parts: Optional[str] = Query(None, description="Required parts, comma-separated (e.g., mouth:nut-cracker)"),
    parts_match: str = Query("all", description="Match 'all' or 'any' parts"),
    gene_type: str = Query("d", description="Gene type for parts filter: d, r1, r2, any"),

    # Price filters
    min_price: Optional[float] = Query(None, description="Minimum listing price (ETH)"),
    max_price: Optional[float] = Query(None, description="Maximum listing price (ETH)"),
    listed_only: bool = Query(False, description="Only return listed Axies"),

    # Owner filter
    owner: Optional[str] = Query(None, description="Filter by owner wallet address"),

    # Pagination and sorting
    sort: str = Query("price", description="Sort field: price, purity, id, breed_count"),
    order: str = Query("asc", description="Sort order: asc, desc"),
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(20, ge=1, le=100, description="Results per page"),

    db: AsyncSession = Depends(get_db),
):
    """
    Search and filter Axies.

    Returns paginated results with optional filters for class, purity,
    breed count, parts, and price range.
    """
    # Build base query with eager loading to prevent N+1 queries
    query = select(Axie).options(
        selectinload(Axie.parts).selectinload(AxiePart.part),
        selectinload(Axie.listings),
    )

    # Apply class filter
    if class_:
        try:
            axie_class = AxieClass(class_.lower())
            query = query.where(Axie.class_ == axie_class)
        except ValueError:
            raise HTTPException(400, f"Invalid class: {class_}")

    if classes:
        class_list = []
        for c in classes.split(","):
            try:
                class_list.append(AxieClass(c.strip().lower()))
            except ValueError:
                pass
        if class_list:
            query = query.where(Axie.class_.in_(class_list))

    # Apply purity filter
    if purity is not None:
        query = query.where(Axie.purity_score >= purity)
    if max_purity is not None:
        query = query.where(Axie.purity_score <= max_purity)

    # Apply breed count filter
    if breed_count is not None:
        query = query.where(Axie.breed_count <= breed_count)
    if min_breed_count is not None:
        query = query.where(Axie.breed_count >= min_breed_count)

    # Apply owner filter
    if owner:
        query = query.where(Axie.owner_address == owner.lower())

    # Apply listing filters
    if listed_only or min_price is not None or max_price is not None:
        query = query.join(Listing, and_(
            Listing.axie_id == Axie.id,
            Listing.status == "active"
        ))

        if min_price is not None:
            query = query.where(Listing.price_eth >= min_price)
        if max_price is not None:
            query = query.where(Listing.price_eth <= max_price)

    # Apply sorting
    sort_column = {
        "price": Listing.price_eth if (listed_only or min_price or max_price) else Axie.id,
        "purity": Axie.purity_score,
        "id": Axie.id,
        "breed_count": Axie.breed_count,
    }.get(sort, Axie.id)

    if order == "desc":
        query = query.order_by(sort_column.desc())
    else:
        query = query.order_by(sort_column.asc())

    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Apply pagination
    offset = (page - 1) * per_page
    query = query.offset(offset).limit(per_page)

    # Execute query
    result = await db.execute(query)
    axies = result.scalars().all()

    # Format response
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


@router.get("/{axie_id}")
async def get_axie(
    axie_id: int,
    include_listing: bool = Query(True, description="Include current listing if any"),
    include_sales: bool = Query(False, description="Include sales history"),
    db: AsyncSession = Depends(get_db),
):
    """
    Get detailed information for a single Axie.

    Returns complete Axie data including genes, parts, stats,
    and optionally listing and sales history.
    """
    # Try to get from database first - eager load relationships to prevent N+1 queries
    query = select(Axie).where(Axie.id == axie_id).options(
        selectinload(Axie.parts).selectinload(AxiePart.part),
    )

    if include_listing:
        query = query.options(selectinload(Axie.listings))
    if include_sales:
        query = query.options(selectinload(Axie.sales))

    result = await db.execute(query)
    axie = result.scalar_one_or_none()

    if axie:
        # Return from database
        data = axie.to_dict()

        if include_listing:
            active_listing = next(
                (l for l in axie.listings if l.status == "active"),
                None
            )
            if active_listing:
                data["listing"] = {
                    "price_eth": float(active_listing.price_eth),
                    "price_usd": float(active_listing.price_usd) if active_listing.price_usd else None,
                    "listed_at": active_listing.listed_at.isoformat(),
                    "expires_at": active_listing.expires_at.isoformat() if active_listing.expires_at else None,
                }

        if include_sales:
            data["sales_history"] = [
                {
                    "price_eth": float(s.price_eth),
                    "price_usd": float(s.price_usd) if s.price_usd else None,
                    "sold_at": s.sold_at.isoformat(),
                    "seller": s.seller_address,
                    "buyer": s.buyer_address,
                }
                for s in sorted(axie.sales, key=lambda x: x.sold_at, reverse=True)[:10]
            ]

        return {"success": True, "data": data}

    # If not in database, try to fetch from Sky Mavis API
    try:
        async with SkyMavisClient() as client:
            axie_data = await client.get_axie(axie_id)
            if axie_data:
                return {
                    "success": True,
                    "data": {
                        "id": axie_data.id,
                        "name": axie_data.name,
                        "class": axie_data.class_,
                        "breed_count": axie_data.breedCount,
                        "genes": axie_data.genes,
                        "image_url": axie_data.image,
                        "owner": axie_data.owner,
                        "purity_score": axie_data.purity_score,
                        "stats": axie_data.stats,
                        "parts": {
                            part.type: {"name": part.name, "class": part.class_}
                            for part in axie_data.parts
                        },
                        "listing": {
                            "price_wei": axie_data.auction.get("currentPrice"),
                            "price_usd": axie_data.auction.get("currentPriceUSD"),
                        } if axie_data.auction else None,
                    },
                    "source": "api",
                }
    except Exception as e:
        pass

    raise HTTPException(404, f"Axie {axie_id} not found")


@router.get("/{axie_id}/genes")
async def get_axie_genes(axie_id: int, db: AsyncSession = Depends(get_db)):
    """
    Get parsed gene data for an Axie.

    Returns the decoded genes showing all body parts
    with their dominant and recessive genes.
    """
    # Get axie from DB
    result = await db.execute(select(Axie).where(Axie.id == axie_id))
    axie = result.scalar_one_or_none()

    if not axie:
        # Try API
        try:
            async with SkyMavisClient() as client:
                axie_data = await client.get_axie(axie_id)
                if axie_data and axie_data.genes:
                    genes = axie_data.genes
                else:
                    raise HTTPException(404, f"Axie {axie_id} not found")
        except Exception:
            raise HTTPException(404, f"Axie {axie_id} not found")
    else:
        genes = axie.genes

    # Parse genes
    parser = GeneParser()
    parsed = parser.parse(genes)

    return {
        "success": True,
        "data": parsed.to_dict(),
    }


@router.get("/{axie_id}/siblings")
async def get_axie_siblings(
    axie_id: int,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """
    Get Axies with the same parents (siblings).
    """
    # Get the axie's parents
    result = await db.execute(select(Axie).where(Axie.id == axie_id))
    axie = result.scalar_one_or_none()

    if not axie:
        raise HTTPException(404, f"Axie {axie_id} not found")

    if not axie.matron_id or not axie.sire_id:
        return {
            "success": True,
            "data": [],
            "meta": {"total": 0, "page": page, "per_page": per_page, "total_pages": 0}
        }

    # Find siblings
    query = select(Axie).where(
        Axie.matron_id == axie.matron_id,
        Axie.sire_id == axie.sire_id,
        Axie.id != axie_id,
    )

    # Count
    count_result = await db.execute(select(func.count()).select_from(query.subquery()))
    total = count_result.scalar() or 0

    # Paginate
    offset = (page - 1) * per_page
    query = query.offset(offset).limit(per_page)

    result = await db.execute(query)
    siblings = result.scalars().all()

    return {
        "success": True,
        "data": [s.to_dict() for s in siblings],
        "meta": {
            "total": total,
            "page": page,
            "per_page": per_page,
            "total_pages": (total + per_page - 1) // per_page,
        }
    }


@router.get("/{axie_id}/children")
async def get_axie_children(
    axie_id: int,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """
    Get all offspring of an Axie.
    """
    # Find children (where this axie is matron or sire)
    query = select(Axie).where(
        or_(Axie.matron_id == axie_id, Axie.sire_id == axie_id)
    )

    # Count
    count_result = await db.execute(select(func.count()).select_from(query.subquery()))
    total = count_result.scalar() or 0

    # Paginate
    offset = (page - 1) * per_page
    query = query.offset(offset).limit(per_page)

    result = await db.execute(query)
    children = result.scalars().all()

    return {
        "success": True,
        "data": [c.to_dict() for c in children],
        "meta": {
            "total": total,
            "page": page,
            "per_page": per_page,
            "total_pages": (total + per_page - 1) // per_page,
        }
    }
