#!/usr/bin/env python3
"""
Claude Code Integration Module
==============================
Programmatic interface for prompt assessment within Claude Code sessions.

This module provides functions that can be called directly from Claude Code
to assess prompts without interactive CLI prompts.

Usage in Claude Code:
    from tools.prompt_assessor.src.claude_integration import (
        quick_assess,
        assess_from_dict,
        compare_prompts,
        get_benchmark_stats
    )
"""

import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

# Import from main assessor
try:
    from .assessor import (
        Assessment,
        AssessmentMetadata,
        AttributeRating,
        AssessmentEngine,
        ReportGenerator,
        ComparisonEngine,
        AttributeConfig,
        Grade
    )
except ImportError:
    # Direct execution fallback
    from assessor import (
        Assessment,
        AssessmentMetadata,
        AttributeRating,
        AssessmentEngine,
        ReportGenerator,
        ComparisonEngine,
        AttributeConfig,
        Grade
    )


# ============================================================================
# Quick Assessment Interface
# ============================================================================

def quick_assess(
    prompt_id: str,
    prompt_text: str,
    codebase: str,
    ratings: Dict[str, float],
    evidence: Optional[Dict[str, str]] = None,
    tokens_used: int = 0,
    execution_time: float = 0.0,
    category: str = "discovery",
    strengths: Optional[List[str]] = None,
    weaknesses: Optional[List[str]] = None,
    recommendations: Optional[List[str]] = None,
    save: bool = True
) -> Dict[str, Any]:
    """
    Quick assessment with minimal input.

    Args:
        prompt_id: Unique identifier for the prompt
        prompt_text: The actual prompt text
        codebase: Name of the codebase being analyzed
        ratings: Dict mapping attribute keys to scores (1-5)
            Keys: comprehension_depth, coverage_breadth, accuracy, actionability,
                  bridging_capability, domain_alignment, clarity_structure,
                  efficiency, gap_detection, reproducibility
        evidence: Optional dict mapping attribute keys to evidence strings
        tokens_used: Number of tokens used in execution
        execution_time: Execution time in minutes
        category: Prompt category (discovery/tracing/analysis/alignment/diagnostic/comparative)
        strengths: List of identified strengths
        weaknesses: List of identified weaknesses
        recommendations: List of improvement recommendations
        save: Whether to save the assessment to disk

    Returns:
        Dict containing assessment results and computed scores

    Example:
        result = quick_assess(
            prompt_id="ARCH-001",
            prompt_text="Analyze the architecture...",
            codebase="AxiePro",
            ratings={
                "comprehension_depth": 4.5,
                "coverage_breadth": 4.0,
                "accuracy": 4.5,
                "actionability": 4.0,
                "bridging_capability": 4.5,
                "domain_alignment": 4.0,
                "clarity_structure": 4.5,
                "efficiency": 3.5,
                "gap_detection": 4.0,
                "reproducibility": 4.0
            },
            tokens_used=8500,
            execution_time=3.0
        )
    """
    engine = AssessmentEngine()
    evidence = evidence or {}

    # Create assessment
    assessment = engine.create_assessment(prompt_id, prompt_text, codebase, category)
    assessment.metadata.tokens_used = tokens_used
    assessment.metadata.execution_time_minutes = execution_time

    # Apply ratings
    for attr_key, score in ratings.items():
        if attr_key in assessment.ratings:
            engine.rate_attribute(
                assessment,
                attr_key,
                score,
                evidence.get(attr_key, "")
            )

    # Add qualitative data
    assessment.strengths = strengths or []
    assessment.weaknesses = weaknesses or []
    assessment.recommendations = recommendations or []

    # Save if requested
    if save:
        filepath = engine.save_assessment(assessment)

    # Return results
    result = assessment.to_dict()
    if save:
        result["saved_to"] = str(filepath)

    return result


def assess_from_dict(data: Dict[str, Any], save: bool = True) -> Dict[str, Any]:
    """
    Create assessment from a complete dictionary.

    Useful for programmatically creating assessments with full control.

    Args:
        data: Complete assessment data matching the template structure
        save: Whether to save to disk

    Returns:
        Assessment results with computed scores
    """
    assessment = Assessment.from_dict(data)

    if save:
        engine = AssessmentEngine()
        filepath = engine.save_assessment(assessment)
        result = assessment.to_dict()
        result["saved_to"] = str(filepath)
        return result

    return assessment.to_dict()


# ============================================================================
# Comparison Interface
# ============================================================================

def compare_prompts(assessment_files: List[str]) -> str:
    """
    Compare multiple assessments and return markdown report.

    Args:
        assessment_files: List of paths to assessment JSON files

    Returns:
        Markdown comparison report
    """
    engine = AssessmentEngine()
    assessments = [engine.load_assessment(Path(f)) for f in assessment_files]

    comparison = ComparisonEngine(assessments)
    report = comparison.generate_comparison_report()

    # Add improvement delta if applicable
    if len(assessments) >= 2:
        deltas = comparison.get_improvement_delta()
        report += "\n\n## Improvement (First → Last)\n"
        for key, delta in deltas.items():
            sign = "+" if delta >= 0 else ""
            report += f"- {key}: {sign}{delta:.2f}\n"

    return report


def get_benchmark_stats() -> Dict[str, Any]:
    """
    Get benchmark statistics across all saved assessments.

    Returns:
        Dictionary with average scores, best/worst scores, etc.
    """
    engine = AssessmentEngine()
    assessment_files = engine.list_assessments()

    if not assessment_files:
        return {"error": "No assessments found"}

    assessments = [engine.load_assessment(f) for f in assessment_files]

    # Calculate per-attribute averages
    attr_stats = {}
    for a in assessments:
        for key, rating in a.ratings.items():
            if key not in attr_stats:
                attr_stats[key] = {
                    "scores": [],
                    "name": rating.name,
                    "code": rating.code
                }
            attr_stats[key]["scores"].append(rating.score)

    # Compute statistics
    for key, data in attr_stats.items():
        scores = data["scores"]
        data["average"] = sum(scores) / len(scores)
        data["min"] = min(scores)
        data["max"] = max(scores)
        data["count"] = len(scores)
        del data["scores"]  # Remove raw data

    # Overall statistics
    total_scores = [a.total_score for a in assessments]

    return {
        "assessment_count": len(assessments),
        "overall": {
            "average": sum(total_scores) / len(total_scores),
            "best": max(total_scores),
            "worst": min(total_scores),
            "best_prompt": assessments[total_scores.index(max(total_scores))].metadata.prompt_id,
            "worst_prompt": assessments[total_scores.index(min(total_scores))].metadata.prompt_id
        },
        "by_attribute": attr_stats
    }


# ============================================================================
# Report Generation
# ============================================================================

def generate_report(assessment_file: str) -> str:
    """
    Generate markdown report for an assessment.

    Args:
        assessment_file: Path to assessment JSON file

    Returns:
        Markdown report string
    """
    engine = AssessmentEngine()
    assessment = engine.load_assessment(Path(assessment_file))
    return ReportGenerator(assessment).generate_full_report()


def generate_score_card(assessment_file: str) -> str:
    """
    Generate a concise score card for an assessment.

    Args:
        assessment_file: Path to assessment JSON file

    Returns:
        Concise score card string
    """
    engine = AssessmentEngine()
    assessment = engine.load_assessment(Path(assessment_file))

    lines = [
        f"## Score Card: {assessment.metadata.prompt_id}",
        f"**Grade: {assessment.grade.letter}** | **Score: {assessment.total_score:.2f}/5.00**",
        "",
        "| Attribute | Score |",
        "|-----------|-------|"
    ]

    for key, rating in assessment.ratings.items():
        lines.append(f"| {rating.code} {rating.name} | {rating.score:.1f} |")

    lines.extend([
        "",
        f"**Efficiency:** {assessment.efficiency_ratio:.0f} tokens/point"
    ])

    return "\n".join(lines)


# ============================================================================
# Inline Assessment Helper (for Claude Code conversations)
# ============================================================================

def inline_assess(
    prompt_text: str,
    output_summary: str,
    cd: float, cb: float, ac: float, at: float, bc: float,
    da: float, cs: float, ef: float, gd: float, rp: float,
    prompt_id: Optional[str] = None,
    codebase: str = "unknown"
) -> str:
    """
    Inline assessment using abbreviated attribute codes.
    Returns formatted assessment summary.

    Args:
        prompt_text: The prompt that was tested
        output_summary: Brief summary of what the prompt produced
        cd: Comprehension Depth score (1-5)
        cb: Coverage Breadth score (1-5)
        ac: Accuracy score (1-5)
        at: Actionability score (1-5)
        bc: Bridging Capability score (1-5)
        da: Domain Alignment score (1-5)
        cs: Clarity & Structure score (1-5)
        ef: Efficiency score (1-5)
        gd: Gap Detection score (1-5)
        rp: Reproducibility score (1-5)
        prompt_id: Optional ID (auto-generated if not provided)
        codebase: Name of the codebase

    Returns:
        Formatted assessment summary as string
    """
    if prompt_id is None:
        prompt_id = f"PROMPT-{datetime.now().strftime('%Y%m%d%H%M%S')}"

    ratings = {
        "comprehension_depth": cd,
        "coverage_breadth": cb,
        "accuracy": ac,
        "actionability": at,
        "bridging_capability": bc,
        "domain_alignment": da,
        "clarity_structure": cs,
        "efficiency": ef,
        "gap_detection": gd,
        "reproducibility": rp
    }

    result = quick_assess(
        prompt_id=prompt_id,
        prompt_text=prompt_text[:500] + "..." if len(prompt_text) > 500 else prompt_text,
        codebase=codebase,
        ratings=ratings,
        save=True
    )

    # Format output
    computed = result["computed"]

    profile = ""
    for key, rating in result["ratings"].items():
        score = rating["score"]
        bar = "█" * int(score) + "░" * (5 - int(score))
        profile += f"{rating['code']} {bar} {score:.1f}\n"

    return f"""
## Prompt Assessment: {prompt_id}

**Output Summary:** {output_summary}

### Scores
```
{profile}```

**Total: {computed['total_score']:.2f}/5.00** | **Grade: {computed['grade']}** | **{computed['percentage']:.0f}%**

*Saved to: {result.get('saved_to', 'Not saved')}*
"""


# ============================================================================
# Export Functions for External Use
# ============================================================================

__all__ = [
    'quick_assess',
    'assess_from_dict',
    'compare_prompts',
    'get_benchmark_stats',
    'generate_report',
    'generate_score_card',
    'inline_assess'
]


if __name__ == "__main__":
    # Example usage
    result = quick_assess(
        prompt_id="TEST-001",
        prompt_text="Test prompt for demonstration",
        codebase="TestProject",
        ratings={
            "comprehension_depth": 4.0,
            "coverage_breadth": 3.5,
            "accuracy": 4.5,
            "actionability": 4.0,
            "bridging_capability": 3.5,
            "domain_alignment": 4.0,
            "clarity_structure": 4.0,
            "efficiency": 3.5,
            "gap_detection": 4.0,
            "reproducibility": 4.0
        },
        tokens_used=5000,
        execution_time=2.0,
        strengths=["Good accuracy", "Clear structure"],
        weaknesses=["Could improve efficiency"],
        save=False  # Don't save for demo
    )

    print("Quick Assessment Result:")
    print(json.dumps(result, indent=2))
