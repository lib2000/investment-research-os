"""Portfolio policy scaffold helpers."""

from __future__ import annotations

from datetime import date

from . import portfolio_risk_storage
from .models import (
    PolicyAllocationAdjustment,
    PortfolioHolding,
    ReinforcementPortfolioOptimizationRequest,
    ReinforcementPortfolioOptimizationResponse,
)


def build_policy_state_features(
    holdings: list[PortfolioHolding],
    regime_summary: str,
    tags: list[str],
) -> list[str]:
    sectors = sorted({holding.sector for holding in holdings if holding.sector and holding.sector != "Unknown"})
    themes = sorted({tag for holding in holdings for tag in holding.theme_tags})
    return [
        f"시장 상태: {regime_summary}",
        f"보유 종목 수: {len(holdings)}",
        f"섹터 노출: {', '.join(sectors[:8]) or '미분류'}",
        f"테마 노출: {', '.join(themes[:10]) or '미분류'}",
        f"시장 태그: {', '.join(tags[:8]) or '없음'}",
        "가격/수익률, 시장일지, 실적 반응, 리스크 스캔 결과를 상태 변수로 누적 학습합니다.",
    ]


def policy_adjustment_for_holding(
    holding: PortfolioHolding,
    *,
    max_position_weight: float,
    risk_profile: str,
    market_tags: list[str],
) -> PolicyAllocationAdjustment:
    weight = float(holding.weight or 0)
    suggested = weight
    action = "유지"
    reasons: list[str] = []
    profile = risk_profile.lower()
    theme_hits = len(set(holding.theme_tags) & set(market_tags))

    if weight > max_position_weight:
        suggested = min(suggested, max_position_weight)
        action = "축소 후보"
        reasons.append(f"현재 비중 {weight:.1%}가 단일 종목 한도 {max_position_weight:.1%}를 초과")
    if holding.unrealized_return is not None and holding.unrealized_return < -0.18:
        suggested = min(suggested, max(weight * 0.75, 0))
        action = "리스크 축소"
        reasons.append(f"미실현 수익률 {holding.unrealized_return:.1%}로 손실 확대 구간")
    if holding.unrealized_return is not None and holding.unrealized_return > 0.25 and profile in {"conservative", "보수", "보수적"}:
        suggested = min(suggested, weight * 0.85)
        action = "일부 이익 보호"
        reasons.append("보수적 위험 성향에서 큰 수익 포지션의 이익 보호 필요")
    if theme_hits and weight < max_position_weight * 0.75 and action == "유지":
        suggested = min(max_position_weight, weight * 1.1 if weight else max_position_weight * 0.25)
        action = "관찰 후 증액 후보"
        reasons.append(f"시장 태그와 보유 테마가 {theme_hits}개 겹침")
    if not reasons:
        reasons.append("현재 정책 기준에서 강한 증액/축소 신호 없음")

    return PolicyAllocationAdjustment(
        ticker=holding.ticker,
        current_weight=round(weight, 4),
        suggested_weight=round(max(suggested, 0), 4),
        action=action,
        rationale="; ".join(reasons),
    )


def render_reinforcement_policy_markdown(
    response: ReinforcementPortfolioOptimizationResponse,
    portfolio_value: float,
    report_date: date,
) -> str:
    adjustments = "\n".join(
        f"- {item.ticker}: {item.action} | 현재 {item.current_weight:.1%} -> 제안 {item.suggested_weight:.1%} | {item.rationale}"
        for item in response.allocation_adjustments
    ) or "- 조정 후보 없음"
    return f"""---
portfolio_name: {response.portfolio_name}
type: reinforcement-portfolio-optimizer
date: {report_date.isoformat()}
objective: {response.objective}
risk_profile: {response.risk_profile}
---

# {response.portfolio_name} 강화학습형 포트폴리오 정책 최적화

- 학습 모드: {response.learning_mode}
- 포트폴리오 총액: {portfolio_value:,.0f}
- 목표 함수: {response.objective}

## 상태 변수

{chr(10).join(f"- {item}" for item in response.state_features)}

## 행동 공간

{chr(10).join(f"- {item}" for item in response.action_space)}

## 보상 함수

{chr(10).join(f"- {item}" for item in response.reward_function)}

## 정책 요약

{response.learned_policy_summary}

## 비중 조정 후보

{adjustments}

## 리스크 가드레일

{chr(10).join(f"- {item}" for item in response.risk_guardrails)}

## 다음 학습 데이터

{chr(10).join(f"- {item}" for item in response.next_training_data_needed)}
"""


def run_reinforcement_portfolio_policy(
    runtime,
    request: ReinforcementPortfolioOptimizationRequest,
    settings,
) -> ReinforcementPortfolioOptimizationResponse:
    holdings, portfolio_value = runtime.normalize_portfolio_holdings(request.holdings, None)
    if not holdings:
        store = runtime.read_portfolio_store(settings)
        key = runtime.portfolio_store_key(request.portfolio_name)
        saved = store.get("portfolios", {}).get(key)
        if saved:
            saved_portfolio = runtime.SavedPortfolio.model_validate(saved)
            holdings, portfolio_value = runtime.normalize_portfolio_holdings(
                saved_portfolio.holdings,
                saved_portfolio.portfolio_value,
            )

    regime_summary, market_tags = runtime.infer_policy_market_regime(request.market_state, settings)
    state_features = build_policy_state_features(holdings, regime_summary, market_tags)
    action_space = [
        "유지: 기존 비중 유지",
        "관찰 후 증액 후보: 시장 상태와 투자 논거가 강화될 때만 분할 증액",
        "축소 후보: 집중도 또는 손실 확대 위험을 줄이기 위한 비중 축소",
        "리밸런싱: 섹터/테마 쏠림을 낮추고 현금 또는 방어 노출 확보",
        "학습 보류: 데이터 신뢰도 또는 시장 신호가 부족하면 행동하지 않음",
    ]
    reward_function = [
        "위험조정수익률 개선: 수익률 상승보다 변동성·낙폭을 함께 반영",
        "최대낙폭 패널티: 손실 확대 포지션과 고집중 포지션에 음의 보상",
        "논거 일치 보상: 시장일지 태그, 실적 반응, 저장 메모가 같은 방향이면 양의 보상",
        "거래 비용 패널티: 잦은 매매와 근거 없는 회전율을 감점",
        "데이터 품질 패널티: 실제 데이터 부족, 레거시 리포트, 낮은 신뢰도 자료를 감점",
    ]
    allocation_adjustments = [
        policy_adjustment_for_holding(
            holding,
            max_position_weight=request.max_position_weight,
            risk_profile=request.risk_profile,
            market_tags=market_tags,
        )
        for holding in holdings
    ]
    allocation_adjustments.sort(
        key=lambda item: (abs(item.current_weight - item.suggested_weight), item.current_weight),
        reverse=True,
    )
    response = ReinforcementPortfolioOptimizationResponse(
        portfolio_name=request.portfolio_name,
        objective=request.objective,
        risk_profile=request.risk_profile,
        learning_mode="offline_policy_scaffold",
        state_features=state_features,
        action_space=action_space,
        reward_function=reward_function,
        learned_policy_summary=(
            "현재는 실거래 자동 강화학습이 아니라, 누적 시장일지·포트폴리오·실적/뉴스 분석을 "
            "상태/행동/보상 구조로 변환하는 오프라인 정책 학습 준비 단계입니다. 데이터가 쌓이면 "
            "실제 에피소드별 보상 학습으로 확장할 수 있습니다."
        ),
        allocation_adjustments=allocation_adjustments[:20],
        risk_guardrails=[
            f"단일 종목 권장 상한: {request.max_position_weight:.0%}",
            "실거래 자동 집행은 하지 않고, 학습 결과는 후보 행동으로만 표시합니다.",
            "정책 업데이트 전 최신 시장일지, 실적 분석, 포트폴리오 리스크 스캔을 함께 확인합니다.",
            "데이터 공급자가 경고를 반환한 종목은 증액 보상을 제한합니다.",
        ],
        next_training_data_needed=[
            "일별 포트폴리오 평가금액과 현금 비중",
            "시장일지의 심리·리스크·태그와 다음 날 수익률",
            "매매 전략 실행 여부와 실제 진입/청산 결과",
            "실적 발표 전후 주가 반응과 논거 변화",
            "정보입력 메모의 신뢰도와 이후 투자 논거 적중 여부",
        ],
        saved_to_research_memory=request.save_result,
    )
    if request.save_result:
        response = portfolio_risk_storage.save_reinforcement_portfolio_policy(
            runtime.portfolio_risk_storage_runtime(),
            response=response,
            portfolio_name=request.portfolio_name,
            portfolio_value=portfolio_value,
            settings=settings,
        )
    return response
