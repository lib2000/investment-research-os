import json
from pathlib import Path

from research_os.rag_memory import connect_rag_db, initialize_rag_db
from research_os.research_memory import read_manifest, resolve_vault_dir
from research_os.settings import Settings


SCOPE_LABEL_BY_TICKER = {
    "SECTOR": "섹터/산업 자료",
    "POLICY": "정책/규제 자료",
    "FLOWS": "수급/자금 흐름 자료",
    "MARKET": "시장/시황 자료",
    "MARKET-KR": "국내 시장 자료",
    "MARKET-US": "미국 시장 자료",
    "MARKET-GLOBAL": "글로벌 시장 자료",
    "MACRO": "매크로 자료",
    "RATES": "금리/물가 자료",
    "CUSTOMS": "수출입/관세 자료",
    "INBOX": "미분류 입력 자료",
}


def _clean_text(value: object) -> str:
    return " ".join(str(value or "").replace("\xa0", " ").split()).strip()


def _llm_entry_label(entry: dict) -> tuple[str, str]:
    ticker = _clean_text(entry.get("ticker")).upper()
    source_type = _clean_text(entry.get("source_type"))
    tags = entry.get("tags") if isinstance(entry.get("tags"), list) else []
    company_name = _clean_text(
        entry.get("company_name")
        or entry.get("companyName")
        or entry.get("name")
        or entry.get("holding_name")
        or entry.get("label")
    )
    if company_name:
        return company_name, "종목 자료"
    if ticker in SCOPE_LABEL_BY_TICKER:
        return SCOPE_LABEL_BY_TICKER[ticker], SCOPE_LABEL_BY_TICKER[ticker]
    if source_type.endswith("_research"):
        scope = source_type.replace("_research", "").replace("_", " ")
        return f"{scope.title()} 자료", "범위 자료"
    if any(str(tag).startswith("research_scope:") for tag in tags):
        scope_tags = [str(tag).split(":", 1)[1] for tag in tags if str(tag).startswith("research_scope:")]
        scope = ", ".join(scope_tags[:2]) if scope_tags else "범위"
        return f"{scope} 자료", "범위 자료"
    if ticker:
        return f"{ticker} 종목 자료", "종목 자료"
    return "수동 LLM 저장 자료", "범위 미확인"


def _read_bridge_raw_content(vault_parent: Path, json_relative_path: str | None) -> str:
    if not json_relative_path:
        return ""
    candidate = (vault_parent / str(json_relative_path)).resolve()
    try:
        candidate.relative_to(vault_parent)
        payload = json.loads(candidate.read_text(encoding="utf-8"))
    except Exception:
        return ""
    return str(payload.get("raw_content") or "")


def _rag_relative_paths(vault_dir: Path) -> set[str]:
    initialize_rag_db(vault_dir)
    with connect_rag_db(vault_dir) as connection:
        rows = connection.execute(
            """
            SELECT source_relative_path
            FROM research_memory_documents
            WHERE source_relative_path IS NOT NULL AND source_relative_path != ''
            """
        ).fetchall()
    return {str(row["source_relative_path"] or "") for row in rows}


def build_llm_bridge_storage_status(settings: Settings, limit: int = 10) -> dict:
    vault_dir = resolve_vault_dir(settings.research_vault_dir)
    manifest_entries = read_manifest(vault_dir)
    llm_entries: list[dict] = []
    vault_parent = vault_dir.parent.resolve()

    for entry in manifest_entries:
        if not isinstance(entry, dict) or entry.get("type") != "research-capture":
            continue
        raw_content = _read_bridge_raw_content(vault_parent, entry.get("json_relative_path"))
        if "[수동 LLM 분석 응답]" not in raw_content and "[원 프롬프트]" not in raw_content:
            continue
        display_label, scope_label = _llm_entry_label(entry)
        llm_entries.append(
            {
                "ticker": entry.get("ticker"),
                "label": display_label,
                "display_label": display_label,
                "scope_label": scope_label,
                "type": entry.get("type"),
                "date": entry.get("date"),
                "file_name": entry.get("file_name"),
                "relative_path": entry.get("relative_path"),
                "json_relative_path": entry.get("json_relative_path"),
                "summary": entry.get("summary"),
                "source_type": entry.get("source_type"),
                "tags": entry.get("tags") or [],
                "raw_content_includes_prompt": "[원 프롬프트]" in raw_content,
                "raw_content_includes_llm_response": "[LLM 응답]" in raw_content,
            }
        )

    llm_entries.sort(
        key=lambda item: (
            str(item.get("date") or ""),
            str(item.get("file_name") or ""),
        ),
        reverse=True,
    )

    rag_paths = _rag_relative_paths(vault_dir)

    recent_entries = []
    active_count = 0
    rag_connected_count = 0
    active_rag_connected_count = 0
    for entry in llm_entries:
        relative_path = str(entry.get("relative_path") or "")
        archived = "archived" in [str(tag).lower() for tag in entry.get("tags", [])]
        rag_connected = relative_path in rag_paths
        if not archived:
            active_count += 1
        if rag_connected:
            rag_connected_count += 1
            if not archived:
                active_rag_connected_count += 1
        if len(recent_entries) < max(1, min(limit, 50)):
            recent_entries.append(
                {
                    **entry,
                    "archived": archived,
                    "rag_connected": rag_connected,
                    "rag_status_label": "RAG 연결" if rag_connected else ("보관 문서라 RAG 제외" if archived else "RAG 미연결"),
                }
            )

    return {
        "status": "success",
        "module": "llm_bridge_storage_status",
        "saved_count": len(llm_entries),
        "active_count": active_count,
        "rag_document_count": len(rag_paths),
        "rag_connected_count": rag_connected_count,
        "active_rag_connected_count": active_rag_connected_count,
        "latest_entries": recent_entries,
        "storage_policy": "LLM 응답과 원 프롬프트를 research-capture 원문/JSON으로 저장하고 RAG 문서로 색인합니다.",
        "next_action": (
            "최근 LLM 응답이 저장/RAG에 연결되어 있습니다."
            if recent_entries and any(item.get("rag_connected") for item in recent_entries)
            else "저장된 LLM 응답이 없거나 RAG 색인을 다시 갱신해야 합니다."
        ),
    }
