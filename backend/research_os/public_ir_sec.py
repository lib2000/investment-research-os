"""Public IR/SEC collection helpers.

This module keeps the collector inside the Investment Research OS backend instead
of running a separate service. It only handles public http/https URLs and stores
safe metadata/extracted text into research memory for RAG reuse.
"""

from __future__ import annotations

from datetime import date, datetime, timezone
from re import findall, sub
from typing import Any, Callable
from urllib.parse import urlparse

from pydantic import BaseModel, Field, HttpUrl

from research_os.firecrawl_ir_collector import build_firecrawl_ir_readiness_status
from research_os.firecrawl_monitor_events import (
    build_firecrawl_monitor_webhook_status,
    summarize_firecrawl_monitor_event_store,
)
from research_os.firecrawl_monitor_collector import build_firecrawl_monitor_readiness_status
from research_os.rag_memory import upsert_research_memory_document
from research_os.research_memory import (
    read_manifest,
    resolve_vault_dir,
    save_research_markdown,
    update_manifest,
)
from research_os.web_capture import (
    fetch_capture_source_url,
    is_unusable_source_url,
    render_source_url_body,
    render_source_url_context,
    render_url_only_capture_context,
)

PUBLIC_IR_SEC_KEY = "PUBLIC_IR_SEC"
PUBLIC_IR_SEC_REPORT_TYPE = "public-ir-sec"


class PublicIrSecCollectRequest(BaseModel):
    url: HttpUrl
    target_key: str = Field(default=PUBLIC_IR_SEC_KEY, min_length=1, max_length=64)
    save_result: bool = True
    force: bool = False
    no_screenshot: bool = True
    source_title: str | None = None
    source_provider: str | None = None
    source_type: str | None = None
    source_category: str | None = None
    filing_form: str | None = None
    filing_group: str | None = None
    published_at: str | None = None


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _safe_key(value: str | None, fallback: str = PUBLIC_IR_SEC_KEY) -> str:
    cleaned = sub(r"[^A-Za-z0-9._-]+", "_", str(value or "").strip().upper()).strip("_")
    return cleaned or fallback


def _safe_title(value: str | None, fallback: str = "공개 IR/SEC 자료") -> str:
    title = " ".join(str(value or "").split())
    return title[:140] or fallback


def _host_label(source_url: str) -> tuple[str, str, list[str]]:
    parsed = urlparse(source_url)
    host = (parsed.hostname or "").lower()
    path = (parsed.path or "").lower()
    tags = ["public_ir_sec"]
    if host.endswith("sec.gov"):
        return "SEC EDGAR", "official_filing", [*tags, "sec", "edgar", "official_filing"]
    if host.startswith("ir.") or "investor" in host or "/ir" in path or "investors" in path:
        if "press-release" in path or "news-events" in path or "newsroom" in path:
            return host or "공개 IR", "ir_press_release", [*tags, "ir", "investor_relations", "press_release"]
        return host or "공개 IR", "ir_presentation", [*tags, "ir", "investor_relations"]
    if "benzinga.com" in host:
        return "Benzinga", "earnings_data", [*tags, "earnings_data", "market_data"]
    return host or "공개 웹", "other", tags


def _normalize_public_ir_source_type(source_url: str, value: str) -> str:
    host = (urlparse(source_url).hostname or "").lower()
    normalized = _safe_key(value, "other").lower()
    if host.endswith("sec.gov") and normalized in {"sec", "sec_edgar", "official_filing"}:
        return "official_filing"
    return normalized


def _summary_from_text(
    title: str,
    text: str,
    source_provider: str,
    *,
    extracted_body_available: bool = True,
) -> str:
    compact = " ".join((text or "").split())
    if compact and extracted_body_available:
        return f"{source_provider} 공개 자료 `{title}`에서 추출한 본문 {len(compact):,}자를 저장했습니다. {compact[:260]}"
    return f"{source_provider} 공개 자료 `{title}` URL과 메타데이터를 저장했습니다. 본문은 후속 복사/파일 보강이 필요합니다."


def _capture_quality(
    url_info: dict[str, Any],
    body_text: str,
    *,
    extracted_body_available: bool = True,
) -> dict[str, Any]:
    status = str(url_info.get("status") or "unknown")
    body_chars = len(body_text or "") if extracted_body_available else 0
    url_unavailable = is_unusable_source_url(url_info) or not extracted_body_available
    if url_unavailable:
        quality_status = "보강 필요"
        action = "본문 추출이 제한되었습니다. URL-only 보관 후 원문 복사 또는 파일 첨부로 보강하세요."
    elif body_chars >= 500:
        quality_status = "정상"
        action = "추천/리포트/RAG 근거로 바로 활용 가능합니다."
    elif body_chars:
        quality_status = "보강 필요"
        action = "본문이 짧습니다. 원문 PDF/본문 복사로 보강하면 분석 품질이 올라갑니다."
    else:
        quality_status = "보강 필요"
        action = "본문 추출이 제한되었습니다. URL-only 보관 후 원문 복사 또는 파일 첨부로 보강하세요."
    return {
        "status": quality_status,
        "source_status": status,
        "body_chars": body_chars,
        "url_text_unavailable": url_unavailable,
        "needs_body_copy": url_unavailable or body_chars < 500,
        "recommended_action": action,
    }


def _render_markdown(payload: dict[str, Any], body_text: str) -> str:
    lines = [
        f"# {payload['title']}",
        "",
        "## 공개 IR/SEC 수집 메타데이터",
        f"- 출처: {payload['source_provider']}",
        f"- 원본 URL: {payload['source_url']}",
        f"- 최종 URL: {payload.get('final_url') or payload['source_url']}",
        f"- 처리 상태: {payload['source_url_processing'].get('status')}",
        f"- 본문 글자 수: {payload['body_chars']}",
        f"- 문서 링크 추정: {payload['doc_links']}",
        f"- 저장 정책: {payload['copyright_policy']}",
        f"- 품질 상태: {payload['capture_quality'].get('status')}",
        "",
        "## 요약",
        payload.get("summary") or "요약 없음",
        "",
        "## 후속 활용",
        "- 보유/관심 종목과 직접 연결되는 내용은 최근 1주 자료, RAG 검색, 오늘 추천 근거에 재사용됩니다.",
        "- 본문이 제한된 자료는 URL-only로 남기고, 원문 복사/파일 첨부로 보강하세요.",
        "",
        "## 본문/URL 맥락",
    ]
    if body_text:
        lines.append(body_text[:30000])
    else:
        lines.append(render_url_only_capture_context(payload["source_url"], payload.get("source_url_processing") or {}))
    return "\n".join(lines).strip() + "\n"


def _find_existing_entry(vault_dir, source_url: str, target_key: str) -> dict[str, Any] | None:
    normalized_url = source_url.strip()
    normalized_key = _safe_key(target_key)
    for entry in reversed(read_manifest(vault_dir)):
        if str(entry.get("ticker") or "").upper() != normalized_key:
            continue
        if str(entry.get("source_url") or "").strip() == normalized_url:
            return entry
    return None


def _trusted_ticker_verification(ticker: str, candidate: Any) -> dict[str, Any] | None:
    """Keep only server-verified ticker metadata for portfolio evidence."""
    normalized = _safe_key(ticker, "")
    if not normalized or normalized == PUBLIC_IR_SEC_KEY or not isinstance(candidate, dict):
        return None
    official_symbol = _safe_key(str(candidate.get("official_symbol") or ""), "")
    if candidate.get("verified") is not True or official_symbol != normalized:
        return None
    return {
        "requested_symbol": _safe_key(str(candidate.get("requested_symbol") or normalized), normalized),
        "official_symbol": official_symbol,
        "company_name": _safe_title(str(candidate.get("company_name") or normalized), normalized),
        "exchange": _safe_title(str(candidate.get("exchange") or ""), "") or None,
        "country": _safe_title(str(candidate.get("country") or ""), "") or None,
        "verified": True,
        "verification_source": _safe_title(
            str(candidate.get("verification_source") or "local_cached_registry"),
            "local_cached_registry",
        ),
        "message": _safe_title(
            str(candidate.get("message") or "서버의 티커 레지스트리에서 확인했습니다."),
            "서버의 티커 레지스트리에서 확인했습니다.",
        ),
    }


def _is_official_portfolio_source_entry(entry: dict[str, Any]) -> bool:
    """Limit automatic ticker binding to official SEC, issuer-IR, or KRX ETF URLs."""
    source_url = str(entry.get("source_url") or entry.get("final_url") or "").strip()
    parsed = urlparse(source_url)
    host = (parsed.hostname or "").lower()
    source_type = _safe_key(str(entry.get("source_type") or ""), "").lower()
    if parsed.scheme != "https" or not host:
        return False
    if source_type in {"official_filing", "sec_company_submissions"}:
        return host.endswith("sec.gov")
    if source_type in {"company_ir_press_releases", "ir_press_release", "ir_presentation"}:
        return host.startswith("ir.") or "investor" in host or "investors" in host
    if source_type == "krx_etf_product":
        return host == "kind.krx.co.kr"
    return False


def _apply_ticker_verification_to_existing_entry(
    vault_dir,
    entry: dict[str, Any],
    ticker_verification: dict[str, Any] | None,
) -> tuple[dict[str, Any], bool]:
    if not ticker_verification or not _is_official_portfolio_source_entry(entry):
        return entry, False
    if entry.get("ticker_verification") == ticker_verification:
        return entry, False
    updated = {**entry, "ticker_verification": ticker_verification}
    update_manifest(vault_dir=vault_dir, entry=updated)
    return updated, True


def backfill_public_ir_sec_ticker_verifications(
    vault_dir,
    *,
    ticker_verification_for: Callable[[str], dict[str, Any] | None],
    target_tickers: set[str] | None = None,
    apply: bool = False,
) -> dict[str, Any]:
    """Attach verified ticker metadata to existing official public-source entries only.

    This changes manifest metadata only; it does not create a report, complete a
    review gate, alter a holding, or accept non-official URLs as evidence.
    """
    requested = {_safe_key(value, "") for value in (target_tickers or set())}
    requested.discard("")
    updated: list[str] = []
    skipped: list[dict[str, str]] = []
    for entry in read_manifest(vault_dir):
        if not isinstance(entry, dict):
            continue
        if str(entry.get("scope") or "") != "public_ir_sec" and str(entry.get("type") or "") != PUBLIC_IR_SEC_REPORT_TYPE:
            continue
        ticker = _safe_key(str(entry.get("ticker") or ""), "")
        if not ticker or ticker == PUBLIC_IR_SEC_KEY:
            continue
        if requested and ticker not in requested:
            continue
        if not _is_official_portfolio_source_entry(entry):
            skipped.append({"ticker": ticker, "file_name": str(entry.get("file_name") or ""), "reason": "non_official_source"})
            continue
        verification = _trusted_ticker_verification(ticker, ticker_verification_for(ticker))
        if not verification:
            skipped.append({"ticker": ticker, "file_name": str(entry.get("file_name") or ""), "reason": "ticker_not_verified"})
            continue
        if entry.get("ticker_verification") == verification:
            skipped.append({"ticker": ticker, "file_name": str(entry.get("file_name") or ""), "reason": "already_verified"})
            continue
        if apply:
            update_manifest(vault_dir=vault_dir, entry={**entry, "ticker_verification": verification})
        updated.append(str(entry.get("file_name") or ticker))
    return {
        "status": "success",
        "module": "public_ir_sec_ticker_verification_backfill",
        "apply": apply,
        "requested_tickers": sorted(requested),
        "updated_count": len(updated),
        "updated_files": updated,
        "skipped_count": len(skipped),
        "skipped": skipped,
        "changes_document_coverage": False,
        "changes_review_gate": False,
    }


def collect_public_ir_sec_url(
    request: PublicIrSecCollectRequest,
    settings: Any,
    *,
    ticker_verification: dict[str, Any] | None = None,
) -> dict[str, Any]:
    source_url = str(request.url).strip()
    target_key = _safe_key(request.target_key)
    vault_dir = resolve_vault_dir(settings.research_vault_dir)
    trusted_ticker_verification = _trusted_ticker_verification(target_key, ticker_verification)
    existing_entry = _find_existing_entry(vault_dir, source_url, target_key)
    if existing_entry and not request.force:
        existing_entry, metadata_backfilled = _apply_ticker_verification_to_existing_entry(
            vault_dir,
            existing_entry,
            trusted_ticker_verification,
        )
        return {
            "status": "skipped_existing",
            "module": "public_ir_sec_collection",
            "message": "이미 같은 URL이 공개 IR/SEC 저장 데이터에 있습니다. force=true로 다시 수집할 수 있습니다.",
            "source_url": source_url,
            "target_key": target_key,
            "existing_entry": existing_entry,
            "storage": {
                "relative_path": existing_entry.get("relative_path"),
                "json_relative_path": existing_entry.get("json_relative_path"),
            },
            "ticker_verification_backfilled": metadata_backfilled,
            "rag_document": None,
        }

    url_info = fetch_capture_source_url(source_url)
    extracted_body_text = render_source_url_body(url_info)
    body_text = extracted_body_text
    extracted_body_available = bool(extracted_body_text) and not is_unusable_source_url(url_info)
    if not body_text and url_info:
        body_text = render_source_url_context(url_info)
    provider, source_type, tags = _host_label(source_url)
    provider = _safe_title(request.source_provider, provider)
    source_type = _normalize_public_ir_source_type(source_url, request.source_type or source_type)
    title = _safe_title(request.source_title or url_info.get("title") or url_info.get("original_title"), provider)
    source_category = _safe_title(request.source_category, "공개 IR/SEC 자료")
    filing_form = _safe_title(request.filing_form, "")
    filing_group = _safe_key(request.filing_group, "").lower()
    published_at = _safe_title(request.published_at, "")
    metadata_tags = [
        value
        for value in [
            source_category,
            filing_form,
            filing_group,
            published_at,
        ]
        if value
    ]
    body_chars = len(extracted_body_text or "")
    context_chars = len(body_text or "")
    doc_links = len(set(findall(r"https?://[^\s)\]]+", body_text or "")))
    quality = _capture_quality(
        url_info,
        extracted_body_text,
        extracted_body_available=extracted_body_available,
    )
    policy = (
        "공개 http/https 자료만 수집합니다. 자동 로그인, 자동 전송, 웹 채팅창 자동 수집은 하지 않으며 "
        "본문 추출 제한 자료는 URL/메타데이터 중심으로 보관합니다."
    )
    payload = {
        "status": "success" if body_chars else "url_only_saved",
        "module": "public_ir_sec_collection",
        "target_key": target_key,
        "source_url": source_url,
        "final_url": url_info.get("final_url") or source_url,
        "source_provider": provider,
        "source_type": source_type,
        "source_category": source_category,
        "filing_form": filing_form,
        "filing_group": filing_group,
        "published_at": published_at,
        "title": title,
        "summary": _summary_from_text(
            title,
            extracted_body_text,
            provider,
            extracted_body_available=extracted_body_available,
        ),
        "body_chars": body_chars,
        "context_chars": context_chars,
        "doc_links": doc_links,
        "collected_at": _utc_now_iso(),
        "no_screenshot": request.no_screenshot,
        "copyright_policy": policy,
        "source_url_processing": url_info,
        "capture_quality": quality,
        "tags": sorted(
            set(
                [
                    *tags,
                    "rag_candidate",
                    "codex_app_source",
                    *metadata_tags,
                    *( ["url_text_unavailable", "needs_body_copy"] if quality.get("needs_body_copy") else [] ),
                ]
            )
        ),
        "storage": None,
        "rag_document": None,
    }
    if not request.save_result:
        return payload

    markdown = _render_markdown(payload, body_text)
    manifest_entry = {
        "title": title,
        "summary": payload["summary"],
        "scope": "public_ir_sec",
        "source_type": source_type,
        "source_url": source_url,
        "final_url": payload["final_url"],
        "source_provider": provider,
        "source_category": source_category,
        "filing_form": filing_form,
        "filing_group": filing_group,
        "published_at": published_at,
        "confidence": 0.84 if body_chars >= 500 else 0.62,
        "source_confidence": 0.84 if body_chars >= 500 else 0.62,
        "tags": payload["tags"],
        "capture_quality": quality,
        "capture_quality_status": quality["status"],
        "source_url_processing": url_info,
        "copyright_policy": policy,
        "body_chars": body_chars,
        "context_chars": context_chars,
        "doc_links": doc_links,
        "collected_at": payload["collected_at"],
    }
    if trusted_ticker_verification and _is_official_portfolio_source_entry(
        {
            **manifest_entry,
            "source_url": source_url,
            "final_url": payload["final_url"],
        }
    ):
        manifest_entry["ticker_verification"] = trusted_ticker_verification
    storage = save_research_markdown(
        vault_dir=vault_dir,
        ticker=target_key,
        report_type=PUBLIC_IR_SEC_REPORT_TYPE,
        markdown=markdown,
        structured_payload={**payload, "extracted_text": body_text[:30000]},
        manifest_entry=manifest_entry,
        report_date=date.today(),
        file_suffix=title,
    )
    payload["storage"] = storage.model_dump(mode="json")
    saved_entry = next(
        (
            entry for entry in read_manifest(vault_dir)
            if entry.get("file_name") == storage.file_name and str(entry.get("ticker") or "").upper() == target_key
        ),
        None,
    )
    if saved_entry:
        payload["rag_document"] = upsert_research_memory_document(
            vault_dir=vault_dir,
            entry=saved_entry,
            full_text=markdown,
        )
    return payload


def _needs_body_duplicate_title_groups(entries: list[dict[str, Any]], limit: int = 10) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str, str], list[dict[str, Any]]] = {}
    for entry in entries:
        ticker = str(entry.get("ticker") or "").upper()
        title = str(entry.get("title") or entry.get("file_name") or "").strip()
        if not title:
            continue
        filing_key = str(entry.get("published_at") or entry.get("source_url") or entry.get("final_url") or "").strip()
        grouped.setdefault((ticker, title, filing_key), []).append(entry)

    groups: list[dict[str, Any]] = []
    for (ticker, title, filing_key), group_entries in grouped.items():
        if len(group_entries) < 2:
            continue
        groups.append(
            {
                "ticker": ticker,
                "title": title,
                "filing_key": filing_key,
                "count": len(group_entries),
                "source_urls": [
                    str(item.get("source_url") or item.get("final_url") or "")
                    for item in group_entries[: max(1, min(limit, 50))]
                    if item.get("source_url") or item.get("final_url")
                ],
                "file_names": [
                    str(item.get("file_name") or "")
                    for item in group_entries[: max(1, min(limit, 50))]
                    if item.get("file_name")
                ],
            }
        )
    groups.sort(key=lambda item: (-int(item["count"]), str(item["ticker"]), str(item["title"])))
    return groups[: max(1, min(limit, 50))]


def _needs_body_repeated_title_groups(entries: list[dict[str, Any]], limit: int = 10) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for entry in entries:
        ticker = str(entry.get("ticker") or "").upper()
        title = str(entry.get("title") or entry.get("file_name") or "").strip()
        if not title:
            continue
        grouped.setdefault((ticker, title), []).append(entry)

    groups: list[dict[str, Any]] = []
    for (ticker, title), group_entries in grouped.items():
        if len(group_entries) < 2:
            continue
        filing_keys: list[str] = []
        for entry in group_entries:
            filing_key = str(entry.get("published_at") or entry.get("source_url") or entry.get("final_url") or "").strip()
            if filing_key and filing_key not in filing_keys:
                filing_keys.append(filing_key)
        groups.append(
            {
                "ticker": ticker,
                "title": title,
                "count": len(group_entries),
                "filing_keys": filing_keys[: max(1, min(limit, 50))],
                "file_names": [
                    str(item.get("file_name") or "")
                    for item in group_entries[: max(1, min(limit, 50))]
                    if item.get("file_name")
                ],
            }
        )
    groups.sort(key=lambda item: (-int(item["count"]), str(item["ticker"]), str(item["title"])))
    return groups[: max(1, min(limit, 50))]


def _body_followup_reason(entry: dict[str, Any]) -> dict[str, Any]:
    quality = entry.get("capture_quality") if isinstance(entry.get("capture_quality"), dict) else {}
    source = entry.get("source_url_processing") if isinstance(entry.get("source_url_processing"), dict) else {}
    text = " ".join(
        str(value or "")
        for value in [
            entry.get("title"),
            entry.get("filing_form"),
            source.get("original_text"),
            source.get("text"),
        ]
    )
    normalized = text.upper()
    if "6-K" in normalized and ("EXHIBIT" in normalized or "99.1" in normalized):
        sec_hint = _sec_exhibit_followup_hint(entry)
        return {
            "reason": "sec_exhibit_followup",
            "label": "6-K 첨부 Exhibit 추적",
            "recommended_action": "6-K 본문은 wrapper가 짧습니다. 참조된 Exhibit 99.1/연간보고서/보도자료 원문을 별도 수집해 보강하세요.",
            **sec_hint,
        }
    if quality.get("url_text_unavailable"):
        return {
            "reason": "url_text_unavailable",
            "label": "URL 원문 제한",
            "recommended_action": "원문 링크 확인 또는 파일/본문 복사로 보강하세요.",
        }
    if int(quality.get("body_chars") or entry.get("body_chars") or 0) < 500:
        return {
            "reason": "short_body",
            "label": "본문 짧음",
            "recommended_action": "본문이 짧습니다. 원문 PDF/본문 복사로 보강하면 분석 품질이 올라갑니다.",
        }
    return {
        "reason": "needs_review",
        "label": "보강 확인",
        "recommended_action": str(quality.get("recommended_action") or "원문 확인 후 보강 여부를 판단하세요."),
    }


def _sec_exhibit_followup_hint(entry: dict[str, Any]) -> dict[str, Any]:
    source = entry.get("source_url_processing") if isinstance(entry.get("source_url_processing"), dict) else {}
    source_url = str(entry.get("source_url") or source.get("source_url") or source.get("final_url") or "").strip()
    parsed = urlparse(source_url)
    parts = [part for part in parsed.path.split("/") if part]
    hint: dict[str, Any] = {}
    if len(parts) >= 5 and parts[:3] == ["Archives", "edgar", "data"]:
        cik = parts[3]
        accession = parts[4]
        base_url = f"{parsed.scheme}://{parsed.netloc}/Archives/edgar/data/{cik}/{accession}"
        hint["sec_archive_directory_url"] = f"{base_url}/"
        if len(accession) == 18 and accession.isdigit():
            dashed = f"{accession[:10]}-{accession[10:12]}-{accession[12:]}"
            hint["sec_filing_index_url"] = f"{base_url}/{dashed}-index.html"
            hint["sec_accession_number"] = dashed
        else:
            hint["sec_accession_number"] = accession
    exhibit_labels = sorted(set(findall(r"\b99\.\d+\b", str(source.get("original_text") or source.get("text") or ""))))
    if exhibit_labels:
        hint["expected_exhibits"] = exhibit_labels[:10]
    return hint


def _needs_body_entry_preview(entry: dict[str, Any]) -> dict[str, Any]:
    preview = dict(entry)
    preview["body_followup"] = _body_followup_reason(entry)
    return preview


def public_ir_sec_status_payload(settings: Any, limit: int = 10) -> dict[str, Any]:
    vault_dir = resolve_vault_dir(settings.research_vault_dir)
    entries = [
        entry for entry in read_manifest(vault_dir)
        if str(entry.get("scope") or "") == "public_ir_sec"
        or str(entry.get("ticker") or "").upper() == PUBLIC_IR_SEC_KEY
        or str(entry.get("type") or "") == PUBLIC_IR_SEC_REPORT_TYPE
    ]
    entries.sort(key=lambda item: (str(item.get("date") or ""), str(item.get("file_name") or "")), reverse=True)
    recent = entries[: max(1, min(limit, 50))]
    needs_body = [entry for entry in entries if (entry.get("capture_quality") or {}).get("needs_body_copy")]
    needs_body_preview = [
        _needs_body_entry_preview(entry)
        for entry in needs_body[: max(1, min(limit, 50))]
    ]
    sec_exhibit_followup_entries = [
        entry for entry in needs_body_preview
        if (entry.get("body_followup") or {}).get("reason") == "sec_exhibit_followup"
    ]
    needs_body_duplicate_title_groups = _needs_body_duplicate_title_groups(needs_body, limit=limit)
    needs_body_repeated_title_groups = _needs_body_repeated_title_groups(needs_body, limit=limit)
    next_actions = [
        "공개 IR/SEC URL을 입력해 보유/관심 종목과 연결되는 자료를 수집하세요.",
        "URL-only 자료는 원문 링크 확인 또는 파일/본문 복사로 보강하세요.",
        "최근 1주 자료와 오늘 추천 근거에서 공개 IR/SEC 연결 여부를 확인하세요.",
    ]
    empty_state = None if entries else {
        "title": "아직 수집된 공개 IR/SEC 자료가 없습니다.",
        "message": "공개 SEC/IR URL을 수집하면 저장 데이터, 최근 1주 자료, RAG, 오늘 추천 근거에 순서대로 연결됩니다.",
    }
    return {
        "status": "success",
        "module": "public_ir_sec_status",
        "storage_key": PUBLIC_IR_SEC_KEY,
        "entry_count": len(entries),
        "recent_count": len(recent),
        "needs_body_copy_count": len(needs_body),
        "needs_body_copy_entries": needs_body_preview,
        "sec_exhibit_followup_count": len(sec_exhibit_followup_entries),
        "sec_exhibit_followup_entries": sec_exhibit_followup_entries[: max(1, min(limit, 50))],
        "needs_body_duplicate_title_group_count": len(needs_body_duplicate_title_groups),
        "needs_body_duplicate_title_groups": needs_body_duplicate_title_groups,
        "needs_body_repeated_title_group_count": len(needs_body_repeated_title_groups),
        "needs_body_repeated_title_groups": needs_body_repeated_title_groups,
        "policy": "공개 IR/SEC 자료만 수집하고 제한 자료는 URL/메타데이터 중심으로 보관합니다.",
        "firecrawl_ir": build_firecrawl_ir_readiness_status(settings),
        "firecrawl_monitor": build_firecrawl_monitor_readiness_status(settings),
        "firecrawl_monitor_events": summarize_firecrawl_monitor_event_store(settings, limit=limit),
        "firecrawl_monitor_webhook": build_firecrawl_monitor_webhook_status(settings),
        "empty_state": empty_state,
        "next_actions": next_actions,
        "recent_entries": recent,
    }
