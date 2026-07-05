"""Agent operating foundation readiness for high-performance local workflows."""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from research_os.daily_recommendation_store import daily_recommendation_store_path
from research_os.local_ai_survival import build_local_ai_survival_status
from research_os.research_memory import read_manifest, resolve_vault_dir
from research_os.settings import Settings
from research_os.state_store import portfolio_store_path


LOCAL_TIMEZONE = ZoneInfo("Asia/Seoul")


@dataclass(frozen=True)
class AgentFoundationCheck:
    key: str
    label: str
    ready: bool
    score: float
    evidence: str
    next_action: str
    critical: bool = True

    def to_dict(self) -> dict:
        bounded_score = max(0.0, min(100.0, float(self.score)))
        return {
            "key": self.key,
            "label": self.label,
            "ready": self.ready,
            "score": round(bounded_score, 1),
            "evidence": self.evidence,
            "next_action": self.next_action,
            "critical": self.critical,
        }


def _read_json(path: Path, default: object) -> object:
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception:
        return default
    return payload


def _project_root(vault_dir: Path) -> Path:
    if vault_dir.name == "research_vault":
        return vault_dir.parent
    return Path.cwd()


def _exists_count(root: Path, relative_paths: list[str]) -> int:
    return sum(1 for relative in relative_paths if (root / relative).exists())


def _rag_document_count(vault_dir: Path) -> int:
    db_path = vault_dir / "_system" / "research_memory.sqlite3"
    if not db_path.exists():
        return 0
    try:
        with sqlite3.connect(db_path) as connection:
            row = connection.execute("select count(*) from research_memory_documents").fetchone()
    except sqlite3.Error:
        return 0
    return int(row[0] or 0) if row else 0


def _portfolio_counts(settings: Settings) -> tuple[int, int]:
    payload = _read_json(portfolio_store_path(settings), {"portfolios": {}})
    portfolios = payload.get("portfolios") if isinstance(payload, dict) else {}
    if not isinstance(portfolios, dict):
        return 0, 0
    holding_count = 0
    for portfolio in portfolios.values():
        holdings = portfolio.get("holdings") if isinstance(portfolio, dict) else []
        if isinstance(holdings, list):
            holding_count += len(holdings)
    return len(portfolios), holding_count


def _daily_recommendation_count(settings: Settings) -> int:
    payload = _read_json(daily_recommendation_store_path(settings), {"records": []})
    records = payload.get("records") if isinstance(payload, dict) else []
    return len(records) if isinstance(records, list) else 0


def _bridge_age_hours(openclaw_dir: Path) -> float | None:
    candidates: list[object] = []
    for name in (
        "bridge_status.json",
        "investment_research_context.json",
        "openclaw_first_read.json",
        "openclaw_bridge_manifest.json",
    ):
        payload = _read_json(openclaw_dir / name, {})
        if not isinstance(payload, dict):
            continue
        candidates.extend(
            [
                payload.get("context_generated_at"),
                payload.get("generated_at"),
                payload.get("copied_at"),
            ]
        )
    for candidate in candidates:
        generated = str(candidate or "").strip()
        if not generated:
            continue
        try:
            parsed = datetime.fromisoformat(generated.replace("Z", "+00:00"))
        except ValueError:
            continue
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=LOCAL_TIMEZONE)
        return max(
            0.0,
            (datetime.now(LOCAL_TIMEZONE) - parsed.astimezone(LOCAL_TIMEZONE)).total_seconds()
            / 3600,
        )
    return None


def _score_from_count(ready_count: int, total_count: int) -> float:
    if total_count <= 0:
        return 0.0
    return ready_count / total_count * 100.0


def build_agent_operating_foundation_status(settings: Settings) -> dict:
    """Return a secret-free readiness payload for robust local agent operation."""

    vault_dir = resolve_vault_dir(settings.research_vault_dir)
    root = _project_root(vault_dir)
    system_dir = vault_dir / "_system"
    openclaw_dir = system_dir / "openclaw_integration"
    local_ai = build_local_ai_survival_status(settings)

    manifest_count = len(read_manifest(vault_dir))
    rag_count = _rag_document_count(vault_dir)
    portfolio_count, holding_count = _portfolio_counts(settings)
    recommendation_count = _daily_recommendation_count(settings)

    context_files = [
        "docs/operations-readiness.md",
        "docs/openclaw-investment-research-bridge.md",
        "docs/structure-map.md",
        "research_vault/_system/openclaw_integration/openclaw_first_read.json",
        "research_vault/_system/openclaw_integration/investment_research_context.json",
    ]
    tool_contract_files = [
        "tools/check_json_contracts.py",
        "tools/check_offline_readiness.py",
        "tools/check_operational_readiness_score.py",
        "tools/check_openclaw_quick_health.py",
        "tools/check_public_repo_safety.py",
        "tools/check_local_ai_survival.py",
    ]
    eval_gate_files = [
        "tools/check_console_static_contract.py",
        "tools/check_console_asset_and_js.py",
        "tools/smoke_research_console_clicks.py",
        "tools/check_backend_module_health.py",
        "tests/test_backend_regressions.py",
    ]
    observability_files = [
        "backend/research_os/system_health.py",
        "backend/research_os/code_knowledge.py",
        "tools/build_code_knowledge_graph.py",
        "tools/check_code_knowledge_graph.py",
        "tools/show_openclaw_bridge_status.py",
    ]

    context_ready = _exists_count(root, context_files)
    tool_ready = _exists_count(root, tool_contract_files)
    eval_ready = _exists_count(root, eval_gate_files)
    observability_ready = _exists_count(root, observability_files)

    bridge_age = _bridge_age_hours(openclaw_dir)
    bridge_fresh = bridge_age is not None and bridge_age <= 24.0
    safe_defaults_ready = (
        settings.firecrawl_ir_enabled is False
        and settings.firecrawl_ir_dry_run is True
        and settings.firecrawl_monitor_enabled is False
        and settings.firecrawl_monitor_dry_run is True
        and settings.telegram_brief_delivery_enabled is False
        and settings.telegram_brief_delivery_dry_run is True
        and settings.market_signal_graph_enabled is False
    )
    automation_ready = bool(
        settings.daily_recommendations_enabled
        and settings.daily_recommendations_time
        and settings.telegram_market_close_auto_journal
        and settings.telegram_market_close_journal_time
    )

    checks = [
        AgentFoundationCheck(
            key="mission_context",
            label="목표/맥락 패킷",
            ready=context_ready == len(context_files) and bridge_fresh,
            score=min(_score_from_count(context_ready, len(context_files)), 100.0 if bridge_fresh else 80.0),
            evidence=f"문서/first-read/context {context_ready}/{len(context_files)}개, OpenClaw age {bridge_age:.2f}h" if bridge_age is not None else f"문서/first-read/context {context_ready}/{len(context_files)}개, OpenClaw age 미확인",
            next_action="OpenClaw 번들이 낡았으면 `tools\\sync_openclaw_investment_context.ps1 -RequireCompletionAudit`를 실행하세요.",
        ),
        AgentFoundationCheck(
            key="memory_substrate",
            label="장기 기억/RAG 기반",
            ready=manifest_count > 0 and rag_count > 0 and portfolio_count > 0 and recommendation_count > 0,
            score=(
                (25.0 if manifest_count > 0 else 0.0)
                + (25.0 if rag_count > 0 else 0.0)
                + (25.0 if portfolio_count > 0 and holding_count > 0 else 0.0)
                + (25.0 if recommendation_count > 0 else 0.0)
            ),
            evidence=f"manifest {manifest_count}개, RAG {rag_count}개, 포트폴리오 {portfolio_count}개/{holding_count}행, 추천 {recommendation_count}개",
            next_action="저장/RAG가 비면 `python tools\\check_rag_failure_diagnostics.py --strict`와 추천 저장 점검을 먼저 실행하세요.",
        ),
        AgentFoundationCheck(
            key="tool_contracts",
            label="도구 계약/CLI 표준",
            ready=tool_ready == len(tool_contract_files),
            score=_score_from_count(tool_ready, len(tool_contract_files)),
            evidence=f"핵심 도구 계약 {tool_ready}/{len(tool_contract_files)}개",
            next_action="누락 도구가 있으면 JSON 출력/exit code 계약을 갖춘 check_*.py로 복구하세요.",
        ),
        AgentFoundationCheck(
            key="safety_controls",
            label="안전 기본값/민감정보 차단",
            ready=safe_defaults_ready and (root / "tools/check_public_repo_safety.py").exists(),
            score=100.0 if safe_defaults_ready else 70.0,
            evidence=(
                "Firecrawl/Telegram/Market Signal Graph 실전 전송은 기본 비활성 또는 dry-run"
                if safe_defaults_ready
                else "일부 실전 전송 플래그가 켜져 있어 운영 전 재확인이 필요"
            ),
            next_action="실전 전환은 env 파일과 preflight를 거쳐 개별적으로만 켜세요.",
        ),
        AgentFoundationCheck(
            key="evaluation_gates",
            label="평가/회귀 게이트",
            ready=eval_ready == len(eval_gate_files),
            score=_score_from_count(eval_ready, len(eval_gate_files)),
            evidence=f"콘솔/백엔드/스모크/회귀 게이트 {eval_ready}/{len(eval_gate_files)}개",
            next_action="기능 추가 후 py_compile, unittest, console static, smoke, offline readiness를 순서대로 실행하세요.",
        ),
        AgentFoundationCheck(
            key="observability",
            label="관측 가능성/상태 요약",
            ready=observability_ready == len(observability_files),
            score=_score_from_count(observability_ready, len(observability_files)),
            evidence=f"health/code graph/OpenClaw status {observability_ready}/{len(observability_files)}개",
            next_action="상태 요약이 비면 `python tools\\build_code_knowledge_graph.py --print-summary`를 실행하세요.",
        ),
        AgentFoundationCheck(
            key="automation_cadence",
            label="자동화 주기/운영 리듬",
            ready=automation_ready,
            score=100.0 if automation_ready else 60.0,
            evidence=f"추천 {settings.daily_recommendations_time}, 미국 시장일지 {settings.telegram_market_close_journal_time}, 즐겨찾기 {settings.telegram_favorite_posts_time}",
            next_action="주요 자동화 시간이 비어 있으면 settings/env의 실행 시각을 복구하세요.",
            critical=False,
        ),
        AgentFoundationCheck(
            key="local_ai_resilience",
            label="고급 AI 제한 대비",
            ready=bool(local_ai.get("local_operation_ready")),
            score=100.0 if local_ai.get("local_operation_ready") else 0.0,
            evidence=f"로컬 생존 핵심 {local_ai.get('critical_ready_count')}/{local_ai.get('critical_check_count')} ready",
            next_action="`python tools\\check_local_ai_survival.py --json --strict`로 부족 항목을 먼저 보강하세요.",
        ),
    ]

    total_score = round(sum(item.score for item in checks) / len(checks), 1) if checks else 0.0
    critical_missing = [item for item in checks if item.critical and not item.ready]
    status = "ok" if total_score >= 95.0 and not critical_missing else "needs_attention"
    return {
        "status": status,
        "module": "agent_operating_foundation_status",
        "design": "agent_operating_foundation_v1",
        "generated_at": datetime.now(LOCAL_TIMEZONE).isoformat(timespec="seconds"),
        "score": total_score,
        "min_score": 95.0,
        "foundation_ready": status == "ok",
        "critical_ready_count": sum(1 for item in checks if item.critical and item.ready),
        "critical_check_count": sum(1 for item in checks if item.critical),
        "optional_ready_count": sum(1 for item in checks if not item.critical and item.ready),
        "optional_check_count": sum(1 for item in checks if not item.critical),
        "checks": [item.to_dict() for item in checks],
        "operating_principles": [
            "에이전트는 매번 최신 first-read와 OpenClaw context를 먼저 읽고 작업합니다.",
            "장기 기억은 research_vault manifest, RAG SQLite, 추천/포트폴리오 JSON을 기준으로 삼습니다.",
            "외부 호출과 실전 전송은 기본 비활성/dry-run이며, preflight와 완료 감사 후에만 켭니다.",
            "모든 주요 도구는 JSON 출력과 exit code를 갖춰 자동 점검에 편입됩니다.",
            "작업 완료 후 커밋/푸시, OpenClaw 동기화, offline readiness로 폐루프를 닫습니다.",
        ],
        "next_actions": [item.next_action for item in critical_missing]
        or [
            "에이전트 운영 기반은 준비되어 있습니다. 새 기능을 붙일 때 이 점검을 offline readiness와 함께 유지하세요.",
        ],
    }

