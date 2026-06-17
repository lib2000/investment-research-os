"""Research workflow attachment and file-processing helpers."""

from __future__ import annotations

from datetime import date, datetime
from pathlib import Path

from research_os import research_workflow_rendering
from research_os.research_memory import ResearchStorageInfo


def workflow_material_excerpt(value: str | None, limit: int = 900) -> str:
    return research_workflow_rendering.workflow_material_excerpt(value, limit)


def prepare_workflow_attachment(
    runtime,
    *,
    vault_dir: Path,
    storage_key: str,
    payload: dict,
    storage_date: date,
) -> dict | None:
    file_bytes = runtime.decode_attachment_base64(payload.get("file_content_base64"))
    if file_bytes is None:
        return None
    safe_key = runtime.normalize_ticker(storage_key) or "WORKFLOW"
    attachments_dir = vault_dir / safe_key / "_attachments"
    attachments_dir.mkdir(parents=True, exist_ok=True)
    safe_name = runtime.safe_attachment_file_name(payload.get("file_name"))
    timestamp = datetime.now().strftime("%H%M%S")
    attachment_path = attachments_dir / f"{safe_key}-workflow-attachment-{storage_date.isoformat()}-{timestamp}-{safe_name}"
    attachment_path.write_bytes(file_bytes)
    extraction = runtime.extract_uploaded_file_text(
        file_bytes,
        payload.get("file_name"),
        payload.get("file_mime_type"),
        source_path=attachment_path,
    )
    return {
        "file_name": payload.get("file_name") or safe_name,
        "mime_type": payload.get("file_mime_type") or "application/octet-stream",
        "size": len(file_bytes),
        "relative_path": attachment_path.relative_to(vault_dir).as_posix(),
        "text_extraction": extraction.get("text_extraction"),
        "extracted_text": extraction.get("extracted_text") or "",
        "document_type": extraction.get("document_type"),
        "extraction_quality": extraction.get("extraction_quality"),
        "extraction_char_count": extraction.get("extraction_char_count"),
        "extraction_preview": extraction.get("extraction_preview"),
        "extraction_warnings": extraction.get("extraction_warnings") or [],
        "extraction_profile": extraction.get("extraction_profile") or {},
    }


def upsert_saved_workflow_rag_document(
    runtime,
    *,
    vault_dir: Path,
    storage: ResearchStorageInfo,
    storage_key: str,
    report_type: str,
    summary: str,
    markdown: str,
    tags: list[str] | None = None,
    source_confidence: float = 0.85,
    metadata: dict | None = None,
) -> dict:
    entry = {
        "ticker": runtime.normalize_ticker(storage_key) or "GENERAL",
        "type": report_type,
        "date": runtime.current_storage_date().isoformat(),
        "file_name": storage.file_name,
        "relative_path": storage.relative_path,
        "json_file_name": storage.json_file_name,
        "json_relative_path": storage.json_relative_path,
        "summary": summary,
        "title": storage.file_name,
        "source_confidence": source_confidence,
        "tags": tags or [],
        **(metadata or {}),
    }
    return runtime.upsert_research_memory_document(
        vault_dir=vault_dir,
        entry=entry,
        full_text=markdown,
    )


def infer_model_update_items(material_text: str) -> list[dict]:
    return research_workflow_rendering.infer_model_update_items(material_text)


def render_file_processing_markdown(file_processing: dict | None) -> str:
    return research_workflow_rendering.render_file_processing_markdown(file_processing)


def render_earnings_filing_note_markdown(response: dict, storage_date: date) -> str:
    return research_workflow_rendering.render_earnings_filing_note_markdown(response, storage_date)


def render_lp_report_staging_markdown(response: dict, storage_date: date) -> str:
    return research_workflow_rendering.render_lp_report_staging_markdown(response, storage_date)


def build_earnings_filing_note_response(runtime, payload: dict, settings) -> dict:
    requested_ticker = str(payload.get("ticker") or "").strip()
    ticker = runtime.resolve_ticker_symbol_from_alias(requested_ticker, settings)
    profile = runtime.official_ticker_registry.get(ticker) or runtime.read_dynamic_ticker_registry(settings).get(ticker)
    if not profile:
        raise runtime.HTTPException(
            status_code=422,
            detail=f"{requested_ticker or '미입력'}는 로컬/캐시 티커 레지스트리에서 확인되지 않았습니다. 먼저 대시보드 티커 진단이나 정보 입력으로 등록하세요.",
        )
    company_name = profile.get("company_name") or ticker
    earnings_call = str(payload.get("earnings_call") or payload.get("earnings_call_text") or "")
    filing_material = str(payload.get("filing_material") or payload.get("filing_text") or "")
    model_notes = str(payload.get("model_notes") or "")
    vault_dir = runtime.resolve_vault_dir(settings.research_vault_dir)
    attachment_info = prepare_workflow_attachment(
        runtime,
        vault_dir=vault_dir,
        storage_key=ticker,
        payload=payload,
        storage_date=runtime.current_storage_date(),
    )
    profile_points = [
        runtime.InjectedDataPoint(
            source_type=runtime.DataSourceType.OTHER,
            label="official_company_profile",
            value=(
                f"{company_name} | 사업 맥락: {profile.get('business_context') or 'n/a'} | "
                f"핵심 KPI: {', '.join(profile.get('watch_kpis') or []) or 'n/a'}"
            ),
            as_of=runtime.current_storage_date().isoformat(),
            source_url="official_ticker_registry",
            confidence=0.95,
        )
    ]
    ticker_dir = vault_dir / ticker
    saved_report_count = len(list(ticker_dir.glob(f"{ticker}-*.md"))) if ticker_dir.exists() else 0
    injected_data = [
        *profile_points,
        runtime.InjectedDataPoint(
            source_type=runtime.DataSourceType.RESEARCH_MEMORY,
            label="linked_workspace_reports",
            value=f"모델 업데이트 전 참고 가능한 저장 리포트 {saved_report_count}개",
            as_of=runtime.current_storage_date().isoformat(),
            confidence=1.0,
        ),
    ]
    material_text = "\n".join([
        earnings_call,
        filing_material,
        model_notes,
        attachment_info.get("extracted_text", "") if attachment_info else "",
        *[f"{item.label}: {item.value}" for item in injected_data[:8]],
    ])
    model_updates = infer_model_update_items(material_text)
    evidence_summary = workflow_material_excerpt(material_text, 1200)
    note_draft = [
        {
            "title": "핵심 요약",
            "body": f"{company_name}의 최신 어닝 콜/공시 자료를 기준으로 모델 업데이트가 필요한 항목은 {', '.join(item['item'] for item in model_updates)}입니다.",
        },
        {
            "title": "투자 논거 변화",
            "body": "기존 투자 논거는 숫자 업데이트 전까지 유지하되, 가이던스·마진·현금흐름 신호가 기존 강세/기준/약세 시나리오 중 어느 쪽을 강화하는지 재분류해야 합니다.",
        },
        {
            "title": "근거 메모",
            "body": evidence_summary,
        },
    ]
    open_questions = [
        "회사 가이던스가 컨센서스 대비 상향/하향인지 확인",
        "매출 성장률과 마진 변화가 일회성인지 구조적인지 확인",
        "현금흐름, CAPEX, 재고/운전자본 변화가 밸류에이션에 미치는 영향 확인",
    ]
    next_actions = [
        "모델의 매출, 마진, FCF, 목표 멀티플 입력값 업데이트",
        "업데이트된 모델 결과를 팀 리포트와 매매 전략에 재연결",
        "다음 실적 전 확인할 KPI를 체크리스트 또는 저장 데이터에 반영",
    ]
    return {
        "status": "success",
        "module": "earnings_filing_note",
        "ticker": ticker,
        "company_name": company_name,
        "model_updates": model_updates,
        "note_draft": note_draft,
        "open_questions": open_questions,
        "next_actions": next_actions,
        "file_processing": {
            key: value for key, value in (attachment_info or {}).items() if key != "extracted_text"
        },
        "injected_data": [item.model_dump(mode="json") for item in injected_data],
    }


def build_gp_lp_staging_response(runtime, payload: dict, settings) -> dict:
    fund_name = str(payload.get("fund_name") or "GP 패키지").strip()
    package_text = str(payload.get("gp_package") or payload.get("gp_package_text") or "")
    valuation_method = str(payload.get("valuation_method") or "멀티플/DCF 혼합").strip()
    base_case = str(payload.get("base_case") or "기준 시나리오").strip()
    vault_dir = runtime.resolve_vault_dir(settings.research_vault_dir)
    storage_key = runtime.normalize_ticker(fund_name) or "LP-REPORT"
    attachment_info = prepare_workflow_attachment(
        runtime,
        vault_dir=vault_dir,
        storage_key=storage_key,
        payload=payload,
        storage_date=runtime.current_storage_date(),
    )
    if attachment_info and attachment_info.get("extracted_text"):
        package_text = "\n".join([package_text, attachment_info.get("extracted_text", "")]).strip()
    package_summary = runtime.summarize_capture(package_text) if package_text else "입력된 GP 패키지 본문이 없어 스테이징 틀만 생성했습니다."
    lower_text = package_text.lower()
    valuation_template_output = [
        f"사용 템플릿: {valuation_method}",
        f"기준 시나리오: {base_case}",
        "NAV/공정가치, 매출 성장률, EBITDA/FCF, 할인율 또는 목표 멀티플 입력값을 LP 보고 전 확정해야 합니다.",
        "전분기 대비 변동이 큰 자산은 GP 코멘트, 거래 사례, 외부 평가 근거를 별도 첨부하세요.",
    ]
    if any(word in lower_text for word in ["down round", "write-down", "손상", "감액", "하락"]):
        valuation_template_output.append("감액 신호가 있어 약세 시나리오와 손상 근거 확인이 필요합니다.")
    if any(word in lower_text for word in ["exit", "ipo", "m&a", "상장", "매각"]):
        valuation_template_output.append("엑시트 이벤트가 언급되어 회수 시점과 할인율 민감도 표를 추가하세요.")
    valuation_template_rows = [
        {
            "line_item": "NAV/공정가치",
            "input_status": "확인 필요",
            "model_action": "전분기 NAV와 이번 평가가치 차이를 입력",
            "lp_note": "평가 기준일과 통화 단위를 명확히 표시",
        },
        {
            "line_item": "매출 성장률",
            "input_status": "GP 본문/파일에서 추출",
            "model_action": "전년 대비 및 전분기 대비 성장률 분리",
            "lp_note": "성장률 둔화/가속의 원인을 한 줄로 설명",
        },
        {
            "line_item": "EBITDA/FCF",
            "input_status": "보강 필요",
            "model_action": "수익성 개선과 현금 소진 속도 확인",
            "lp_note": "손익과 현금흐름 방향이 다르면 별도 리스크로 표기",
        },
        {
            "line_item": "할인율/목표 멀티플",
            "input_status": valuation_method,
            "model_action": "피어 멀티플 또는 DCF 할인율을 전분기와 비교",
            "lp_note": "평가 방법이 바뀐 경우 LP 질문 대비",
        },
        {
            "line_item": "엑시트/펀딩 이벤트",
            "input_status": "이벤트 여부 확인",
            "model_action": "IPO, M&A, 다운라운드 가능성 반영",
            "lp_note": "회수 가능성과 감액 가능성을 분리해 설명",
        },
    ]
    lp_report_draft = [
        {
            "title": "LP 보고 초안 요약",
            "body": f"{fund_name}의 GP 패키지를 기준으로 {valuation_method} 템플릿을 실행할 준비가 되었습니다. 핵심은 평가가치 변동, 실현/미실현 손익, 주요 포트폴리오 이벤트를 LP가 바로 이해할 수 있게 정리하는 것입니다.",
        },
        {
            "title": "포트폴리오 업데이트",
            "body": "주요 자산별 매출/마진/현금흐름/KPI 변화와 밸류에이션 변동 원인을 한 줄씩 연결하세요. 변동 폭이 큰 자산은 GP 원문 근거를 각주 또는 부록으로 붙입니다.",
        },
        {
            "title": "본문 근거",
            "body": workflow_material_excerpt(package_text, 1000),
        },
    ]
    lp_risk_flags = [
        "GP 제공 수치와 내부 밸류에이션 입력값의 기준일 불일치 가능성",
        "평가 방법 변경 또는 비교 멀티플 변경 시 LP 질문 가능성",
        "현금 소진, 추가 펀딩 필요, 엑시트 지연 자산은 별도 설명 필요",
    ]
    staging_checklist = [
        "GP 패키지 원문, 보유 비중, 평가 기준일 확인",
        "밸류에이션 템플릿 입력값과 전분기 입력값 비교",
        "LP 보고용 요약표, 주요 변동 사유, 리스크 플래그 확정",
        "최종 보고 전 수치 단위, 통화, 기준일, 소수점 표기 검수",
    ]
    return {
        "status": "success",
        "module": "gp_lp_staging",
        "fund_name": fund_name,
        "gp_package_summary": package_summary,
        "valuation_method": valuation_method,
        "valuation_template_output": valuation_template_output,
        "valuation_template_rows": valuation_template_rows,
        "lp_report_draft": lp_report_draft,
        "lp_risk_flags": lp_risk_flags,
        "staging_checklist": staging_checklist,
        "file_processing": {
            key: value for key, value in (attachment_info or {}).items() if key != "extracted_text"
        },
    }

def save_earnings_filing_note_response(runtime, response: dict, settings) -> dict:
    storage_date = runtime.current_storage_date()
    vault_dir = runtime.resolve_vault_dir(settings.research_vault_dir)
    markdown = render_earnings_filing_note_markdown(response, storage_date)
    summary = f"{response['company_name']} 어닝 콜/공시 기반 모델 업데이트 노트 초안"
    storage = runtime.save_research_markdown(
        vault_dir=vault_dir,
        ticker=response["ticker"],
        report_type="earnings-filing-note",
        markdown=markdown,
        structured_payload=response,
        manifest_entry={
            "summary": summary,
            "model_updates": response["model_updates"],
            "open_questions": response["open_questions"],
            "source_confidence": 0.88,
            "tags": ["earnings", "filing", "model_update", "valuation", "rag_connected"],
            "ticker_verification": {
                "official_symbol": response["ticker"],
                "company_name": response["company_name"],
                "verified": True,
                "verification_source": "local_or_dynamic_registry",
            },
        },
        report_date=storage_date,
    )
    response["storage"] = storage
    response["rag_document"] = upsert_saved_workflow_rag_document(
        runtime,
        vault_dir=vault_dir,
        storage=storage,
        storage_key=response["ticker"],
        report_type="earnings-filing-note",
        summary=summary,
        markdown=markdown,
        tags=["earnings", "filing", "model_update", "valuation", "workflow"],
        source_confidence=0.88,
        metadata={
            "ticker_verification": {
                "official_symbol": response["ticker"],
                "company_name": response["company_name"],
                "verified": True,
                "verification_source": "local_or_dynamic_registry",
            },
            "model_updates": response["model_updates"],
            "open_questions": response["open_questions"],
        },
    )
    return response


def save_gp_lp_staging_response(runtime, response: dict, settings) -> dict:
    storage_date = runtime.current_storage_date()
    vault_dir = runtime.resolve_vault_dir(settings.research_vault_dir)
    storage_key = runtime.normalize_ticker(response["fund_name"]) or "LP-REPORT"
    markdown = render_lp_report_staging_markdown(response, storage_date)
    summary = f"{response['fund_name']} LP 보고 스테이징"
    storage = runtime.save_research_markdown(
        vault_dir=vault_dir,
        ticker=storage_key,
        report_type="lp-report-staging",
        markdown=markdown,
        structured_payload=response,
        manifest_entry={
            "summary": summary,
            "fund_name": response["fund_name"],
            "valuation_method": response["valuation_method"],
            "lp_risk_flags": response["lp_risk_flags"],
            "source_confidence": 0.82,
            "tags": ["gp_package", "lp_report", "valuation_template", "workflow", "rag_connected"],
        },
        report_date=storage_date,
    )
    response["storage"] = storage
    response["rag_document"] = upsert_saved_workflow_rag_document(
        runtime,
        vault_dir=vault_dir,
        storage=storage,
        storage_key=storage_key,
        report_type="lp-report-staging",
        summary=summary,
        markdown=markdown,
        tags=["gp_package", "lp_report", "valuation_template", "workflow"],
        source_confidence=0.82,
        metadata={
            "fund_name": response["fund_name"],
            "valuation_method": response["valuation_method"],
            "lp_risk_flags": response["lp_risk_flags"],
        },
    )
    return response
