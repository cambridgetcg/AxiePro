#!/usr/bin/env python3
"""
Prompt Effectiveness Assessor
=============================
A standardized tool for evaluating codebase exploration prompts.

Usage:
    python assessor.py new <prompt_id>           # Create new assessment
    python assessor.py rate <assessment_file>    # Interactive rating session
    python assessor.py score <assessment_file>   # Calculate and display scores
    python assessor.py report <assessment_file>  # Generate markdown report
    python assessor.py compare <file1> <file2>   # Compare two assessments
    python assessor.py history                   # View assessment history
    python assessor.py benchmark                 # Show benchmark statistics

Version: 1.0.0
"""

import json
import yaml
import os
import sys
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, List, Any
from enum import Enum


# ============================================================================
# Configuration
# ============================================================================

TOOL_DIR = Path(__file__).parent.parent
CONFIG_DIR = TOOL_DIR / "config"
ASSESSMENTS_DIR = TOOL_DIR / "assessments"
TEMPLATES_DIR = TOOL_DIR / "templates"


class Grade(Enum):
    A = ("A", 4.5, 5.0, "Excellent - Use as template")
    A_MINUS = ("A-", 4.0, 4.49, "Very Good - Minor refinements")
    B_PLUS = ("B+", 3.5, 3.99, "Good - Some improvements needed")
    B = ("B", 3.0, 3.49, "Adequate - Notable gaps")
    C_PLUS = ("C+", 2.5, 2.99, "Below Average - Significant rework")
    C = ("C", 2.0, 2.49, "Poor - Major revision needed")
    F = ("F", 0.0, 1.99, "Ineffective - Redesign from scratch")

    def __init__(self, letter: str, min_score: float, max_score: float, desc: str):
        self.letter = letter
        self.min_score = min_score
        self.max_score = max_score
        self.desc = desc

    @classmethod
    def from_score(cls, score: float) -> "Grade":
        for grade in cls:
            if grade.min_score <= score <= grade.max_score:
                return grade
        return cls.F


# ============================================================================
# Data Classes
# ============================================================================

@dataclass
class AttributeRating:
    """Rating for a single attribute."""
    code: str
    name: str
    score: float
    weight: float
    evidence: str = ""

    @property
    def weighted_score(self) -> float:
        return self.score * self.weight


@dataclass
class AssessmentMetadata:
    """Metadata for an assessment."""
    prompt_id: str
    date: str
    codebase: str
    category: str
    assessor: str = "Claude Code"
    execution_time_minutes: float = 0.0
    tokens_used: int = 0
    agent_type: str = "Explore"
    version: str = "1.0.0"


@dataclass
class Assessment:
    """Complete prompt assessment."""
    metadata: AssessmentMetadata
    prompt_text: str
    ratings: Dict[str, AttributeRating] = field(default_factory=dict)
    execution_summary: Dict[str, Any] = field(default_factory=dict)
    strengths: List[str] = field(default_factory=list)
    weaknesses: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)

    @property
    def total_score(self) -> float:
        if not self.ratings:
            return 0.0
        return sum(r.weighted_score for r in self.ratings.values())

    @property
    def percentage(self) -> float:
        return (self.total_score / 5.0) * 100

    @property
    def grade(self) -> Grade:
        return Grade.from_score(self.total_score)

    @property
    def efficiency_ratio(self) -> float:
        """Tokens per score point."""
        if self.total_score == 0:
            return float('inf')
        return self.metadata.tokens_used / self.total_score

    def to_dict(self) -> dict:
        return {
            "metadata": asdict(self.metadata),
            "prompt_text": self.prompt_text,
            "ratings": {k: asdict(v) for k, v in self.ratings.items()},
            "execution_summary": self.execution_summary,
            "strengths": self.strengths,
            "weaknesses": self.weaknesses,
            "recommendations": self.recommendations,
            "computed": {
                "total_score": round(self.total_score, 2),
                "percentage": round(self.percentage, 1),
                "grade": self.grade.letter,
                "efficiency_ratio": round(self.efficiency_ratio, 0)
            }
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Assessment":
        metadata = AssessmentMetadata(**data["metadata"])
        ratings = {
            k: AttributeRating(**v)
            for k, v in data.get("ratings", {}).items()
        }
        return cls(
            metadata=metadata,
            prompt_text=data.get("prompt_text", ""),
            ratings=ratings,
            execution_summary=data.get("execution_summary", {}),
            strengths=data.get("strengths", []),
            weaknesses=data.get("weaknesses", []),
            recommendations=data.get("recommendations", [])
        )


# ============================================================================
# Attribute Configuration Loader
# ============================================================================

class AttributeConfig:
    """Loads and provides access to attribute configuration."""

    def __init__(self, config_path: Optional[Path] = None):
        self.config_path = config_path or CONFIG_DIR / "attributes.yaml"
        self._config = self._load_config()

    def _load_config(self) -> dict:
        if self.config_path.exists():
            with open(self.config_path) as f:
                return yaml.safe_load(f)
        return self._default_config()

    def _default_config(self) -> dict:
        """Fallback configuration if YAML not found."""
        return {
            "attributes": {
                "comprehension_depth": {"code": "CD", "name": "Comprehension Depth", "weight": 0.15},
                "coverage_breadth": {"code": "CB", "name": "Coverage Breadth", "weight": 0.12},
                "accuracy": {"code": "AC", "name": "Accuracy", "weight": 0.15},
                "actionability": {"code": "AT", "name": "Actionability", "weight": 0.12},
                "bridging_capability": {"code": "BC", "name": "Bridging Capability", "weight": 0.10},
                "domain_alignment": {"code": "DA", "name": "Domain Alignment", "weight": 0.10},
                "clarity_structure": {"code": "CS", "name": "Clarity & Structure", "weight": 0.08},
                "efficiency": {"code": "EF", "name": "Efficiency", "weight": 0.08},
                "gap_detection": {"code": "GD", "name": "Gap Detection", "weight": 0.05},
                "reproducibility": {"code": "RP", "name": "Reproducibility", "weight": 0.05},
            }
        }

    @property
    def attributes(self) -> dict:
        return self._config.get("attributes", {})

    def get_attribute(self, key: str) -> dict:
        return self.attributes.get(key, {})

    def get_rubric(self, key: str) -> dict:
        return self.get_attribute(key).get("rubric", {})


# ============================================================================
# Assessment Engine
# ============================================================================

class AssessmentEngine:
    """Main engine for creating and managing assessments."""

    def __init__(self):
        self.config = AttributeConfig()
        ASSESSMENTS_DIR.mkdir(parents=True, exist_ok=True)

    def create_assessment(
        self,
        prompt_id: str,
        prompt_text: str,
        codebase: str,
        category: str = "discovery"
    ) -> Assessment:
        """Create a new assessment with empty ratings."""
        metadata = AssessmentMetadata(
            prompt_id=prompt_id,
            date=datetime.now().strftime("%Y-%m-%d"),
            codebase=codebase,
            category=category
        )

        # Initialize empty ratings for all attributes
        ratings = {}
        for key, attr in self.config.attributes.items():
            ratings[key] = AttributeRating(
                code=attr["code"],
                name=attr["name"],
                score=0.0,
                weight=attr["weight"]
            )

        return Assessment(
            metadata=metadata,
            prompt_text=prompt_text,
            ratings=ratings
        )

    def rate_attribute(
        self,
        assessment: Assessment,
        attribute_key: str,
        score: float,
        evidence: str = ""
    ) -> None:
        """Rate a single attribute."""
        if attribute_key not in assessment.ratings:
            raise ValueError(f"Unknown attribute: {attribute_key}")
        if not 1.0 <= score <= 5.0:
            raise ValueError(f"Score must be between 1.0 and 5.0, got {score}")

        assessment.ratings[attribute_key].score = score
        assessment.ratings[attribute_key].evidence = evidence

    def save_assessment(self, assessment: Assessment, filename: Optional[str] = None) -> Path:
        """Save assessment to JSON file."""
        if filename is None:
            filename = f"{assessment.metadata.prompt_id}_{assessment.metadata.date}.json"

        filepath = ASSESSMENTS_DIR / filename
        with open(filepath, 'w') as f:
            json.dump(assessment.to_dict(), f, indent=2)

        return filepath

    def load_assessment(self, filepath: Path) -> Assessment:
        """Load assessment from JSON file."""
        with open(filepath) as f:
            data = json.load(f)
        return Assessment.from_dict(data)

    def list_assessments(self) -> List[Path]:
        """List all saved assessments."""
        return sorted(ASSESSMENTS_DIR.glob("*.json"))


# ============================================================================
# Report Generator
# ============================================================================

class ReportGenerator:
    """Generates markdown reports from assessments."""

    def __init__(self, assessment: Assessment):
        self.assessment = assessment
        self.a = assessment  # shorthand

    def generate_full_report(self) -> str:
        """Generate complete markdown report."""
        sections = [
            self._header(),
            self._metadata_section(),
            self._prompt_section(),
            self._ratings_table(),
            self._score_summary(),
            self._attribute_profile(),
            self._strengths_weaknesses(),
            self._recommendations(),
            self._footer()
        ]
        return "\n\n".join(sections)

    def _header(self) -> str:
        return f"""# Prompt Assessment: {self.a.metadata.prompt_id}
**Grade: {self.a.grade.letter}** | **Score: {self.a.total_score:.2f}/5.00** ({self.a.percentage:.0f}%)"""

    def _metadata_section(self) -> str:
        m = self.a.metadata
        return f"""## Metadata
| Field | Value |
|-------|-------|
| Prompt ID | {m.prompt_id} |
| Date | {m.date} |
| Codebase | {m.codebase} |
| Category | {m.category} |
| Execution Time | {m.execution_time_minutes} min |
| Tokens Used | {m.tokens_used:,} |
| Efficiency | {self.a.efficiency_ratio:.0f} tokens/point |"""

    def _prompt_section(self) -> str:
        return f"""## Prompt Text
```
{self.a.prompt_text}
```"""

    def _ratings_table(self) -> str:
        rows = ["| Attribute | Score | Weight | Weighted | Evidence |",
                "|-----------|-------|--------|----------|----------|"]

        for key, rating in self.a.ratings.items():
            evidence = rating.evidence[:50] + "..." if len(rating.evidence) > 50 else rating.evidence
            rows.append(
                f"| **{rating.name}** | {rating.score:.1f} | {rating.weight:.0%} | "
                f"{rating.weighted_score:.3f} | {evidence} |"
            )

        return "## Attribute Ratings\n\n" + "\n".join(rows)

    def _score_summary(self) -> str:
        return f"""## Score Summary
```
Total Weighted Score: {self.a.total_score:.2f} / 5.00
Percentage: {self.a.percentage:.0f}%
Grade: {self.a.grade.letter} - {self.a.grade.desc}
Tokens per Point: {self.a.efficiency_ratio:.0f}
```"""

    def _attribute_profile(self) -> str:
        lines = ["## Attribute Profile", "```"]

        for key, rating in self.a.ratings.items():
            bar_length = int(rating.score * 4)
            bar = "█" * bar_length + "░" * (20 - bar_length)
            lines.append(f"{rating.code} {bar} {rating.score:.1f}  {rating.name}")

        lines.append("   " + "─" * 21)
        lines.append("   0    1    2    3    4    5")
        lines.append("```")

        return "\n".join(lines)

    def _strengths_weaknesses(self) -> str:
        strengths = "\n".join(f"- {s}" for s in self.a.strengths) or "- None identified"
        weaknesses = "\n".join(f"- {w}" for w in self.a.weaknesses) or "- None identified"

        return f"""## Strengths
{strengths}

## Weaknesses
{weaknesses}"""

    def _recommendations(self) -> str:
        recs = "\n".join(f"{i+1}. {r}" for i, r in enumerate(self.a.recommendations))
        return f"""## Optimization Recommendations
{recs if recs else "No recommendations provided."}"""

    def _footer(self) -> str:
        return f"---\n*Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')} | Framework v{self.a.metadata.version}*"


# ============================================================================
# Comparison Engine
# ============================================================================

class ComparisonEngine:
    """Compares two or more assessments."""

    def __init__(self, assessments: List[Assessment]):
        self.assessments = assessments

    def generate_comparison_report(self) -> str:
        """Generate comparison markdown."""
        lines = ["# Prompt Comparison Report", ""]

        # Header row
        header = "| Attribute |"
        divider = "|-----------|"
        for a in self.assessments:
            header += f" {a.metadata.prompt_id} |"
            divider += "-------|"
        lines.extend([header, divider])

        # Get all attribute keys from first assessment
        for key, rating in self.assessments[0].ratings.items():
            row = f"| {rating.name} |"
            for a in self.assessments:
                score = a.ratings[key].score
                row += f" {score:.1f} |"
            lines.append(row)

        # Total row
        total_row = "| **TOTAL** |"
        for a in self.assessments:
            total_row += f" **{a.total_score:.2f}** |"
        lines.append(total_row)

        # Grade row
        grade_row = "| **Grade** |"
        for a in self.assessments:
            grade_row += f" **{a.grade.letter}** |"
        lines.append(grade_row)

        return "\n".join(lines)

    def get_improvement_delta(self) -> Dict[str, float]:
        """Calculate improvement between first and last assessment."""
        if len(self.assessments) < 2:
            return {}

        first = self.assessments[0]
        last = self.assessments[-1]

        deltas = {}
        for key in first.ratings:
            deltas[key] = last.ratings[key].score - first.ratings[key].score
        deltas["total"] = last.total_score - first.total_score

        return deltas


# ============================================================================
# Interactive CLI
# ============================================================================

class InteractiveCLI:
    """Interactive command-line interface for assessments."""

    def __init__(self):
        self.engine = AssessmentEngine()
        self.config = AttributeConfig()

    def run_interactive_rating(self, assessment: Assessment) -> Assessment:
        """Run interactive rating session."""
        print("\n" + "=" * 60)
        print("INTERACTIVE PROMPT ASSESSMENT")
        print("=" * 60)
        print(f"\nPrompt ID: {assessment.metadata.prompt_id}")
        print(f"Codebase: {assessment.metadata.codebase}")
        print("-" * 60)

        for key, attr in self.config.attributes.items():
            print(f"\n📊 {attr['name']} ({attr['code']})")
            print(f"   Weight: {attr['weight']:.0%}")

            # Show rubric if available
            rubric = attr.get('rubric', {})
            if rubric:
                print("   Rubric:")
                for score, desc in sorted(rubric.items(), reverse=True):
                    print(f"     {score}: {desc[:60]}...")

            # Get score
            while True:
                try:
                    score_input = input(f"\n   Score (1-5): ").strip()
                    score = float(score_input)
                    if 1.0 <= score <= 5.0:
                        break
                    print("   ❌ Score must be between 1.0 and 5.0")
                except ValueError:
                    print("   ❌ Please enter a valid number")

            # Get evidence
            evidence = input("   Evidence (optional): ").strip()

            self.engine.rate_attribute(assessment, key, score, evidence)
            print(f"   ✓ Rated {attr['code']}: {score}")

        # Get metadata
        print("\n" + "-" * 60)
        print("Additional Information:")

        try:
            tokens = input("Tokens used (0 if unknown): ").strip()
            assessment.metadata.tokens_used = int(tokens) if tokens else 0
        except ValueError:
            assessment.metadata.tokens_used = 0

        try:
            time_min = input("Execution time in minutes (0 if unknown): ").strip()
            assessment.metadata.execution_time_minutes = float(time_min) if time_min else 0.0
        except ValueError:
            assessment.metadata.execution_time_minutes = 0.0

        # Get qualitative feedback
        print("\nStrengths (enter blank line to finish):")
        while True:
            strength = input("  + ").strip()
            if not strength:
                break
            assessment.strengths.append(strength)

        print("\nWeaknesses (enter blank line to finish):")
        while True:
            weakness = input("  - ").strip()
            if not weakness:
                break
            assessment.weaknesses.append(weakness)

        print("\nRecommendations (enter blank line to finish):")
        while True:
            rec = input("  → ").strip()
            if not rec:
                break
            assessment.recommendations.append(rec)

        return assessment

    def display_score_summary(self, assessment: Assessment) -> None:
        """Display score summary in terminal."""
        print("\n" + "=" * 60)
        print("ASSESSMENT RESULTS")
        print("=" * 60)

        # Attribute scores
        print("\nAttribute Scores:")
        for key, rating in assessment.ratings.items():
            bar = "█" * int(rating.score * 2) + "░" * (10 - int(rating.score * 2))
            print(f"  {rating.code} {bar} {rating.score:.1f} {rating.name}")

        print("-" * 60)
        print(f"Total Score:    {assessment.total_score:.2f} / 5.00")
        print(f"Percentage:     {assessment.percentage:.0f}%")
        print(f"Grade:          {assessment.grade.letter} - {assessment.grade.desc}")
        print(f"Efficiency:     {assessment.efficiency_ratio:.0f} tokens/point")
        print("=" * 60)


# ============================================================================
# Main CLI Entry Point
# ============================================================================

def print_usage():
    """Print usage information."""
    print(__doc__)


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print_usage()
        return

    command = sys.argv[1].lower()
    engine = AssessmentEngine()
    cli = InteractiveCLI()

    if command == "new":
        if len(sys.argv) < 3:
            print("Usage: assessor.py new <prompt_id>")
            return

        prompt_id = sys.argv[2]
        print(f"\nCreating new assessment: {prompt_id}")

        # Get basic info
        codebase = input("Codebase name: ").strip() or "Unknown"
        category = input("Category (discovery/tracing/analysis/alignment/diagnostic): ").strip() or "discovery"
        print("Enter prompt text (end with empty line):")

        lines = []
        while True:
            line = input()
            if not line:
                break
            lines.append(line)
        prompt_text = "\n".join(lines)

        assessment = engine.create_assessment(prompt_id, prompt_text, codebase, category)
        assessment = cli.run_interactive_rating(assessment)

        filepath = engine.save_assessment(assessment)
        print(f"\n✓ Assessment saved to: {filepath}")

        cli.display_score_summary(assessment)

    elif command == "rate":
        if len(sys.argv) < 3:
            print("Usage: assessor.py rate <assessment_file>")
            return

        filepath = Path(sys.argv[2])
        assessment = engine.load_assessment(filepath)
        assessment = cli.run_interactive_rating(assessment)
        engine.save_assessment(assessment, filepath.name)

        cli.display_score_summary(assessment)

    elif command == "score":
        if len(sys.argv) < 3:
            print("Usage: assessor.py score <assessment_file>")
            return

        filepath = Path(sys.argv[2])
        assessment = engine.load_assessment(filepath)
        cli.display_score_summary(assessment)

    elif command == "report":
        if len(sys.argv) < 3:
            print("Usage: assessor.py report <assessment_file>")
            return

        filepath = Path(sys.argv[2])
        assessment = engine.load_assessment(filepath)
        report = ReportGenerator(assessment).generate_full_report()

        report_path = filepath.with_suffix(".md")
        with open(report_path, 'w') as f:
            f.write(report)

        print(f"✓ Report saved to: {report_path}")
        print("\n" + report)

    elif command == "compare":
        if len(sys.argv) < 4:
            print("Usage: assessor.py compare <file1> <file2> [file3...]")
            return

        assessments = [engine.load_assessment(Path(f)) for f in sys.argv[2:]]
        comparison = ComparisonEngine(assessments)
        report = comparison.generate_comparison_report()

        print(report)

        if len(assessments) >= 2:
            deltas = comparison.get_improvement_delta()
            print("\n## Improvement (First → Last)")
            for key, delta in deltas.items():
                sign = "+" if delta >= 0 else ""
                print(f"  {key}: {sign}{delta:.2f}")

    elif command == "history":
        assessments = engine.list_assessments()

        if not assessments:
            print("No assessments found.")
            return

        print("\nAssessment History:")
        print("-" * 80)

        for filepath in assessments:
            try:
                assessment = engine.load_assessment(filepath)
                print(f"  {filepath.name}")
                print(f"    Score: {assessment.total_score:.2f} | Grade: {assessment.grade.letter} | "
                      f"Codebase: {assessment.metadata.codebase}")
            except Exception as e:
                print(f"  {filepath.name} - Error loading: {e}")

        print("-" * 80)

    elif command == "benchmark":
        assessments = [engine.load_assessment(f) for f in engine.list_assessments()]

        if not assessments:
            print("No assessments for benchmarking.")
            return

        print("\nBenchmark Statistics")
        print("=" * 60)

        # Calculate averages per attribute
        attr_totals = {}
        for a in assessments:
            for key, rating in a.ratings.items():
                if key not in attr_totals:
                    attr_totals[key] = {"sum": 0, "count": 0, "name": rating.name}
                attr_totals[key]["sum"] += rating.score
                attr_totals[key]["count"] += 1

        print("\nAttribute Averages:")
        for key, data in attr_totals.items():
            avg = data["sum"] / data["count"]
            bar = "█" * int(avg * 2) + "░" * (10 - int(avg * 2))
            print(f"  {bar} {avg:.2f} {data['name']}")

        # Overall statistics
        scores = [a.total_score for a in assessments]
        print(f"\nOverall Statistics:")
        print(f"  Assessments: {len(assessments)}")
        print(f"  Average Score: {sum(scores)/len(scores):.2f}")
        print(f"  Best Score: {max(scores):.2f}")
        print(f"  Worst Score: {min(scores):.2f}")

    else:
        print(f"Unknown command: {command}")
        print_usage()


if __name__ == "__main__":
    main()
