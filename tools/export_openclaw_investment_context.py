from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from collections import Counter
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SYSTEM_DIR = PROJECT_ROOT / "research_vault" / "_system"
DEFAULT_OUTPUT_DIR = SYSTEM_DIR / "openclaw_integration"
KST = ZoneInfo("Asia/Seoul")
KNOWLEDGE_GRAPH_FILES = {
    "nodes": "openclaw_knowledge_graph_nodes.json",
    "edges": "openclaw_knowledge_graph_edges.json",
    "master_index": "openclaw_knowledge_graph_master_index.md",
    "glossary": "openclaw_knowledge_graph_glossary.md",
    "marginalia": "openclaw_knowledge_graph_marginalia_queue.md",
}
FIRST_READ_JSON_FILE = "openclaw_first_read.json"
FIRST_READ_MARKDOWN_FILE = "openclaw_first_read.md"


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


def graph_id_segment(value: object, *, fallback: str = "item") -> str:
    text = safe_text(value, 80).lower()
    normalized = []
    for char in text:
        if char.isascii() and char.isalnum():
            normalized.append(char)
        elif char in ("-", "_", "."):
            normalized.append("-")
        elif char.isspace():
            normalized.append("-")
    slug = "-".join("".join(normalized).split("-"))
    if slug:
        return slug[:48]
    digest = hashlib.sha1(str(value or fallback).encode("utf-8")).hexdigest()[:10]
    return f"{fallback}-{digest}"


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
        "telegram_priority_brief": {
            "design": "telegram_brief_sender_v1",
            "delivery_design": "telegram_brief_delivery_v1",
            "mode": "important_only",
            "include_sections": [
                "today_recommendations_kr_us_top_3",
                "portfolio_health",
                "top_movers",
                "watch_items",
            ],
            "suppress_low_priority": [
                "routine_status_ok",
                "dry_run_transport_details",
                "raw_hash_or_storage_paths",
                "empty_reference_sections",
            ],
            "safe_defaults": {
                "TELEGRAM_BRIEF_DELIVERY_ENABLED": "false",
                "TELEGRAM_BRIEF_DELIVERY_DRY_RUN": "true",
                "TELEGRAM_BRIEF_CLEANUP_ENABLED": "false",
            },
            "live_send_requires": ["--enabled", "--submit", "bot token", "chat id"],
            "live_cleanup_requires": ["--enabled", "--submit", "--cleanup-enabled", "message_id ledger"],
            "daily_operations": {
                "script": "tools\\run_daily_research_operations.ps1",
                "default_step": "check_telegram_brief_delivery.py --write-state",
                "skip_switch": "-SkipTelegramBriefDelivery",
                "live_send_switch": "-SubmitTelegramBriefDelivery",
                "live_cleanup_switch": "-EnableTelegramBriefCleanup",
            },
            "message_goal": "Send one concise Investment Priority Brief instead of routine operational noise.",
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


def build_personal_knowledge_graph_blueprint() -> dict:
    return {
        "schema": "openclaw_personal_knowledge_graph_blueprint_v1",
        "source": {
            "source_file_label": "투자.txt",
            "applied_as": "OpenClaw bridge knowledge graph blueprint",
            "raw_content_excluded": True,
            "reason": "원문에는 초안/예시/깨진 스캐폴드가 섞여 있어 안전한 스키마로 정규화해 반영합니다.",
        },
        "recommended_layering": {
            "strategy": "기존 OpenClaw knowledge ingestion 위에 Knowledge Graph Layer를 추가합니다.",
            "avoid": "검증기 없이 별도 대형 그래프 DB를 먼저 만들지 않습니다.",
            "storage_model": "Markdown index + JSON/YAML nodes + JSON/YAML edges + validator + graph export",
        },
        "principles": [
            {"name": "Master Index", "role": "전체 지식 지도를 담당하고 주제별 진입점을 제공합니다."},
            {"name": "Glossary", "role": "안정적으로 검증된 개념 정의를 보관합니다."},
            {"name": "Marginalia", "role": "미검증 메모, 질문, 실험 가설을 분리해 지식 오염을 막습니다."},
            {"name": "Edges", "role": "개념, 주제, 출처, 결정 사이의 관계를 명시합니다."},
            {"name": "Validator", "role": "노드/엣지 필수 필드와 깨진 참조를 점검합니다."},
        ],
        "node_types": [
            "concept",
            "topic",
            "source",
            "project",
            "decision",
            "note",
            "artifact",
        ],
        "edge_types": [
            "is_a",
            "part_of",
            "related_to",
            "depends_on",
            "uses",
            "contrasts_with",
            "causes",
            "mitigates",
            "based_on",
            "explores",
        ],
        "seed_nodes": [
            {
                "id": "concept.relu",
                "type": "concept",
                "term": "ReLU",
                "canonical_name": "Rectified Linear Unit",
                "definition": "입력값이 0보다 작으면 0을 출력하고, 0보다 크면 입력값을 그대로 출력하는 활성화 함수입니다.",
                "formula": "f(x) = max(0, x)",
                "domain": ["deep_learning", "neural_networks"],
                "related": [
                    "concept.activation_function",
                    "concept.vanishing_gradient",
                    "concept.leaky_relu",
                    "concept.gelu",
                ],
                "status": "verified",
                "confidence": "high",
            },
            {
                "id": "topic.graph_rendering_8000_nodes",
                "type": "topic",
                "title": "8000-node network visualization rendering optimization",
                "domain": ["visualization", "graph_rendering", "performance_engineering"],
                "problem": "수천 개 노드와 엣지를 가진 네트워크를 브라우저에서 탐색 가능한 속도로 렌더링합니다.",
                "master_index_path": ["Engineering", "Visualization", "Large Graph Rendering"],
                "glossary_links": [
                    "concept.force_directed_layout",
                    "concept.webgl_rendering",
                    "concept.level_of_detail",
                    "concept.spatial_index",
                    "concept.edge_bundling",
                ],
                "marginalia_links": ["note.graph_rendering_lod_experiment"],
                "recommended_strategies": [
                    "Canvas/WebGL rendering",
                    "Web Worker layout",
                    "precomputed or incremental layout",
                    "edge bundling and filtering",
                    "viewport culling",
                    "memoization and dirty-region rendering",
                    "picking layer for interactions",
                    "progressive loading and clustering",
                ],
                "status": "active_research",
            },
            {
                "id": "note.graph_rendering_lod_experiment",
                "type": "note",
                "title": "8000-node graph LOD rendering experiment",
                "parent": "topic.graph_rendering_8000_nodes",
                "content": "대규모 그래프는 전체 세부 정보를 즉시 렌더링하기보다 줌 레벨과 선택 상태에 따라 점진적으로 보여주는 편이 안정적입니다.",
                "hypothesis": "LOD, 클러스터링, viewport culling을 결합하면 8000개 노드에서도 상호작용 지연을 줄일 수 있습니다.",
                "status": "unverified",
                "next_action": "1000, 4000, 8000, 16000개 노드 synthetic benchmark를 만들어 렌더링 시간을 비교합니다.",
            },
        ],
        "seed_edges": [
            {"from": "concept.relu", "to": "concept.activation_function", "type": "is_a"},
            {"from": "concept.relu", "to": "concept.dead_relu", "type": "related_to"},
            {"from": "topic.graph_rendering_8000_nodes", "to": "concept.webgl_rendering", "type": "uses"},
            {"from": "note.graph_rendering_lod_experiment", "to": "topic.graph_rendering_8000_nodes", "type": "explores"},
        ],
        "validation_rules": [
            "Every node must have id and type.",
            "Concept nodes require term or title and definition.",
            "Topic nodes require title and status.",
            "Marginalia/note nodes require parent.",
            "Every edge must include from, to, and type.",
            "Edge type must be one of the declared edge_types.",
            "Status should be one of verified, active_research, unverified, or deprecated.",
        ],
        "milestones": [
            {"id": "M24", "title": "Personal Knowledge Graph Schema"},
            {"id": "M25", "title": "Master Index Builder"},
            {"id": "M26", "title": "Glossary Extractor"},
            {"id": "M27", "title": "Marginalia Queue"},
            {"id": "M28", "title": "Graph JSON Exporter"},
            {"id": "M29", "title": "8000-node Visualization Benchmark"},
        ],
        "next_actions": [
            "Keep this blueprint in the OpenClaw bridge context first.",
            "Add a validator before creating OpenClaw-side knowledge_graph files.",
            "After validation passes, scaffold Master Index, Glossary, Marginalia, and graph export files.",
        ],
    }


def _today_kst() -> str:
    return datetime.now(tz=KST).date().isoformat()


def _git_log_since_today(project_root: Path) -> list[dict]:
    today = _today_kst()
    command = [
        "git",
        "-C",
        str(project_root),
        "log",
        f"--since={today} 00:00:00 +0900",
        "--pretty=format:%h%x09%ad%x09%s",
        "--date=iso-local",
    ]
    try:
        completed = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", timeout=10)
    except Exception:
        return []
    if completed.returncode != 0:
        return []
    commits = []
    for line in completed.stdout.splitlines():
        parts = line.split("\t", 2)
        if len(parts) != 3:
            continue
        commits.append({"commit": parts[0], "committed_at": parts[1], "subject": parts[2]})
    return commits


def build_today_work_report(project_root: Path) -> dict:
    commits = _git_log_since_today(project_root)
    subjects = [str(item.get("subject") or "") for item in commits]
    category_rules = [
        ("openclaw_bridge", ("OpenClaw", "openclaw"), "OpenClaw 투자리서치 bridge, first-read, status summary, completion audit, hash 검증"),
        ("telegram_pipeline", ("Telegram", "telegram"), "텔레그램 즐겨찾기 인기글, 중요 브리프, 보유 리포트 알림/사후점검"),
        ("recommendation_insights", ("recommendation", "recommendations", "sentiment", "insight"), "오늘 추천, 텔레그램 심리, 통합 투자 인사이트 반영"),
        ("firecrawl_monitor", ("Firecrawl", "firecrawl"), "Firecrawl IR/Monitor 안전 기본값, dry-run, 운영 preflight"),
        ("local_ai_agent_foundation", ("local AI", "agent operating", "survival", "foundation"), "고급 AI 제한 대비 로컬 AI 생존 모드와 에이전트 운영 기반 readiness"),
        ("interest_console_ui", ("interest", "summaries", "locale"), "관심종목/관심섹터 콘솔 UI 정렬과 클릭 상세 표시"),
        ("console_backend_ops", ("console", "backend", "restart", "status"), "연구 콘솔/API 상태 노출, 백엔드 재시작 guard, 운영 상태 검증"),
        ("portfolio_reports", ("portfolio", "report alert", "holding"), "포트폴리오/보유 종목 리포트 알림과 상태 점검"),
        ("calendar_readiness", ("calendar", "earnings"), "투자 캘린더와 실적 일정 readiness"),
    ]
    categories = []
    for key, needles, label in category_rules:
        count = sum(1 for subject in subjects if any(needle.lower() in subject.lower() for needle in needles))
        if count:
            categories.append({"key": key, "label": label, "commit_count": count})
    return {
        "date": _today_kst(),
        "source": "git_log_since_local_midnight",
        "commit_count": len(commits),
        "has_implementation_today": len(commits) > 0,
        "correction_for_openclaw": "오늘 구현 작업 없음이라고 답하면 안 됩니다. 이 today_work_report와 bridge_status source_git를 먼저 확인하세요.",
        "summary": [item["label"] for item in categories[:8]],
        "categories": categories,
        "latest_commits": commits[:16],
    }


def build_next_schedule() -> list[dict]:
    return [
        {"time": "07:00", "task": "OpenClaw 보유 종목 신규 리포트 알림", "status": "scheduled/live submit, first run pending", "command": "tools\\check_portfolio_report_alert_task_status.py --json"},
        {"time": "07:10", "task": "보유 종목 리포트 알림 사후점검", "status": "scheduled", "command": "tools\\check_portfolio_report_alert_task_status.py --task-name 'InvestmentJournalApp OpenClaw Portfolio Report Alert Postrun' --json"},
        {"time": "07:20", "task": "미국 시장 일지 자동 반영", "status": "enabled", "command": "tools\\run_telegram_us_market_close_journal.ps1"},
        {"time": "08:00", "task": "한국/미국 오늘 추천 1~3위 생성/저장", "status": "enabled", "command": "tools\\check_daily_recommendations_store.py --require-milestones --require-quality"},
        {"time": "22:00", "task": "텔레그램 즐겨찾기 채널 인기글 수집 및 뉴스/심리 반영", "status": "enabled", "command": "tools\\check_telegram_favorite_posts.py --sample --enabled"},
        {"time": "on demand", "task": "OpenClaw 최신 컨텍스트 동기화 및 완료 감사", "status": "manual/safe", "command": "powershell.exe -ExecutionPolicy Bypass -File .\\tools\\sync_openclaw_investment_context.ps1 -RequireCompletionAudit"},
    ]

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
            "backend_health_url": "http://127.0.0.1:8001/api/v1/system/health",
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
        "today_work_report": build_today_work_report(project_root),
        "next_schedule": build_next_schedule(),
        "answer_correction": {
            "wrong_claim": "오늘(2026-07-05) 특별히 새로 구현된 작업 기록은 없습니다.",
            "correct_basis": "bridge_status.json source_git와 openclaw_first_read.json today_work_report를 우선 확인해야 합니다.",
            "expected_answer": "오늘 구현 작업과 다음 스케줄을 today_work_report/next_schedule 기준으로 보고합니다.",
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
        "openclaw_knowledge_graph_blueprint": build_personal_knowledge_graph_blueprint(),
        "openclaw_usage": {
            "status_file": "bridge_status.json",
            "read_this_first": FIRST_READ_MARKDOWN_FILE,
            "read_this_first_json": FIRST_READ_JSON_FILE,
            "machine_readable": "investment_research_context.json",
            "knowledge_graph_blueprint": "openclaw_knowledge_graph_blueprint.md",
            "knowledge_graph_blueprint_json": "openclaw_knowledge_graph_blueprint.json",
            "completion_report": "openclaw_bridge_completion_report.md",
            "completion_report_json": "openclaw_bridge_completion_report.json",
            "status_summary_command": "python tools\\show_openclaw_bridge_status.py --json",
            "quick_health_command": "python tools\\check_openclaw_quick_health.py --json",
            "today_answer_readiness_command": "python tools\\check_openclaw_today_answer_readiness.py --json",
            "today_answer_quality_command": "python tools\\check_openclaw_today_answer_quality.py --json",
            "priority_answer_quality_command": "python tools\\check_openclaw_priority_answer_quality.py --json",
            "question_read_order_command": "python tools\\check_openclaw_question_read_order.py --json",
            "answer_samples_command": "python tools\\check_openclaw_answer_samples.py --json",
            "actual_answer_audit_command": "python tools\\check_openclaw_actual_answer_audit.py --json",
            "answer_capture_cycle_command": "python tools\\check_openclaw_answer_capture_cycle.py --json",
            "answer_capture_cycle_run_command": "powershell.exe -ExecutionPolicy Bypass -File .\\tools\\run_openclaw_answer_capture_cycle.ps1 -Collect -WriteState",
            "answer_capture_cycle_register_command": "powershell.exe -ExecutionPolicy Bypass -File .\\tools\\register_openclaw_answer_capture_cycle_task.ps1 -Collect",
            "answer_capture_task_status_command": "python tools\\check_openclaw_answer_capture_task_status.py --json",
            "answer_capture_canary_command": "python tools\\check_openclaw_answer_capture_canary.py --json",
            "actual_answer_capture_command": "python tools\\capture_openclaw_actual_answer.py --route-id today_work_report --answer-file <path> --audit --json",
            "pending_answer_collect_command": "python tools\\collect_openclaw_pending_answers.py --json",
            "actual_answer_capture_status_command": "python tools\\check_openclaw_actual_answer_capture_status.py --json",
            "safe_refresh_command": "powershell.exe -ExecutionPolicy Bypass -File .\\tools\\sync_openclaw_investment_context.ps1",
            "strict_refresh_command": "powershell.exe -ExecutionPolicy Bypass -File .\\tools\\sync_openclaw_investment_context.ps1 -RequireCompletionAudit",
            "final_completion_audit_command": "python tools\\check_openclaw_bridge_completion.py --max-age-hours 24 --require-report-hashes",
            "knowledge_graph_validation_command": "python tools\\check_openclaw_knowledge_graph.py --max-age-hours 24",
            "wsl_refresh_command": "powershell.exe -ExecutionPolicy Bypass -File .\\tools\\sync_openclaw_wsl_investment_context.ps1",
            "wsl_answer_context_command": "python tools\\check_openclaw_wsl_answer_context.py --json",
            "wsl_fresh_bootstrap_command": "python tools\\check_openclaw_wsl_answer_context.py --require-fresh-bootstrap --json",
            "backend_watchdog_status_command": "python tools\\check_research_backend_watchdog_task_status.py --json",
            "backend_watchdog_ensure_command": "powershell.exe -ExecutionPolicy Bypass -File .\\scripts\\ensure-research-backend.ps1",
            "backend_watchdog_register_command": "powershell.exe -ExecutionPolicy Bypass -File .\\tools\\register_research_backend_watchdog_task.ps1",
            "market_journal_linkage_command": "python tools\\check_market_journal_linkage.py --strict --json",
            "market_journal_linkage_backlog_command": "python tools\\check_market_journal_linkage.py --strict --write-backlog --json",
            "operational_schedule_status_command": "python tools\\check_operational_schedule_status.py --json --allow-warnings",
            "offline_readiness_command": "python tools\\check_offline_readiness.py --json",
            "suggested_heartbeat_note": "투자리서치 상태 확인은 bridge_status.json의 source git, generated_at, completion_report_sha256을 기준으로 판단합니다.",
            "safe_actions": [
                "최신 추천/관심종목/텔레그램 인기글 요약 조회",
                "텔레그램 발송은 오늘 추천과 주의 신호 중심의 Investment Priority Brief 1건으로 축약",
                "일일 운영 루틴에서 텔레그램 delivery ledger dry-run 상태 확인",
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
    telegram_priority = state["news_and_telegram"].get("telegram_priority_brief") or {}
    nps = state["nps_rebalancing"]
    firecrawl = state["firecrawl_monitoring"]
    kg = context.get("openclaw_knowledge_graph_blueprint") or {}
    today_report = context.get("today_work_report") or {}
    next_schedule = context.get("next_schedule") or []
    lines = [
        "# Investment Research OS Context for OpenClaw",
        "",
        f"- 생성: {context['generated_at']}",
        f"- 원본 프로젝트: `{context['source_project']['root']}`",
        f"- 콘솔: {context['source_project']['research_console_url']}",
        f"- 백엔드 헬스: {context['source_project']['backend_health_url']}",
        "- 민감정보: API 키, 토큰, 원문 DB, 브로커 인증 정보 제외",
        "",
        "## 오픈클로 답변 정정",
        "",
        f"- 오늘 구현 작업 없음: `false` (git 오늘 커밋 {today_report.get('commit_count', 0)}개)",
        f"- 정정 기준: {today_report.get('correction_for_openclaw', 'bridge_status와 today_work_report 확인')}",
        "",
        "## 오늘 구현 보고",
        "",
        *(f"- {item}" for item in today_report.get("summary") or ["오늘 구현 요약을 생성하지 못했습니다. git log와 bridge_status를 확인하세요."]),
        "",
        "### 오늘 최신 커밋",
        "",
        *(f"- `{item.get('commit')}` {item.get('committed_at')} - {item.get('subject')}" for item in (today_report.get("latest_commits") or [])[:8]),
        "",
        "## 다음 스케줄",
        "",
        *(f"- {item.get('time')}: {item.get('task')} ({item.get('status')})" for item in next_schedule),
        "",
        "## 현재 핵심 상태",
        "",
        f"- 오늘 추천 최신일: {rec.get('latest_recommendation_date')} / 최신 {rec.get('latest_count')}개 / 누적 {rec.get('record_count')}개",
        f"- 시장별 추천: {rec.get('latest_market_counts')}",
        f"- 관심종목: {state['interests'].get('ticker_count')}개 / 관심섹터: {state['interests'].get('sector_count')}개",
        f"- 포트폴리오: {state['portfolios'].get('portfolio_count')}개 / 보유 종목 {state['portfolios'].get('total_holding_count')}개",
        f"- 뉴스 인박스: {state['news_and_telegram'].get('news_item_count')}개 / 텔레그램 인기글 {telegram.get('news_inbox_count')}개",
        f"- 텔레그램 발송 기준: {telegram_priority.get('mode')} / {telegram_priority.get('message_goal')}",
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
            "## OpenClaw 개인 지식 그래프 Blueprint",
            "",
            f"- 적용 방식: {(kg.get('recommended_layering') or {}).get('strategy')}",
            f"- 저장 모델: {(kg.get('recommended_layering') or {}).get('storage_model')}",
            "- 별도 파일: `openclaw_knowledge_graph_blueprint.md`, `openclaw_knowledge_graph_blueprint.json`",
        ]
    )
    for principle in kg.get("principles", []):
        lines.append(f"- {principle.get('name')}: {principle.get('role')}")
    seed_ids = [item.get("id") for item in kg.get("seed_nodes", []) if item.get("id")]
    if seed_ids:
        lines.append(f"- 초기 seed node: {', '.join(seed_ids)}")
    milestones = [f"{item.get('id')} {item.get('title')}" for item in kg.get("milestones", [])]
    if milestones:
        lines.append(f"- 다음 milestone: {' -> '.join(milestones)}")
    lines.extend(
        [
            "",
            "## 오픈클로 사용 규칙",
            "",
            "- 이 파일은 투자 판단 보조용 요약입니다. 실거래 주문 또는 계좌 인증 정보 공유에 사용하지 않습니다.",
            "- 먼저 `bridge_status.json`에서 source git, 최신성, completion_report_sha256을 확인합니다.",
            "- 완료 상태는 `openclaw_bridge_completion_report.md`, `openclaw_bridge_completion_report.json`, `python tools\\check_openclaw_bridge_completion.py --max-age-hours 24 --require-report-hashes`로 확인합니다.",
            "- 빠른 상태 요약은 `python tools\\show_openclaw_bridge_status.py --json`으로 확인합니다.",
            "- OpenClaw 전용 빠른 헬스체크는 `python tools\\check_openclaw_quick_health.py --json`으로 확인합니다.",
            "- 오늘 작업/다음 스케줄 답변 준비도는 `python tools\\check_openclaw_today_answer_readiness.py --json`으로 확인합니다.",
            "- 오늘 작업/다음 스케줄 답변 품질 smoke는 `python tools\\check_openclaw_today_answer_quality.py --json`으로 확인합니다.",
            "- 추천/중요 메시지 답변 품질 smoke는 `python tools\\check_openclaw_priority_answer_quality.py --json`으로 확인합니다.",
            "- 질문별 read-order smoke는 `python tools\\check_openclaw_question_read_order.py --json`으로 확인합니다.",
            "- 질문별 답변 샘플 smoke는 `python tools\\check_openclaw_answer_samples.py --json`으로 확인합니다.",
            "- OpenClaw 실제 답변 캡처는 `python tools\\capture_openclaw_actual_answer.py --route-id today_work_report --answer-file <path> --audit --json`으로 저장 후 감사합니다.",
            "- OpenClaw 답변 캡처 cycle은 `python tools\\check_openclaw_answer_capture_cycle.py --json`으로 dry-run 점검하고, `powershell.exe -ExecutionPolicy Bypass -File .\\tools\\run_openclaw_answer_capture_cycle.ps1 -Collect -WriteState`로 실제 처리합니다.",
            "- OpenClaw pending 답변 파일은 `pending_actual_answers`에 저장한 뒤 `python tools\\collect_openclaw_pending_answers.py --json`으로 캡처/감사/처리완료 이동합니다.",
            "- OpenClaw 실제 답변 캡처 상태는 `python tools\\check_openclaw_actual_answer_capture_status.py --json`으로 확인합니다.",
            "- OpenClaw 실제 답변 사후감사는 `python tools\\check_openclaw_actual_answer_audit.py --json`으로 확인합니다.",
            "- WSL PA 실제 답변 컨텍스트는 `python tools\\check_openclaw_wsl_answer_context.py --json`으로 확인합니다.",
            "- OpenClaw 답변 직전 fresh bootstrap은 `python tools\\check_openclaw_wsl_answer_context.py --require-fresh-bootstrap --json`으로 확인합니다.",
            "- 시장일지 관심/보유 연결 현황은 `python tools\\check_market_journal_linkage.py --strict --json`으로 확인합니다.",
            "- 시장일지 미연결 우선 보강 큐는 `python tools\\check_market_journal_linkage.py --strict --write-backlog --json`으로 생성합니다.",
            "- 07:20/08:00/22:00 백엔드 운영 스케줄 상태는 `python tools\\check_operational_schedule_status.py --json --allow-warnings`로 확인합니다.",
            "- 전체 운영 준비도는 `python tools\\check_offline_readiness.py --json`으로 확인합니다.",
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


def render_knowledge_graph_blueprint_markdown(blueprint: dict) -> str:
    lines = [
        "# OpenClaw Personal Knowledge Graph Blueprint",
        "",
        f"- schema: `{blueprint.get('schema')}`",
        "- source: `투자.txt` 내용 검토 후 정규화 적용",
        "- raw source content: excluded",
        f"- strategy: {(blueprint.get('recommended_layering') or {}).get('strategy')}",
        f"- storage model: {(blueprint.get('recommended_layering') or {}).get('storage_model')}",
        "",
        "## Principles",
        "",
    ]
    for item in blueprint.get("principles", []):
        lines.append(f"- {item.get('name')}: {item.get('role')}")
    lines.extend(["", "## Node Types", ""])
    for item in blueprint.get("node_types", []):
        lines.append(f"- `{item}`")
    lines.extend(["", "## Edge Types", ""])
    for item in blueprint.get("edge_types", []):
        lines.append(f"- `{item}`")
    lines.extend(["", "## Seed Nodes", ""])
    for item in blueprint.get("seed_nodes", []):
        title = item.get("term") or item.get("title") or item.get("id")
        lines.append(f"- `{item.get('id')}` ({item.get('type')}): {title} / status={item.get('status')}")
    lines.extend(["", "## Seed Edges", ""])
    for item in blueprint.get("seed_edges", []):
        lines.append(f"- `{item.get('from')}` -[{item.get('type')}]-> `{item.get('to')}`")
    lines.extend(["", "## Validation Rules", ""])
    for item in blueprint.get("validation_rules", []):
        lines.append(f"- {item}")
    lines.extend(["", "## Milestones", ""])
    for item in blueprint.get("milestones", []):
        lines.append(f"- `{item.get('id')}`: {item.get('title')}")
    lines.extend(["", "## Next Actions", ""])
    for item in blueprint.get("next_actions", []):
        lines.append(f"- {item}")
    lines.append("")
    return "\n".join(lines)


def build_personal_knowledge_graph_artifacts(blueprint: dict, context: dict | None = None) -> dict:
    nodes: list[dict] = []
    edges: list[dict] = []
    node_ids: set[str] = set()
    edge_keys: set[tuple[str, str, str]] = set()

    def add_node(node: dict) -> None:
        node_id = str(node.get("id") or "")
        if not node_id or node_id in node_ids:
            return
        node.setdefault("source", "openclaw_knowledge_graph_blueprint")
        node.setdefault("raw_source_excluded", True)
        node.setdefault("graph_layer", "personal_knowledge_graph")
        nodes.append(node)
        node_ids.add(node_id)

    def add_edge(from_id: str, to_id: str, edge_type: str, **extra: object) -> None:
        if not from_id or not to_id or not edge_type:
            return
        key = (from_id, to_id, edge_type)
        if key in edge_keys:
            return
        edge = {"from": from_id, "to": to_id, "type": edge_type}
        edge.update(extra)
        edge.setdefault("source", "openclaw_knowledge_graph_builder")
        edge.setdefault("raw_source_excluded", True)
        edges.append(edge)
        edge_keys.add(key)

    for item in blueprint.get("seed_nodes", []):
        if not isinstance(item, dict):
            continue
        node = dict(item)
        add_node(node)
    for item in blueprint.get("seed_edges", []):
        if not isinstance(item, dict):
            continue
        add_edge(str(item.get("from") or ""), str(item.get("to") or ""), str(item.get("type") or ""), source="openclaw_knowledge_graph_blueprint")

    context = context or {}
    state = context.get("current_state") if isinstance(context.get("current_state"), dict) else {}
    recommendations = ((state.get("daily_recommendations") or {}).get("latest_rows") or [])
    recommendation_date = (state.get("daily_recommendations") or {}).get("latest_recommendation_date")
    project_node_id = "project.investment_research_os.daily_recommendations"
    add_node(
        {
            "id": project_node_id,
            "type": "project",
            "title": "Investment Research OS daily recommendations",
            "status": "active_research",
            "generated_at": context.get("generated_at"),
            "recommendation_date": recommendation_date,
            "description": "한국/미국 오늘의 추천 1~3위와 관련 근거를 OpenClaw 지식 그래프로 연결합니다.",
            "source": "investment_research_context",
        }
    )

    for item in recommendations:
        if not isinstance(item, dict):
            continue
        market = graph_id_segment(item.get("market"), fallback="market")
        rank = graph_id_segment(item.get("rank"), fallback="rank")
        ticker = graph_id_segment(item.get("ticker"), fallback="ticker")
        rec_node_id = f"topic.today_recommendation.{market}.{rank}.{ticker}"
        add_node(
            {
                "id": rec_node_id,
                "type": "topic",
                "title": f"{item.get('market')}#{item.get('rank')} {item.get('ticker')} {item.get('company_name')}",
                "status": "active_research",
                "market": item.get("market"),
                "rank": item.get("rank"),
                "ticker": item.get("ticker"),
                "company_name": item.get("company_name"),
                "score": item.get("score"),
                "baseline_price": item.get("baseline_price"),
                "currency": item.get("currency"),
                "recommendation_date": recommendation_date,
                "master_index_path": ["Investment Research", "Daily Recommendations", str(item.get("market") or "UNKNOWN")],
                "source": "daily_recommendations.latest_rows",
            }
        )
        add_edge(rec_node_id, project_node_id, "part_of", reason="today recommendation belongs to daily recommendation run")

        for label in item.get("investment_direction_labels") or []:
            concept_id = f"concept.investment_direction.{graph_id_segment(label, fallback='direction')}"
            add_node(
                {
                    "id": concept_id,
                    "type": "concept",
                    "term": label,
                    "definition": f"투자리서치 시스템에서 추천 종목을 해석할 때 사용하는 투자 방향 라벨: {label}",
                    "domain": ["investment_direction", "portfolio_theme"],
                    "status": "active_research",
                    "confidence": "medium",
                    "source": "daily_recommendations.investment_direction_labels",
                }
            )
            add_edge(rec_node_id, concept_id, "related_to", reason="recommendation carries investment direction label")

        for index, reason in enumerate(item.get("reasons") or [], start=1):
            source_id = f"source.recommendation_reason.{market}.{rank}.{ticker}.{index}"
            add_node(
                {
                    "id": source_id,
                    "type": "source",
                    "title": f"{item.get('ticker')} recommendation reason {index}",
                    "summary": safe_text(reason, 220),
                    "source_family": "recommendation_reason",
                    "status": "verified",
                    "source": "daily_recommendations.reasons",
                }
            )
            add_edge(rec_node_id, source_id, "based_on", reason="recommendation reason")

        for signal in item.get("signal_breakdown") or []:
            if not isinstance(signal, dict):
                continue
            signal_key = graph_id_segment(signal.get("key") or signal.get("label"), fallback="signal")
            source_id = f"source.recommendation_signal.{market}.{rank}.{ticker}.{signal_key}"
            add_node(
                {
                    "id": source_id,
                    "type": "source",
                    "title": signal.get("label") or signal.get("key") or "recommendation signal",
                    "summary": signal.get("summary"),
                    "source_family": "recommendation_signal",
                    "score_applied": signal.get("score_applied"),
                    "status": "verified" if signal.get("score_applied") else "active_research",
                    "source": "daily_recommendations.signal_breakdown",
                }
            )
            add_edge(rec_node_id, source_id, "based_on", reason="recommendation signal breakdown")

    telegram = ((state.get("news_and_telegram") or {}).get("telegram_favorite_posts") or {})
    top_posts = telegram.get("top_posts") if isinstance(telegram.get("top_posts"), list) else []
    for index, post in enumerate(top_posts[:10], start=1):
        if not isinstance(post, dict):
            continue
        post_id = f"source.telegram_favorite_popular_post.{index}"
        add_node(
            {
                "id": post_id,
                "type": "source",
                "title": post.get("title") or f"Telegram favorite popular post {index}",
                "summary": post.get("title"),
                "url": post.get("url"),
                "channel_label": post.get("channel_label"),
                "view_count": post.get("view_count"),
                "published_at": post.get("published_at"),
                "source_family": "telegram_favorite_popular_post",
                "status": "active_research",
                "source": "news_and_telegram.telegram_favorite_posts.top_posts",
            }
        )
        add_edge(project_node_id, post_id, "based_on", reason="telegram market sentiment input")

    nps = state.get("nps_rebalancing") or {}
    if nps:
        nps_id = "source.nps.public_rebalancing_context"
        add_node(
            {
                "id": nps_id,
                "type": "source",
                "title": "NPS domestic equity 14 percent public-source monitor",
                "summary": "; ".join(nps.get("notes") or []),
                "status": nps.get("status") or "active_research",
                "as_of": nps.get("as_of"),
                "public_sources_only": nps.get("public_sources_only"),
                "url": nps.get("primary_article_url"),
                "source_family": "nps_public_rebalancing",
                "source": "nps_rebalancing",
            }
        )
        add_edge(project_node_id, nps_id, "based_on", reason="portfolio allocation policy context")

    firecrawl = state.get("firecrawl_monitoring") or {}
    if firecrawl:
        firecrawl_id = "source.firecrawl.monitoring_status"
        add_node(
            {
                "id": firecrawl_id,
                "type": "source",
                "title": "Firecrawl monitoring safety and webhook status",
                "summary": f"ready={firecrawl.get('webhook_ready')} last={firecrawl.get('last_webhook_status')}",
                "status": "verified",
                "webhook_ready": firecrawl.get("webhook_ready"),
                "safety_defaults": firecrawl.get("safety_defaults"),
                "source_family": "firecrawl_monitoring",
                "source": "firecrawl_monitoring",
            }
        )
        add_edge(project_node_id, firecrawl_id, "depends_on", reason="web monitoring safety status gates live collection")

    return {
        "schema": "openclaw_personal_knowledge_graph_artifacts_v1",
        "source_schema": blueprint.get("schema"),
        "generated_from": "openclaw_knowledge_graph_blueprint.json",
        "storage_model": (blueprint.get("recommended_layering") or {}).get("storage_model"),
        "node_count": len(nodes),
        "edge_count": len(edges),
        "node_types": blueprint.get("node_types") or [],
        "edge_types": blueprint.get("edge_types") or [],
        "nodes": nodes,
        "edges": edges,
        "files": KNOWLEDGE_GRAPH_FILES,
    }


def render_knowledge_graph_master_index(artifacts: dict) -> str:
    topic_nodes = [node for node in artifacts.get("nodes", []) if node.get("type") == "topic"]
    concept_nodes = [node for node in artifacts.get("nodes", []) if node.get("type") == "concept"]
    note_nodes = [node for node in artifacts.get("nodes", []) if node.get("type") == "note"]
    lines = [
        "# OpenClaw Knowledge Graph Master Index",
        "",
        f"- schema: `{artifacts.get('schema')}`",
        f"- nodes: {artifacts.get('node_count')}",
        f"- edges: {artifacts.get('edge_count')}",
        "- source: `openclaw_knowledge_graph_blueprint.json`",
        "",
        "## Topics",
        "",
    ]
    if topic_nodes:
        for node in topic_nodes:
            path = " > ".join(node.get("master_index_path") or [])
            lines.append(f"- `{node.get('id')}`: {node.get('title')} / path: {path or 'unassigned'} / status={node.get('status')}")
    else:
        lines.append("- none")
    lines.extend(["", "## Concepts", ""])
    if concept_nodes:
        for node in concept_nodes:
            lines.append(f"- `{node.get('id')}`: {node.get('term') or node.get('title')} / status={node.get('status')}")
    else:
        lines.append("- none")
    lines.extend(["", "## Marginalia Queue", ""])
    if note_nodes:
        for node in note_nodes:
            lines.append(f"- `{node.get('id')}` -> `{node.get('parent')}` / status={node.get('status')}")
    else:
        lines.append("- none")
    lines.extend(["", "## Graph Files", ""])
    for key, filename in (artifacts.get("files") or {}).items():
        lines.append(f"- {key}: `{filename}`")
    lines.append("")
    return "\n".join(lines)


def render_knowledge_graph_glossary(artifacts: dict) -> str:
    lines = ["# OpenClaw Knowledge Graph Glossary", ""]
    concept_nodes = [node for node in artifacts.get("nodes", []) if node.get("type") == "concept"]
    if not concept_nodes:
        lines.append("- none")
    for node in concept_nodes:
        lines.extend(
            [
                f"## {node.get('term') or node.get('title') or node.get('id')}",
                "",
                f"- id: `{node.get('id')}`",
                f"- canonical: {node.get('canonical_name') or ''}",
                f"- definition: {node.get('definition') or ''}",
                f"- formula: `{node.get('formula') or ''}`",
                f"- status: {node.get('status')}",
                f"- related: {', '.join(node.get('related') or [])}",
                "",
            ]
        )
    return "\n".join(lines)


def render_knowledge_graph_marginalia_queue(artifacts: dict) -> str:
    lines = ["# OpenClaw Knowledge Graph Marginalia Queue", ""]
    note_nodes = [node for node in artifacts.get("nodes", []) if node.get("type") == "note"]
    if not note_nodes:
        lines.append("- none")
    for node in note_nodes:
        lines.extend(
            [
                f"## {node.get('title') or node.get('id')}",
                "",
                f"- id: `{node.get('id')}`",
                f"- parent: `{node.get('parent')}`",
                f"- status: {node.get('status')}",
                f"- hypothesis: {node.get('hypothesis') or ''}",
                f"- next_action: {node.get('next_action') or ''}",
                "",
                str(node.get("content") or ""),
                "",
            ]
        )
    return "\n".join(lines)


def build_openclaw_read_order(graph_files: dict | None = None) -> list[str]:
    graph_files = graph_files or KNOWLEDGE_GRAPH_FILES
    return [
        "bridge_status.json",
        FIRST_READ_MARKDOWN_FILE,
        FIRST_READ_JSON_FILE,
        "openclaw_bridge_manifest.json",
        "investment_research_context.md",
        "investment_research_context.json",
        "openclaw_knowledge_graph_blueprint.md",
        "openclaw_knowledge_graph_blueprint.json",
        graph_files["nodes"],
        graph_files["edges"],
        graph_files["master_index"],
        graph_files["glossary"],
        graph_files["marginalia"],
        "openclaw_bridge_completion_report.md",
        "openclaw_bridge_completion_report.json",
    ]


def build_openclaw_question_routes() -> list[dict]:
    return [
        {
            "id": "today_work_report",
            "question": "오늘 시스템에서 구현한 작업 보고하고 다음 스케줄을 말해줘",
            "read_order": ["bridge_status.json", FIRST_READ_MARKDOWN_FILE, FIRST_READ_JSON_FILE],
            "required_payload_keys": ["today_work_report", "next_schedule", "answer_correction"],
            "quality_command": "python tools\\check_openclaw_today_answer_quality.py --json",
        },
        {
            "id": "recommendations_priority",
            "question": "오늘 추천 종목과 중요 메시지 알려줘",
            "read_order": [
                "bridge_status.json",
                FIRST_READ_MARKDOWN_FILE,
                FIRST_READ_JSON_FILE,
                "investment_research_context.md",
                "investment_research_context.json",
            ],
            "required_payload_keys": ["latest_recommendations", "latest_market_counts", "telegram"],
            "quality_command": "python tools\\check_openclaw_priority_answer_quality.py --json",
        },
        {
            "id": "bridge_status_completion",
            "question": "현재 연동 상태와 완료 감사 결과 알려줘",
            "read_order": [
                "bridge_status.json",
                "openclaw_bridge_completion_report.md",
                "openclaw_bridge_completion_report.json",
            ],
            "required_payload_keys": ["primary_files", "operational_commands"],
            "quality_command": "python tools\\check_openclaw_bridge_completion.py --max-age-hours 24 --require-report-hashes",
        },
        {
            "id": "knowledge_graph_context",
            "question": "투자 방향과 지식 그래프 컨텍스트 알려줘",
            "read_order": [
                "bridge_status.json",
                "openclaw_knowledge_graph_blueprint.md",
                "openclaw_knowledge_graph_blueprint.json",
                "openclaw_knowledge_graph_nodes.json",
                "openclaw_knowledge_graph_edges.json",
                "openclaw_knowledge_graph_master_index.md",
            ],
            "required_payload_keys": ["primary_files", "operational_commands"],
            "quality_command": "python tools\\check_openclaw_knowledge_graph.py --max-age-hours 24",
        },
    ]


def build_first_read_packet(context: dict) -> dict:
    state = context.get("current_state") or {}
    rec = state.get("daily_recommendations") or {}
    news = state.get("news_and_telegram") or {}
    openclaw_usage = context.get("openclaw_usage") or {}
    recommendations = []
    for row in rec.get("latest_rows") or []:
        if not isinstance(row, dict):
            continue
        recommendations.append(
            {
                "market": row.get("market"),
                "rank": row.get("rank"),
                "ticker": row.get("ticker"),
                "company_name": row.get("company_name"),
                "score": row.get("score"),
                "baseline_price": row.get("baseline_price"),
                "currency": row.get("currency"),
                "investment_direction": row.get("investment_direction"),
                "evidence_quality": row.get("evidence_quality_grade"),
                "next_tracking_date": row.get("next_tracking_date"),
            }
        )
    return {
        "schema": "openclaw_investment_research_first_read_v1",
        "generated_at": context.get("generated_at"),
        "status": "ready",
        "read_this_first": True,
        "purpose": "Give OpenClaw a compact, sanitized first-read packet before it loads the larger research context.",
        "source_project": context.get("source_project"),
        "today_work_report": context.get("today_work_report") or {},
        "next_schedule": context.get("next_schedule") or [],
        "answer_correction": context.get("answer_correction") or {},
        "latest_recommendation_date": rec.get("latest_recommendation_date"),
        "latest_market_counts": rec.get("latest_market_counts") or {},
        "latest_recommendations": recommendations,
        "telegram": {
            "favorite_saved_count": (news.get("telegram_favorite_posts") or {}).get("saved_count"),
            "priority_brief_design": (news.get("telegram_priority_brief") or {}).get("design"),
            "priority_delivery_design": (news.get("telegram_priority_brief") or {}).get("delivery_design"),
            "delivery_safe_defaults": (news.get("telegram_priority_brief") or {}).get("safe_defaults"),
        },
        "safety": {
            "secrets_excluded": True,
            "decision_support_only": True,
            "restricted_actions": openclaw_usage.get("restricted_actions") or [],
            "safe_actions": openclaw_usage.get("safe_actions") or [],
        },
        "read_order": build_openclaw_read_order(),
        "question_routes": build_openclaw_question_routes(),
        "primary_files": {
            "human_context": "investment_research_context.md",
            "machine_context": "investment_research_context.json",
            "manifest": "openclaw_bridge_manifest.json",
            "status": "bridge_status.json",
            "completion_report": "openclaw_bridge_completion_report.md",
            "completion_report_json": "openclaw_bridge_completion_report.json",
        },
        "operational_commands": {
            "status_summary": openclaw_usage.get("status_summary_command"),
            "quick_health": openclaw_usage.get("quick_health_command"),
            "today_answer_readiness": openclaw_usage.get("today_answer_readiness_command"),
            "today_answer_quality": openclaw_usage.get("today_answer_quality_command"),
            "priority_answer_quality": openclaw_usage.get("priority_answer_quality_command"),
            "question_read_order": openclaw_usage.get("question_read_order_command"),
            "answer_samples": openclaw_usage.get("answer_samples_command"),
            "actual_answer_audit": openclaw_usage.get("actual_answer_audit_command"),
            "answer_capture_cycle": openclaw_usage.get("answer_capture_cycle_command"),
            "answer_capture_cycle_run": openclaw_usage.get("answer_capture_cycle_run_command"),
            "answer_capture_cycle_register": openclaw_usage.get("answer_capture_cycle_register_command"),
            "answer_capture_task_status": openclaw_usage.get("answer_capture_task_status_command"),
            "answer_capture_canary": openclaw_usage.get("answer_capture_canary_command"),
            "actual_answer_capture": openclaw_usage.get("actual_answer_capture_command"),
            "pending_answer_collect": openclaw_usage.get("pending_answer_collect_command"),
            "actual_answer_capture_status": openclaw_usage.get("actual_answer_capture_status_command"),
            "safe_refresh": openclaw_usage.get("safe_refresh_command"),
            "strict_refresh": openclaw_usage.get("strict_refresh_command"),
            "final_completion_audit": openclaw_usage.get("final_completion_audit_command"),
            "wsl_refresh": openclaw_usage.get("wsl_refresh_command"),
            "wsl_answer_context": openclaw_usage.get("wsl_answer_context_command"),
            "wsl_fresh_bootstrap": openclaw_usage.get("wsl_fresh_bootstrap_command"),
            "backend_watchdog_status": openclaw_usage.get("backend_watchdog_status_command"),
            "backend_watchdog_ensure": openclaw_usage.get("backend_watchdog_ensure_command"),
            "backend_watchdog_register": openclaw_usage.get("backend_watchdog_register_command"),
            "market_journal_linkage": openclaw_usage.get("market_journal_linkage_command"),
            "market_journal_linkage_backlog": openclaw_usage.get("market_journal_linkage_backlog_command"),
            "operational_schedule_status": openclaw_usage.get("operational_schedule_status_command"),
            "offline_readiness": openclaw_usage.get("offline_readiness_command"),
        },
        "optimization_notes": [
            "Start with this packet for current state, then read bridge_status.json for hashes and freshness.",
            "Use market counts to confirm KR/US recommendation coverage before using ranked rows.",
            "Use completion report hashes before trusting copied OpenClaw files.",
        ],
    }


def render_first_read_markdown(packet: dict) -> str:
    today_report = packet.get("today_work_report") or {}
    answer_correction = packet.get("answer_correction") or {}
    lines = [
        "# OpenClaw Investment Research First Read",
        "",
        f"- status: `{packet.get('status')}`",
        f"- generated_at: `{packet.get('generated_at')}`",
        f"- latest recommendation date: `{packet.get('latest_recommendation_date')}`",
        f"- latest market counts: `{json.dumps(packet.get('latest_market_counts') or {}, ensure_ascii=False, separators=(',', ':'))}`",
        f"- telegram favorite saved: `{(packet.get('telegram') or {}).get('favorite_saved_count')}`",
        f"- today implementation commits: `{today_report.get('commit_count', 0)}`",
        "",
        "## Answer Correction",
        "",
        f"- wrong claim to avoid: `{answer_correction.get('wrong_claim', '오늘 작업 없음')}`",
        f"- correct basis: {answer_correction.get('correct_basis', 'bridge_status와 today_work_report 확인')}",
        "",
        "## Today Implementation Report",
        "",
    ]
    for item in today_report.get("summary") or []:
        lines.append(f"- {item}")
    if not today_report.get("summary"):
        lines.append("- No summary generated; inspect bridge_status.json and git source state.")
    lines.extend(["", "### Latest Today Commits", ""])
    for item in (today_report.get("latest_commits") or [])[:8]:
        lines.append(f"- `{item.get('commit')}` {item.get('committed_at')} - {item.get('subject')}")
    lines.extend(["", "## Next Schedule", ""])
    for item in packet.get("next_schedule") or []:
        lines.append(f"- {item.get('time')}: {item.get('task')} ({item.get('status')})")
    lines.extend(["", "## Latest Recommendations", ""])
    for row in packet.get("latest_recommendations") or []:
        lines.append(
            f"- {row.get('market')}#{row.get('rank')} `{row.get('ticker')}` {row.get('company_name')} "
            f"| score {row.get('score')} | baseline {row.get('baseline_price')} {row.get('currency')} "
            f"| quality {row.get('evidence_quality') or 'n/a'}"
        )
    lines.extend(
        [
            "",
            "## Safety",
            "",
            "- decision support only: `true`",
            "- secrets excluded: `true`",
            "- never place trades or expose broker/API secrets from this bridge",
            "",
            "## Read Order",
            "",
        ]
    )
    for index, filename in enumerate(packet.get("read_order") or [], start=1):
        lines.append(f"{index}. `{filename}`")
    lines.extend(["", "## Commands", ""])
    for key, command in (packet.get("operational_commands") or {}).items():
        lines.append(f"- {key}: `{command}`")
    lines.extend(["", "## Question Routes", ""])
    for route in packet.get("question_routes") or []:
        lines.append(f"- {route.get('id')}: {route.get('question')}")
        lines.append(f"  - read_order: {' -> '.join(route.get('read_order') or [])}")
        lines.append(f"  - quality_command: `{route.get('quality_command')}`")
    lines.extend(["", "## Optimization Notes", ""])
    for note in packet.get("optimization_notes") or []:
        lines.append(f"- {note}")
    lines.append("")
    return "\n".join(lines)

def build_bridge_manifest(context: dict) -> dict:
    graph_files = KNOWLEDGE_GRAPH_FILES
    return {
        "schema": "investment_research_openclaw_bridge_v1",
        "generated_at": datetime.now(tz=KST).isoformat(timespec="seconds"),
        "context_generated_at": context.get("generated_at"),
        "source_project": context.get("source_project"),
        "today_work_report": context.get("today_work_report") or {},
        "next_schedule": context.get("next_schedule") or [],
        "answer_correction": context.get("answer_correction") or {},
        "first_read_file": FIRST_READ_MARKDOWN_FILE,
        "first_read_json_file": FIRST_READ_JSON_FILE,
        "context_file": "investment_research_context.json",
        "markdown_file": "investment_research_context.md",
        "knowledge_graph_blueprint_file": "openclaw_knowledge_graph_blueprint.md",
        "knowledge_graph_blueprint_json_file": "openclaw_knowledge_graph_blueprint.json",
        "knowledge_graph_files": graph_files,
        "status_file": "bridge_status.json",
        "readme_file": "README.md",
        "read_order": build_openclaw_read_order(graph_files),
        "completion_report_file": "openclaw_bridge_completion_report.md",
        "completion_report_json_file": "openclaw_bridge_completion_report.json",
        "safe_refresh_command": "powershell.exe -ExecutionPolicy Bypass -File .\\tools\\sync_openclaw_investment_context.ps1",
        "strict_refresh_command": "powershell.exe -ExecutionPolicy Bypass -File .\\tools\\sync_openclaw_investment_context.ps1 -RequireCompletionAudit",
        "validation_command": "python tools\\check_openclaw_investment_context.py --max-age-hours 24",
        "completion_audit_command": "python tools\\check_openclaw_bridge_completion.py --max-age-hours 24",
        "knowledge_graph_validation_command": "python tools\\check_openclaw_knowledge_graph.py --max-age-hours 24",
        "final_completion_audit_command": "python tools\\check_openclaw_bridge_completion.py --max-age-hours 24 --require-report-hashes",
        "status_summary_command": "python tools\\show_openclaw_bridge_status.py --json",
        "quick_health_command": "python tools\\check_openclaw_quick_health.py --json",
        "today_answer_readiness_command": "python tools\\check_openclaw_today_answer_readiness.py --json",
        "today_answer_quality_command": "python tools\\check_openclaw_today_answer_quality.py --json",
        "priority_answer_quality_command": "python tools\\check_openclaw_priority_answer_quality.py --json",
        "question_read_order_command": "python tools\\check_openclaw_question_read_order.py --json",
        "answer_samples_command": "python tools\\check_openclaw_answer_samples.py --json",
        "actual_answer_audit_command": "python tools\\check_openclaw_actual_answer_audit.py --json",
        "answer_capture_cycle_command": "python tools\\check_openclaw_answer_capture_cycle.py --json",
        "answer_capture_cycle_run_command": "powershell.exe -ExecutionPolicy Bypass -File .\\tools\\run_openclaw_answer_capture_cycle.ps1 -Collect -WriteState",
        "answer_capture_cycle_register_command": "powershell.exe -ExecutionPolicy Bypass -File .\\tools\\register_openclaw_answer_capture_cycle_task.ps1 -Collect",
        "answer_capture_task_status_command": "python tools\\check_openclaw_answer_capture_task_status.py --json",
        "answer_capture_canary_command": "python tools\\check_openclaw_answer_capture_canary.py --json",
        "actual_answer_capture_command": "python tools\\capture_openclaw_actual_answer.py --route-id today_work_report --answer-file <path> --audit --json",
        "pending_answer_collect_command": "python tools\\collect_openclaw_pending_answers.py --json",
        "actual_answer_capture_status_command": "python tools\\check_openclaw_actual_answer_capture_status.py --json",
        "wsl_refresh_command": "powershell.exe -ExecutionPolicy Bypass -File .\\tools\\sync_openclaw_wsl_investment_context.ps1",
        "wsl_answer_context_command": "python tools\\check_openclaw_wsl_answer_context.py --json",
        "wsl_fresh_bootstrap_command": "python tools\\check_openclaw_wsl_answer_context.py --require-fresh-bootstrap --json",
        "backend_watchdog_status_command": "python tools\\check_research_backend_watchdog_task_status.py --json",
        "backend_watchdog_ensure_command": "powershell.exe -ExecutionPolicy Bypass -File .\\scripts\\ensure-research-backend.ps1",
        "backend_watchdog_register_command": "powershell.exe -ExecutionPolicy Bypass -File .\\tools\\register_research_backend_watchdog_task.ps1",
        "market_journal_linkage_command": "python tools\\check_market_journal_linkage.py --strict --json",
        "market_journal_linkage_backlog_command": "python tools\\check_market_journal_linkage.py --strict --write-backlog --json",
        "operational_schedule_status_command": "python tools\\check_operational_schedule_status.py --json --allow-warnings",
        "offline_readiness_command": "python tools\\check_offline_readiness.py --json",
        "sanitization": context.get("sanitization"),
        "restricted_actions": (context.get("openclaw_usage") or {}).get("restricted_actions", []),
    }


def write_context(context: dict, output_dir: Path) -> dict:
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "investment_research_context.json"
    md_path = output_dir / "investment_research_context.md"
    kg_json_path = output_dir / "openclaw_knowledge_graph_blueprint.json"
    kg_md_path = output_dir / "openclaw_knowledge_graph_blueprint.md"
    kg_nodes_path = output_dir / KNOWLEDGE_GRAPH_FILES["nodes"]
    kg_edges_path = output_dir / KNOWLEDGE_GRAPH_FILES["edges"]
    kg_master_index_path = output_dir / KNOWLEDGE_GRAPH_FILES["master_index"]
    kg_glossary_path = output_dir / KNOWLEDGE_GRAPH_FILES["glossary"]
    kg_marginalia_path = output_dir / KNOWLEDGE_GRAPH_FILES["marginalia"]
    first_read_json_path = output_dir / FIRST_READ_JSON_FILE
    first_read_md_path = output_dir / FIRST_READ_MARKDOWN_FILE
    manifest_path = output_dir / "openclaw_bridge_manifest.json"
    json_path.write_text(json.dumps(context, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    md_path.write_text(render_markdown(context), encoding="utf-8")
    blueprint = context.get("openclaw_knowledge_graph_blueprint") or {}
    graph_artifacts = build_personal_knowledge_graph_artifacts(blueprint, context)
    kg_json_path.write_text(json.dumps(blueprint, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    kg_md_path.write_text(render_knowledge_graph_blueprint_markdown(blueprint), encoding="utf-8")
    kg_nodes_path.write_text(json.dumps(graph_artifacts["nodes"], ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    kg_edges_path.write_text(json.dumps(graph_artifacts["edges"], ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    kg_master_index_path.write_text(render_knowledge_graph_master_index(graph_artifacts), encoding="utf-8")
    kg_glossary_path.write_text(render_knowledge_graph_glossary(graph_artifacts), encoding="utf-8")
    kg_marginalia_path.write_text(render_knowledge_graph_marginalia_queue(graph_artifacts), encoding="utf-8")
    first_read_packet = build_first_read_packet(context)
    first_read_json_path.write_text(json.dumps(first_read_packet, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    first_read_md_path.write_text(render_first_read_markdown(first_read_packet), encoding="utf-8")
    manifest_path.write_text(json.dumps(build_bridge_manifest(context), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {
        "json_path": str(json_path),
        "markdown_path": str(md_path),
        "knowledge_graph_blueprint_json_path": str(kg_json_path),
        "knowledge_graph_blueprint_markdown_path": str(kg_md_path),
        "knowledge_graph_nodes_path": str(kg_nodes_path),
        "knowledge_graph_edges_path": str(kg_edges_path),
        "knowledge_graph_master_index_path": str(kg_master_index_path),
        "knowledge_graph_glossary_path": str(kg_glossary_path),
        "knowledge_graph_marginalia_path": str(kg_marginalia_path),
        "first_read_json_path": str(first_read_json_path),
        "first_read_markdown_path": str(first_read_md_path),
        "manifest_path": str(manifest_path),
    }


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
