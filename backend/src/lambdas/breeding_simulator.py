"""
Breeding Simulator Lambda

Builds breeding intelligence database by analyzing historical breeding outcomes.
Uses 10% of daily API capacity (2k requests/day).

This Lambda represents CREATIVE path-building - transforming unused API capacity
into breeding ROI calculator that enables profitable breeding decisions.

Purpose Prompter alignment:
- CREATIVITY: Pioneering breeding probability engine in uncharted territory
- JUSTICE: Right place for breeding intelligence (dedicated Lambda)
- BEAUTY: Elegant probability calculation from real breeding data
- UNDERSTANDING: Deep comprehension of gene inheritance patterns
"""

import asyncio
import json
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any, Set
from decimal import Decimal
from collections import Counter

import httpx
from aws_lambda_powertools.metrics import MetricUnit

from src.lambdas.common import (
    logger,
    tracer,
    metrics,
    get_secrets,
    get_db_connection,
    HTTP_TIMEOUT_SECONDS,
)
from src.services.skymavis_client import SkyMavisClient


# Configuration
CLASSES_TO_ANALYZE = ["beast", "plant", "aquatic", "bird", "bug", "reptile"]
TOP_AXIES_PER_CLASS = 50  # Top 50 purest axies per class
CHILDREN_TO_FETCH = 100  # Fetch up to 100 children per parent
MIN_CHILDREN_FOR_ANALYSIS = 3  # Need at least 3 children for meaningful stats


def calculate_purity(parts: List[Dict], axie_class: str) -> int:
    """Calculate purity score (number of parts matching class)."""
    if not parts or not axie_class:
        return 0

    axie_class_lower = axie_class.lower()
    return sum(1 for part in parts if part.get("class", "").lower() == axie_class_lower)


def analyze_breeding_outcomes(
    parent1_id: int,
    parent2_id: int,
    children: List[Dict[str, Any]],
) -> Optional[Dict[str, Any]]:
    """
    Analyze breeding outcomes from a list of children.

    Returns statistics about class distribution, purity, etc.
    """
    if len(children) < MIN_CHILDREN_FOR_ANALYSIS:
        return None

    # Analyze class distribution
    class_counts = Counter(child.get("class", "unknown").lower() for child in children)
    total = len(children)
    class_distribution = {
        cls: round(count / total, 3)
        for cls, count in class_counts.items()
    }

    # Analyze purity distribution
    purity_scores = [child.get("purity_score", 0) for child in children]
    purity_counts = Counter(purity_scores)
    purity_distribution = {
        str(purity): round(count / total, 3)
        for purity, count in purity_counts.items()
    }

    # Calculate average purity
    avg_purity = sum(purity_scores) / total if purity_scores else 0

    # Calculate premium rate (purity >= 5)
    premium_count = sum(1 for p in purity_scores if p >= 5)
    premium_rate = premium_count / total if total > 0 else 0

    return {
        "parent1_id": parent1_id,
        "parent2_id": parent2_id,
        "offspring_count": total,
        "class_distribution": class_distribution,
        "purity_distribution": purity_distribution,
        "avg_purity": round(avg_purity, 2),
        "premium_rate": round(premium_rate, 3),
        "sample_size": total,
    }


def store_breeding_outcome(conn, outcome: Dict[str, Any]) -> bool:
    """Store breeding outcome in database."""
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO breeding_outcomes (
                    parent1_id,
                    parent2_id,
                    offspring_count,
                    class_distribution,
                    purity_distribution,
                    avg_purity,
                    premium_rate,
                    sample_size,
                    last_updated
                )
                VALUES (
                    %(parent1_id)s,
                    %(parent2_id)s,
                    %(offspring_count)s,
                    %(class_distribution)s,
                    %(purity_distribution)s,
                    %(avg_purity)s,
                    %(premium_rate)s,
                    %(sample_size)s,
                    NOW()
                )
                ON CONFLICT (parent1_id, parent2_id) DO UPDATE SET
                    offspring_count = EXCLUDED.offspring_count,
                    class_distribution = EXCLUDED.class_distribution,
                    purity_distribution = EXCLUDED.purity_distribution,
                    avg_purity = EXCLUDED.avg_purity,
                    premium_rate = EXCLUDED.premium_rate,
                    sample_size = EXCLUDED.sample_size,
                    last_updated = NOW()
                """,
                outcome,
            )
            conn.commit()
            return True
    except Exception as e:
        logger.error(f"Error storing breeding outcome: {e}")
        conn.rollback()
        return False


def get_parent_pairs_to_analyze(conn, limit: int = 100) -> List[tuple[int, int]]:
    """
    Get parent pairs that need analysis.

    Strategy:
    1. Find axies with children (matron/sire of other axies)
    2. Look for pairs we haven't analyzed yet
    3. Prioritize high-purity parents
    """
    with conn.cursor() as cur:
        # Find popular parent pairs from existing axies
        cur.execute(
            """
            SELECT DISTINCT
                a1.matron_id as parent1_id,
                a1.sire_id as parent2_id,
                COUNT(*) as offspring_count
            FROM axies a1
            WHERE a1.matron_id IS NOT NULL
              AND a1.sire_id IS NOT NULL
            GROUP BY a1.matron_id, a1.sire_id
            HAVING COUNT(*) >= %s
            AND NOT EXISTS (
                SELECT 1 FROM breeding_outcomes bo
                WHERE (bo.parent1_id = a1.matron_id AND bo.parent2_id = a1.sire_id)
                   OR (bo.parent1_id = a1.sire_id AND bo.parent2_id = a1.matron_id)
            )
            ORDER BY COUNT(*) DESC
            LIMIT %s
            """,
            (MIN_CHILDREN_FOR_ANALYSIS, limit),
        )
        return [(row[0], row[1]) for row in cur.fetchall()]


@tracer.capture_method
async def analyze_axie_breeding(
    client: SkyMavisClient,
    conn,
    axie_id: int,
) -> int:
    """
    Analyze breeding outcomes for an axie.

    Returns number of breeding outcomes stored.
    """
    outcomes_stored = 0

    try:
        # Fetch children
        children, total = await client.get_axie_children(
            axie_id,
            size=CHILDREN_TO_FETCH,
        )

        if total < MIN_CHILDREN_FOR_ANALYSIS:
            logger.debug(f"Axie {axie_id} has only {total} children, skipping")
            return 0

        logger.info(f"Analyzing {len(children)} children of axie {axie_id}")

        # Group children by other parent
        # If this axie is the matron, group by sire
        # If this axie is the sire, group by matron
        by_other_parent: Dict[int, List[Dict]] = {}

        for child in children:
            # Prepare child data
            child_data = {
                "id": child.id,
                "class": child.axie_class if hasattr(child, 'axie_class') else child.class_type,
                "purity_score": calculate_purity(
                    child.parts if hasattr(child, 'parts') else [],
                    child.axie_class if hasattr(child, 'axie_class') else child.class_type
                ),
                "breed_count": child.breed_count if hasattr(child, 'breed_count') else 0,
            }

            # Determine other parent
            if hasattr(child, 'matronId') and child.matronId == axie_id:
                # This axie is the matron, other parent is sire
                other_parent = child.sireId if hasattr(child, 'sireId') else None
            elif hasattr(child, 'sireId') and child.sireId == axie_id:
                # This axie is the sire, other parent is matron
                other_parent = child.matronId if hasattr(child, 'matronId') else None
            else:
                continue

            if other_parent:
                if other_parent not in by_other_parent:
                    by_other_parent[other_parent] = []
                by_other_parent[other_parent].append(child_data)

        # Analyze each parent pair
        for other_parent_id, pair_children in by_other_parent.items():
            outcome = analyze_breeding_outcomes(
                axie_id,
                other_parent_id,
                pair_children,
            )

            if outcome and store_breeding_outcome(conn, outcome):
                outcomes_stored += 1
                logger.info(
                    f"Stored breeding outcome: {axie_id} × {other_parent_id} "
                    f"({outcome['offspring_count']} children, "
                    f"{outcome['avg_purity']:.1f} avg purity, "
                    f"{outcome['premium_rate']*100:.0f}% premium rate)"
                )

        return outcomes_stored

    except Exception as e:
        logger.error(f"Error analyzing axie {axie_id}: {e}")
        return 0


@logger.inject_lambda_context
@tracer.capture_lambda_handler
@metrics.log_metrics
def handler(event, context):
    """
    Lambda handler for breeding simulator.

    Runs daily, analyzes ~100 parent pairs with children data.
    API usage: ~2,000 requests per run × 1 run/day = 2,000 requests/day (10%).
    """
    timestamp = datetime.now(timezone.utc)
    logger.info(f"Starting breeding analysis at {timestamp}")

    async def analyze():
        conn = get_db_connection()
        secrets = get_secrets()

        total_analyzed = 0
        total_outcomes = 0

        try:
            async with httpx.AsyncClient(timeout=HTTP_TIMEOUT_SECONDS) as http_client:
                client = SkyMavisClient(
                    http_client=http_client,
                    api_key=secrets.get("SKYMAVIS_API_KEY"),
                )

                # Strategy 1: Analyze known parent pairs from existing data
                parent_pairs = get_parent_pairs_to_analyze(conn, limit=50)
                logger.info(f"Found {len(parent_pairs)} parent pairs to analyze from existing data")

                for parent1_id, parent2_id in parent_pairs:
                    # Analyze from parent1's perspective
                    outcomes = await analyze_axie_breeding(client, conn, parent1_id)
                    total_analyzed += 1
                    total_outcomes += outcomes

                    # Small delay to avoid rate limiting
                    await asyncio.sleep(0.1)

                # Strategy 2: Analyze top purity axies (discover new patterns)
                logger.info("Analyzing top purity axies for new breeding patterns...")

                for axie_class in CLASSES_TO_ANALYZE:
                    try:
                        # Search for top purity axies
                        top_axies, _ = await client.search_axies(
                            classes=[axie_class],
                            parts=[],  # No specific parts
                            breed_count_max=7,  # Still breedable
                            sort_by="PriceAsc",  # Start with cheaper ones
                            size=min(TOP_AXIES_PER_CLASS, 20),  # Limit to avoid rate limiting
                        )

                        logger.info(f"Analyzing {len(top_axies)} {axie_class} axies")

                        for axie in top_axies:
                            outcomes = await analyze_axie_breeding(client, conn, axie.id)
                            total_analyzed += 1
                            total_outcomes += outcomes

                            # Small delay
                            await asyncio.sleep(0.1)

                    except Exception as e:
                        logger.error(f"Error analyzing {axie_class}: {e}")
                        continue

                logger.info(
                    f"Breeding analysis complete: "
                    f"analyzed {total_analyzed} axies, "
                    f"stored {total_outcomes} breeding outcomes"
                )

                # Metrics
                metrics.add_metric(name="AxiesAnalyzed", unit=MetricUnit.Count, value=total_analyzed)
                metrics.add_metric(name="BreedingOutcomesStored", unit=MetricUnit.Count, value=total_outcomes)

                if total_analyzed > 0:
                    outcomes_per_axie = total_outcomes / total_analyzed
                    metrics.add_metric(name="OutcomesPerAxie", unit=MetricUnit.Count, value=outcomes_per_axie)

                return {
                    "total_analyzed": total_analyzed,
                    "total_outcomes": total_outcomes,
                    "timestamp": timestamp.isoformat(),
                }

        except Exception as e:
            logger.error(f"Fatal error in breeding analysis: {e}", exc_info=True)
            raise
        finally:
            if conn:
                conn.close()

    # Run async function
    result = asyncio.run(analyze())

    logger.info(
        f"Breeding analysis complete: {result['total_outcomes']} outcomes stored"
    )

    return {
        "statusCode": 200,
        "body": json.dumps({
            "message": "Breeding analysis complete",
            "axies_analyzed": result["total_analyzed"],
            "outcomes_stored": result["total_outcomes"],
            "timestamp": result["timestamp"],
        }),
    }
