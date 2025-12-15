"""
Breeding API endpoints.

Provides routes for:
- Breeding simulation
- Breeding history
- Best pairs finder
"""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models import Axie, BreedingPair, Breed, get_db
from src.utils.gene_parser import GeneParser
from src.services.skymavis_client import SkyMavisClient

router = APIRouter(prefix="/breeding", tags=["breeding"])


class BreedingRequest(BaseModel):
    """Request body for breeding simulation."""
    matron_id: int
    sire_id: int


@router.post("/simulate")
async def simulate_breeding(
    request: BreedingRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Simulate breeding outcomes between two Axies.

    Returns probability distributions for:
    - Offspring class
    - Each body part outcome
    - Expected value and ROI analysis
    """
    matron_id = request.matron_id
    sire_id = request.sire_id

    # Get both axies
    matron_genes = None
    sire_genes = None
    matron_data = None
    sire_data = None

    # Try database first
    result = await db.execute(select(Axie).where(Axie.id == matron_id))
    matron = result.scalar_one_or_none()
    if matron:
        matron_genes = matron.genes
        matron_data = {
            "id": matron.id,
            "class": matron.class_.value,
            "breed_count": matron.breed_count,
        }

    result = await db.execute(select(Axie).where(Axie.id == sire_id))
    sire = result.scalar_one_or_none()
    if sire:
        sire_genes = sire.genes
        sire_data = {
            "id": sire.id,
            "class": sire.class_.value,
            "breed_count": sire.breed_count,
        }

    # If not in DB, fetch from API
    if not matron_genes or not sire_genes:
        try:
            async with SkyMavisClient() as client:
                if not matron_genes:
                    axie = await client.get_axie(matron_id)
                    if axie:
                        matron_genes = axie.genes
                        matron_data = {
                            "id": axie.id,
                            "class": axie.class_,
                            "breed_count": axie.breedCount,
                        }

                if not sire_genes:
                    axie = await client.get_axie(sire_id)
                    if axie:
                        sire_genes = axie.genes
                        sire_data = {
                            "id": axie.id,
                            "class": axie.class_,
                            "breed_count": axie.breedCount,
                        }
        except Exception as e:
            pass

    if not matron_genes:
        raise HTTPException(404, f"Matron Axie {matron_id} not found")
    if not sire_genes:
        raise HTTPException(404, f"Sire Axie {sire_id} not found")

    # Parse genes and calculate breeding probabilities
    parser = GeneParser()
    matron_parsed = parser.parse(matron_genes)
    sire_parsed = parser.parse(sire_genes)

    breeding_outcome = parser.calculate_breeding_probabilities(
        matron_parsed, sire_parsed
    )

    # Calculate breeding cost (simplified - actual cost varies)
    matron_breed_count = matron_data.get("breed_count", 0) if matron_data else 0
    sire_breed_count = sire_data.get("breed_count", 0) if sire_data else 0

    # SLP cost table (simplified)
    slp_cost_table = [900, 1350, 2250, 3600, 5850, 9450, 15300]
    matron_slp = slp_cost_table[min(matron_breed_count, 6)]
    sire_slp = slp_cost_table[min(sire_breed_count, 6)]
    total_slp = matron_slp + sire_slp

    # AXS cost (0.5 AXS per breed as of recent updates)
    axs_cost = 0.5

    return {
        "success": True,
        "data": {
            "matron": matron_data,
            "sire": sire_data,
            "cost": {
                "slp": total_slp,
                "axs": axs_cost,
            },
            "class_probabilities": breeding_outcome.class_probabilities,
            "part_probabilities": {
                part_type: [
                    {
                        "part": p.part.name,
                        "class": p.part.class_,
                        "probability": round(p.probability, 4),
                    }
                    for p in probs
                ]
                for part_type, probs in breeding_outcome.part_probabilities.items()
            },
            "expected_purity": breeding_outcome.expected_purity,
        }
    }


@router.get("/history")
async def get_breeding_history(
    axie_id: Optional[int] = Query(None, description="Filter by Axie ID"),
    role: str = Query("both", description="Role: matron, sire, both"),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """
    Get breeding history for an Axie.
    """
    if not axie_id:
        raise HTTPException(400, "axie_id is required")

    # Find breeding pairs involving this axie
    if role == "matron":
        pairs_query = select(BreedingPair).where(BreedingPair.matron_id == axie_id)
    elif role == "sire":
        pairs_query = select(BreedingPair).where(BreedingPair.sire_id == axie_id)
    else:
        pairs_query = select(BreedingPair).where(
            (BreedingPair.matron_id == axie_id) | (BreedingPair.sire_id == axie_id)
        )

    result = await db.execute(pairs_query)
    pairs = result.scalars().all()

    if not pairs:
        return {
            "success": True,
            "data": [],
            "meta": {"total": 0, "page": page, "per_page": per_page, "total_pages": 0}
        }

    pair_ids = [p.id for p in pairs]

    # Get breeds for these pairs
    breeds_query = (
        select(Breed)
        .where(Breed.pair_id.in_(pair_ids))
        .order_by(Breed.breed_at.desc())
    )

    result = await db.execute(breeds_query)
    breeds = result.scalars().all()

    # Build pair lookup
    pair_lookup = {p.id: p for p in pairs}

    history = []
    for breed in breeds:
        pair = pair_lookup.get(breed.pair_id)
        if pair:
            history.append({
                "id": breed.id,
                "matron_id": pair.matron_id,
                "sire_id": pair.sire_id,
                "offspring_id": breed.offspring_id,
                "breed_at": breed.breed_at.isoformat(),
                "cost_slp": breed.breed_cost_slp,
                "cost_axs": float(breed.breed_cost_axs) if breed.breed_cost_axs else None,
                "tx_hash": breed.tx_hash,
            })

    # Paginate
    total = len(history)
    start = (page - 1) * per_page
    end = start + per_page
    paginated = history[start:end]

    return {
        "success": True,
        "data": paginated,
        "meta": {
            "total": total,
            "page": page,
            "per_page": per_page,
            "total_pages": (total + per_page - 1) // per_page,
        }
    }


@router.get("/best-pairs")
async def find_best_pairs(
    axie_id: int = Query(..., description="Your Axie's ID"),
    target_class: Optional[str] = Query(None, description="Target offspring class"),
    max_cost_slp: Optional[int] = Query(None, description="Maximum SLP cost"),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """
    Find optimal breeding pairs for an Axie.

    Returns ranked list of potential partners based on:
    - Gene compatibility
    - Target trait probability
    - Cost efficiency
    """
    # Get the axie
    result = await db.execute(select(Axie).where(Axie.id == axie_id))
    axie = result.scalar_one_or_none()

    if not axie:
        raise HTTPException(404, f"Axie {axie_id} not found")

    # Find potential partners (same class preferred, low breed count)
    partners_query = (
        select(Axie)
        .where(
            Axie.id != axie_id,
            Axie.breed_count < 7,
        )
        .order_by(Axie.purity_score.desc(), Axie.breed_count.asc())
        .limit(100)  # Limit candidates for performance
    )

    if target_class:
        try:
            from src.models import AxieClass
            partners_query = partners_query.where(
                Axie.class_ == AxieClass(target_class.lower())
            )
        except ValueError:
            pass

    result = await db.execute(partners_query)
    candidates = result.scalars().all()

    # Score each candidate
    parser = GeneParser()
    axie_genes = parser.parse(axie.genes)

    scored_pairs = []
    for candidate in candidates:
        candidate_genes = parser.parse(candidate.genes)
        outcome = parser.calculate_breeding_probabilities(axie_genes, candidate_genes)

        # Calculate expected value score
        target = target_class or axie.class_.value
        class_prob = outcome.class_probabilities.get(target, 0)

        score = (
            class_prob * 100 +
            outcome.expected_purity * 10 +
            (7 - candidate.breed_count) * 5
        )

        scored_pairs.append({
            "partner_id": candidate.id,
            "partner_class": candidate.class_.value,
            "partner_purity": candidate.purity_score,
            "partner_breed_count": candidate.breed_count,
            "target_class_probability": round(class_prob, 4),
            "expected_purity": outcome.expected_purity,
            "score": round(score, 2),
        })

    # Sort by score
    scored_pairs.sort(key=lambda x: x["score"], reverse=True)

    # Paginate
    total = len(scored_pairs)
    start = (page - 1) * per_page
    end = start + per_page
    paginated = scored_pairs[start:end]

    return {
        "success": True,
        "data": paginated,
        "meta": {
            "total": total,
            "page": page,
            "per_page": per_page,
            "total_pages": (total + per_page - 1) // per_page,
        }
    }
