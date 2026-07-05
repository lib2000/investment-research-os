"""Secret-free readiness payload for operating without premium external AI."""

from __future__ import annotations

import json
import os
import sqlite3
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from research_os.daily_recommendation_store import (
    daily_recommendation_state_path,
    daily_recommendation_store_path,
)
from research_os.research_memory import read_manifest, resolve_vault_dir
from research_os.settings import Settings
from research_os.state_store import portfolio_store_path


LOCAL_TIMEZONE = ZoneInfo("Asia/Seoul")


@dataclass(frozen=True)
class LocalSurvivalCheck:
    key: str
    label: str
    ready: bool
    evidence: str
    action: str
    critical: bool = True

    def to_dict(self) -> dict:
        return {
            "key": self.key,
            "label": self.label,
            "ready": self.ready,
            "evidence": self.evidence,
            "action": self.action,
            "critical": self.critical,
        }


def _read_json(path: Path, default: object) -> object:
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception:
        return default


def _project_root_from_vault(vault_dir: Path) -> Path:
    if vault_dir.name == "research_vault":
        return vault_dir.parent
    return Path.cwd()


def _file_state(path: Path, root: Path | None = None) -> dict:
    exists = path.exists()
    display_path = path
    if root is not None:
        try:
            display_path = path.relative_to(root)
        except ValueError:
            display_path = path
    return {
        "exists": exists,
        "path": str(display_path),
        "size_bytes": path.stat().st_size if exists else 0,
    }


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


def _truthy_env(names: list[str]) -> list[str]:
    configured = []
    for name in names:
        value = os.environ.get(name)
        if value and value.strip() and "placeholder" not in value.lower():
            configured.append(name)
    return configured


def _safe_env_labels(names: list[str]) -> list[str]:
    labels = []
    for name in names:
        label = name.lower()
        for suffix in ("_api_key", "_key", "_token", "_secret", "_base_url", "_endpoint"):
            label = label.replace(suffix, "")
        labels.append(label.replace("_", "-"))
    return labels


def _source_file_ready(root: Path, relative_path: str) -> bool:
    return (root / relative_path).exists()


def build_local_ai_survival_status(settings: Settings) -> dict:
    """Build a local-first resilience status without network calls or secrets."""

    vault_dir = resolve_vault_dir(settings.research_vault_dir)
    root = _project_root_from_vault(vault_dir)
    system_dir = vault_dir / "_system"
    manifest = read_manifest(vault_dir)
    manifest_count = len(manifest)
    rag_count = _rag_document_count(vault_dir)

    portfolio_path = portfolio_store_path(settings)
    portfolio_payload = _read_json(portfolio_path, {"portfolios": {}})
    portfolios = portfolio_payload.get("portfolios") if isinstance(portfolio_payload, dict) else {}
    portfolio_count = len(portfolios) if isinstance(portfolios, dict) else 0
    holding_count = 0
    if isinstance(portfolios, dict):
        for portfolio in portfolios.values():
            holdings = portfolio.get("holdings") if isinstance(portfolio, dict) else []
            if isinstance(holdings, list):
                holding_count += len(holdings)

    daily_path = daily_recommendation_store_path(settings)
    daily_payload = _read_json(daily_path, {"records": []})
    daily_records = daily_payload.get("records") if isinstance(daily_payload, dict) else []
    daily_record_count = len(daily_records) if isinstance(daily_records, list) else 0

    required_files = {
        "manual_llm_bridge": "backend/research_os/llm_bridge_status.py",
        "rag_synthesis": "backend/research_os/rag_synthesis.py",
        "daily_recommendations": "backend/research_os/daily_recommendations.py",
        "investment_insight_hub": "backend/research_os/investment_insight_hub.py",
        "market_signal_contract": "backend/research_os/market_signal_graph_pipeline_contract.py",
        "offline_readiness": "tools/check_offline_readiness.py",
        "public_repo_safety": "tools/check_public_repo_safety.py",
    }
    missing_required_files = [
        label for label, relative in required_files.items() if not _source_file_ready(root, relative)
    ]

    optional_local_model_env = _truthy_env(
        [
            "LOCAL_AI_ENDPOINT",
            "LOCAL_LLM_ENDPOINT",
            "OLLAMA_BASE_URL",
            "LM_STUDIO_BASE_URL",
            "OPENAI_API_BASE",
        ]
    )
    external_ai_env = _truthy_env(["OPENAI_API_KEY", "DEEPSEEK_API_KEY", "ANTHROPIC_API_KEY", "GEMINI_API_KEY"])

    openclaw_dir = system_dir / "openclaw_integration"
    openclaw_bundle_files = [
        openclaw_dir / "bridge_status.json",
        openclaw_dir / "openclaw_first_read.json",
        openclaw_dir / "investment_research_context.json",
    ]
    openclaw_ready_count = sum(1 for path in openclaw_bundle_files if path.exists())

    checks = [
        LocalSurvivalCheck(
            key="portfolio_store",
            label="로컬 포트폴리오 저장소",
            ready=portfolio_count > 0 and holding_count > 0,
            evidence=f"포트폴리오 {portfolio_count}개, 보유 행 {holding_count}개",
            action="저장 포트폴리오가 비어 있으면 콘솔에서 보유 종목을 다시 저장하세요.",
        ),
        LocalSurvivalCheck(
            key="research_vault_manifest",
            label="저장 리서치 Manifest",
            ready=manifest_count > 0,
            evidence=f"manifest entries {manifest_count}개",
            action="저장 데이터가 비어 있으면 리포트/뉴스/공시를 먼저 수집하세요.",
        ),
        LocalSurvivalCheck(
            key="rag_index",
            label="로컬 RAG 색인",
            ready=rag_count > 0,
            evidence=f"RAG 문서 {rag_count}개",
            action="RAG 문서가 0개이면 `python tools\\check_rag_failure_diagnostics.py --strict` 후 색인을 갱신하세요.",
        ),
        LocalSurvivalCheck(
            key="daily_recommendations",
            label="AI 비의존 추천 저장/추적",
            ready=daily_record_count > 0 and daily_path.exists(),
            evidence=f"추천 기록 {daily_record_count}개",
            action="추천 기록이 없으면 `python tools\\check_daily_recommendations_store.py --require-quality`를 실행하세요.",
        ),
        LocalSurvivalCheck(
            key="deterministic_engines",
            label="규칙 기반 분석 엔진",
            ready=not missing_required_files,
            evidence=(
                "필수 모듈 확인"
                if not missing_required_files
                else "누락: " + ", ".join(missing_required_files)
            ),
            action="필수 모듈 누락 시 최신 main을 가져오거나 해당 파일을 복구하세요.",
        ),
        LocalSurvivalCheck(
            key="manual_llm_bridge",
            label="수동/로컬 LLM 브리지",
            ready=_source_file_ready(root, "backend/research_os/llm_bridge_status.py")
            and _source_file_ready(root, "mobile_app/research_console/console.js"),
            evidence="원 프롬프트/응답 붙여넣기 저장 및 RAG 연결 경로 존재",
            action="고급 AI 접속 제한 시 로컬 모델 또는 다른 PC에서 얻은 응답을 콘솔 LLM 브리지에 붙여넣으세요.",
        ),
        LocalSurvivalCheck(
            key="openclaw_bundle",
            label="OpenClaw 로컬 컨텍스트 번들",
            ready=openclaw_ready_count >= 2,
            evidence=f"핵심 번들 {openclaw_ready_count}/{len(openclaw_bundle_files)}개",
            action="번들이 낡았으면 `tools\\sync_openclaw_investment_context.ps1 -RequireCompletionAudit`를 실행하세요.",
            critical=False,
        ),
    ]

    critical_missing = [item for item in checks if item.critical and not item.ready]
    noncritical_missing = [item for item in checks if not item.critical and not item.ready]
    local_operation_ready = not critical_missing
    status = "ok" if local_operation_ready else "needs_attention"

    return {
        "status": status,
        "module": "local_ai_survival_status",
        "design": "local_ai_survival_v1",
        "mode": "local_first",
        "generated_at": datetime.now(LOCAL_TIMEZONE).isoformat(timespec="seconds"),
        "retail_advanced_ai_dependency": "optional",
        "local_operation_ready": local_operation_ready,
        "critical_ready_count": sum(1 for item in checks if item.critical and item.ready),
        "critical_check_count": sum(1 for item in checks if item.critical),
        "optional_ready_count": sum(1 for item in checks if not item.critical and item.ready),
        "optional_check_count": sum(1 for item in checks if not item.critical),
        "checks": [item.to_dict() for item in checks],
        "fallback_layers": [
            "로컬 JSON/SQLite 저장소 기반 포트폴리오, 관심종목, 추천 이력 유지",
            "RAG 색인과 저장 리서치 manifest로 외부 모델 없이 근거 검색",
            "규칙 기반 추천, 컨센서스 스캔, 포트폴리오 신호 점수, 뉴스/공시 우선순위 분류",
            "수동/로컬 LLM 브리지로 로컬 모델 응답을 붙여넣어 저장/RAG 반영",
            "OpenClaw 컨텍스트 번들로 별도 로컬 시스템이 같은 요약을 읽도록 동기화",
        ],
        "optional_local_model": {
            "configured": bool(optional_local_model_env),
            "configured_count": len(optional_local_model_env),
            "configured_sources": _safe_env_labels(optional_local_model_env),
            "policy": "로컬 모델 endpoint는 있으면 보강 계층으로 쓰고, 없어도 핵심 운영은 규칙/RAG로 계속합니다.",
        },
        "external_ai": {
            "configured": bool(external_ai_env),
            "configured_count": len(external_ai_env),
            "configured_sources": _safe_env_labels(external_ai_env),
            "policy": "OpenAI/DeepSeek 등 외부 고급 모델은 필수 의존성이 아니라 분석 보강 계층입니다.",
        },
        "storage": {
            "vault_dir": str(vault_dir),
            "portfolio_store": _file_state(portfolio_path, root),
            "daily_recommendations": _file_state(daily_path, root),
            "daily_recommendation_state": _file_state(daily_recommendation_state_path(settings), root),
            "openclaw_bundle_dir": _file_state(openclaw_dir, root),
        },
        "next_actions": [
            item.action for item in [*critical_missing, *noncritical_missing]
        ]
        or [
            "현재 구조는 외부 고급 AI 접근 제한 시에도 로컬 저장/RAG/규칙 기반 분석으로 기본 운영 가능합니다.",
            "실전 전에는 `python tools\\check_local_ai_survival.py --json --strict`를 오프라인 readiness와 함께 실행하세요.",
        ],
    }
