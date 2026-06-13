"""Helpers for portfolio intelligent table scoring."""

from __future__ import annotations


def build_readiness_summary(
    *,
    verified: bool,
    current_price,
    memory_count: int,
    thesis_connected: bool,
    target_price,
    week52_high,
    target_upside,
    week52_proximity,
) -> dict:
    readiness_score = 0
    readiness_score += 20 if verified else 0
    readiness_score += 20 if current_price is not None else 0
    readiness_score += 20 if memory_count > 0 else 0
    readiness_score += 20 if thesis_connected else 0
    readiness_score += 10 if target_price is not None else 0
    readiness_score += 10 if week52_high is not None else 0
    if not verified:
        next_action = "공식 티커 인증을 먼저 보강"
    elif current_price is None:
        next_action = "현재가 자동 입력 상태 확인"
    elif not thesis_connected:
        next_action = "팀 리포트로 기준 투자 논거 생성"
    elif memory_count < 3:
        next_action = "정보입력에 뉴스·리포트 추가 저장"
    elif target_price is None:
        next_action = "매매전략에서 목표가·손절가 보강"
    elif week52_high is None:
        next_action = "차트분석으로 52주 위치 확인"
    elif target_upside is not None and target_upside <= 0.05:
        next_action = "목표가 근접: 일부 이익실현 또는 목표 재점검"
    elif week52_proximity is not None and week52_proximity >= 0.95:
        next_action = "52주 고점권: 추격매수보다 변동성 확인"
    else:
        next_action = "새 자료 유입 시 논거 변화만 갱신"
    return {
        "data_readiness_score": round(readiness_score / 100, 4),
        "next_action": next_action,
    }
