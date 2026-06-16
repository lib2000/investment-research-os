"""Helpers for Korea Customs trade-data quality policy."""

from __future__ import annotations

from datetime import date
from re import sub

from fastapi import HTTPException

from research_os.data_providers import fetch_customs_total_trend_status, fetch_customs_trade_rows
from research_os.state_store import current_storage_date, current_storage_timestamp


CUSTOMS_VALID_STORAGE_POLICY = (
    "실제 수출입 수치가 있는 행만 research_vault/CUSTOMS와 RAG 색인에 저장합니다."
)
CUSTOMS_EMPTY_STORAGE_POLICY = (
    "실제 수출입 수치가 없는 빈 응답과 서비스 상태 메시지는 저장/RAG 반영하지 않습니다."
)
CUSTOMS_STRATEGIC_ITEMS = [
    {
        "item_code": "190230",
        "label": "라면/가공식품",
        "linked_sectors": ["음식료", "수출소비재"],
        "watch_reason": "삼양식품 등 음식료 수출주의 수요 강도와 재고 부담을 점검",
    },
    {
        "item_code": "8542",
        "label": "반도체",
        "linked_sectors": ["반도체", "AI 인프라"],
        "watch_reason": "반도체 수출 회복, 재고 조정, AI 서버 수요 흐름을 점검",
    },
    {
        "item_code": "8504",
        "label": "변압기/전력기기",
        "linked_sectors": ["전력기기", "전력망"],
        "watch_reason": "전력 인프라 수출과 전력기기 피어 밸류에이션 근거를 점검",
    },
    {
        "item_code": "850760",
        "label": "리튬이온 배터리",
        "linked_sectors": ["2차전지", "기후변화"],
        "watch_reason": "배터리 수출 둔화/회복과 원재료·재고 부담을 점검",
    },
]


def customs_trade_quality_metadata(has_valid_data: bool, valid_row_count: int = 0) -> dict[str, object]:
    """Return UI/API metadata for deciding whether customs data can be stored."""
    if has_valid_data:
        return {
            "data_quality": "valid_trade_rows",
            "data_quality_label": "수출입 수치 확인",
            "storage_policy": CUSTOMS_VALID_STORAGE_POLICY,
            "storage_skip_expected": False,
            "next_action": "수출주, 재고 부담, 환율 민감 섹터 점검에 보조 신호로 반영하세요.",
        }
    return {
        "data_quality": "no_valid_trade_rows",
        "data_quality_label": "실제 수출입 수치 없음",
        "storage_policy": CUSTOMS_EMPTY_STORAGE_POLICY,
        "storage_skip_expected": True,
        "next_action": (
            "기간, HS코드, 국가 조건을 재확인하고 수출입총괄(GW) 진단의 권한/응답 상태를 확인하세요."
        ),
    }


def _safe_provider_error_message(error: Exception, settings) -> str:
    message = str(error)
    for key in (
        getattr(settings, "fmp_api_key", ""),
        getattr(settings, "fmp_api_key_legacy", ""),
        getattr(settings, "customs_trade_api_key", ""),
    ):
        if key:
            message = message.replace(str(key), "****")
    return message


def yymm_add_months(yymm: str, months: int) -> str:
    year = int(yymm[:4])
    month = int(yymm[4:6]) + months
    while month <= 0:
        month += 12
        year -= 1
    while month > 12:
        month -= 12
        year += 1
    return f"{year:04d}{month:02d}"


def customs_default_period(today: date | None = None, current_date_func=current_storage_date) -> tuple[str, str, str]:
    selected = today or current_date_func()
    current_yymm = f"{selected.year:04d}{selected.month:02d}"
    end_yymm = current_yymm if selected.day >= 11 else yymm_add_months(current_yymm, -1)
    start_yymm = yymm_add_months(end_yymm, -2)
    release_cycle = "1일 확정/전월 점검" if selected.day < 11 else "11일·21일 잠정 수출입 동향 점검"
    return start_yymm, end_yymm, release_cycle


def safe_customs_number(value: object) -> float:
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def aggregate_customs_trade_rows(rows: list[dict], theme: dict) -> dict:
    export_value = sum(safe_customs_number(row.get("export_value_usd")) for row in rows)
    import_value = sum(safe_customs_number(row.get("import_value_usd")) for row in rows)
    export_weight = sum(safe_customs_number(row.get("export_weight")) for row in rows)
    import_weight = sum(safe_customs_number(row.get("import_weight")) for row in rows)
    balance = export_value - import_value
    country_buckets: dict[str, dict] = {}
    for row in rows:
        country = row.get("country_name") or row.get("country_code") or "국가 미상"
        bucket = country_buckets.setdefault(
            country,
            {"country": country, "export_value_usd": 0.0, "import_value_usd": 0.0},
        )
        bucket["export_value_usd"] += safe_customs_number(row.get("export_value_usd"))
        bucket["import_value_usd"] += safe_customs_number(row.get("import_value_usd"))
    top_countries = sorted(
        country_buckets.values(),
        key=lambda item: item["export_value_usd"] + item["import_value_usd"],
        reverse=True,
    )[:5]
    if export_value > import_value * 1.2:
        signal = "수출 우위"
        inventory_signal = "재고 부담 낮음 또는 해외 수요 우위 가능성"
    elif import_value > export_value * 1.2:
        signal = "수입/재고 부담 우위"
        inventory_signal = "원재료·재고 축적 또는 내수/생산 투입 부담 확인 필요"
    else:
        signal = "균형"
        inventory_signal = "수출입 균형권. 가격/재고 지표와 함께 재확인"
    return {
        "item_code": theme["item_code"],
        "label": theme["label"],
        "linked_sectors": theme["linked_sectors"],
        "watch_reason": theme["watch_reason"],
        "row_count": len(rows),
        "export_value_usd": export_value,
        "import_value_usd": import_value,
        "trade_balance_usd": balance,
        "export_weight": export_weight,
        "import_weight": import_weight,
        "signal": signal,
        "inventory_signal": inventory_signal,
        "top_countries": top_countries,
    }


def build_customs_trade_snapshot(
    *,
    settings,
    start_yymm: str | None = None,
    end_yymm: str | None = None,
    item_code: str = "",
    country_code: str = "",
    trade_rows_fetcher=fetch_customs_trade_rows,
    current_date_func=current_storage_date,
    current_timestamp_func=current_storage_timestamp,
) -> dict:
    default_start, default_end, release_cycle = customs_default_period(current_date_func=current_date_func)
    start_yymm = sub(r"\D", "", start_yymm or default_start)[:6]
    end_yymm = sub(r"\D", "", end_yymm or default_end)[:6]
    if len(start_yymm) != 6 or len(end_yymm) != 6:
        raise HTTPException(status_code=422, detail="start_yymm/end_yymm은 YYYYMM 형식이어야 합니다.")

    themes = [
        theme
        for theme in CUSTOMS_STRATEGIC_ITEMS
        if not item_code or theme["item_code"].startswith(str(item_code).strip())
    ]
    if item_code and not themes:
        themes = [
            {
                "item_code": str(item_code).strip(),
                "label": f"HS {str(item_code).strip()}",
                "linked_sectors": ["사용자 지정 품목"],
                "watch_reason": "사용자 지정 품목의 수출입 흐름을 점검",
            }
        ]
    warnings: list[str] = []
    aggregates: list[dict] = []
    source_urls: list[str] = []
    raw_rows: list[dict] = []
    for theme in themes:
        fetched = trade_rows_fetcher(
            settings,
            start_yymm=start_yymm,
            end_yymm=end_yymm,
            item_code=theme["item_code"],
            country_code=country_code,
        )
        warnings.extend(fetched.get("warnings") or [])
        if fetched.get("source_url") and fetched["source_url"] not in source_urls:
            source_urls.append(fetched["source_url"])
        rows = fetched.get("rows") or []
        raw_rows.extend(rows[:20])
        aggregates.append(aggregate_customs_trade_rows(rows, theme))
    total_valid_rows = sum(int(item.get("row_count") or 0) for item in aggregates)
    if total_valid_rows == 0:
        warnings.append(
            "조회 조건에서 실제 수출입 수치가 있는 행을 찾지 못했습니다. "
            "빈 응답은 저장/RAG 반영하지 않습니다."
        )
    quality_metadata = customs_trade_quality_metadata(
        bool(total_valid_rows),
        valid_row_count=total_valid_rows,
    )

    aggregates.sort(
        key=lambda item: abs(float(item.get("trade_balance_usd") or 0)),
        reverse=True,
    )
    key_takeaways = []
    for item in aggregates:
        if item["row_count"]:
            key_takeaways.append(
                f"{item['label']}은 {item['signal']} 신호입니다. "
                f"{item['inventory_signal']}."
            )
        else:
            key_takeaways.append(
                f"{item['label']}은 이번 조회 조건에서 표시 가능한 행이 없습니다. HS코드/기간/국가 조건을 재확인하세요."
            )
    sector_implications = [
        (
            f"{item['label']} 관련 섹터({', '.join(item['linked_sectors'])})는 {item['signal']} 신호를 보조 지표로 반영합니다."
            if item.get("row_count")
            else f"{item['label']} 관련 섹터({', '.join(item['linked_sectors'])})는 이번 조회에서 실제 수출입 수치가 없어 투자 신호로 반영하지 않습니다."
        )
        for item in aggregates
    ]
    return {
        "status": "success" if total_valid_rows else "warning",
        "module": "korea_customs_trade_snapshot",
        "source": "관세청 품목별 국가별 수출입실적(GW)",
        "release_schedule": "매월 1일, 11일, 21일 발표 자료를 우선 확인",
        "release_cycle": release_cycle,
        "start_yymm": start_yymm,
        "end_yymm": end_yymm,
        "item_code": item_code,
        "country_code": country_code,
        "source_urls": source_urls,
        "warnings": list(dict.fromkeys(warnings))[:5],
        "has_valid_data": bool(total_valid_rows),
        "valid_row_count": total_valid_rows,
        **quality_metadata,
        "aggregates": aggregates,
        "raw_rows_preview": raw_rows[:20],
        "key_takeaways": key_takeaways,
        "sector_implications": sector_implications,
        "portfolio_usage": [
            "수출 비중이 큰 보유 종목은 해당 품목의 수출 우위/둔화를 투자 논거 가중치에 반영합니다.",
            "수입이 수출보다 빠르게 늘면 원재료·재고 부담 가능성을 리스크 스캔에 보조 신호로 반영합니다.",
            "시장일지와 일일 브리핑은 이 데이터를 섹터 흐름·재고 사이클 체크포인트로 자동 참조합니다.",
        ],
        "generated_at": current_timestamp_func(),
    }


def render_customs_trade_markdown(snapshot: dict, storage_date: date) -> str:
    aggregate_lines = []
    for item in snapshot.get("aggregates", []):
        if item.get("row_count"):
            aggregate_lines.append(
                f"- {item['label']}({item['item_code']}): {item['signal']} / "
                f"수출 ${item['export_value_usd']:,.0f}, 수입 ${item['import_value_usd']:,.0f}, "
                f"무역수지 ${item['trade_balance_usd']:,.0f} / {item['inventory_signal']}"
            )
        else:
            aggregate_lines.append(
                f"- {item['label']}({item['item_code']}): 실제 수출입 수치 없음 / 저장·RAG 반영 제외"
            )
    return f"""---
ticker: CUSTOMS
type: customs-trade-brief
date: {storage_date.isoformat()}
module: korea_customs_trade_snapshot
source: korea_customs_service_public_data
period: {snapshot.get('start_yymm')}~{snapshot.get('end_yymm')}
---

# 관세청 수출입 동향 투자 참고자료: {snapshot.get('start_yymm')}~{snapshot.get('end_yymm')}

## 발표 주기

- {snapshot.get('release_schedule')}
- 현재 반영 기준: {snapshot.get('release_cycle')}

## 핵심 신호

{chr(10).join(f"- {item}" for item in snapshot.get("key_takeaways", []))}

## 품목별 요약

{chr(10).join(aggregate_lines) if aggregate_lines else "- 표시할 품목 데이터가 없습니다."}

## 섹터 시사점

{chr(10).join(f"- {item}" for item in snapshot.get("sector_implications", []))}

## 포트폴리오 활용

{chr(10).join(f"- {item}" for item in snapshot.get("portfolio_usage", []))}

## 데이터 경고

{chr(10).join(f"- {item}" for item in snapshot.get("warnings", [])) if snapshot.get("warnings") else "- 표시할 경고 없음"}
"""


def attach_customs_total_trend_diagnostic(
    snapshot: dict,
    settings,
    total_trend_fetcher=fetch_customs_total_trend_status,
    error_message_formatter=_safe_provider_error_message,
) -> dict:
    if snapshot.get("has_valid_data") or snapshot.get("total_trend_status"):
        return snapshot
    warnings = list(snapshot.get("warnings") or [])
    try:
        total_trend_status = total_trend_fetcher(
            settings,
            start_yymm=str(snapshot.get("start_yymm") or ""),
            end_yymm=str(snapshot.get("end_yymm") or ""),
        )
        for warning in total_trend_status.get("warnings", []):
            if warning not in warnings:
                warnings.append(warning)
        return {
            **snapshot,
            "total_trend_status": total_trend_status,
            "warnings": warnings[:5],
        }
    except Exception as exc:
        message = error_message_formatter(exc, settings)
        if message not in warnings:
            warnings.append(message)
        return {**snapshot, "warnings": warnings[:5]}


def should_check_customs_trade_today(settings, selected_date: date | None = None, current_date_func=current_storage_date) -> bool:
    today = selected_date or current_date_func()
    try:
        release_days = {
            int(value.strip())
            for value in str(settings.customs_trade_release_days or "1,11,21").split(",")
            if value.strip()
        }
    except ValueError:
        release_days = {1, 11, 21}
    return today.day in release_days


def build_daily_customs_trade_reference(
    settings,
    should_check_func=should_check_customs_trade_today,
    snapshot_builder=build_customs_trade_snapshot,
    diagnostic_attacher=attach_customs_total_trend_diagnostic,
    error_message_formatter=_safe_provider_error_message,
) -> dict | None:
    if not should_check_func(settings):
        return None
    try:
        snapshot = snapshot_builder(settings=settings)
    except Exception as exc:
        return {
            "status": "warning",
            "summary": f"관세청 수출입 동향 자동 확인 실패: {error_message_formatter(exc, settings)}",
            "release_schedule": settings.customs_trade_release_days,
            "key_takeaways": [],
            "warnings": [error_message_formatter(exc, settings)],
        }
    snapshot = diagnostic_attacher(snapshot, settings)
    return {
        "status": "success" if snapshot.get("has_valid_data") else "warning",
        "source": snapshot.get("source"),
        "period": f"{snapshot.get('start_yymm')}~{snapshot.get('end_yymm')}",
        "release_cycle": snapshot.get("release_cycle"),
        "has_valid_data": bool(snapshot.get("has_valid_data")),
        "data_quality": snapshot.get("data_quality"),
        "data_quality_label": snapshot.get("data_quality_label"),
        "storage_policy": snapshot.get("storage_policy"),
        "storage_skip_expected": snapshot.get("storage_skip_expected"),
        "next_action": snapshot.get("next_action"),
        "total_trend_status": snapshot.get("total_trend_status"),
        "key_takeaways": snapshot.get("key_takeaways", [])[:4],
        "sector_implications": snapshot.get("sector_implications", [])[:4],
        "warnings": snapshot.get("warnings", [])[:5],
    }

def save_customs_trade_snapshot(runtime, snapshot: dict, settings) -> dict:
    if not snapshot.get("has_valid_data"):
        return {
            **snapshot,
            "storage_skipped": True,
            "storage_skip_reason": str(
                snapshot.get("storage_policy")
                or "실제 수출입 수치가 없어 저장/RAG 반영을 건너뜁니다."
            ),
        }
    storage_date = runtime.current_storage_date()
    vault_dir = runtime.resolve_vault_dir(settings.research_vault_dir)
    markdown = runtime.render_customs_trade_markdown(snapshot, storage_date)
    summary = (
        f"관세청 수출입 동향 {snapshot.get('start_yymm')}~{snapshot.get('end_yymm')}: "
        f"{'; '.join(snapshot.get('key_takeaways', [])[:2]) or '요약 없음'}"
    )
    source_confidence = 0.88 if not snapshot.get("warnings") else 0.72
    storage = runtime.save_research_markdown(
        vault_dir=vault_dir,
        ticker="CUSTOMS",
        report_type="customs-trade-brief",
        markdown=markdown,
        structured_payload=snapshot,
        manifest_entry={
            "summary": summary,
            "source": snapshot.get("source"),
            "source_confidence": source_confidence,
            "tags": ["customs", "trade", "exports", "imports", "inventory", "macro", "sector"],
            "sector_implications": snapshot.get("sector_implications", []),
            "release_schedule": snapshot.get("release_schedule"),
        },
        report_date=storage_date,
        file_suffix=f"{snapshot.get('start_yymm')}-{snapshot.get('end_yymm')}",
    )
    rag_document = runtime.upsert_saved_workflow_rag_document(
        vault_dir=vault_dir,
        storage=storage,
        storage_key="CUSTOMS",
        report_type="customs-trade-brief",
        summary=summary,
        markdown=markdown,
        tags=["customs", "exports", "imports", "inventory", "macro", "sector"],
        source_confidence=source_confidence,
        metadata={
            "source": snapshot.get("source"),
            "source_urls": snapshot.get("source_urls"),
            "release_schedule": snapshot.get("release_schedule"),
            "sector_implications": snapshot.get("sector_implications"),
        },
    )
    return {**snapshot, "storage": storage, "rag_document": rag_document}
