from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SYSTEM_DIR = PROJECT_ROOT / "research_vault" / "_system"
DEFAULT_OUTPUT_DIR = SYSTEM_DIR / "openclaw_integration"
KST = ZoneInfo("Asia/Seoul")


def load_json(path: Path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return default
    except json.JSONDecodeError:
        return default


def safe_text(value: object, limit: int = 220) -> str:
    text = " ".join(str(value or "").replace("\r\n", "\n").replace("\r", "\n").split())
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "…"


def top_items(items: list, limit: int) -> list:
    return [item for item in items if item is not None][:limit]


def build_recommendation_state(store: dict) -> dict:
    records = [item for item in store.get("records", []) if isinstance(item, dict)]
    latest_date = store.get("latest_recommendation_date") or max(
        (str(item.get("recommendation_date") or "") for item in records),
        default="",
    )
    latest_rows = [
        item
        for item in records
        if str(item.get("recommendation_date") or "") == str(latest_date)
    ]
    latest_rows.sort(key=lambda item: (str(item.get("market") or ""), int(item.get("rank") or 999)))
    market_counts = Counter(str(item.get("market") or "UNKNOWN") for item in latest_rows)
    sanitized_rows = []
    for item in latest_rows:
        direction_labels = item.get("investment_direction_labels") or []
        direction_profile = item.get("investment_direction_profile")
        if not direction_labels and isinstance(direction_profile, dict):
            direction_labels = [
                theme.get("label")
                for theme in direction_profile.get("themes", [])
                if isinstance(theme, dict) and theme.get("label")
            ]
        sanitized_rows.append(
            {
                "market": item.get("market"),
                "market_label": item.get("market_label"),
                "rank": item.get("rank"),
                "ticker": item.get("ticker"),
                "company_name": item.get("company_name"),
                "score": item.get("score"),
                "currency": item.get("currency"),
                "baseline_price": item.get("baseline_price"),
                "investment_direction_labels": direction_labels,
                "reasons": [safe_text(value, 180) for value in top_items(item.get("reasons") or [], 5)],
                "risk_notes": [safe_text(value, 180) for value in top_items(item.get("risk_notes") or [], 4)],
                "signal_breakdown": [
                    {
                        "key": signal.get("key"),
                        "label": signal.get("label"),
                        "summary": safe_text(signal.get("summary"), 160),
                        "score_applied": signal.get("score_applied"),
                    }
                    for signal in top_items(item.get("signal_breakdown") or [], 8)
                ],
                "evidence_quality": {
                    "grade": item.get("evidence_quality_grade"),
                    "score": item.get("evidence_quality_score"),
                    "evidence_count": item.get("evidence_count") or len(item.get("evidence_sources") or []),
                },
                "next_tracking": item.get("next_tracking"),
            }
        )
    return {
        "latest_recommendation_date": latest_date,
        "updated_at": store.get("updated_at"),
        "tracking_updated_at": store.get("tracking_updated_at"),
        "record_count": len(records),
        "latest_count": len(latest_rows),
        "latest_market_counts": dict(market_counts),
        "latest_rows": sanitized_rows,
    }


def build_interest_state(store: dict) -> dict:
    tickers = [item for item in store.get("tickers", []) if isinstance(item, dict)]
    sectors = [item for item in store.get("sectors", []) if isinstance(item, dict)]
    ticker_counts = Counter(str(item.get("region") or item.get("market") or "UNKNOWN") for item in tickers)
    sector_counts = Counter(str(item.get("region") or item.get("market") or "UNKNOWN") for item in sectors)
    prune = store.get("kiwoom_buy_group_prune") if isinstance(store.get("kiwoom_buy_group_prune"), dict) else {}
    return {
        "updated_at": store.get("updated_at"),
        "ticker_count": len(tickers),
        "sector_count": len(sectors),
        "ticker_counts_by_region": dict(ticker_counts),
        "sector_counts_by_region": dict(sector_counts),
        "kiwoom_buy_group_prune": {
            "enabled": prune.get("enabled"),
            "source_group_name": prune.get("source_group_name"),
            "kept_count": prune.get("kept_count"),
            "removed_count": prune.get("removed_count"),
            "updated_at": prune.get("updated_at"),
        },
        "sample_tickers": [
            {
                "ticker": item.get("ticker"),
                "name": (item.get("verification") or {}).get("company_name") or item.get("name"),
                "region": item.get("region") or item.get("market"),
                "tags": item.get("tags") or [],
            }
            for item in tickers[:20]
        ],
        "sample_sectors": [
            {
                "name": item.get("name") or item.get("sector"),
                "region": item.get("region") or item.get("market"),
                "tags": item.get("tags") or [],
            }
            for item in sectors[:20]
        ],
    }


def build_portfolio_state(store: dict) -> dict:
    portfolios = store.get("portfolios") if isinstance(store.get("portfolios"), dict) else {}
    summaries = []
    total_holdings = 0
    for _, portfolio in portfolios.items():
        if not isinstance(portfolio, dict):
            continue
        holdings = [item for item in portfolio.get("holdings", []) if isinstance(item, dict)]
        total_holdings += len(holdings)
        currency_counts = Counter(str(item.get("currency") or "UNKNOWN") for item in holdings)
        summaries.append(
            {
                "portfolio_name": portfolio.get("portfolio_name"),
                "holding_count": len(holdings),
                "currency_counts": dict(currency_counts),
                "sample_holdings": [
                    {
                        "ticker": item.get("ticker"),
                        "name": item.get("name"),
                        "currency": item.get("currency"),
                        "sector": item.get("sector"),
                        "theme_tags": item.get("theme_tags") or [],
                        "sync_status": item.get("sync_status"),
                    }
                    for item in holdings[:12]
                ],
            }
        )
    return {
        "portfolio_count": len(summaries),
        "total_holding_count": total_holdings,
        "portfolios": summaries,
    }


def build_news_state(news_inbox: dict, telegram_state: dict) -> dict:
    items = [item for item in news_inbox.get("items", []) if isinstance(item, dict)]
    scope_counts = Counter(str(item.get("scope") or "UNKNOWN") for item in items)
    telegram_items = [
        item
        for item in items
        if item.get("scope_reason") == "telegram_favorite_popular_post"
        or "telegram_favorite" in {str(tag) for tag in item.get("tags", [])}
    ]
    return {
        "news_inbox_updated_at": news_inbox.get("updated_at"),
        "news_item_count": len(items),
        "scope_counts": dict(scope_counts),
        "telegram_favorite_posts": {
            "status": telegram_state.get("status"),
            "last_run_at": telegram_state.get("last_run_at"),
            "candidate_count": telegram_state.get("candidate_count"),
            "saved_count": telegram_state.get("saved_count"),
            "duplicate_count": telegram_state.get("duplicate_count"),
            "message": telegram_state.get("last_attempt_message"),
            "top_posts": [
                {
                    "channel_label": item.get("channel_label"),
                    "title": safe_text(item.get("title"), 140),
                    "url": item.get("url"),
                    "view_count": item.get("view_count"),
                    "published_at": item.get("published_at"),
                }
                for item in top_items(telegram_state.get("top_posts") or [], 10)
            ],
            "news_inbox_count": len(telegram_items),
        },
    }


def build_nps_state(store: dict) -> dict:
    context = store.get("public_rebalancing_context") if isinstance(store.get("public_rebalancing_context"), dict) else {}
    return {
        "status": store.get("status"),
        "as_of": store.get("as_of"),
        "generated_at": store.get("generated_at"),
        "refresh_status": store.get("refresh_status"),
        "public_sources_only": context.get("status") == "public_sources_only",
        "primary_article_url": context.get("primary_article_url"),
        "latest_event_date": store.get("latest_event_date"),
        "domestic_stock_row_count": store.get("domestic_stock_row_count"),
        "large_holding_row_count": store.get("large_holding_row_count"),
        "notes": [
            "국민연금 세부 리밸런싱 주문 시점과 규모는 비공개이므로 공개 공시/보도 기반으로만 반영합니다.",
            "국내주식 비중 14% 유지 요구는 자동 점검/경고 컨텍스트로 연결합니다.",
        ],
    }


def build_firecrawl_state(store: dict) -> dict:
    return {
        "webhook_ready": store.get("webhook_ready"),
        "updated_at": store.get("updated_at"),
        "last_webhook_status": store.get("last_webhook_status"),
        "last_webhook_error": store.get("last_webhook_error"),
        "accepted_count": store.get("accepted_count"),
        "rejected_count": store.get("rejected_count"),
        "safety_defaults": {
            "enabled_default": False,
            "dry_run_default": True,
            "require_secret_and_rpc_preflight": True,
        },
    }


def build_context(project_root: Path) -> dict:
    system_dir = project_root / "research_vault" / "_system"
    daily_recommendations = load_json(system_dir / "daily_recommendations.json", {})
    interest_list = load_json(system_dir / "interest_list.json", {})
    user_portfolios = load_json(system_dir / "user_portfolios.json", {})
    news_inbox = load_json(system_dir / "news_inbox.json", {})
    telegram_state = load_json(system_dir / "telegram_favorite_posts_state.json", {})
    nps_snapshot = load_json(system_dir / "nps_portfolio_change_snapshot.json", {})
    firecrawl_status = load_json(system_dir / "firecrawl_monitor_webhook_status.json", {})
    generated_at = datetime.now(tz=KST).isoformat(timespec="seconds")
    return {
        "module": "openclaw_investment_research_context",
        "generated_at": generated_at,
        "source_project": {
            "name": "InvestmentJournalApp / investment-research-os",
            "root": str(project_root),
            "backend_health_url": "http://127.0.0.1:8001/api/v1/health",
            "research_console_url": "http://127.0.0.1:8001/console/index.html",
        },
        "sanitization": {
            "raw_tokens_excluded": True,
            "excluded_store_examples": [
                "kis_access_token.json",
                "kiwoom_access_token.json",
                "research_memory.sqlite3",
                "raw uploaded files",
                "broker/API secrets",
            ],
            "export_scope": "summary_only",
        },
        "workstreams": [
            "한국/미국 오늘의 추천 1~3위 생성 및 상세 근거 화면",
            "보유 종목/관심 종목/섹터 한국·미국 분리 관리와 상세 보기",
            "키움 관심그룹 매수 종목 90개 기준 관심종목 정리",
            "시장 데이터·공시·법령·뉴스·투자 심리 통합 인사이트 허브",
            "텔레그램 즐겨찾기 채널 인기글 매일 22시 수집 및 뉴스/심리 반영",
            "국민연금 국내주식 비중 14% 유지 요구에 맞춘 공개자료 기반 모니터",
            "Firecrawl 모니터링 안전 기본값과 웹훅/프리플라이트 상태 관리",
            "미국 시장 일지와 리서치/공시/IR 자료 자동 수집 품질 점검",
        ],
        "current_state": {
            "daily_recommendations": build_recommendation_state(daily_recommendations),
            "interests": build_interest_state(interest_list),
            "portfolios": build_portfolio_state(user_portfolios),
            "news_and_telegram": build_news_state(news_inbox, telegram_state),
            "nps_rebalancing": build_nps_state(nps_snapshot),
            "firecrawl_monitoring": build_firecrawl_state(firecrawl_status),
        },
        "openclaw_usage": {
            "read_this_first": "investment_research_context.md",
            "machine_readable": "investment_research_context.json",
            "suggested_heartbeat_note": "투자리서치 상태 확인은 이 번들의 generated_at과 backend_health_url을 기준으로 판단합니다.",
            "safe_actions": [
                "최신 추천/관심종목/텔레그램 인기글 요약 조회",
                "투자리서치 백엔드 health 확인",
                "투자 판단 전 근거 문서와 최신성 점검 요청",
            ],
            "restricted_actions": [
                "실거래 주문",
                "브로커 API 키/토큰 공유",
                "키움/KIS 계좌 원문 잔고 외부 전송",
            ],
        },
    }


def render_markdown(context: dict) -> str:
    state = context["current_state"]
    rec = state["daily_recommendations"]
    telegram = state["news_and_telegram"]["telegram_favorite_posts"]
    nps = state["nps_rebalancing"]
    firecrawl = state["firecrawl_monitoring"]
    lines = [
        "# Investment Research OS Context for OpenClaw",
        "",
        f"- 생성: {context['generated_at']}",
        f"- 원본 프로젝트: `{context['source_project']['root']}`",
        f"- 콘솔: {context['source_project']['research_console_url']}",
        f"- 백엔드 헬스: {context['source_project']['backend_health_url']}",
        "- 민감정보: API 키, 토큰, 원문 DB, 브로커 인증 정보 제외",
        "",
        "## 현재 핵심 상태",
        "",
        f"- 오늘 추천 최신일: {rec.get('latest_recommendation_date')} / 최신 {rec.get('latest_count')}개 / 누적 {rec.get('record_count')}개",
        f"- 시장별 추천: {rec.get('latest_market_counts')}",
        f"- 관심종목: {state['interests'].get('ticker_count')}개 / 관심섹터: {state['interests'].get('sector_count')}개",
        f"- 포트폴리오: {state['portfolios'].get('portfolio_count')}개 / 보유 종목 {state['portfolios'].get('total_holding_count')}개",
        f"- 뉴스 인박스: {state['news_and_telegram'].get('news_item_count')}개 / 텔레그램 인기글 {telegram.get('news_inbox_count')}개",
        f"- 국민연금 공개자료 스냅샷: {nps.get('status')} / 기준 {nps.get('as_of')}",
        f"- Firecrawl 웹훅: ready={firecrawl.get('webhook_ready')} / last={firecrawl.get('last_webhook_status')}",
        "",
        "## 최신 추천",
        "",
    ]
    for item in rec.get("latest_rows", []):
        directions = ", ".join(item.get("investment_direction_labels") or []) or "방향 미지정"
        lines.append(
            f"- {item.get('market')} {item.get('rank')}위 `{item.get('ticker')}` {item.get('company_name')}: "
            f"점수 {item.get('score')}, 기준가 {item.get('baseline_price')} {item.get('currency')}, {directions}"
        )
    lines.extend(
        [
            "",
            "## 오픈클로 사용 규칙",
            "",
            "- 이 파일은 투자 판단 보조용 요약입니다. 실거래 주문 또는 계좌 인증 정보 공유에 사용하지 않습니다.",
            "- 추천 상세 판단은 원본 투자리서치 콘솔과 근거 문서 확인 후 진행합니다.",
            "- 국민연금 리밸런싱은 공개 공시/보도 기반 모니터링이며 실시간 주문 데이터가 아닙니다.",
            "- Firecrawl은 기본적으로 `enabled=false`, `dry_run=true` 안전 설정을 유지합니다.",
            "",
            "## 완료된 주요 연동 범위",
            "",
        ]
    )
    for item in context.get("workstreams", []):
        lines.append(f"- {item}")
    lines.append("")
    return "\n".join(lines)


def build_bridge_manifest(context: dict) -> dict:
    return {
        "schema": "investment_research_openclaw_bridge_v1",
        "generated_at": datetime.now(tz=KST).isoformat(timespec="seconds"),
        "context_generated_at": context.get("generated_at"),
        "source_project": context.get("source_project"),
        "context_file": "investment_research_context.json",
        "markdown_file": "investment_research_context.md",
        "status_file": "bridge_status.json",
        "readme_file": "README.md",
        "completion_report_file": "openclaw_bridge_completion_report.md",
        "safe_refresh_command": "powershell.exe -ExecutionPolicy Bypass -File .\\tools\\sync_openclaw_investment_context.ps1",
        "strict_refresh_command": "powershell.exe -ExecutionPolicy Bypass -File .\\tools\\sync_openclaw_investment_context.ps1 -RequireCompletionAudit",
        "validation_command": "python tools\\check_openclaw_investment_context.py --max-age-hours 24",
        "completion_audit_command": "python tools\\check_openclaw_bridge_completion.py --max-age-hours 24",
        "sanitization": context.get("sanitization"),
        "restricted_actions": (context.get("openclaw_usage") or {}).get("restricted_actions", []),
    }


def write_context(context: dict, output_dir: Path) -> dict:
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "investment_research_context.json"
    md_path = output_dir / "investment_research_context.md"
    manifest_path = output_dir / "openclaw_bridge_manifest.json"
    json_path.write_text(json.dumps(context, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    md_path.write_text(render_markdown(context), encoding="utf-8")
    manifest_path.write_text(json.dumps(build_bridge_manifest(context), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {"json_path": str(json_path), "markdown_path": str(md_path), "manifest_path": str(manifest_path)}


def main() -> int:
    parser = argparse.ArgumentParser(description="Export sanitized Investment Research OS context for OpenClaw.")
    parser.add_argument("--project-root", type=Path, default=PROJECT_ROOT)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--print-summary", action="store_true")
    args = parser.parse_args()
    project_root = args.project_root.resolve()
    output_dir = args.output_dir.resolve()
    context = build_context(project_root)
    result = write_context(context, output_dir)
    if args.print_summary:
        print(json.dumps({"status": "ok", **result}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
