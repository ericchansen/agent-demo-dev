"""Quota estimation calculations and report orchestration."""

from __future__ import annotations

import re
from collections import defaultdict
from collections.abc import Mapping, Sequence
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import cast

from src.agents.quota_estimator.data_sources import SalesDataSource, resolve_sales_data_source
from src.agents.quota_estimator.models import (
    GeneratedArtifact,
    HistoricalSalesRow,
    QuotaEstimate,
    QuotaRecommendation,
    ResearchContext,
    WorkIQActivity,
)
from src.agents.quota_estimator.renderers import render_quota_html, render_quota_pdf, render_quota_xlsx

_DEFAULT_FORMATS = ("xlsx", "html", "pdf")
_SUPPORTED_FORMATS = frozenset(_DEFAULT_FORMATS)
_DATE_FIELDS = (
    "order_date",
    "OrderDate",
    "orderDate",
    "sales_order_date",
    "SalesOrderDate",
    "order_timestamp",
    "orderTimestamp",
)
_TERRITORY_FIELDS = (
    "territory",
    "territory_name",
    "Territory",
    "SalesTerritory",
    "TerritoryName",
    "sales_territory",
    "salesTerritory",
    "territory_name_uc",
)
_CATEGORY_FIELDS = (
    "category",
    "product_category",
    "ProductCategory",
    "stock_item_category",
    "StockItemCategory",
    "productCategory",
    "item_category",
)
_REVENUE_FIELDS = (
    "revenue",
    "total_revenue",
    "sales_amount",
    "TotalDue",
    "extended_price",
    "ExtendedPrice",
    "net_sales_amount",
    "gross_sales_amount",
    "salesAmount",
    "extendedAmount",
)
_QUANTITY_FIELDS = (
    "quantity",
    "Quantity",
    "quantity_sold",
    "QuantitySold",
    "units_sold",
    "sold_quantity",
    "quantitySold",
)

# Deterministic scenario adjustments applied on top of the trend, market, and engagement signals.
_SCENARIO_ADJUSTMENTS: dict[str, float] = {
    "conservative": -0.03,
    "base": 0.0,
    "aggressive": 0.03,
}
_DEFAULT_SCENARIO = "base"


def _normalize_scenario(scenario: str | None) -> str:
    if scenario is None:
        return _DEFAULT_SCENARIO
    normalized = str(scenario).strip().lower()
    if not normalized:
        return _DEFAULT_SCENARIO
    if normalized not in _SCENARIO_ADJUSTMENTS:
        allowed = ", ".join(sorted(_SCENARIO_ADJUSTMENTS))
        raise ValueError(f"Unsupported scenario '{scenario}'. Allowed values: {allowed}.")
    return normalized


def build_quota_estimate(
    *,
    customer_name: str,
    sales_rows: Sequence[Mapping[str, object]],
    research_data: Mapping[str, object] | None = None,
    workiq_activity: Mapping[str, object] | None = None,
    data_source: str | None = None,
    scenario: str | None = _DEFAULT_SCENARIO,
    generated_at: datetime | None = None,
) -> QuotaEstimate:
    """Build a deterministic quota estimate from normalized sales, research, and WorkIQ inputs."""
    normalized_scenario = _normalize_scenario(scenario)
    source = resolve_sales_data_source(data_source, sales_rows)
    normalized_rows = _normalize_sales_rows(sales_rows)
    research_context = _normalize_research_context(research_data or {})
    activity = _normalize_workiq_activity(workiq_activity or {})
    recommendations = _build_recommendations(normalized_rows, research_context, activity, normalized_scenario)
    timestamp = generated_at or datetime.now()

    methodology = _build_methodology(source, normalized_scenario)
    citations = [
        source.citation,
        *research_context.citations,
        f"WorkIQ activity context: {activity.source}.",
    ]

    return QuotaEstimate(
        customer_name=customer_name,
        generated_at=timestamp,
        scenario=normalized_scenario,
        sales_rows=normalized_rows,
        research_context=research_context,
        workiq_activity=activity,
        recommendations=recommendations,
        methodology=methodology,
        citations=citations,
    )


def _build_methodology(source: SalesDataSource, scenario: str) -> str:
    return (
        f"Normalized historical sales rows from {source.query_surface} into the shared quota row contract "
        "(territory, category, order date, revenue, and quantity), grouped rows by territory and product category, "
        "calculated a bounded "
        "historical trend for each group, then adjusted growth using market research and WorkIQ engagement "
        f"signals and the '{scenario}' scenario. Recommended quota equals trailing revenue "
        "multiplied by the final growth rate."
    )


def generate_quota_estimation_report(
    *,
    customer_name: str,
    sales_rows: Sequence[Mapping[str, object]],
    research_data: Mapping[str, object] | None = None,
    workiq_activity: Mapping[str, object] | None = None,
    data_source: str | None = None,
    scenario: str | None = _DEFAULT_SCENARIO,
    output_dir: str | Path = Path("output") / "quota-estimates",
    formats: Sequence[str] | None = None,
    generated_at: datetime | None = None,
) -> dict[str, object]:
    """Generate quota estimate artifacts and return a JSON-serializable result."""
    estimate = build_quota_estimate(
        customer_name=customer_name,
        sales_rows=sales_rows,
        research_data=research_data,
        workiq_activity=workiq_activity,
        data_source=data_source,
        scenario=scenario,
        generated_at=generated_at,
    )
    requested_formats = _normalize_formats(formats)
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    stem = f"{_slugify_filename(customer_name)}_{estimate.scenario}_quota_estimate"

    artifacts: list[GeneratedArtifact] = []
    for fmt in requested_formats:
        artifact_path = output_path / f"{stem}.{fmt}"
        if fmt == "xlsx":
            rendered = render_quota_xlsx(estimate, artifact_path)
        elif fmt == "html":
            rendered = render_quota_html(estimate, artifact_path)
        elif fmt == "pdf":
            rendered = render_quota_pdf(estimate, artifact_path)
        else:
            raise ValueError(f"Unsupported quota report format: {fmt}")
        artifacts.append(GeneratedArtifact(format=fmt, path=Path(rendered)))

    estimate_with_artifacts = QuotaEstimate(
        customer_name=estimate.customer_name,
        generated_at=estimate.generated_at,
        scenario=estimate.scenario,
        sales_rows=estimate.sales_rows,
        research_context=estimate.research_context,
        workiq_activity=estimate.workiq_activity,
        recommendations=estimate.recommendations,
        methodology=estimate.methodology,
        citations=estimate.citations,
        artifacts=artifacts,
    )
    return quota_estimate_to_dict(estimate_with_artifacts)


def quota_estimate_to_dict(estimate: QuotaEstimate) -> dict[str, object]:
    """Convert a quota estimate into a JSON-serializable dictionary."""
    return {
        "status": "success",
        "customer_name": estimate.customer_name,
        "generated_at": estimate.generated_at.isoformat(timespec="seconds"),
        "scenario": estimate.scenario,
        "summary": {
            "trailing_revenue_total": round(estimate.trailing_revenue_total, 2),
            "recommended_quota_total": round(estimate.recommended_quota_total, 2),
            "overall_growth_rate": round(estimate.overall_growth_rate, 4),
        },
        "recommendations": [
            {
                "territory": item.territory,
                "category": item.category,
                "trailing_revenue": round(item.trailing_revenue, 2),
                "trailing_quantity": round(item.trailing_quantity, 2),
                "historical_growth_rate": round(item.historical_growth_rate, 4),
                "market_adjustment": round(item.market_adjustment, 4),
                "engagement_adjustment": round(item.engagement_adjustment, 4),
                "scenario_adjustment": round(item.scenario_adjustment, 4),
                "recommended_growth_rate": round(item.recommended_growth_rate, 4),
                "recommended_quota": round(item.recommended_quota, 2),
                "rationale": item.rationale,
            }
            for item in estimate.recommendations
        ],
        "research_context": {
            "summary": estimate.research_context.summary,
            "growth_rate_hint": estimate.research_context.growth_rate_hint,
        },
        "workiq_activity": {
            "source": estimate.workiq_activity.source,
            "engagement_score": estimate.workiq_activity.engagement_score,
            "activity_count": estimate.workiq_activity.activity_count,
            "last_contact": estimate.workiq_activity.last_contact,
        },
        "methodology": estimate.methodology,
        "citations": estimate.citations,
        "artifacts": {artifact.format: str(artifact.path.resolve()) for artifact in estimate.artifacts},
    }


def _normalize_sales_rows(rows: Sequence[Mapping[str, object]]) -> list[HistoricalSalesRow]:
    if not rows:
        raise ValueError("sales_rows must include at least one sales row.")

    normalized: list[HistoricalSalesRow] = []
    for index, row in enumerate(rows):
        territory = _coerce_required_str(row, _TERRITORY_FIELDS, index)
        category = _coerce_optional_str(row, _CATEGORY_FIELDS, "All Products")
        order_date = _coerce_required_date(row, _DATE_FIELDS, index)
        revenue = _coerce_required_float(row, _REVENUE_FIELDS, index)
        quantity = _coerce_optional_float(row, _QUANTITY_FIELDS, 0.0)
        normalized.append(
            HistoricalSalesRow(
                territory=territory,
                category=category,
                order_date=order_date,
                revenue=revenue,
                quantity=quantity,
            )
        )

    return normalized


def _normalize_research_context(raw: Mapping[str, object]) -> ResearchContext:
    summary = _coerce_str(raw.get("summary"), "No market research context supplied.")
    growth_hint = _extract_growth_rate(raw)
    citations: list[str] = []

    articles = raw.get("articles")
    if isinstance(articles, list):
        for item in articles:
            if not isinstance(item, Mapping):
                continue
            title = _coerce_str(item.get("title"), "Untitled research")
            source = _coerce_str(item.get("source"), "market research")
            url = _coerce_str(item.get("url"), "")
            citation = f"{title} - {source}"
            if url:
                citation = f"{citation} ({url})"
            citations.append(citation)

    if not citations and summary:
        citations.append("Market research summary provided to quota-estimator.")

    return ResearchContext(summary=summary, growth_rate_hint=growth_hint, citations=citations)


def _normalize_workiq_activity(raw: Mapping[str, object]) -> WorkIQActivity:
    source = _coerce_str(raw.get("source"), "synthetic demo activity")
    engagement_score = _coerce_str(raw.get("engagement_score"), "Medium")
    last_contact_value = raw.get("last_contact")
    last_contact = _coerce_str(last_contact_value, "") if last_contact_value is not None else None
    recent_activity = raw.get("recent_activity")
    activity_count = len(recent_activity) if isinstance(recent_activity, list) else 0
    return WorkIQActivity(
        source=source,
        engagement_score=engagement_score,
        activity_count=activity_count,
        last_contact=last_contact or None,
    )


def _build_recommendations(
    rows: Sequence[HistoricalSalesRow],
    research_context: ResearchContext,
    activity: WorkIQActivity,
    scenario: str,
) -> list[QuotaRecommendation]:
    grouped: dict[tuple[str, str], list[HistoricalSalesRow]] = defaultdict(list)
    for row in rows:
        grouped[(row.territory, row.category)].append(row)

    recommendations: list[QuotaRecommendation] = []
    market_adjustment = _market_adjustment(research_context.growth_rate_hint)
    engagement_adjustment = _engagement_adjustment(activity)
    scenario_adjustment = _SCENARIO_ADJUSTMENTS[scenario]

    for territory, category in sorted(grouped):
        group_rows = grouped[(territory, category)]
        trailing_revenue = sum(row.revenue for row in group_rows)
        trailing_quantity = sum(row.quantity for row in group_rows)
        historical_growth_rate = _historical_growth_rate(group_rows)
        recommended_growth_rate = _clamp(
            0.04 + (historical_growth_rate * 0.5) + market_adjustment + engagement_adjustment + scenario_adjustment,
            -0.05,
            0.25,
        )
        recommended_quota = trailing_revenue * (1 + recommended_growth_rate)
        rationale = (
            f"{territory} / {category}: trend {historical_growth_rate * 100:.1f}%, "
            f"market adjustment {market_adjustment * 100:.1f}%, "
            f"engagement adjustment {engagement_adjustment * 100:.1f}%, "
            f"{scenario} scenario adjustment {scenario_adjustment * 100:.1f}%."
        )
        recommendations.append(
            QuotaRecommendation(
                territory=territory,
                category=category,
                trailing_revenue=trailing_revenue,
                trailing_quantity=trailing_quantity,
                historical_growth_rate=historical_growth_rate,
                market_adjustment=market_adjustment,
                engagement_adjustment=engagement_adjustment,
                scenario_adjustment=scenario_adjustment,
                recommended_growth_rate=recommended_growth_rate,
                recommended_quota=recommended_quota,
                rationale=rationale,
            )
        )

    return recommendations


def _historical_growth_rate(rows: Sequence[HistoricalSalesRow]) -> float:
    if len(rows) < 2:
        return 0.0

    ordered = sorted(rows, key=lambda row: row.order_date)
    first_date = ordered[0].order_date
    last_date = ordered[-1].order_date
    if first_date == last_date:
        return 0.0

    midpoint_ordinal = first_date.toordinal() + ((last_date.toordinal() - first_date.toordinal()) // 2)
    midpoint = date.fromordinal(midpoint_ordinal)
    previous_revenue = sum(row.revenue for row in ordered if row.order_date <= midpoint)
    recent_revenue = sum(row.revenue for row in ordered if row.order_date > midpoint)

    if previous_revenue <= 0:
        return 0.05 if recent_revenue > 0 else 0.0

    return _clamp((recent_revenue - previous_revenue) / previous_revenue, -0.20, 0.30)


def _market_adjustment(growth_rate_hint: float | None) -> float:
    if growth_rate_hint is None:
        return 0.0
    return _clamp(growth_rate_hint / 4, -0.03, 0.05)


def _engagement_adjustment(activity: WorkIQActivity) -> float:
    score = activity.engagement_score.lower().strip()
    score_adjustments = {
        "very high": 0.04,
        "high": 0.03,
        "medium": 0.01,
        "moderate": 0.01,
        "low": -0.02,
        "none": -0.03,
    }
    score_adjustment = score_adjustments.get(score, 0.0)
    volume_adjustment = min(activity.activity_count, 6) * 0.002
    return _clamp(score_adjustment + volume_adjustment, -0.03, 0.05)


def _extract_growth_rate(raw: Mapping[str, object]) -> float | None:
    explicit = raw.get("growth_rate")
    if isinstance(explicit, (int, float)):
        value = float(explicit)
        return value / 100 if abs(value) > 1 else value

    metrics = raw.get("key_metrics")
    if isinstance(metrics, Mapping):
        for key in ("revenue_yoy_growth", "market_growth", "growth_rate"):
            metric_value = metrics.get(key)
            parsed = _parse_percentage(metric_value)
            if parsed is not None:
                return parsed

    return _parse_percentage(raw.get("summary"))


def _parse_percentage(value: object) -> float | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        numeric = float(value)
        return numeric / 100 if abs(numeric) > 1 else numeric

    match = re.search(r"(-?\d+(?:\.\d+)?)\s*%", str(value))
    if match is None:
        return None
    return float(match.group(1)) / 100


def _normalize_formats(formats: Sequence[str] | None) -> tuple[str, ...]:
    requested = tuple(fmt.lower().strip(". ") for fmt in (formats or _DEFAULT_FORMATS))
    unsupported = sorted(fmt for fmt in requested if fmt not in _SUPPORTED_FORMATS)
    if unsupported:
        raise ValueError(f"Unsupported quota report format(s): {', '.join(unsupported)}")
    return requested or _DEFAULT_FORMATS


def _coerce_required_str(row: Mapping[str, object], fields: Sequence[str], index: int) -> str:
    value = _first_present(row, fields)
    text = _coerce_str(value, "")
    if not text:
        raise ValueError(f"sales_rows[{index}] is missing one of: {', '.join(fields)}")
    return text


def _coerce_optional_str(row: Mapping[str, object], fields: Sequence[str], default: str) -> str:
    return _coerce_str(_first_present(row, fields), default) or default


def _coerce_required_float(row: Mapping[str, object], fields: Sequence[str], index: int) -> float:
    value = _first_present(row, fields)
    parsed = _coerce_float(value)
    if parsed is None:
        raise ValueError(f"sales_rows[{index}] is missing numeric field one of: {', '.join(fields)}")
    return parsed


def _coerce_optional_float(row: Mapping[str, object], fields: Sequence[str], default: float) -> float:
    parsed = _coerce_float(_first_present(row, fields))
    return default if parsed is None else parsed


def _coerce_required_date(row: Mapping[str, object], fields: Sequence[str], index: int) -> date:
    value = _first_present(row, fields)
    parsed = _coerce_date(value)
    if parsed is None:
        raise ValueError(f"sales_rows[{index}] is missing date field one of: {', '.join(fields)}")
    return parsed


def _first_present(row: Mapping[str, object], fields: Sequence[str]) -> object | None:
    for field in fields:
        if field in row and row[field] not in (None, ""):
            return row[field]
    return None


def _coerce_str(value: object, default: str = "") -> str:
    if value is None:
        return default
    if isinstance(value, str):
        return value.strip()
    return str(value).strip()


def _coerce_float(value: object) -> float | None:
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        normalized = value.replace("$", "").replace(",", "").strip()
        if normalized:
            return float(normalized)
    return None


def _coerce_date(value: object) -> date | None:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if not isinstance(value, str):
        return None

    text = value.strip()
    if not text:
        return None
    for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%m/%d/%Y"):
        try:
            return datetime.strptime(text[:19], fmt).date()
        except ValueError:
            continue
    return None


def _slugify_filename(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "_", value.strip().lower()).strip("._")
    return cleaned or "quota_estimate"


def _clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(maximum, value))


def demo_sales_rows(as_of: date | None = None) -> list[dict[str, object]]:
    """Return deterministic sample sales rows for local demos and compatibility wrappers.

    Order dates are generated relative to ``as_of`` (defaults to today) so demos always show a
    recent trailing window. Pass a fixed ``as_of`` in tests to keep output deterministic.
    """
    anchor = as_of or date.today()

    def _offset(days: int) -> str:
        return (anchor - timedelta(days=days)).isoformat()

    return [
        {
            "territory": "Northwest",
            "category": "Novelty Items",
            "order_date": _offset(320),
            "revenue": 190000,
            "quantity": 410,
        },
        {
            "territory": "Northwest",
            "category": "Novelty Items",
            "order_date": _offset(40),
            "revenue": 260000,
            "quantity": 520,
        },
        {
            "territory": "Northwest",
            "category": "Toys",
            "order_date": _offset(270),
            "revenue": 90000,
            "quantity": 240,
        },
        {
            "territory": "Northwest",
            "category": "Toys",
            "order_date": _offset(20),
            "revenue": 125000,
            "quantity": 300,
        },
        {
            "territory": "Southwest",
            "category": "Clothing",
            "order_date": _offset(250),
            "revenue": 155000,
            "quantity": 350,
        },
        {
            "territory": "Southwest",
            "category": "Clothing",
            "order_date": _offset(15),
            "revenue": 165000,
            "quantity": 360,
        },
    ]


def demo_research_data(customer_name: str) -> dict[str, object]:
    """Return deterministic market context when live research is not configured."""
    return {
        "company_name": customer_name,
        "summary": (
            f"{customer_name} is expanding digital retail and distributor channels. "
            "Comparable novelty goods accounts show 12% year-over-year demand growth."
        ),
        "key_metrics": {"revenue_yoy_growth": "12%"},
        "articles": [
            {
                "title": f"{customer_name} retail expansion signal",
                "source": "Synthetic market research",
                "url": "https://example.com/quota-research",
                "summary": "Demo market context used when SEARCH_PROVIDER is mock or unavailable.",
            }
        ],
    }


def demo_workiq_activity(customer_name: str, as_of: date | None = None) -> dict[str, object]:
    """Return deterministic synthetic WorkIQ activity for tenants without WorkIQ credentials.

    Activity dates are generated relative to ``as_of`` (defaults to today). Pass a fixed ``as_of``
    in tests to keep output deterministic.
    """
    anchor = as_of or date.today()

    def _offset(days: int) -> str:
        return (anchor - timedelta(days=days)).isoformat()

    return {
        "customer": customer_name,
        "source": "synthetic demo activity (WorkIQ credentials not configured)",
        "engagement_score": "High",
        "last_contact": _offset(3),
        "recent_activity": [
            {"type": "email", "subject": f"FY planning - {customer_name}", "date": _offset(3)},
            {"type": "meeting", "subject": f"Quota workshop - {customer_name}", "date": _offset(13)},
            {"type": "email", "subject": f"Pricing proposal - {customer_name}", "date": _offset(21)},
            {"type": "meeting", "subject": f"QBR prep - {customer_name}", "date": _offset(34)},
        ],
    }


def forecast_payload_from_estimate(estimate: QuotaEstimate) -> dict[str, object]:
    """Convert a full quota estimate into the legacy forecast_quota payload."""
    by_category: dict[str, tuple[float, float]] = {}
    for recommendation in estimate.recommendations:
        current, projected = by_category.get(recommendation.category, (0.0, 0.0))
        by_category[recommendation.category] = (
            current + recommendation.trailing_revenue,
            projected + recommendation.recommended_quota,
        )

    items: list[dict[str, object]] = []
    for category, totals in sorted(by_category.items()):
        current, projected = totals
        growth_rate = 0.0 if current == 0 else (projected - current) / current
        items.append(
            {
                "category": category,
                "current_fy_revenue": round(current, 2),
                "growth_rate": round(growth_rate, 4),
                "projected_fy_revenue": round(projected, 2),
            }
        )

    return {
        "customer": estimate.customer_name,
        "scenario": estimate.scenario,
        "current_fy_total": round(estimate.trailing_revenue_total, 2),
        "projected_fy_total": round(estimate.recommended_quota_total, 2),
        "overall_growth_rate": round(estimate.overall_growth_rate, 4),
        "methodology": estimate.methodology,
        "items": cast(object, items),
    }
