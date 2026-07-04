from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE_DIR = PROJECT_ROOT / "research_vault" / "_system" / "openclaw_integration"
DEFAULT_OPENCLAW_DIR = Path.home() / ".openclaw" / "workspace" / "data" / "investment_research"


SECRET_PATTERNS = [
    re.compile(r'"access_token"\s*:', re.IGNORECASE),
    re.compile(r'"refresh_token"\s*:', re.IGNORECASE),
    re.compile(r'"app(?:_|-)?secret"\s*:', re.IGNORECASE),
    re.compile(r'"secret(?:_|-)?key"\s*:', re.IGNORECASE),
    re.compile(r"Bearer\s+[A-Za-z0-9._~+/=-]{12,}", re.IGNORECASE),
    re.compile(r"kis_access_token\.json\s*:\s*\{", re.IGNORECASE),
    re.compile(r"kiwoom_access_token\.json\s*:\s*\{", re.IGNORECASE),
]


def load_context(path: Path) -> dict:
    if not path.exists():
        raise AssertionError(f"context JSON not found: {path}")
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError as exc:
        raise AssertionError(f"context JSON is invalid: {path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise AssertionError(f"context JSON root must be object: {path}")
    return payload


def parse_generated_at(value: object) -> datetime:
    if not value:
        raise AssertionError("generated_at is missing")
    text = str(value)
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError as exc:
        raise AssertionError(f"generated_at is invalid: {text}") from exc
    if parsed.tzinfo is None:
        raise AssertionError("generated_at must include timezone")
    return parsed


def validate_context(payload: dict, *, max_age_hours: float | None = None) -> list[str]:
    messages: list[str] = []
    if payload.get("module") != "openclaw_investment_research_context":
        raise AssertionError("module mismatch")
    generated_at = parse_generated_at(payload.get("generated_at"))
    age_hours = (datetime.now(timezone.utc) - generated_at.astimezone(timezone.utc)).total_seconds() / 3600
    if max_age_hours is not None and age_hours > max_age_hours:
        raise AssertionError(f"context is stale: {age_hours:.2f}h > {max_age_hours:.2f}h")
    state = payload.get("current_state")
    if not isinstance(state, dict):
        raise AssertionError("current_state missing")
    rec = state.get("daily_recommendations")
    if not isinstance(rec, dict):
        raise AssertionError("daily_recommendations missing")
    latest_rows = rec.get("latest_rows")
    if not isinstance(latest_rows, list) or len(latest_rows) < 6:
        raise AssertionError("daily recommendation latest rows must include KR/US top 3")
    market_counts = rec.get("latest_market_counts") or {}
    if int(market_counts.get("KR") or 0) < 3 or int(market_counts.get("US") or 0) < 3:
        raise AssertionError(f"KR/US recommendation counts are incomplete: {market_counts}")
    sanitization = payload.get("sanitization") or {}
    if sanitization.get("raw_tokens_excluded") is not True:
        raise AssertionError("raw token exclusion flag must be true")
    telegram = ((state.get("news_and_telegram") or {}).get("telegram_favorite_posts") or {})
    if int(telegram.get("saved_count") or 0) <= 0:
        raise AssertionError("telegram favorite posts are not reflected")
    nps = state.get("nps_rebalancing") or {}
    if nps.get("public_sources_only") is not True:
        raise AssertionError("NPS context must be marked as public-sources-only")
    firecrawl = state.get("firecrawl_monitoring") or {}
    defaults = firecrawl.get("safety_defaults") or {}
    if defaults.get("enabled_default") is not False or defaults.get("dry_run_default") is not True:
        raise AssertionError("Firecrawl safety defaults must remain enabled=false and dry_run=true")
    messages.append(
        f"generated_at={payload.get('generated_at')} latest={rec.get('latest_recommendation_date')} "
        f"rows={len(latest_rows)} telegram_saved={telegram.get('saved_count')}"
    )
    return messages


def validate_no_secret_like_content(path: Path) -> None:
    text = path.read_text(encoding="utf-8-sig")
    for pattern in SECRET_PATTERNS:
        if pattern.search(text):
            raise AssertionError(f"secret-like content found in {path}: {pattern.pattern}")


def validate_bundle(directory: Path, *, max_age_hours: float | None = None) -> list[str]:
    json_path = directory / "investment_research_context.json"
    md_path = directory / "investment_research_context.md"
    manifest_path = directory / "openclaw_bridge_manifest.json"
    if not md_path.exists():
        raise AssertionError(f"context Markdown not found: {md_path}")
    if not manifest_path.exists():
        raise AssertionError(f"OpenClaw bridge manifest not found: {manifest_path}")
    validate_no_secret_like_content(json_path)
    validate_no_secret_like_content(md_path)
    validate_no_secret_like_content(manifest_path)
    payload = load_context(json_path)
    messages = validate_context(payload, max_age_hours=max_age_hours)
    manifest = load_context(manifest_path)
    if manifest.get("schema") != "investment_research_openclaw_bridge_v1":
        raise AssertionError("OpenClaw bridge manifest schema mismatch")
    if manifest.get("context_generated_at") != payload.get("generated_at"):
        raise AssertionError("OpenClaw bridge manifest generated_at does not match context")
    if manifest.get("context_file") != "investment_research_context.json":
        raise AssertionError("OpenClaw bridge manifest context_file mismatch")
    if manifest.get("markdown_file") != "investment_research_context.md":
        raise AssertionError("OpenClaw bridge manifest markdown_file mismatch")
    command_fields = [
        "safe_refresh_command",
        "strict_refresh_command",
        "validation_command",
        "completion_audit_command",
    ]
    missing_commands = [field for field in command_fields if not manifest.get(field)]
    if missing_commands:
        raise AssertionError(f"OpenClaw bridge manifest must include commands: {', '.join(missing_commands)}")
    if manifest.get("completion_report_file") != "openclaw_bridge_completion_report.md":
        raise AssertionError("OpenClaw bridge manifest completion_report_file mismatch")
    markdown = md_path.read_text(encoding="utf-8-sig")
    for required in ["오늘 추천 최신일", "민감정보", "오픈클로 사용 규칙", "KR 1위", "US 1위"]:
        if required not in markdown:
            raise AssertionError(f"Markdown context is missing required text: {required}")
    status_path = directory / "bridge_status.json"
    if status_path.exists():
        status = load_context(status_path)
        if status.get("status") != "ok":
            raise AssertionError(f"bridge status is not ok: {status.get('status')}")
        if status.get("context_generated_at") != payload.get("generated_at"):
            raise AssertionError("bridge status generated_at does not match context")
        if status.get("secrets_excluded") is not True:
            raise AssertionError("bridge status must confirm secrets_excluded=true")
        if not status.get("source_git_commit") or not status.get("source_git_branch"):
            raise AssertionError("bridge status must include source git commit and branch")
        if status.get("source_git_dirty") not in (True, False):
            raise AssertionError("bridge status must include source_git_dirty boolean")
        readme_path = directory / "README.md"
        if not readme_path.exists():
            raise AssertionError(f"OpenClaw bridge README not found: {readme_path}")
        validate_no_secret_like_content(readme_path)
        readme = readme_path.read_text(encoding="utf-8-sig")
        for required in [
            "investment_research_context.md",
            "investment_research_context.json",
            "openclaw_bridge_manifest.json",
            "openclaw_bridge_completion_report.md",
            "bridge_status.json",
            "secrets",
            "account-auth material are excluded",
        ]:
            if required not in readme:
                raise AssertionError(f"OpenClaw bridge README is missing required text: {required}")
    return messages


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate sanitized OpenClaw Investment Research context bundles.")
    parser.add_argument("--source-dir", type=Path, default=DEFAULT_SOURCE_DIR)
    parser.add_argument("--openclaw-dir", type=Path, default=DEFAULT_OPENCLAW_DIR)
    parser.add_argument("--skip-openclaw", action="store_true")
    parser.add_argument("--max-age-hours", type=float, default=24.0)
    parser.add_argument("--json", action="store_true", help="검증 결과를 JSON으로 출력합니다.")
    args = parser.parse_args()

    checks = [(args.source_dir.resolve(), "source")]
    if not args.skip_openclaw:
        checks.append((args.openclaw_dir.resolve(), "openclaw"))
    result = {
        "status": "ok",
        "source_dir": str(args.source_dir.resolve()),
        "openclaw_dir": None if args.skip_openclaw else str(args.openclaw_dir.resolve()),
        "checks": [],
    }
    try:
        for directory, label in checks:
            messages = validate_bundle(directory, max_age_hours=args.max_age_hours)
            result["checks"].append({"label": label, "directory": str(directory), "messages": messages})
    except AssertionError as exc:
        result["status"] = "failure"
        result["error"] = str(exc)

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        if result["status"] == "ok":
            for check in result["checks"]:
                print(f"[{check['label']}] ok: {check['directory']}")
                for message in check["messages"]:
                    print(f"  - {message}")
        else:
            print(f"[failure] {result['error']}")
    return 0 if result["status"] == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())
