"""Check and optionally backfill RAG citation documents for daily recommendations."""

from __future__ import annotations

import argparse
import json
import sqlite3
from pathlib import Path
from typing import Any

DEFAULT_STORE = Path("research_vault/_system/daily_recommendations.json")


RAG_REPORT_TYPE_PRIORITY = {
    "public-ir-sec": 95,
    "earnings-filing-note": 92,
    "dart-filing-watch": 90,
    "official_filing": 88,
    "thesis-impact-review": 82,
    "collaborative-team-report": 78,
    "dossier-synthesis": 76,
    "research-capture": 72,
    "earnings-reaction": 70,
    "research-checklist": 65,
    "smart-trade-setup": 62,
}


def normalize_ticker(value: object) -> str:
    text = str(value or "").strip().upper()
    return "".join(char for char in text if char.isalnum() or char in {".", "-", "_"})


def safe_float(value: object, default: float = 0.7) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def json_list(value: object) -> list[Any]:
    if isinstance(value, list):
        return value
    if not isinstance(value, str):
        return []
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError:
        return []
    return parsed if isinstance(parsed, list) else []


def evidence_document_claims(document: dict[str, Any], claims: list[str]) -> list[str]:
    report_type = str(document.get("report_type") or "").lower()
    source_type = str(document.get("source_type") or "").lower()
    haystack = " ".join(
        str(document.get(key) or "")
        for key in ("title", "summary", "content_excerpt", "source_file_name", "source_relative_path")
    ).lower()
    matched: list[str] = []
    for claim in claims:
        claim_text = str(claim or "").strip()
        if not claim_text:
            continue
        claim_lower = claim_text.lower()
        if "공개 ir/sec" in claim_lower and ("public-ir-sec" in report_type or "sec" in source_type):
            matched.append(claim_text)
        elif "공시" in claim_lower and ("filing" in source_type or "dart" in report_type):
            matched.append(claim_text)
        elif "목표가" in claim_lower or "리포트" in claim_lower:
            if report_type in {"thesis-impact-review", "collaborative-team-report", "dossier-synthesis", "research-capture"}:
                matched.append(claim_text)
        elif "최근 근거 파일" in claim_lower and str(document.get("source_relative_path") or "").split("/")[-1].lower() in claim_lower:
            matched.append(claim_text)
        elif "rag 연결" in claim_lower:
            matched.append(claim_text)
        else:
            tokens = [token for token in claim_lower.replace("/", " ").replace(":", " ").split() if len(token) >= 4]
            if tokens and any(token in haystack for token in tokens[:8]):
                matched.append(claim_text)
    return list(dict.fromkeys(matched))[:3]


def normalize_evidence_documents(value: object, limit: int = 5) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in value:
        if not isinstance(item, dict):
            continue
        relative_path = str(item.get("source_relative_path") or item.get("relative_path") or "").strip()
        title = str(item.get("title") or item.get("source_file_name") or relative_path or "").strip()
        if not relative_path and not title:
            continue
        key = relative_path or title
        if key in seen:
            continue
        seen.add(key)
        rows.append(
            {
                "title": title,
                "source_relative_path": relative_path,
                "source_date": str(item.get("source_date") or item.get("date") or "").strip(),
                "report_type": str(item.get("report_type") or "").strip(),
                "source_type": str(item.get("source_type") or "").strip(),
                "confidence": item.get("confidence"),
                "citation_label": str(item.get("citation_label") or "근거 문서").strip(),
                "matched_claims": [str(claim).strip() for claim in item.get("matched_claims", []) if str(claim or "").strip()][:3],
            }
        )
    return rows[: max(1, min(limit, 10))]


def build_evidence_documents(vault_dir: Path, ticker: str, evidence_sources: object, reasons: object, limit: int = 5) -> list[dict[str, Any]]:
    normalized_ticker = normalize_ticker(ticker)
    if not normalized_ticker:
        return []
    db_path = vault_dir / "_system" / "research_memory.sqlite3"
    if not db_path.exists():
        return []
    try:
        with sqlite3.connect(db_path) as connection:
            connection.row_factory = sqlite3.Row
            rows = connection.execute(
                """
                SELECT ticker, report_type, title, summary, content_excerpt, source_type,
                       source_file_name, source_relative_path, json_relative_path,
                       source_date, confidence, tags_json, updated_at
                FROM research_memory_documents
                WHERE upper(ticker) = ?
                ORDER BY source_date DESC, updated_at DESC
                LIMIT 80
                """,
                (normalized_ticker,),
            ).fetchall()
    except sqlite3.Error:
        return []
    claims = [str(item).strip() for item in [*(evidence_sources or []), *(reasons or [])] if str(item or "").strip()]
    scored: list[tuple[float, dict[str, Any]]] = []
    for row in rows:
        payload = dict(row)
        tags = [str(tag) for tag in json_list(payload.get("tags_json"))]
        if "archived" in {tag.lower() for tag in tags}:
            continue
        report_type = str(payload.get("report_type") or "")
        source_type = str(payload.get("source_type") or "")
        matched_claims = evidence_document_claims(payload, claims)
        priority = RAG_REPORT_TYPE_PRIORITY.get(report_type, RAG_REPORT_TYPE_PRIORITY.get(source_type, 55))
        confidence = safe_float(payload.get("confidence"), 0.7)
        score = priority + (confidence * 10) + (len(matched_claims) * 12) + min(len(str(payload.get("content_excerpt") or "")) / 400, 6)
        scored.append((score, {
            "title": str(payload.get("title") or payload.get("source_file_name") or "").strip(),
            "source_relative_path": str(payload.get("source_relative_path") or "").strip(),
            "json_relative_path": str(payload.get("json_relative_path") or "").strip(),
            "source_date": str(payload.get("source_date") or "").strip(),
            "report_type": report_type,
            "source_type": source_type,
            "confidence": confidence,
            "citation_label": "RAG 근거 문서",
            "matched_claims": matched_claims,
        }))
    scored.sort(key=lambda item: (item[0], item[1].get("source_date") or ""), reverse=True)
    return normalize_evidence_documents([item for _, item in scored], limit=limit)

def project_root(start: Path) -> Path:
    for candidate in [start, *start.parents]:
        if (candidate / "backend" / "research_os_main.py").exists() and (candidate / "research_vault").exists():
            return candidate
    raise SystemExit("InvestmentJournalApp 프로젝트 루트를 찾지 못했습니다.")


def load_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SystemExit(f"추천 저장 파일을 읽지 못했습니다: {path} / {exc}") from exc
    if not isinstance(payload, dict) or not isinstance(payload.get("records"), list):
        raise SystemExit("추천 저장 파일의 records 구조를 확인해야 합니다.")
    return payload


def citation_rows(record: dict[str, Any]) -> list[dict[str, Any]]:
    rows = record.get("evidence_documents")
    return [item for item in rows if isinstance(item, dict)] if isinstance(rows, list) else []


def citation_is_usable(item: dict[str, Any], root: Path) -> bool:
    relative_path = str(item.get("source_relative_path") or "").strip()
    if not relative_path:
        return False
    path = (root / relative_path).resolve()
    try:
        path.relative_to(root.resolve())
    except ValueError:
        return False
    return path.exists() and path.is_file()


def main() -> int:
    parser = argparse.ArgumentParser(description="매일 추천의 RAG 근거 문서 연결을 점검/보강합니다.")
    parser.add_argument("--store", type=Path, default=DEFAULT_STORE)
    parser.add_argument("--min-citations-per-record", type=int, default=1)
    parser.add_argument("--write-back", action="store_true")
    parser.add_argument("--strict", action="store_true")
    parser.add_argument("--limit", type=int, default=12)
    args = parser.parse_args()

    root = project_root(Path.cwd())
    store_path = args.store if args.store.is_absolute() else root / args.store
    payload = load_json(store_path)
    vault_dir = root / "research_vault"
    records = [item for item in payload.get("records", []) if isinstance(item, dict)]
    missing: list[dict[str, Any]] = []
    invalid: list[dict[str, Any]] = []
    updated = 0

    for record in records:
        rows = citation_rows(record)
        usable_count = sum(1 for row in rows if citation_is_usable(row, root))
        if usable_count < args.min_citations_per_record:
            missing.append(record)
            generated = build_evidence_documents(
                vault_dir,
                str(record.get("ticker") or ""),
                record.get("evidence_sources") or [],
                record.get("reasons") or [],
            )
            if args.write_back and generated:
                record["evidence_documents"] = generated
                updated += 1
        else:
            broken = [row for row in rows if not citation_is_usable(row, root)]
            if broken:
                invalid.append(record)

    if args.write_back and updated:
        payload["records"] = records
        payload["citation_backfilled_at"] = payload.get("updated_at")
        store_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    remaining_missing = []
    remaining_invalid = []
    for record in records:
        rows = citation_rows(record)
        usable_count = sum(1 for row in rows if citation_is_usable(row, root))
        if usable_count < args.min_citations_per_record:
            remaining_missing.append(record)
        elif any(not citation_is_usable(row, root) for row in rows):
            remaining_invalid.append(record)

    print(f"추천 저장 파일: {store_path.relative_to(root)}")
    print(f"추천 기록: {len(records)}개 | 보강 대상 {len(missing)}개 | 이번 보강 {updated}개")
    print(f"근거 문서 부족: {len(remaining_missing)}개 | 경로 확인 필요: {len(remaining_invalid)}개")
    for record in remaining_missing[: max(0, args.limit)]:
        print(
            "- 근거 문서 부족: "
            f"{record.get('recommendation_date')} {record.get('rank')}위 "
            f"{record.get('company_name') or record.get('ticker')}"
        )
    for record in remaining_invalid[: max(0, args.limit)]:
        print(
            "- 근거 문서 경로 확인: "
            f"{record.get('recommendation_date')} {record.get('rank')}위 "
            f"{record.get('company_name') or record.get('ticker')}"
        )

    ok = not remaining_missing and not remaining_invalid
    if args.strict and not ok:
        print("매일 추천 RAG 근거 문서 연결 확인 필요")
        return 1
    print("매일 추천 RAG 근거 문서 연결 정상" if ok else "매일 추천 RAG 근거 문서 연결 경고")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
