from __future__ import annotations

import argparse
import hashlib
import json
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
            "read_this_first": "investment_research_context.md",
            "machine_readable": "investment_research_context.json",
            "knowledge_graph_blueprint": "openclaw_knowledge_graph_blueprint.md",
            "knowledge_graph_blueprint_json": "openclaw_knowledge_graph_blueprint.json",
            "completion_report": "openclaw_bridge_completion_report.md",
            "completion_report_json": "openclaw_bridge_completion_report.json",
            "status_summary_command": "python tools\\show_openclaw_bridge_status.py --json",
            "final_completion_audit_command": "python tools\\check_openclaw_bridge_completion.py --max-age-hours 24 --require-report-hashes",
            "knowledge_graph_validation_command": "python tools\\check_openclaw_knowledge_graph.py --max-age-hours 24",
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


def build_bridge_manifest(context: dict) -> dict:
    graph_files = KNOWLEDGE_GRAPH_FILES
    return {
        "schema": "investment_research_openclaw_bridge_v1",
        "generated_at": datetime.now(tz=KST).isoformat(timespec="seconds"),
        "context_generated_at": context.get("generated_at"),
        "source_project": context.get("source_project"),
        "context_file": "investment_research_context.json",
        "markdown_file": "investment_research_context.md",
        "knowledge_graph_blueprint_file": "openclaw_knowledge_graph_blueprint.md",
        "knowledge_graph_blueprint_json_file": "openclaw_knowledge_graph_blueprint.json",
        "knowledge_graph_files": graph_files,
        "status_file": "bridge_status.json",
        "readme_file": "README.md",
        "read_order": [
            "bridge_status.json",
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
        ],
        "completion_report_file": "openclaw_bridge_completion_report.md",
        "completion_report_json_file": "openclaw_bridge_completion_report.json",
        "safe_refresh_command": "powershell.exe -ExecutionPolicy Bypass -File .\\tools\\sync_openclaw_investment_context.ps1",
        "strict_refresh_command": "powershell.exe -ExecutionPolicy Bypass -File .\\tools\\sync_openclaw_investment_context.ps1 -RequireCompletionAudit",
        "validation_command": "python tools\\check_openclaw_investment_context.py --max-age-hours 24",
        "completion_audit_command": "python tools\\check_openclaw_bridge_completion.py --max-age-hours 24",
        "knowledge_graph_validation_command": "python tools\\check_openclaw_knowledge_graph.py --max-age-hours 24",
        "final_completion_audit_command": "python tools\\check_openclaw_bridge_completion.py --max-age-hours 24 --require-report-hashes",
        "status_summary_command": "python tools\\show_openclaw_bridge_status.py --json",
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
