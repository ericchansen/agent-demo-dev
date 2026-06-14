"""Typed data models for quota estimation reports."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import TypedDict


class SalesRowInput(TypedDict, total=False):
    """Loose input row accepted from Fabric Data Agent query output."""

    territory: str
    territory_name: str
    Territory: str
    SalesTerritory: str
    category: str
    product_category: str
    ProductCategory: str
    order_date: str
    OrderDate: str
    revenue: float
    total_revenue: float
    TotalDue: float
    quantity: float
    Quantity: float


class ResearchArticleInput(TypedDict, total=False):
    """Research article shape emitted by the researcher MCP server."""

    title: str
    source: str
    url: str
    snippet: str
    summary: str
    date: str


class ResearchInput(TypedDict, total=False):
    """Research context accepted by the quota estimator."""

    company_name: str
    summary: str
    articles: list[ResearchArticleInput]
    key_metrics: dict[str, object]
    growth_rate: float


class WorkIQInput(TypedDict, total=False):
    """WorkIQ or synthetic M365 activity input accepted by the estimator."""

    customer: str
    source: str
    engagement_score: str
    last_contact: str
    recent_activity: list[dict[str, object]]


@dataclass(frozen=True)
class HistoricalSalesRow:
    """Normalized sales row from WWI historical sales data."""

    territory: str
    category: str
    order_date: date
    revenue: float
    quantity: float


@dataclass(frozen=True)
class ResearchContext:
    """Normalized market context and citable sources."""

    summary: str
    growth_rate_hint: float | None = None
    citations: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class WorkIQActivity:
    """Normalized M365 activity signal used as an engagement adjustment."""

    source: str
    engagement_score: str
    activity_count: int
    last_contact: str | None = None


@dataclass(frozen=True)
class QuotaRecommendation:
    """Recommended quota line item for a territory and product category."""

    territory: str
    category: str
    trailing_revenue: float
    trailing_quantity: float
    historical_growth_rate: float
    market_adjustment: float
    engagement_adjustment: float
    scenario_adjustment: float
    recommended_growth_rate: float
    recommended_quota: float
    rationale: str


@dataclass(frozen=True)
class GeneratedArtifact:
    """Generated quota report artifact metadata."""

    format: str
    path: Path


@dataclass(frozen=True)
class QuotaEstimate:
    """Complete quota estimate before or after rendering artifacts."""

    customer_name: str
    generated_at: datetime
    scenario: str
    sales_rows: list[HistoricalSalesRow]
    research_context: ResearchContext
    workiq_activity: WorkIQActivity
    recommendations: list[QuotaRecommendation]
    methodology: str
    citations: list[str]
    artifacts: list[GeneratedArtifact] = field(default_factory=list)

    @property
    def trailing_revenue_total(self) -> float:
        return sum(item.trailing_revenue for item in self.recommendations)

    @property
    def recommended_quota_total(self) -> float:
        return sum(item.recommended_quota for item in self.recommendations)

    @property
    def overall_growth_rate(self) -> float:
        trailing = self.trailing_revenue_total
        if trailing == 0:
            return 0.0
        return (self.recommended_quota_total - trailing) / trailing
