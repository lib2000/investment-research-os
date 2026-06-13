"""Target-price parsing helpers backed by stored research memory files."""

from __future__ import annotations

import json
from pathlib import Path
from re import IGNORECASE, findall, finditer


def target_price_numeric_value(runtime, raw_value: object, unit: str | None) -> float | None:
    value = runtime.parse_float_or_none(raw_value)
    if value is None:
        return None
    unit_text = str(unit or "").upper()
    if "만원" in str(unit or ""):
        return value * 10000
    if unit_text in {"BN", "B"}:
        return None
    return value


def parse_structured_trade_target_from_json(runtime, memory_file, holding_currency: str) -> dict | None:
    json_path = Path(memory_file.absolute_path).with_suffix(".json")
    if not json_path.exists():
        return None
    try:
        payload = json.loads(json_path.read_text(encoding="utf-8", errors="ignore"))
    except (OSError, json.JSONDecodeError):
        return None
    targets = payload.get("targets")
    if not isinstance(targets, list):
        return None
    for target in targets:
        if not isinstance(target, dict):
            continue
        value = runtime.parse_float_or_none(target.get("price"))
        if value is None:
            continue
        result = runtime.target_price_result(
            value=value,
            currency=(holding_currency or "KRW").upper(),
            memory_file=memory_file,
            source_label="smart-trade-setup:구조화 목표가",
            confidence=0.9,
        )
        if result:
            return result
    return None


def parse_explicit_analyst_target_from_text(
    runtime,
    text: str,
    memory_file,
    holding_currency: str,
) -> dict | None:
    patterns = [
        r"(목표\s*주가|목표\s*가격|목표가|target\s*price|TP)\s*(?:를|은|는|로|까지)?\s*[:：]?\s*(\$|₩)?\s*([0-9][0-9,]*(?:\.\d+)?)\s*(만원|원|달러|USD|KRW)?",
        r"(이에\s*목표\s*주가)\s*(\$|₩)?\s*([0-9][0-9,]*(?:\.\d+)?)\s*(만원|원|달러|USD|KRW)?",
    ]
    for pattern in patterns:
        for match in finditer(pattern, text, flags=0):
            prefix = text[max(0, match.start() - 12):match.start()]
            if "직전" in prefix or "기존" in prefix:
                continue
            label, symbol, raw_value, unit = match.groups()
            value = target_price_numeric_value(runtime, raw_value, unit)
            if value is None:
                continue
            currency = runtime.target_price_currency(symbol, unit, holding_currency)
            result = runtime.target_price_result(
                value=value,
                currency=currency,
                memory_file=memory_file,
                source_label=f"{memory_file.report_type}:명시 목표주가",
                confidence=0.85 if "target" in label.lower() or "목표" in label else 0.8,
            )
            if result:
                return result
    return None


def parse_tactical_trade_target_from_text(
    runtime,
    text: str,
    memory_file,
    holding_currency: str,
) -> dict | None:
    pattern = r"(?:1차|2차|3차)\s*목표가?\s*[:：]?\s*(\$|₩)?\s*([0-9][0-9,]*(?:\.\d+)?)\s*(만원|원|달러|USD|KRW)?"
    for symbol, raw_value, unit in findall(pattern, text, flags=0):
        value = target_price_numeric_value(runtime, raw_value, unit)
        if value is None:
            continue
        currency = runtime.target_price_currency(symbol, unit, holding_currency)
        result = runtime.target_price_result(
            value=value,
            currency=currency,
            memory_file=memory_file,
            source_label=f"{memory_file.report_type}:전술 목표가",
            confidence=0.75,
        )
        if result:
            return result
    return None


def extract_target_price_observations_from_text(
    runtime,
    text: str,
    memory_file,
    holding_currency: str,
    ticker_context: str | None = None,
) -> list[dict]:
    patterns = [
        r"(컨센서스|평균\s*목표\s*주가|증권사\s*평균|목표\s*주가|목표\s*가격|목표가|target\s*price|TP)[^。\n\r]{0,45}?(\$|₩)?\s*([0-9][0-9,]*(?:\.\d+)?)\s*(만원|원|달러|USD|KRW)?",
        r"(\$|₩)?\s*([0-9][0-9,]*(?:\.\d+)?)\s*(만원|원|달러|USD|KRW)?\s*(?:으로|까지|로)?\s*(목표\s*주가|목표가|target\s*price)",
    ]
    observations: list[dict] = []
    seen: set[tuple[str, float, str]] = set()
    for pattern_index, pattern in enumerate(patterns):
        for match in finditer(pattern, text, flags=IGNORECASE):
            if pattern_index == 0:
                _label, symbol, raw_value, unit = match.groups()
            else:
                symbol, raw_value, unit, _label = match.groups()
            value = target_price_numeric_value(runtime, raw_value, unit)
            currency = runtime.target_price_currency(symbol, unit, holding_currency)
            context = text[max(0, match.start() - 90): min(len(text), match.end() + 90)]
            if (
                value is None
                or not runtime.is_plausible_target_price(value, currency)
                or runtime.is_probable_year_or_metadata_number(
                    raw_value,
                    symbol,
                    unit,
                    context,
                    ticker_context=ticker_context,
                )
            ):
                continue
            if any(blocker in context for blocker in ["현재가", "종가", "시가총액", "매출", "영업이익"]):
                if "목표" not in context and "target" not in context.lower():
                    continue
            key = (memory_file.file_name, round(value, 4), currency)
            if key in seen:
                continue
            seen.add(key)
            source_type, confidence = runtime.target_price_context_source_type(context)
            observations.append(
                {
                    "target_price": round(value, 4),
                    "target_price_currency": currency,
                    "source_file": memory_file.file_name,
                    "source_type": source_type,
                    "source_report_type": memory_file.report_type,
                    "source_date": runtime.infer_report_date_from_file(memory_file.file_name),
                    "modified_at": memory_file.modified_at,
                    "confidence": confidence,
                    "context": " ".join(context.split())[:240],
                }
            )
    return observations


def build_target_price_consensus_from_memory(
    runtime,
    ticker: str,
    vault_dir: Path,
    holding_currency: str,
    *,
    limit_files: int = 40,
    manifest_entries: list[dict] | None = None,
) -> dict | None:
    normalized_ticker = runtime.normalize_ticker(ticker)
    observations: list[dict] = []
    allowed_report_types = {"research-capture", "thesis-impact-review", "dossier-synthesis"}
    for memory_file in runtime.list_research_memory_files(
        normalized_ticker,
        vault_dir,
        manifest_entries=manifest_entries,
    )[:limit_files]:
        if memory_file.report_type not in allowed_report_types:
            continue
        try:
            text = Path(memory_file.absolute_path).read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        observations.extend(
            extract_target_price_observations_from_text(
                runtime,
                text,
                memory_file,
                holding_currency,
                ticker_context=normalized_ticker,
            )
        )
    observations = [
        item
        for item in observations
        if item.get("target_price_currency") == (holding_currency or "KRW").upper()
    ]
    if not observations:
        return None
    observations.sort(
        key=lambda item: (
            item.get("source_date") or "",
            item.get("confidence") or 0,
            item.get("modified_at") or "",
        ),
        reverse=True,
    )
    recent = observations[:12]
    values = [float(item["target_price"]) for item in recent if item.get("target_price")]
    if not values:
        return None
    values = runtime.filter_target_price_outliers(values)
    sorted_values = sorted(values)
    midpoint = len(sorted_values) // 2
    median = (
        sorted_values[midpoint]
        if len(sorted_values) % 2
        else (sorted_values[midpoint - 1] + sorted_values[midpoint]) / 2
    )
    consensus_value = sum(values) / len(values)
    return {
        "target_price": round(consensus_value, 4),
        "target_price_currency": (holding_currency or "KRW").upper(),
        "target_price_median": round(median, 4),
        "target_price_high": round(max(values), 4),
        "target_price_low": round(min(values), 4),
        "source_count": len(recent),
        "observation_count": len(observations),
        "source_type": "저장 증권사 리포트 컨센서스",
        "confidence": round(sum(float(item.get("confidence") or 0.75) for item in recent) / len(recent), 2),
        "latest_source_file": recent[0].get("source_file"),
        "latest_source_date": recent[0].get("source_date"),
        "latest_context": recent[0].get("context"),
        "observations": recent,
    }


def parse_latest_target_price_from_memory(
    runtime,
    ticker: str,
    vault_dir: Path,
    holding_currency: str,
) -> dict | None:
    normalized_ticker = runtime.normalize_ticker(ticker)
    memory_files = runtime.list_research_memory_files(normalized_ticker, vault_dir)[:30]
    explicit_source_types = {"research-capture", "thesis-impact-review"}
    trade_source_types = {"smart-trade-setup"}

    for memory_file in memory_files:
        if memory_file.report_type not in explicit_source_types:
            continue
        try:
            text = Path(memory_file.absolute_path).read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        result = parse_explicit_analyst_target_from_text(runtime, text, memory_file, holding_currency)
        if result:
            return result

    for memory_file in memory_files:
        if memory_file.report_type not in trade_source_types:
            continue
        result = parse_structured_trade_target_from_json(runtime, memory_file, holding_currency)
        if result:
            return result

    for memory_file in memory_files:
        if memory_file.report_type not in trade_source_types:
            continue
        try:
            text = Path(memory_file.absolute_path).read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        result = parse_tactical_trade_target_from_text(runtime, text, memory_file, holding_currency)
        if result:
            return result
    return None
