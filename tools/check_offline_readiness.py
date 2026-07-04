"""Run backend-free readiness checks for the Investment Research OS."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo


LOCAL_TIMEZONE = ZoneInfo("Asia/Seoul")
CHECKS = [
    ("Git 동기화 상태", ["tools/check_git_sync_status.py"]),
    ("점검 스크립트 JSON 계약", ["tools/check_json_contracts.py"]),
    ("공개 저장소 안전 점검", ["tools/check_public_repo_safety.py"]),
    ("백엔드 런타임 준비도", ["tools/check_backend_runtime_env.py", "--check-daily-tests"]),
    ("백엔드 모듈 상태", ["tools/check_backend_module_health.py", "--strict"]),
    ("코드 지식 그래프", ["tools/check_code_knowledge_graph.py", "--strict"]),
    ("운영 완성도 95%", ["tools/check_operational_readiness_score.py", "--strict", "--min-score", "95"]),
    ("변경 영향 분석", ["tools/analyze_code_diff_impact.py", "--refresh", "--strict"]),
    ("클래식 콘솔 정적 계약", ["tools/check_console_static_contract.py", "--strict"]),
    ("클래식 콘솔 자산/JS", ["tools/check_console_asset_and_js.py"]),
    (
        "포트폴리오 분석 커버리지",
        [
            "tools/check_portfolio_analysis_coverage.py",
            "--all-portfolios",
            "--min-average-completion",
            "0.95",
            "--write-backlog",
            "--strict",
        ],
    ),
    (
        "포트폴리오 저장 수량",
        [
            "tools/check_portfolio_store.py",
            "--portfolio",
            "이형주",
            "--min-holdings",
            "17",
            "--expected-holdings-count",
            "17",
            "--forbid-zero",
            "--max-price-age-hours",
            "24",
            "--max-portfolio-age-hours",
            "24",
        ],
    ),
    (
        "전체 포트폴리오 저장 구조",
        [
            "tools/check_all_portfolio_store.py",
            "--min-holdings",
            "1",
            "--forbid-zero",
            "--max-price-age-hours",
            "24",
            "--max-sync-age-hours",
            "168",
        ],
    ),
    ("국민연금 국내주식 14%", ["tools/check_nps_domestic_equity_allocation.py", "--rebalance-plan"]),
    ("투자 캘린더/실적 일정", ["tools/check_investment_calendar_store.py", "--strict"]),
    ("리서치 소스 저장 상태", ["tools/check_research_source_store.py", "--strict"]),
    ("매크로/지역 소스 연결 신호", ["tools/check_macro_source_signal_linkage.py", "--strict"]),
    ("저장 자료 중복 리뷰", ["tools/check_storage_duplicate_review.py", "--strict"]),
    ("뉴스 인박스 우선 분류", ["tools/check_news_inbox_priority_queue.py", "--strict"]),
    ("최근 1주 자료/추천 근거", ["tools/check_recent_weekly_brief.py", "--strict"]),
    ("통합 투자 인사이트 허브", ["tools/check_investment_insight_hub.py", "--strict"]),
    ("OpenClaw 투자리서치 브리지", ["tools/check_openclaw_investment_context.py", "--max-age-hours", "24"]),
    ("OpenClaw 완료 감사", ["tools/check_openclaw_bridge_completion.py", "--max-age-hours", "24", "--require-report-hashes"]),
    ("공개 IR/SEC 저장 품질", ["tools/check_public_ir_sec_store.py", "--require-any"]),
    ("Firecrawl IR 수집 payload", ["tools/check_firecrawl_ir_collector.py"]),
    ("Firecrawl Monitor 변화 감지 payload", ["tools/check_firecrawl_monitor_collector.py"]),
    (
        "Firecrawl IR registry 샘플 payload",
        [
            "tools/check_firecrawl_ir_collector.py",
            "--input-json",
            "docs/examples/firecrawl_ir_registry.sample.json",
        ],
    ),
    ("Firecrawl Earnings 수집 payload", ["tools/check_firecrawl_earnings_collector.py"]),
    ("DeepSeek IR 분석 payload", ["tools/check_deepseek_ir_analysis.py"]),
    ("Portfolio Health 변화 감지", ["tools/check_portfolio_change_detection.py"]),
    ("Telegram Portfolio Brief dry-run", ["tools/check_telegram_brief_sender.py"]),
    ("Telegram 즐겨찾기 인기글 dry-run", ["tools/check_telegram_favorite_posts.py", "--sample", "--enabled"]),
    ("Earnings Transcript payload", ["tools/check_earnings_transcript_collector.py"]),
    ("Portfolio Signal 통합 점수", ["tools/check_portfolio_signal_score.py"]),
    ("Portfolio Brief payload", ["tools/check_portfolio_brief_contract.py"]),
    ("Market Signal Graph pipeline contract", ["tools/check_market_signal_graph_pipeline_contract.py"]),
    ("저장 자료 품질", ["tools/check_storage_quality_store.py", "--strict"]),
    ("자동 분류 태그/RAG 품질", ["tools/check_classification_quality.py", "--strict"]),
    ("저장/RAG 실패 진단", ["tools/check_rag_failure_diagnostics.py", "--strict"]),
    (
        "LLM/RAG 저장 상태",
        [
            "tools/check_llm_bridge_store.py",
            "--min-saved-count",
            "0",
            "--min-active-count",
            "0",
            "--min-rag-connected-count",
            "0",
        ],
    ),
    (
        "RAG 합성 저장 상태",
        [
            "tools/check_rag_synthesis_store.py",
            "--min-saved-count",
            "0",
            "--min-rag-connected-count",
            "0",
        ],
    ),
    ("매일 추천 저장/추적", ["tools/check_daily_recommendations_store.py", "--require-milestones", "--require-quality"]),
    ("매일 추천 RAG 근거 문서", ["tools/check_daily_recommendation_citations.py", "--strict"]),
    ("매일 추천 정책 신호 품질", ["tools/check_daily_recommendation_policy_signals.py", "--strict"]),
    (
        "매일 추천 후보 정책",
        [
            "tools/check_daily_recommendation_candidate_policy.py",
            "--require-hold-warning",
            "--expected-held-ticker",
            "112610",
            "--output-json",
            "tmp/daily_recommendation_candidate_policy_preview.json",
        ],
    ),
]


def project_root(start: Path) -> Path:
    for candidate in [start, *start.parents]:
        if (candidate / "backend" / "research_os_main.py").exists() and (
            candidate / "research_vault"
        ).exists():
            return candidate
    raise SystemExit("InvestmentJournalApp 프로젝트 루트를 찾지 못했습니다.")


def build_json_payload(root: Path, *, tail_lines: int) -> dict:
    results = []
    for label, check_args in CHECKS:
        completed = subprocess.run(
            [sys.executable, *check_args],
            cwd=root,
            check=False,
            capture_output=True,
            text=True,
        )
        output = "\n".join(part for part in (completed.stdout, completed.stderr) if part)
        results.append(
            {
                "label": label,
                "args": check_args,
                "returncode": completed.returncode,
                "status": "ok" if completed.returncode == 0 else "error",
                "output_tail": output.splitlines()[-max(0, tail_lines) :],
            }
        )
        if completed.returncode != 0:
            break
    failed = [item for item in results if item["returncode"] != 0]
    return {
        "status": "error" if failed else "ok",
        "project_root": str(root),
        "generated_at": datetime.now(LOCAL_TIMEZONE).isoformat(timespec="seconds"),
        "timezone": str(LOCAL_TIMEZONE),
        "check_count": len(results),
        "expected_check_count": len(CHECKS),
        "failed_count": len(failed),
        "failed_labels": [item["label"] for item in failed],
        "results": results,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Investment Research OS 오프라인 운영 점검을 실행합니다.")
    parser.add_argument("--json", action="store_true", help="전체 점검 결과 요약을 JSON으로 출력합니다.")
    parser.add_argument("--output-json", type=Path, help="전체 점검 결과 요약을 JSON 파일로 저장합니다.")
    parser.add_argument("--tail-lines", type=int, default=12, help="JSON 출력에 포함할 각 점검 출력 마지막 줄 수")
    args = parser.parse_args()

    root = project_root(Path.cwd())
    if args.json or args.output_json:
        payload = build_json_payload(root, tail_lines=args.tail_lines)
        if args.output_json:
            output_path = args.output_json if args.output_json.is_absolute() else root / args.output_json
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        if args.json:
            print(json.dumps(payload, ensure_ascii=False, indent=2))
        failed = [item for item in payload["results"] if item["returncode"] != 0]
        return failed[0]["returncode"] if failed else 0

    print(f"프로젝트 루트: {root}", flush=True)
    for label, args in CHECKS:
        print(f"\n==> {label}", flush=True)
        completed = subprocess.run([sys.executable, *args], cwd=root, check=False)
        if completed.returncode != 0:
            print(f"오프라인 운영 점검 실패: {label}", flush=True)
            return completed.returncode
    print("\n오프라인 운영 점검 통과", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
