"""Firecrawl monitor readiness and safe create helpers."""

from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
import json
from typing import Any
from urllib.parse import urlparse

import httpx


DESIGN_NAME = "firecrawl_monitor_collector_v1"
DEFAULT_MONITOR_EVENTS = ["monitor.page", "monitor.check.completed"]
DEFAULT_MONITOR_SOURCE = {
    "name": "Investment policy and IR monitor",
    "schedule": {"text": "daily at 8am", "timezone": "Asia/Seoul"},
    "goal": (
        "Notify when a monitored policy, filing, investor relations, or market event page "
        "has a meaningful change that may affect portfolio risk or investment decisions."
    ),
    "judgeEnabled": True,
    "targets": [
        {
            "type": "scrape",
            "urls": ["https://www.sec.gov/newsroom/press-releases"],
            "scrapeOptions": {
                "formats": ["markdown", {"type": "changeTracking", "modes": ["git-diff"]}],
                "onlyMainContent": True,
                "removeBase64Images": True,
                "blockAds": True,
            },
        }
    ],
    "retentionDays": 30,
}


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _settings_bool(settings: Any, name: str, default: bool = False) -> bool:
    return bool(getattr(settings, name, default))


def _settings_str(settings: Any, name: str, default: str = "") -> str:
    return str(getattr(settings, name, default) or "").strip()


def _settings_float(settings: Any, name: str, default: float) -> float:
    try:
        return float(getattr(settings, name, default))
    except (TypeError, ValueError):
        return default


def _looks_like_placeholder(value: str) -> bool:
    lowered = str(value or "").strip().lower()
    return not lowered or lowered.startswith("replace-with-") or lowered in {"changeme", "todo", "placeholder"}


def _sha256_json(value: Any) -> str:
    return sha256(json.dumps(value, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()


def _public_url(value: str) -> str:
    url = str(value or "").strip()
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("Firecrawl monitor target URLs must be public http/https URLs.")
    return url


def firecrawl_monitor_endpoint(base_url: str | None) -> str:
    effective_base_url = str(base_url or "https://api.firecrawl.dev/v2").strip().rstrip("/")
    return f"{effective_base_url}/monitor"


def _normalize_schedule(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        schedule = {k: v for k, v in value.items() if k in {"text", "cron", "timezone"} and v}
    elif isinstance(value, str) and value.strip():
        schedule = {"text": value.strip()}
    else:
        schedule = {}
    if not schedule.get("text") and not schedule.get("cron"):
        schedule["text"] = "daily at 8am"
    schedule.setdefault("timezone", "Asia/Seoul")
    return schedule


def _normalize_change_tracking(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        modes = value.get("modes")
        if not isinstance(modes, list) or not modes:
            modes = ["git-diff"]
        normalized: dict[str, Any] = {"type": "changeTracking", "modes": [str(item) for item in modes]}
        if isinstance(value.get("prompt"), str) and value["prompt"].strip():
            normalized["prompt"] = value["prompt"].strip()
        if isinstance(value.get("schema"), dict):
            normalized["schema"] = value["schema"]
        return normalized
    return {"type": "changeTracking", "modes": ["git-diff"]}


def _normalize_scrape_options(value: Any) -> dict[str, Any]:
    options = value.copy() if isinstance(value, dict) else {}
    formats = options.get("formats")
    if not isinstance(formats, list) or not formats:
        formats = ["markdown", _normalize_change_tracking(options.get("changeTracking"))]
    if "markdown" not in formats:
        formats.insert(0, "markdown")
    if not any(isinstance(item, dict) and item.get("type") == "changeTracking" for item in formats):
        formats.append(_normalize_change_tracking(options.get("changeTracking")))
    options["formats"] = formats
    options.setdefault("onlyMainContent", True)
    options.setdefault("removeBase64Images", True)
    options.setdefault("blockAds", True)
    return options


def _normalize_target(target: dict[str, Any]) -> dict[str, Any]:
    target_type = str(target.get("type") or "scrape").strip().lower()
    if target_type not in {"scrape", "crawl", "search"}:
        raise ValueError(f"Unsupported Firecrawl monitor target type: {target_type}")
    normalized: dict[str, Any] = {"type": target_type}
    if target_type == "scrape":
        urls = target.get("urls") or ([target.get("url")] if target.get("url") else [])
        if not isinstance(urls, list) or not urls:
            raise ValueError("Firecrawl scrape monitor targets require urls.")
        normalized["urls"] = [_public_url(str(url)) for url in urls]
        normalized["scrapeOptions"] = _normalize_scrape_options(target.get("scrapeOptions"))
    elif target_type == "crawl":
        url = target.get("url")
        if not url:
            urls = target.get("urls") if isinstance(target.get("urls"), list) else []
            url = urls[0] if urls else ""
        normalized["url"] = _public_url(str(url))
        if target.get("includePaths"):
            normalized["includePaths"] = target.get("includePaths")
        if target.get("excludePaths"):
            normalized["excludePaths"] = target.get("excludePaths")
        normalized["limit"] = int(target.get("limit") or 50)
        normalized["scrapeOptions"] = _normalize_scrape_options(target.get("scrapeOptions"))
    else:
        query = str(target.get("query") or "").strip()
        if not query:
            raise ValueError("Firecrawl search monitor targets require query.")
        normalized["query"] = query
        if target.get("limit"):
            normalized["limit"] = int(target.get("limit"))
    return normalized


def normalize_firecrawl_monitor_sources(data: Any) -> list[dict[str, Any]]:
    if data is None:
        return []
    if isinstance(data, dict):
        for key in ("monitors", "items", "sources"):
            if isinstance(data.get(key), list):
                return normalize_firecrawl_monitor_sources(data[key])
        raw_items = [data]
    elif isinstance(data, list):
        raw_items = data
    else:
        raise ValueError("Firecrawl monitor sources must be a JSON object or list.")
    monitors: list[dict[str, Any]] = []
    for raw in raw_items:
        if not isinstance(raw, dict):
            raise ValueError("Each Firecrawl monitor source must be an object.")
        name = " ".join(str(raw.get("name") or "Investment web monitor").split())[:120]
        targets = raw.get("targets")
        if not isinstance(targets, list) or not targets:
            if raw.get("url") or raw.get("urls"):
                targets = [{"type": "scrape", "url": raw.get("url"), "urls": raw.get("urls")}]
            elif raw.get("query"):
                targets = [{"type": "search", "query": raw.get("query"), "limit": raw.get("limit", 10)}]
            else:
                targets = DEFAULT_MONITOR_SOURCE["targets"]
        normalized = {
            "name": name or "Investment web monitor",
            "schedule": _normalize_schedule(raw.get("schedule")),
            "goal": " ".join(str(raw.get("goal") or DEFAULT_MONITOR_SOURCE["goal"]).split())[:2000],
            "judgeEnabled": bool(raw.get("judgeEnabled", raw.get("judge_enabled", True))),
            "targets": [_normalize_target(target) for target in targets],
            "retentionDays": max(1, min(365, int(raw.get("retentionDays") or raw.get("retention_days") or 30))),
        }
        webhook = raw.get("webhook")
        if isinstance(webhook, dict) and webhook.get("url"):
            normalized["webhook"] = {
                "url": _public_url(str(webhook.get("url"))),
                "headers": webhook.get("headers") if isinstance(webhook.get("headers"), dict) else {},
                "metadata": webhook.get("metadata") if isinstance(webhook.get("metadata"), dict) else {},
                "events": webhook.get("events") if isinstance(webhook.get("events"), list) else DEFAULT_MONITOR_EVENTS,
            }
        notification = raw.get("notification")
        if isinstance(notification, dict):
            normalized["notification"] = notification
        monitors.append(normalized)
    return monitors


def _firecrawl_monitor_sources(settings: Any) -> tuple[list[dict[str, Any]], str | None]:
    raw = _settings_str(settings, "firecrawl_monitor_sources_json")
    if not raw:
        return [normalize_firecrawl_monitor_sources(DEFAULT_MONITOR_SOURCE)[0]], None
    try:
        return normalize_firecrawl_monitor_sources(json.loads(raw)), None
    except (json.JSONDecodeError, ValueError) as exc:
        return [], f"FIRECRAWL_MONITOR_SOURCES_JSON parse failed: {exc}"


def _monitor_create_readiness_errors(
    settings: Any,
    sources: list[dict[str, Any]] | None = None,
    parse_error: str | None = None,
) -> list[str]:
    errors: list[str] = []
    if not _settings_bool(settings, "firecrawl_monitor_enabled"):
        errors.append("FIRECRAWL_MONITOR_ENABLED must be true for monitor create")
    if _settings_bool(settings, "firecrawl_monitor_dry_run", True):
        errors.append("FIRECRAWL_MONITOR_DRY_RUN must be false for monitor create")
    api_key = _settings_str(settings, "firecrawl_api_key")
    if not api_key or _looks_like_placeholder(api_key):
        errors.append("FIRECRAWL_API_KEY must be configured with a non-placeholder value for monitor create")
    if parse_error:
        errors.append(parse_error)
    if sources is None:
        sources, parse_error = _firecrawl_monitor_sources(settings)
        if parse_error:
            errors.append(parse_error)
    if not sources:
        errors.append("FIRECRAWL_MONITOR_SOURCES_JSON did not produce monitor sources")
    elif not any(isinstance(item, dict) and item.get("webhook") for item in sources):
        errors.append("At least one Firecrawl monitor webhook URL must be configured before monitor create")
    return errors


def build_firecrawl_monitor_readiness_status(settings: Any) -> dict[str, Any]:
    enabled = _settings_bool(settings, "firecrawl_monitor_enabled")
    dry_run = _settings_bool(settings, "firecrawl_monitor_dry_run", True)
    api_key = _settings_str(settings, "firecrawl_api_key")
    api_key_configured = bool(api_key) and not _looks_like_placeholder(api_key)
    registry_configured = bool(_settings_str(settings, "firecrawl_monitor_sources_json"))
    webhook_secret = _settings_str(settings, "firecrawl_monitor_webhook_secret")
    webhook_secret_configured = bool(webhook_secret) and not _looks_like_placeholder(webhook_secret)
    sources, parse_error = _firecrawl_monitor_sources(settings)
    create_errors = _monitor_create_readiness_errors(settings, sources, parse_error)
    sample = sources[0] if sources else None
    monitor_webhook_count = sum(1 for item in sources if isinstance(item, dict) and item.get("webhook"))
    warnings = [parse_error] if parse_error else []
    if sources and monitor_webhook_count == 0:
        warnings.append("No Firecrawl monitor webhook target is configured in the normalized registry")
    operational_errors: list[str] = []
    if not registry_configured:
        operational_errors.append("FIRECRAWL_MONITOR_SOURCES_JSON must be configured for operational preflight")
    if not webhook_secret_configured:
        operational_errors.append("FIRECRAWL_MONITOR_WEBHOOK_SECRET must be configured for webhook preflight")
    if sources and monitor_webhook_count == 0:
        operational_errors.append("At least one Firecrawl monitor webhook URL must be configured in FIRECRAWL_MONITOR_SOURCES_JSON")
    if parse_error:
        operational_errors.append(parse_error)
    if not enabled:
        status = "disabled"
        next_action = "FIRECRAWL_MONITOR_ENABLED=false 상태입니다. 모니터 registry와 dry-run 검증을 먼저 완료하세요."
    elif not api_key_configured:
        status = "needs_api_key"
        next_action = "FIRECRAWL_API_KEY를 backend secret env에 설정한 뒤 monitor dry-run을 확인하세요."
    elif warnings:
        status = "needs_attention"
        next_action = "Firecrawl monitor registry JSON 오류를 먼저 해소하세요."
    elif dry_run:
        status = "dry_run_ready"
        next_action = "monitor create payload가 준비되었습니다. 실제 생성 전 예상 credit과 webhook 대상을 검토하세요."
    else:
        status = "ready"
        next_action = "Firecrawl /v2/monitor 생성 호출이 가능합니다."
    preflight_commands = {
        "sample_payload": (
            "python tools\\check_firecrawl_monitor_collector.py "
            "--input-json docs\\examples\\firecrawl_monitor_registry.sample.json --json"
        ),
        "operational_preflight": (
            "python tools\\check_firecrawl_monitor_operational_preflight.py "
            "--env-file backend\\.env.firecrawl-monitor --require-env-registry --require-webhook-secret "
            "--require-monitor-webhook --json"
        ),
        "create_ready_required": (
            "python tools\\check_firecrawl_monitor_operational_preflight.py "
            "--env-file backend\\.env.firecrawl-monitor --require-env-registry --require-webhook-secret "
            "--require-monitor-webhook --require-create-ready --json"
        ),
    }
    return {
        "status": status,
        "module": "firecrawl_monitor_readiness",
        "design": DESIGN_NAME,
        "enabled": enabled,
        "dry_run": dry_run,
        "hosted_api": {
            "api_key_configured": api_key_configured,
            "base_url": _settings_str(settings, "firecrawl_base_url", "https://api.firecrawl.dev/v2").rstrip("/"),
            "timeout_seconds": _settings_float(settings, "firecrawl_timeout_seconds", 30.0),
        },
        "source_registry": {
            "item_count": len(sources),
            "input_source": "env_registry" if registry_configured else "sample",
            "configured": registry_configured,
            "parse_error": parse_error,
        },
        "sample_monitor": {
            "name": sample.get("name") if sample else None,
            "target_count": len(sample.get("targets") or []) if sample else 0,
            "target_types": [target.get("type") for target in (sample.get("targets") or [])] if sample else [],
            "schedule": sample.get("schedule") if sample else None,
            "goal_configured": bool(sample and sample.get("goal")),
            "webhook_configured": bool(sample and sample.get("webhook")),
            "payload_hash_prefix": _sha256_json(sample)[:12] if sample else "",
        },
        "operational_preflight": {
            "ready": not operational_errors,
            "registry_configured": registry_configured,
            "webhook_secret_configured": webhook_secret_configured,
            "monitor_webhook_configured": monitor_webhook_count > 0,
            "monitor_webhook_count": monitor_webhook_count,
            "monitor_count": len(sources),
            "requires_create_ready": False,
            "errors": operational_errors,
            "command": preflight_commands["operational_preflight"],
            "create_ready_command": preflight_commands["create_ready_required"],
        },
        "create_ready": not create_errors,
        "create_readiness_errors": create_errors,
        "operations": {
            "local_secret_env": "backend\\.env.firecrawl-monitor",
            "env_template_command": "python tools\\create_firecrawl_monitor_env_template.py --output backend\\.env.firecrawl-monitor",
            "preflight_commands": preflight_commands,
            "production_checklist": [
                "FIRECRAWL_API_KEY configured in backend secret env",
                "FIRECRAWL_MONITOR_ENABLED=true",
                "FIRECRAWL_MONITOR_DRY_RUN=false",
                "FIRECRAWL_MONITOR_SOURCES_JSON configured",
                "FIRECRAWL_MONITOR_WEBHOOK_SECRET configured",
                "at least one monitor webhook.url configured",
                "final preflight: --require-create-ready before creating monitors",
            ],
        },
        "warnings": warnings,
        "next_action": next_action,
    }


def build_firecrawl_monitor_dry_run_result(settings: Any) -> dict[str, Any]:
    sources, parse_error = _firecrawl_monitor_sources(settings)
    if parse_error:
        return {
            "status": "failed",
            "module": "firecrawl_monitor_dry_run",
            "design": DESIGN_NAME,
            "reason": "firecrawl_monitor_sources_json_parse_error",
            "message": parse_error,
            "source_registry": {"item_count": 0, "input_source": "env_registry", "parse_error": parse_error},
        }
    readiness = build_firecrawl_monitor_readiness_status(settings)
    return {
        "status": "dry_run",
        "module": "firecrawl_monitor_dry_run",
        "design": DESIGN_NAME,
        "source_registry": {
            "item_count": len(sources),
            "input_source": "env_registry" if _settings_str(settings, "firecrawl_monitor_sources_json") else "sample",
            "parse_error": None,
        },
        "readiness_status": readiness.get("status"),
        "operational_preflight": readiness.get("operational_preflight") or {},
        "create_ready": bool(readiness.get("create_ready")),
        "create_readiness_errors": readiness.get("create_readiness_errors") or [],
        "production_checklist": ((readiness.get("operations") or {}).get("production_checklist") or []),
        "monitors": [
            {
                "name": item.get("name"),
                "target_count": len(item.get("targets") or []),
                "target_types": [target.get("type") for target in item.get("targets") or []],
                "schedule": item.get("schedule"),
                "goal": item.get("goal"),
                "webhook_configured": bool(item.get("webhook")),
                "payload_hash_prefix": _sha256_json(item)[:12],
                "payload": item,
            }
            for item in sources
        ],
        "checked_at": _utc_now_iso(),
        "next_action": "dry-run payload를 검토한 뒤 FIRECRAWL_MONITOR_DRY_RUN=false에서 create를 실행하세요.",
    }


def create_firecrawl_monitor(item: dict[str, Any], settings: Any) -> dict[str, Any]:
    errors = _monitor_create_readiness_errors(settings)
    if errors:
        return {"status": "skipped", "reason": "monitor_create_not_ready", "readiness_errors": errors, "design": DESIGN_NAME}
    api_key = _settings_str(settings, "firecrawl_api_key")
    timeout_seconds = _settings_float(settings, "firecrawl_timeout_seconds", 30.0)
    endpoint = firecrawl_monitor_endpoint(_settings_str(settings, "firecrawl_base_url", "https://api.firecrawl.dev/v2"))
    headers = {"authorization": f"Bearer {api_key}", "content-type": "application/json"}
    try:
        with httpx.Client(timeout=timeout_seconds, trust_env=False) as client:
            response = client.post(endpoint, headers=headers, json=item)
        response_text = response.text[:500]
        if response.status_code not in {200, 201}:
            return {
                "status": "failed",
                "reason": "firecrawl_monitor_create_error",
                "design": DESIGN_NAME,
                "http_status": response.status_code,
                "message": response_text,
            }
        body = response.json()
        data = body.get("data") if isinstance(body, dict) else {}
        return {
            "status": "success",
            "design": DESIGN_NAME,
            "http_status": response.status_code,
            "monitor": {
                "id": data.get("id") if isinstance(data, dict) else None,
                "name": data.get("name") if isinstance(data, dict) else item.get("name"),
                "status": data.get("status") if isinstance(data, dict) else None,
                "nextRunAt": data.get("nextRunAt") if isinstance(data, dict) else None,
                "estimatedCreditsPerMonth": data.get("estimatedCreditsPerMonth") if isinstance(data, dict) else None,
            },
            "created_at": _utc_now_iso(),
        }
    except (httpx.RequestError, ValueError) as exc:
        return {"status": "skipped", "reason": "firecrawl_monitor_unreachable", "design": DESIGN_NAME, "message": str(exc)[:500]}
