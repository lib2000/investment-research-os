"""Small helpers for saved portfolio storage."""

from __future__ import annotations

from copy import deepcopy
from re import sub
from typing import Any

from research_os.models import PortfolioHolding, SavedPortfolio
from research_os.settings import Settings
from research_os.state_store import portfolio_store_path, read_json_store, write_json_store


def portfolio_store_key(portfolio_name: str) -> str:
    """Return a stable JSON-store key for a user-visible portfolio name."""
    normalized = sub(r"[^\w-]+", "-", portfolio_name.strip().upper()).strip("-_")
    return normalized or "DEFAULT"


FAMILY_AGGREGATE_PORTFOLIO_NAME = "가족 합산"
FAMILY_AGGREGATE_PORTFOLIO_KEY = portfolio_store_key(FAMILY_AGGREGATE_PORTFOLIO_NAME)
FAMILY_AGGREGATE_METADATA_KEY = "family_aggregate"
FAMILY_AGGREGATE_MODE = "derived_read_only"


def is_family_aggregate_portfolio_name(portfolio_name: str | None) -> bool:
    """Return whether a user-visible name targets the derived family view."""
    return portfolio_store_key(str(portfolio_name or "")) == FAMILY_AGGREGATE_PORTFOLIO_KEY


def portfolio_name_sort_key(portfolio: SavedPortfolio) -> str:
    """Sort saved portfolios by Korean/user-visible name without touching data."""
    return portfolio.portfolio_name.casefold()


def _as_mapping(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _as_number(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    try:
        return float(str(value).replace(",", ""))
    except (TypeError, ValueError):
        return None


def _all_or_none(values: list[float | None]) -> float | None:
    if not values or any(value is None for value in values):
        return None
    return sum(value for value in values if value is not None)


def _first_nonempty(values: list[str | None], default: str | None = None) -> str | None:
    for value in values:
        normalized = str(value or "").strip()
        if normalized:
            return normalized
    return default


def _oldest_timestamp(values: list[str | None]) -> str | None:
    normalized = [str(value).strip() for value in values if str(value or "").strip()]
    return min(normalized) if normalized else None


def _joined_unique(values: list[str]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        normalized = str(value or "").strip()
        if normalized and normalized not in seen:
            seen.add(normalized)
            result.append(normalized)
    return result


def _legacy_family_aggregate_payload(store: dict[str, Any]) -> dict[str, Any] | None:
    portfolios = _as_mapping(store.get("portfolios"))
    for key, payload in portfolios.items():
        if not isinstance(payload, dict):
            continue
        if is_family_aggregate_portfolio_name(str(key)) or is_family_aggregate_portfolio_name(
            str(payload.get("portfolio_name") or "")
        ):
            return payload
    metadata = _as_mapping(store.get(FAMILY_AGGREGATE_METADATA_KEY))
    snapshot = metadata.get("legacy_snapshot")
    return snapshot if isinstance(snapshot, dict) else None


def _family_aggregate_settings(store: dict[str, Any]) -> dict[str, Any]:
    metadata = _as_mapping(store.get(FAMILY_AGGREGATE_METADATA_KEY))
    configured = _as_mapping(metadata.get("settings"))
    legacy = _legacy_family_aggregate_payload(store) or {}

    def value(name: str, default: Any) -> Any:
        for source in (configured, legacy):
            candidate = source.get(name)
            if candidate is not None and candidate != "":
                return candidate
        return default

    return {
        "max_single_position_weight": value("max_single_position_weight", 0.2),
        "max_sector_weight": value("max_sector_weight", 0.35),
        "max_theme_weight": value("max_theme_weight", 0.4),
        "notes": value("notes", ""),
        "created_at": value("created_at", None),
        "migrated_at": metadata.get("migrated_at"),
    }


def family_member_portfolios(store: dict[str, Any]) -> list[SavedPortfolio]:
    """Return valid individual portfolios, explicitly excluding the aggregate alias."""
    members: list[SavedPortfolio] = []
    portfolios = _as_mapping(store.get("portfolios"))
    for key, payload in portfolios.items():
        if not isinstance(payload, dict) or is_family_aggregate_portfolio_name(str(key)):
            continue
        if is_family_aggregate_portfolio_name(str(payload.get("portfolio_name") or "")):
            continue
        try:
            members.append(SavedPortfolio.model_validate(payload))
        except (TypeError, ValueError):
            # The offline structural checker reports malformed source records.
            # A derived display must not make an invalid member editable again.
            continue
    return sorted(members, key=portfolio_name_sort_key)


def _derive_aggregate_holding(
    ticker: str,
    entries: list[tuple[SavedPortfolio, PortfolioHolding]],
) -> PortfolioHolding:
    holdings = [holding for _portfolio, holding in entries]
    source_names = _joined_unique([portfolio.portfolio_name for portfolio, _holding in entries])
    quantities = [_as_number(holding.quantity) for holding in holdings]
    quantity = _all_or_none(quantities)
    currencies = _joined_unique([holding.currency for holding in holdings])
    currency = currencies[0] if len(currencies) == 1 else "MIXED"

    cost_basis = _all_or_none([_as_number(holding.cost_basis) for holding in holdings])
    market_value = _all_or_none([_as_number(holding.market_value) for holding in holdings])
    weighted_costs = [
        quantity_value * average_cost
        if quantity_value is not None and (average_cost := _as_number(holding.average_cost)) is not None
        else None
        for holding, quantity_value in zip(holdings, quantities)
    ]
    weighted_prices = [
        quantity_value * current_price
        if quantity_value is not None and (current_price := _as_number(holding.current_price)) is not None
        else None
        for holding, quantity_value in zip(holdings, quantities)
    ]
    local_cost_sum = _all_or_none(weighted_costs)
    local_price_sum = _all_or_none(weighted_prices)
    average_cost = local_cost_sum / quantity if local_cost_sum is not None and quantity and currency != "MIXED" else None
    current_price = local_price_sum / quantity if local_price_sum is not None and quantity and currency != "MIXED" else None
    unrealized_gain = market_value - cost_basis if market_value is not None and cost_basis is not None else None
    unrealized_return = unrealized_gain / cost_basis if unrealized_gain is not None and cost_basis and cost_basis > 0 else None

    sectors = _joined_unique([
        holding.sector for holding in holdings if str(holding.sector or "").strip() and holding.sector != "Unknown"
    ])
    theme_tags = _joined_unique([tag for holding in holdings for tag in holding.theme_tags])
    return PortfolioHolding(
        ticker=ticker,
        name=_first_nonempty([holding.name for holding in holdings], ticker),
        quantity=quantity,
        average_cost=average_cost,
        current_price=current_price,
        market_value=market_value,
        cost_basis=cost_basis,
        unrealized_gain=unrealized_gain,
        unrealized_return=unrealized_return,
        price_source="family_aggregate",
        price_refresh_status="derived",
        price_checked_at=_oldest_timestamp([holding.price_checked_at for holding in holdings]),
        sector=sectors[0] if len(sectors) == 1 else ("Mixed" if sectors else "Unknown"),
        theme_tags=theme_tags,
        currency=currency,
        sync_status="derived_read_only",
        sync_source="individual_portfolios",
        sync_checked_at=_oldest_timestamp([holding.sync_checked_at for holding in holdings]),
        sync_message=f"{', '.join(source_names)} 개인 포트폴리오에서 자동 합산한 읽기 전용 값입니다.",
    )


def derive_family_aggregate_portfolio(store: dict[str, Any]) -> SavedPortfolio | None:
    """Build a read-only family aggregate from individual saved portfolios."""
    members = family_member_portfolios(store)
    if not members:
        return None

    grouped: dict[str, list[tuple[SavedPortfolio, PortfolioHolding]]] = {}
    for portfolio in members:
        for holding in portfolio.holdings:
            ticker = str(holding.ticker or "").strip().upper()
            if not ticker:
                continue
            grouped.setdefault(ticker, []).append((portfolio, holding))

    aggregate_holdings = [
        _derive_aggregate_holding(ticker, entries)
        for ticker, entries in sorted(grouped.items(), key=lambda item: item[0])
    ]
    portfolio_value = _all_or_none([_as_number(holding.market_value) for holding in aggregate_holdings])
    options = _family_aggregate_settings(store)
    source_names = [portfolio.portfolio_name for portfolio in members]
    notes = str(options.get("notes") or "").strip()
    derived_note = "개인별 포트폴리오를 자동 합산한 읽기 전용 보기입니다. 개별 포트폴리오에서 수정하세요."
    notes = f"{notes}\n\n{derived_note}".strip() if notes else derived_note
    return SavedPortfolio(
        portfolio_name=FAMILY_AGGREGATE_PORTFOLIO_NAME,
        holdings=aggregate_holdings,
        portfolio_value=portfolio_value,
        max_single_position_weight=float(options.get("max_single_position_weight") or 0.2),
        max_sector_weight=float(options.get("max_sector_weight") or 0.35),
        max_theme_weight=float(options.get("max_theme_weight") or 0.4),
        notes=notes,
        holding_count=len(aggregate_holdings),
        created_at=options.get("created_at") or _oldest_timestamp([portfolio.created_at for portfolio in members]),
        updated_at=_oldest_timestamp([portfolio.updated_at for portfolio in members]),
        is_derived=True,
        derived_from_portfolios=source_names,
    )


def with_derived_family_aggregate(store: dict[str, Any]) -> dict[str, Any]:
    """Return a read model that replaces any static family aggregate copy."""
    payload = deepcopy(store) if isinstance(store, dict) else {"portfolios": {}}
    portfolios = payload.get("portfolios")
    if not isinstance(portfolios, dict):
        portfolios = {}
        payload["portfolios"] = portfolios
    legacy = _legacy_family_aggregate_payload(payload)
    if legacy is not None:
        # A read can be followed by a write through legacy API call sites. Keep
        # the hidden static payload in metadata until the explicit migration
        # tool has created a dated backup, rather than silently dropping it.
        metadata = _as_mapping(payload.get(FAMILY_AGGREGATE_METADATA_KEY))
        metadata.setdefault("mode", FAMILY_AGGREGATE_MODE)
        metadata.setdefault("portfolio_name", FAMILY_AGGREGATE_PORTFOLIO_NAME)
        metadata.setdefault("legacy_snapshot", deepcopy(legacy))
        payload[FAMILY_AGGREGATE_METADATA_KEY] = metadata
    aggregate = derive_family_aggregate_portfolio(payload)
    if aggregate is None:
        portfolios.pop(FAMILY_AGGREGATE_PORTFOLIO_KEY, None)
    else:
        portfolios[FAMILY_AGGREGATE_PORTFOLIO_KEY] = aggregate.model_dump(mode="json")
    return payload


def prepare_portfolio_store_for_write(store: dict[str, Any]) -> dict[str, Any]:
    """Strip the read-only aggregate before persisting a mutable portfolio store.

    A pre-migration legacy payload is retained in local metadata if a caller
    writes before the dedicated migration tool has produced its dated backup.
    That avoids silently discarding the old snapshot.
    """
    payload = deepcopy(store) if isinstance(store, dict) else {"portfolios": {}}
    portfolios = payload.get("portfolios")
    if not isinstance(portfolios, dict):
        portfolios = {}
        payload["portfolios"] = portfolios
    aggregate_payload = portfolios.pop(FAMILY_AGGREGATE_PORTFOLIO_KEY, None)
    if isinstance(aggregate_payload, dict) and not aggregate_payload.get("is_derived"):
        metadata = _as_mapping(payload.get(FAMILY_AGGREGATE_METADATA_KEY))
        metadata.setdefault("mode", FAMILY_AGGREGATE_MODE)
        metadata.setdefault("portfolio_name", FAMILY_AGGREGATE_PORTFOLIO_NAME)
        metadata.setdefault(
            "settings",
            {
                key: aggregate_payload.get(key)
                for key in ("max_single_position_weight", "max_sector_weight", "max_theme_weight", "notes", "created_at")
                if aggregate_payload.get(key) is not None
            },
        )
        metadata.setdefault("legacy_snapshot", aggregate_payload)
        payload[FAMILY_AGGREGATE_METADATA_KEY] = metadata
    return payload


def read_portfolio_store(settings: Settings) -> dict[str, Any]:
    """Read portfolios with a reproducible family aggregate in the read model."""
    raw = read_json_store(portfolio_store_path(settings), {"portfolios": {}})
    return with_derived_family_aggregate(raw)


def write_portfolio_store(settings: Settings, store: dict[str, Any]) -> None:
    """Persist only mutable individual portfolios, never the derived aggregate."""
    write_json_store(portfolio_store_path(settings), prepare_portfolio_store_for_write(store))


def family_aggregate_integrity_report(store: dict[str, Any]) -> dict[str, Any]:
    """Describe whether a raw store can safely serve the derived family view."""
    raw_portfolios = _as_mapping(store.get("portfolios"))
    static_entries = [
        key
        for key, payload in raw_portfolios.items()
        if is_family_aggregate_portfolio_name(str(key))
        or (isinstance(payload, dict) and is_family_aggregate_portfolio_name(str(payload.get("portfolio_name") or "")))
    ]
    members = family_member_portfolios(store)
    aggregate = derive_family_aggregate_portfolio(store)
    metadata = _as_mapping(store.get(FAMILY_AGGREGATE_METADATA_KEY))
    errors: list[str] = []
    if static_entries:
        errors.append("활성 포트폴리오 저장소에 정적 가족-합산 사본이 남아 있습니다.")
    if not members:
        errors.append("가족-합산을 계산할 개인별 포트폴리오가 없습니다.")
    if metadata and metadata.get("mode") not in {None, FAMILY_AGGREGATE_MODE}:
        errors.append("가족-합산 메타데이터 모드가 읽기 전용 계산 모드가 아닙니다.")
    return {
        "status": "error" if errors else "ok",
        "mode": FAMILY_AGGREGATE_MODE,
        "family_portfolio_name": FAMILY_AGGREGATE_PORTFOLIO_NAME,
        "legacy_static_entries": static_entries,
        "owner_portfolio_count": len(members),
        "owner_portfolios": [portfolio.portfolio_name for portfolio in members],
        "derived_holding_count": aggregate.holding_count if aggregate else 0,
        "derived_portfolio_value": aggregate.portfolio_value if aggregate else None,
        "derived_updated_at": aggregate.updated_at if aggregate else None,
        "metadata": {
            "present": bool(metadata),
            "mode": metadata.get("mode"),
            "legacy_backup": metadata.get("legacy_backup"),
        },
        "errors": errors,
    }


def infer_holding_fx_rate(holding: PortfolioHolding) -> float:
    """Infer the KRW conversion rate from a saved USD holding when possible."""
    if holding.currency.upper() != "USD":
        return 1.0
    if (
        holding.cost_basis
        and holding.quantity
        and holding.average_cost
        and holding.quantity > 0
        and holding.average_cost > 0
    ):
        inferred = holding.cost_basis / (holding.quantity * holding.average_cost)
        if inferred > 0:
            return inferred
    if (
        holding.market_value
        and holding.quantity
        and holding.average_cost
        and holding.quantity > 0
        and holding.average_cost > 0
        and holding.current_price is None
    ):
        inferred = holding.market_value / (holding.quantity * holding.average_cost)
        if inferred > 0:
            return inferred
    return 1.0
