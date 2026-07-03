"""Firecrawl IR collector payload and Market Signal Graph RPC helpers."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
import json
from typing import Any
from urllib.parse import urlparse

import httpx


DESIGN_NAME = "firecrawl_ir_collector_v1"
SOURCE_PLATFORM = "firecrawl_ir"
SOURCE_KIND = "ir"
CHANNEL = "web"
COLLECTOR = "firecrawl"
TARGET_TYPE = "company_ir"
EXPECTED_FIRECRAWL_MCP_VERSION = "3.17.0"
DEFAULT_READINESS_SAMPLE = {
    "company": "Apple",
    "ticker": "AAPL",
    "raw_url": "https://investor.apple.com/",
    "resolved_url": "https://investor.apple.com/",
    "page_title": "Apple Investor Relations",
    "markdown": "Apple Investor Relations provides earnings releases, SEC filings, governance materials, and shareholder information.",
    "language": "en",
}


@dataclass(frozen=True)
class FirecrawlIrInput:
    company: str
    ticker: str
    raw_url: str
    resolved_url: str | None = None
    page_title: str | None = None
    markdown: str | None = None
    text: str | None = None
    author: str | None = None
    language: str = "en"
    published_at: str | None = None


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_hex(value: str) -> str:
    return sha256(value.encode("utf-8")).hexdigest()


def normalize_ir_markdown(value: str | None, *, max_chars: int = 1400) -> str:
    compact = " ".join(str(value or "").replace("\r", "\n").split())
    if len(compact) <= max_chars:
        return compact
    return compact[: max(0, max_chars - 1)].rstrip() + "..."


def _safe_company(value: str, ticker: str) -> str:
    company = " ".join(str(value or "").split())
    return company or str(ticker or "").strip().upper() or "company"


def _safe_ticker(value: str) -> str:
    return str(value or "").strip().upper()


def _safe_url(raw_url: str, resolved_url: str | None = None) -> str:
    candidate = str(resolved_url or raw_url or "").strip()
    parsed = urlparse(candidate)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("Firecrawl IR payload requires a public http/https URL.")
    return candidate


def _safe_title(value: str | None, company: str) -> str:
    title = " ".join(str(value or "").split())
    return title[:180] or f"{company} Investor Relations"


def _dict_value(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _first_non_empty(*values: Any) -> Any:
    for value in values:
        if value is None:
            continue
        if isinstance(value, str) and not value.strip():
            continue
        return value
    return None


def _firecrawl_payload_containers(item: dict[str, Any]) -> list[dict[str, Any]]:
    containers = [item]
    for key in ["data", "scrape", "firecrawl", "result"]:
        nested = _dict_value(item.get(key))
        if nested:
            containers.append(nested)
    return containers


def _firecrawl_metadata(containers: list[dict[str, Any]]) -> dict[str, Any]:
    for container in containers:
        metadata = _dict_value(container.get("metadata"))
        if metadata:
            return metadata
    return {}


def _coerce_firecrawl_ir_input(item: dict[str, Any]) -> FirecrawlIrInput:
    containers = _firecrawl_payload_containers(item)
    metadata = _firecrawl_metadata(containers)
    markdown = _first_non_empty(*(container.get("markdown") for container in containers))
    text = _first_non_empty(*(container.get("text") for container in containers))
    raw_url = _first_non_empty(
        item.get("raw_url"),
        item.get("source_url"),
        item.get("url"),
        metadata.get("sourceURL"),
        metadata.get("sourceUrl"),
        metadata.get("url"),
        metadata.get("ogUrl"),
    )
    resolved_url = _first_non_empty(
        item.get("resolved_url"),
        item.get("final_url"),
        item.get("resolvedURL"),
        item.get("finalUrl"),
        metadata.get("sourceURL"),
        metadata.get("sourceUrl"),
        metadata.get("url"),
        metadata.get("ogUrl"),
    )
    return FirecrawlIrInput(
        company=str(_first_non_empty(item.get("company"), metadata.get("company")) or ""),
        ticker=str(_first_non_empty(item.get("ticker"), metadata.get("ticker"), metadata.get("symbol")) or ""),
        raw_url=str(raw_url or ""),
        resolved_url=resolved_url,
        page_title=_first_non_empty(item.get("page_title"), item.get("title"), metadata.get("title")),
        markdown=markdown,
        text=text,
        author=_first_non_empty(item.get("author"), metadata.get("author")),
        language=str(_first_non_empty(item.get("language"), metadata.get("language")) or "en"),
        published_at=_first_non_empty(item.get("published_at"), metadata.get("publishedTime")),
    )


def build_firecrawl_ir_signal_payload(item: FirecrawlIrInput | dict[str, Any]) -> dict[str, Any]:
    if isinstance(item, dict):
        item = _coerce_firecrawl_ir_input(item)
    ticker = _safe_ticker(item.ticker)
    company = _safe_company(item.company, ticker)
    raw_url = str(item.raw_url or "").strip()
    resolved_url = _safe_url(raw_url, item.resolved_url)
    title = _safe_title(item.page_title, company)
    summary_source = item.text if item.text is not None else item.markdown
    normalized_text = normalize_ir_markdown(summary_source)
    if not normalized_text:
        normalized_text = f"{company} Investor Relations page captured by Firecrawl."
    external_id = sha256_hex(resolved_url)
    canonical_hash = sha256_hex(f"{SOURCE_PLATFORM}{resolved_url}{title}")
    return {
        "source_name": f"{company}_ir",
        "source_platform": SOURCE_PLATFORM,
        "source_kind": SOURCE_KIND,
        "channel": CHANNEL,
        "external_id": external_id,
        "url": resolved_url,
        "title": title,
        "text": normalized_text,
        "author": item.author or f"{company} Investor Relations",
        "language": item.language or "en",
        "canonical_hash": canonical_hash,
        "metadata": {
            "collector": COLLECTOR,
            "collector_design": DESIGN_NAME,
            "target_type": TARGET_TYPE,
            "company": company,
            "ticker": ticker,
            "page_type": "investor_relations",
            "raw_url": raw_url or resolved_url,
            "resolved_url": resolved_url,
            "content_chars": len(normalized_text),
        },
        "published_at": item.published_at or "",
        "needs_enrichment": True,
        "analysis_status": "pending",
    }


def normalize_firecrawl_ir_inputs(data: Any) -> list[FirecrawlIrInput | dict[str, Any]]:
    if isinstance(data, list):
        return [item for item in data if isinstance(item, dict)]
    if isinstance(data, dict):
        for key in ["items", "sources", "results", "payloads"]:
            value = data.get(key)
            if isinstance(value, list):
                return [item for item in value if isinstance(item, dict)]
        return [data]
    return []


def upsert_external_signal_payload(
    payload: dict[str, Any],
    *,
    rpc_url: str,
    service_role_key: str,
    timeout_seconds: float = 10.0,
) -> dict[str, Any]:
    if not rpc_url:
        return {
            "status": "skipped",
            "reason": "market_signal_graph_rpc_url_missing",
            "design": DESIGN_NAME,
        }
    if not service_role_key:
        return {
            "status": "skipped",
            "reason": "market_signal_graph_service_role_key_missing",
            "design": DESIGN_NAME,
        }
    headers = {
        "apikey": service_role_key,
        "authorization": f"Bearer {service_role_key}",
        "content-type": "application/json",
    }
    try:
        with httpx.Client(timeout=timeout_seconds, trust_env=False) as client:
            response = client.post(rpc_url, headers=headers, json={"payload": payload})
        if response.status_code in {200, 201, 204}:
            data: Any = None
            if response.content:
                try:
                    data = response.json()
                except ValueError:
                    data = response.text[:500]
            return {
                "status": "success",
                "design": DESIGN_NAME,
                "http_status": response.status_code,
                "result": data,
            }
        lowered = response.text.lower()
        reason = "supabase_project_paused" if "paused" in lowered or "inactive" in lowered else "rpc_error"
        return {
            "status": "skipped" if reason == "supabase_project_paused" else "failed",
            "reason": reason,
            "design": DESIGN_NAME,
            "http_status": response.status_code,
            "message": response.text[:500],
        }
    except httpx.RequestError as exc:
        return {
            "status": "skipped",
            "reason": "market_signal_graph_unreachable",
            "design": DESIGN_NAME,
            "message": str(exc)[:500],
        }


def firecrawl_scrape_endpoint(base_url: str | None) -> str:
    effective_base_url = str(base_url or "https://api.firecrawl.dev/v2").strip().rstrip("/")
    return f"{effective_base_url}/scrape"


def scrape_firecrawl_ir_item(
    item: FirecrawlIrInput | dict[str, Any],
    settings: Any,
) -> dict[str, Any]:
    """Call Firecrawl hosted scrape for one public IR URL and return a non-secret dry-run payload."""

    api_key = _settings_str(settings, "firecrawl_api_key")
    if not api_key:
        return {
            "status": "skipped",
            "reason": "firecrawl_api_key_missing",
            "design": DESIGN_NAME,
        }
    input_item = item if isinstance(item, FirecrawlIrInput) else _coerce_firecrawl_ir_input(item)
    url = _safe_url(input_item.raw_url, input_item.resolved_url)
    timeout_seconds = _settings_float(settings, "firecrawl_timeout_seconds", 30.0)
    endpoint = firecrawl_scrape_endpoint(_settings_str(settings, "firecrawl_base_url", "https://api.firecrawl.dev/v2"))
    request_payload = {
        "url": url,
        "formats": ["markdown"],
        "onlyMainContent": True,
        "removeBase64Images": True,
        "blockAds": True,
        "timeout": int(timeout_seconds * 1000),
    }
    headers = {
        "authorization": f"Bearer {api_key}",
        "content-type": "application/json",
    }
    try:
        with httpx.Client(timeout=timeout_seconds, trust_env=False) as client:
            response = client.post(endpoint, headers=headers, json=request_payload)
        response_text = response.text[:500]
        if response.status_code not in {200, 201}:
            return {
                "status": "failed",
                "reason": "firecrawl_scrape_error",
                "design": DESIGN_NAME,
                "http_status": response.status_code,
                "message": response_text,
            }
        try:
            body = response.json()
        except ValueError:
            return {
                "status": "failed",
                "reason": "firecrawl_response_not_json",
                "design": DESIGN_NAME,
                "http_status": response.status_code,
                "message": response_text,
            }
        data = body.get("data") if isinstance(body, dict) else {}
        if not isinstance(data, dict):
            data = {}
        merged_item: dict[str, Any] = {
            "company": input_item.company,
            "ticker": input_item.ticker,
            "raw_url": input_item.raw_url,
            "resolved_url": input_item.resolved_url or input_item.raw_url,
            "page_title": input_item.page_title,
            "language": input_item.language,
            "published_at": input_item.published_at,
            "firecrawl": data,
        }
        payload = build_firecrawl_ir_signal_payload(merged_item)
        metadata = payload.get("metadata") or {}
        return {
            "status": "success",
            "design": DESIGN_NAME,
            "source_platform": SOURCE_PLATFORM,
            "http_status": response.status_code,
            "url": payload.get("url"),
            "title": payload.get("title"),
            "ticker": metadata.get("ticker"),
            "company": metadata.get("company"),
            "content_chars": metadata.get("content_chars"),
            "external_id_prefix": str(payload.get("external_id") or "")[:12],
            "payload": payload,
            "scraped_at": _utc_now_iso(),
        }
    except httpx.RequestError as exc:
        return {
            "status": "skipped",
            "reason": "firecrawl_unreachable",
            "design": DESIGN_NAME,
            "message": str(exc)[:500],
        }


def collection_status_from_rpc_result(rpc_result: dict[str, Any] | None) -> str:
    rpc_status = str((rpc_result or {}).get("status") or "")
    if rpc_status == "success":
        return "success"
    if rpc_status == "failed":
        return "failed"
    return "skipped"


def batch_status_from_counts(status_counts: dict[str, int]) -> str:
    if status_counts.get("failed", 0):
        return "failed"
    if status_counts.get("success", 0):
        return "success"
    if status_counts.get("skipped", 0):
        return "skipped"
    if status_counts.get("dry_run", 0):
        return "dry_run"
    return "success"


def build_firecrawl_ir_collection_result(
    item: FirecrawlIrInput | dict[str, Any],
    settings: Any,
    *,
    dry_run: bool | None = None,
) -> dict[str, Any]:
    payload = build_firecrawl_ir_signal_payload(item)
    effective_dry_run = settings.firecrawl_ir_dry_run if dry_run is None else dry_run
    result = {
        "status": "dry_run" if effective_dry_run else "ready",
        "design": DESIGN_NAME,
        "source_platform": SOURCE_PLATFORM,
        "payload": payload,
        "rpc": None,
        "collected_at": _utc_now_iso(),
    }
    if effective_dry_run:
        return result
    result["rpc"] = upsert_external_signal_payload(
        payload,
        rpc_url=settings.market_signal_graph_rpc_url,
        service_role_key=settings.market_signal_graph_service_role_key,
        timeout_seconds=settings.market_signal_graph_timeout_seconds,
    )
    result["status"] = collection_status_from_rpc_result(result["rpc"])
    return result


def build_firecrawl_ir_batch_result(
    items: list[FirecrawlIrInput | dict[str, Any]],
    settings: Any,
    *,
    dry_run: bool | None = None,
) -> dict[str, Any]:
    results: list[dict[str, Any]] = []
    for item in items:
        try:
            results.append(build_firecrawl_ir_collection_result(item, settings, dry_run=dry_run))
        except Exception as exc:
            results.append(
                {
                    "status": "failed",
                    "design": DESIGN_NAME,
                    "source_platform": SOURCE_PLATFORM,
                    "error": str(exc),
                    "payload": None,
                    "rpc": None,
                    "collected_at": _utc_now_iso(),
                }
            )
    status_counts: dict[str, int] = {}
    for result in results:
        status = str(result.get("status") or "unknown")
        status_counts[status] = status_counts.get(status, 0) + 1
    failed_count = status_counts.get("failed", 0)
    success_count = status_counts.get("success", 0)
    skipped_count = status_counts.get("skipped", 0)
    return {
        "status": batch_status_from_counts(status_counts),
        "design": DESIGN_NAME,
        "source_platform": SOURCE_PLATFORM,
        "item_count": len(items),
        "success_count": success_count,
        "failed_count": failed_count,
        "skipped_count": skipped_count,
        "status_counts": status_counts,
        "results": results,
        "checked_at": _utc_now_iso(),
    }


def _settings_bool(settings: Any, name: str, default: bool = False) -> bool:
    return bool(getattr(settings, name, default))


def _settings_str(settings: Any, name: str, default: str = "") -> str:
    return str(getattr(settings, name, default) or "").strip()


def _settings_float(settings: Any, name: str, default: float) -> float:
    try:
        return float(getattr(settings, name, default))
    except (TypeError, ValueError):
        return default


def _firecrawl_registry_items(settings: Any) -> tuple[list[dict[str, Any]], str | None]:
    raw = _settings_str(settings, "firecrawl_ir_sources_json")
    if not raw:
        return [], None
    try:
        return normalize_firecrawl_ir_inputs(json.loads(raw)), None
    except json.JSONDecodeError as exc:
        return [], f"FIRECRAWL_IR_SOURCES_JSON parse failed: {exc}"


def _rpc_readiness_errors(settings: Any) -> list[str]:
    errors: list[str] = []
    if not _settings_bool(settings, "firecrawl_ir_enabled"):
        errors.append("FIRECRAWL_IR_ENABLED must be true for RPC submit")
    if _settings_bool(settings, "firecrawl_ir_dry_run", True):
        errors.append("FIRECRAWL_IR_DRY_RUN must be false for RPC submit")
    if not _settings_bool(settings, "market_signal_graph_enabled"):
        errors.append("MARKET_SIGNAL_GRAPH_ENABLED must be true for RPC submit")
    if not _settings_str(settings, "market_signal_graph_rpc_url"):
        errors.append("MARKET_SIGNAL_GRAPH_RPC_URL or SUPABASE_URL must be configured for RPC submit")
    if not _settings_str(settings, "market_signal_graph_service_role_key"):
        errors.append("MARKET_SIGNAL_GRAPH_SERVICE_ROLE_KEY or SUPABASE_SERVICE_ROLE_KEY must be configured for RPC submit")
    return errors


def build_firecrawl_ir_readiness_status(settings: Any) -> dict[str, Any]:
    """Return non-secret Firecrawl readiness and a one-item dry-run payload check."""

    enabled = _settings_bool(settings, "firecrawl_ir_enabled")
    dry_run = _settings_bool(settings, "firecrawl_ir_dry_run", True)
    api_key_configured = bool(_settings_str(settings, "firecrawl_api_key"))
    base_url = _settings_str(settings, "firecrawl_base_url", "https://api.firecrawl.dev/v2").rstrip("/")
    timeout_seconds = _settings_float(settings, "firecrawl_timeout_seconds", 30.0)
    configured_mcp_version = _settings_str(settings, "firecrawl_ir_mcp_version", EXPECTED_FIRECRAWL_MCP_VERSION)
    registry_items, registry_error = _firecrawl_registry_items(settings)
    sample_item = registry_items[0] if registry_items else DEFAULT_READINESS_SAMPLE
    dry_run_result = build_firecrawl_ir_collection_result(sample_item, settings, dry_run=True)
    payload = dry_run_result.get("payload") or {}
    payload_metadata = payload.get("metadata") or {}
    rpc_errors = _rpc_readiness_errors(settings)
    warnings: list[str] = []
    if registry_error:
        warnings.append(registry_error)
    if configured_mcp_version != EXPECTED_FIRECRAWL_MCP_VERSION:
        warnings.append(
            f"FIRECRAWL_IR_MCP_VERSION should be {EXPECTED_FIRECRAWL_MCP_VERSION} "
            f"(configured: {configured_mcp_version or 'missing'})"
        )
    if enabled and not api_key_configured:
        warnings.append("FIRECRAWL_API_KEY is not configured, so hosted API scrape calls cannot run.")
    if not enabled:
        status = "disabled"
        next_action = "FIRECRAWL_IR_ENABLED=false 상태입니다. 파일럿 수집 전 API 키와 소스 레지스트리를 먼저 설정하세요."
    elif not api_key_configured:
        status = "needs_api_key"
        next_action = "FIRECRAWL_API_KEY를 설정한 뒤 공개 IR/SEC URL 1건으로 hosted scrape dry-run을 확인하세요."
    elif warnings:
        status = "needs_attention"
        next_action = "Firecrawl 설정 경고를 해소한 뒤 공개 IR/SEC 보조 수집 provider로 연결하세요."
    else:
        status = "ready"
        next_action = "공개 IR/SEC 수집에서 Firecrawl hosted scrape를 선택 provider로 붙일 수 있습니다."
    preflight_commands = {
        "sample_payload": (
            "python tools\\check_firecrawl_ir_collector.py "
            "--input-json docs\\examples\\firecrawl_ir_registry.sample.json --json"
        ),
        "hosted_scrape_dry_run": (
            "python tools\\check_firecrawl_ir_collector.py "
            "--env-file backend\\.env.firecrawl-ir --use-env-registry --hosted-scrape-dry-run --json"
        ),
        "rpc_ready_required": (
            "python tools\\check_firecrawl_ir_collector.py "
            "--env-file backend\\.env.firecrawl-ir --use-env-registry --require-rpc-ready --json"
        ),
        "rpc_submit": (
            "python tools\\check_firecrawl_ir_collector.py "
            "--env-file backend\\.env.firecrawl-ir --use-env-registry --require-rpc-ready --submit --json"
        ),
    }
    return {
        "status": status,
        "module": "firecrawl_ir_readiness",
        "design": DESIGN_NAME,
        "enabled": enabled,
        "dry_run": dry_run,
        "hosted_api": {
            "api_key_configured": api_key_configured,
            "base_url": base_url,
            "timeout_seconds": timeout_seconds,
        },
        "mcp": {
            "configured_version": configured_mcp_version,
            "expected_version": EXPECTED_FIRECRAWL_MCP_VERSION,
            "version_ok": configured_mcp_version == EXPECTED_FIRECRAWL_MCP_VERSION,
        },
        "source_registry": {
            "item_count": len(registry_items),
            "input_source": "env_registry" if registry_items else "sample",
            "parse_error": registry_error,
        },
        "dry_run_sample": {
            "status": dry_run_result.get("status"),
            "source_platform": payload.get("source_platform"),
            "external_id_prefix": str(payload.get("external_id") or "")[:12],
            "url": payload.get("url"),
            "title": payload.get("title"),
            "ticker": payload_metadata.get("ticker"),
            "company": payload_metadata.get("company"),
            "content_chars": payload_metadata.get("content_chars"),
        },
        "rpc": {
            "enabled": bool(_settings_bool(settings, "market_signal_graph_enabled") and enabled),
            "submit_ready": not rpc_errors,
            "readiness_errors": rpc_errors,
        },
        "operations": {
            "secret_env_example": "docs\\examples\\firecrawl_ir_rpc.env.example",
            "local_secret_env": "backend\\.env.firecrawl-ir",
            "preflight_commands": preflight_commands,
            "production_checklist": [
                "FIRECRAWL_API_KEY configured in backend secret env",
                "FIRECRAWL_IR_ENABLED=true",
                "FIRECRAWL_IR_DRY_RUN=false",
                "MARKET_SIGNAL_GRAPH_ENABLED=true",
                "MARKET_SIGNAL_GRAPH_RPC_URL or SUPABASE_URL configured",
                "MARKET_SIGNAL_GRAPH_SERVICE_ROLE_KEY or SUPABASE_SERVICE_ROLE_KEY configured",
                "final preflight: --require-rpc-ready before --submit",
            ],
        },
        "warnings": warnings,
        "next_action": next_action,
    }


def build_firecrawl_ir_hosted_dry_run_result(settings: Any) -> dict[str, Any]:
    registry_items, registry_error = _firecrawl_registry_items(settings)
    if registry_error:
        return {
            "status": "failed",
            "module": "firecrawl_ir_hosted_dry_run",
            "design": DESIGN_NAME,
            "reason": "firecrawl_ir_sources_json_parse_error",
            "message": registry_error,
            "source_registry": {
                "item_count": 0,
                "input_source": "env_registry",
                "parse_error": registry_error,
            },
        }
    sample_item = registry_items[0] if registry_items else DEFAULT_READINESS_SAMPLE
    result = scrape_firecrawl_ir_item(sample_item, settings)
    status = str(result.get("status") or "unknown")
    next_action = ""
    if status == "success":
        next_action = "Firecrawl hosted scrape dry-run이 성공했습니다. 같은 registry로 RPC 저장 전환 전 payload를 검토하세요."
    elif result.get("reason") == "firecrawl_api_key_missing":
        next_action = "FIRECRAWL_API_KEY를 backend secret env에 설정한 뒤 다시 실행하세요."
    else:
        next_action = "Firecrawl hosted scrape 응답과 URL 접근 가능 여부를 확인하세요."
    return {
        "status": status,
        "module": "firecrawl_ir_hosted_dry_run",
        "design": DESIGN_NAME,
        "source_registry": {
            "item_count": len(registry_items),
            "input_source": "env_registry" if registry_items else "sample",
            "parse_error": None,
        },
        "hosted_scrape": {
            key: value
            for key, value in result.items()
            if key
            in {
                "status",
                "reason",
                "design",
                "source_platform",
                "http_status",
                "url",
                "title",
                "ticker",
                "company",
                "content_chars",
                "external_id_prefix",
                "scraped_at",
                "message",
            }
        },
        "payload": result.get("payload") if status == "success" else None,
        "next_action": next_action,
    }
