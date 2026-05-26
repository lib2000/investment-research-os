"""Helpers for Korea Customs trade-data quality policy."""

from __future__ import annotations


CUSTOMS_VALID_STORAGE_POLICY = (
    "실제 수출입 수치가 있는 행만 research_vault/CUSTOMS와 RAG 색인에 저장합니다."
)
CUSTOMS_EMPTY_STORAGE_POLICY = (
    "실제 수출입 수치가 없는 빈 응답과 서비스 상태 메시지는 저장/RAG 반영하지 않습니다."
)


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
