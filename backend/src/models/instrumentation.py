"""
SQLAlchemy models for instrumentation and feedback system.

Captures usage events, performance metrics, and value metrics
to enable purpose alignment measurement.
"""

from datetime import datetime
from typing import Optional
import enum

from sqlalchemy import (
    BigInteger,
    DateTime,
    Enum as SQLEnum,
    Index,
    Integer,
    Numeric,
    SmallInteger,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from .database import Base


class EventType(str, enum.Enum):
    """Instrumentation event types."""
    USAGE = "usage"
    PERFORMANCE = "performance"
    ERROR = "error"
    VALUE = "value"


class Feature(str, enum.Enum):
    """AxiePro features for instrumentation."""
    EXPLORER = "explorer"
    BREEDING = "breeding"
    DEALS = "deals"
    META = "meta"
    ANALYTICS = "analytics"
    PORTFOLIO = "portfolio"
    VALUATION = "valuation"


class FlowStatus(str, enum.Enum):
    """Synthetic flow execution status."""
    RUNNING = "running"
    PASSED = "passed"
    FAILED = "failed"
    ERROR = "error"


class FlowType(str, enum.Enum):
    """Types of synthetic validation flows."""
    DEAL_HUNTER = "deal_hunter"
    BREEDING_PLANNER = "breeding_planner"
    META_SCOUT = "meta_scout"


class InstrumentationEvent(Base):
    """
    Stores all instrumentation events.

    Single table design with event_type discriminator for
    efficient querying and simple schema.
    """

    __tablename__ = "instrumentation_events"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)

    # Event classification
    event_type: Mapped[EventType] = mapped_column(
        SQLEnum(EventType, name="event_type"),
        nullable=False,
    )
    feature: Mapped[Feature] = mapped_column(
        SQLEnum(Feature, name="feature"),
        nullable=False,
    )
    action: Mapped[str] = mapped_column(String(100), nullable=False)

    # Session tracking (anonymous)
    session_id: Mapped[Optional[str]] = mapped_column(String(36), index=True)

    # Event data (flexible JSON storage)
    data: Mapped[Optional[dict]] = mapped_column(JSONB)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
    )

    # Indexes for efficient querying
    __table_args__ = (
        Index("idx_events_feature_time", feature, created_at.desc()),
        Index("idx_events_type_time", event_type, created_at.desc()),
        Index("idx_events_feature_action", feature, action),
        Index("idx_events_session", session_id, created_at.desc()),
    )

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "event_type": self.event_type.value,
            "feature": self.feature.value,
            "action": self.action,
            "session_id": self.session_id,
            "data": self.data,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class ValueMetric(Base):
    """
    Stores calculated value metrics for features.

    These are derived metrics that indicate feature effectiveness:
    - deal_quality: How undervalued detected deals are
    - prediction_accuracy: How accurate breeding predictions are
    - meta_timeliness: How early meta shifts are detected
    """

    __tablename__ = "value_metrics"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)

    # Metric identification
    feature: Mapped[Feature] = mapped_column(
        SQLEnum(Feature, name="feature"),
        nullable=False,
    )
    metric_type: Mapped[str] = mapped_column(String(100), nullable=False)

    # Metric value
    value: Mapped[float] = mapped_column(Numeric(10, 4), nullable=False)

    # Additional context (optional)
    context: Mapped[Optional[dict]] = mapped_column(JSONB)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
    )

    __table_args__ = (
        Index("idx_metrics_feature_type", feature, metric_type, created_at.desc()),
        Index("idx_metrics_type_time", metric_type, created_at.desc()),
    )

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "feature": self.feature.value,
            "metric_type": self.metric_type,
            "value": float(self.value),
            "context": self.context,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class PurposeAlignmentSnapshot(Base):
    """
    Stores periodic snapshots of purpose alignment analysis.

    Calculated hourly from instrumentation data.
    """

    __tablename__ = "purpose_alignment_snapshots"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)

    # Overall score (0-100)
    overall_score: Mapped[int] = mapped_column(SmallInteger, nullable=False)

    # Feature-level scores
    feature_scores: Mapped[dict] = mapped_column(JSONB, nullable=False)

    # Identified gaps
    gaps: Mapped[Optional[dict]] = mapped_column(JSONB)

    # Generated insights
    insights: Mapped[Optional[dict]] = mapped_column(JSONB)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
    )

    __table_args__ = (
        Index("idx_alignment_time", created_at.desc()),
    )

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "overall_score": self.overall_score,
            "feature_scores": self.feature_scores,
            "gaps": self.gaps,
            "insights": self.insights,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class SyntheticFlowRun(Base):
    """
    Stores synthetic flow execution results.

    Tracks automated validation flows that test feature effectiveness
    by simulating real trader scenarios:
    - Deal Hunter: Validates deal quality
    - Breeding Planner: Validates breeding simulation accuracy
    - Meta Scout: Validates meta shift detection timeliness
    """

    __tablename__ = "synthetic_flow_runs"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)

    # Flow identification
    flow_type: Mapped[FlowType] = mapped_column(
        SQLEnum(FlowType, name="flow_type"),
        nullable=False,
    )
    feature: Mapped[Feature] = mapped_column(
        SQLEnum(Feature, name="feature"),
        nullable=False,
    )

    # Execution status
    status: Mapped[FlowStatus] = mapped_column(
        SQLEnum(FlowStatus, name="flow_status"),
        nullable=False,
    )

    # Validation results
    validation_score: Mapped[Optional[float]] = mapped_column(Numeric(10, 4))
    checks_passed: Mapped[Optional[int]] = mapped_column(Integer)
    checks_total: Mapped[Optional[int]] = mapped_column(Integer)

    # Detailed results and errors
    results: Mapped[Optional[dict]] = mapped_column(JSONB)
    error_message: Mapped[Optional[str]] = mapped_column(Text)

    # Timestamps
    started_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime)

    __table_args__ = (
        Index("idx_flow_runs_type_status", flow_type, status, started_at.desc()),
        Index("idx_flow_runs_feature_time", feature, started_at.desc()),
        Index("idx_flow_runs_status_time", status, started_at.desc()),
    )

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "flow_type": self.flow_type.value,
            "feature": self.feature.value,
            "status": self.status.value,
            "validation_score": float(self.validation_score) if self.validation_score else None,
            "checks_passed": self.checks_passed,
            "checks_total": self.checks_total,
            "results": self.results,
            "error_message": self.error_message,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }
