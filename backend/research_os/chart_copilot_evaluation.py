"""Research-only evaluation helpers for TradingView AI Chart Copilot.

The browser extension is intentionally outside this module.  We persist only
secret-free, human-captured observations and compare them with existing local
backtest summaries.  Nothing in this module can place an order.
"""

from __future__ import annotations

import math
import re
from datetime import datetime
from enum import Enum
from typing import Any, Iterable
from uuid import uuid4
from zoneinfo import ZoneInfo

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


KST = ZoneInfo("Asia/Seoul")
PILOT_SYMBOL_TARGET = 20
PILOT_MIN_DAYS = 14
PILOT_MAX_DAYS = 28
REQUIRED_TIMEFRAMES = ("1D", "4H")
OFFICIAL_COPILOT_URL = "https://www.tradingview.com/blog/en/tradingview-ai-chart-copilot-beta-57730/"

_TICKER_RE = re.compile(r"^[A-Z0-9._-]{1,40}$")
_SENSITIVE_RE = re.compile(
    r"(?i)(?:authorization\s*:|bearer\s+[a-z0-9._-]+|api[_ -]?key\s*[:=]|"
    r"access[_ -]?token\s*[:=]|app[_ -]?(?:key|secret)\s*[:=]|비밀번호\s*[:=]|"
    r"sk-[a-z0-9_-]{16,}|gh(?:p|o|u|s|r)_[a-z0-9_-]{16,}|github_pat_[a-z0-9_-]{16,}|"
    r"aiza[a-z0-9_-]{20,}|\b\d{6,12}:[a-z0-9_-]{30,}\b|"
    r"\beyj[a-z0-9_-]{10,}\.[a-z0-9_-]{10,}\.[a-z0-9_-]{10,}\b)"
)
_TIMEFRAME_ALIASES = {
    "D": "1D",
    "1D": "1D",
    "DAILY": "1D",
    "일봉": "1D",
    "4H": "4H",
    "240M": "4H",
    "4시간": "4H",
    "4시간봉": "4H",
}


class PromptProfile(str, Enum):
    CHART_ANALYZER = "chart_analyzer"
    TRADING_MENTOR_ANALYSIS = "trading_mentor_analysis"
    TRADING_MENTOR_INDICATOR = "trading_mentor_indicator"
    TRADE_SETUP_ANALYZER = "trade_setup_analyzer"


class MarketRegime(str, Enum):
    TRENDING = "trending"
    RANGEBOUND = "rangebound"
    UNCLEAR = "unclear"


class ResearchDecision(str, Enum):
    LONG = "long"
    SHORT = "short"
    NO_TRADE = "no_trade"
    UNCLEAR = "unclear"


class HumanVerdict(str, Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"


class ChartCopilotEvaluationRequest(BaseModel):
    """Secret-free observation copied by a human from Chart Copilot."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    ticker: str = Field(min_length=1, max_length=40)
    market: str = Field(default="AUTO", min_length=1, max_length=20)
    analysis_as_of: datetime
    prompt_profile: PromptProfile = PromptProfile.CHART_ANALYZER
    prompt_version: str = Field(default="x10think-chart-copilot-v1", min_length=1, max_length=80)
    model_disclosure: str = Field(default="not_disclosed", min_length=1, max_length=80)
    timeframes: list[str] = Field(default_factory=lambda: list(REQUIRED_TIMEFRAMES), min_length=1, max_length=2)
    regime: MarketRegime = MarketRegime.UNCLEAR
    decision: ResearchDecision = ResearchDecision.NO_TRADE
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    support_levels: list[float] = Field(default_factory=list, max_length=12)
    resistance_levels: list[float] = Field(default_factory=list, max_length=12)
    entry_price: float | None = Field(default=None, gt=0)
    stop_price: float | None = Field(default=None, gt=0)
    target_price: float | None = Field(default=None, gt=0)
    evidence: list[str] = Field(min_length=1, max_length=12)
    invalidation: str = Field(default="", max_length=1200)
    alternate_scenario: str = Field(default="", max_length=1200)
    missing_data: list[str] = Field(default_factory=list, max_length=12)
    human_verdict: HumanVerdict = HumanVerdict.PENDING
    backtest_run_id: str | None = Field(default=None, max_length=120)

    @field_validator("ticker")
    @classmethod
    def normalize_ticker(cls, value: str) -> str:
        ticker = value.strip().upper()
        if not _TICKER_RE.fullmatch(ticker):
            raise ValueError("ticker는 영문, 숫자, 점, 밑줄 또는 하이픈만 사용할 수 있습니다.")
        return ticker

    @field_validator("market")
    @classmethod
    def normalize_market(cls, value: str) -> str:
        return value.strip().upper()

    @field_validator("timeframes")
    @classmethod
    def normalize_timeframes(cls, values: list[str]) -> list[str]:
        normalized: list[str] = []
        for value in values:
            timeframe = _TIMEFRAME_ALIASES.get(str(value).strip().upper())
            if timeframe is None:
                raise ValueError("파일럿 시간봉은 1D와 4H만 허용합니다.")
            if timeframe not in normalized:
                normalized.append(timeframe)
        if not normalized:
            raise ValueError("최소 한 개의 시간봉이 필요합니다.")
        return normalized

    @field_validator("support_levels", "resistance_levels")
    @classmethod
    def validate_levels(cls, values: list[float]) -> list[float]:
        levels = sorted({float(value) for value in values})
        if any(not math.isfinite(value) or value <= 0 for value in levels):
            raise ValueError("가격 레벨은 0보다 큰 유한수여야 합니다.")
        return levels

    @field_validator("evidence", "missing_data")
    @classmethod
    def clean_text_rows(cls, values: list[str]) -> list[str]:
        rows = list(dict.fromkeys(str(value).strip() for value in values if str(value).strip()))
        if any(len(row) > 500 for row in rows):
            raise ValueError("근거와 누락 데이터 항목은 각각 500자 이하여야 합니다.")
        return rows

    @model_validator(mode="after")
    def enforce_research_only_payload(self) -> "ChartCopilotEvaluationRequest":
        if not self.evidence:
            raise ValueError("확인 가능한 분석 근거를 한 개 이상 입력하세요.")
        if self.decision == ResearchDecision.NO_TRADE and any(
            value is not None for value in (self.entry_price, self.stop_price, self.target_price)
        ):
            raise ValueError("no_trade 기록에는 진입가, 손절가, 목표가를 저장하지 않습니다.")
        text_fields = [
            self.prompt_version,
            self.model_disclosure,
            self.invalidation,
            self.alternate_scenario,
            *self.evidence,
            *self.missing_data,
        ]
        if _SENSITIVE_RE.search("\n".join(text_fields)):
            raise ValueError("인증정보로 보이는 문자열은 Chart Copilot 평가에 저장할 수 없습니다.")
        return self


def safe_prompt_template() -> str:
    """Return the project-owned prompt used for consistent manual captures."""

    return (
        "{ticker} ({market}) 차트를 1D와 4H로 분석하세요. 분석 기준 시각과 사용한 가격 구간을 먼저 밝히고, "
        "일봉 시장 국면을 trending/rangebound/unclear 중 하나로 분류하되 계산 근거를 제시하세요. "
        "확인 가능한 스윙 고저점과 지지·저항 가격을 수치로 제시하고 각 레벨의 근거 시점을 설명하세요. "
        "거래 설정이 불충분하면 반드시 no_trade를 선택하세요. 설정이 있을 때만 방향, 진입가, 손절가, "
        "목표가와 계산된 손익비를 제시하세요. 무효화 조건, 반대 시나리오, 누락 데이터와 불확실성을 별도로 "
        "적으세요. 계좌·보유수량·인증정보를 요구하거나 주문·알림을 생성하지 마세요."
    )


def _analysis_timestamp(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=KST)
    return value.astimezone(KST).replace(microsecond=0).isoformat()


def _safe_float(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def calculate_risk_reward(payload: ChartCopilotEvaluationRequest) -> float | None:
    """Calculate declared setup R:R without inferring any missing price."""

    entry, stop, target = payload.entry_price, payload.stop_price, payload.target_price
    if entry is None or stop is None or target is None:
        return None
    if payload.decision == ResearchDecision.LONG:
        risk, reward = entry - stop, target - entry
    elif payload.decision == ResearchDecision.SHORT:
        risk, reward = stop - entry, entry - target
    else:
        return None
    if risk <= 0 or reward <= 0:
        return None
    return round(reward / risk, 4)


def _matching_backtest(
    payload: ChartCopilotEvaluationRequest,
    backtest_runs: Iterable[dict[str, Any]],
) -> dict[str, Any] | None:
    requested_run_id = str(payload.backtest_run_id or "").strip()
    for item in backtest_runs:
        if not isinstance(item, dict):
            continue
        if requested_run_id and str(item.get("run_id") or "") != requested_run_id:
            continue
        symbols = {str(symbol).strip().upper() for symbol in item.get("symbols") or []}
        if payload.ticker not in symbols:
            continue
        return item
    return None


def _baseline_summary(item: dict[str, Any] | None) -> dict[str, Any]:
    if item is None:
        return {
            "status": "unlinked",
            "message": "일치하는 저장 백테스트가 없어 예측 성능을 판단하지 않습니다.",
        }
    total_return = _safe_float(item.get("total_return"))
    return {
        "status": "linked",
        "run_id": str(item.get("run_id") or ""),
        "strategy_name": str(item.get("strategy_name") or "전략"),
        "start_date": item.get("start_date"),
        "end_date": item.get("end_date"),
        "total_return": total_return,
        "max_drawdown": _safe_float(item.get("max_drawdown")),
        "win_rate": _safe_float(item.get("win_rate")),
        "trades_count": max(0, int(item.get("trades_count") or 0)),
        "captured_at": item.get("captured_at") or item.get("saved_at"),
        "interpretation": (
            "historical_strategy_positive"
            if total_return is not None and total_return > 0
            else "historical_strategy_negative"
            if total_return is not None and total_return < 0
            else "historical_strategy_flat_or_unknown"
        ),
        "message": "과거 전략 결과를 연결했지만 현재 Copilot 방향과 동일한 전략이라는 뜻은 아닙니다.",
    }


def build_chart_copilot_evaluation(
    payload: ChartCopilotEvaluationRequest,
    *,
    backtest_runs: Iterable[dict[str, Any]] = (),
    captured_at: datetime | None = None,
) -> dict[str, Any]:
    """Build a calibrated, secret-free evaluation record."""

    backtest = _matching_backtest(payload, backtest_runs)
    baseline = _baseline_summary(backtest)
    risk_reward = calculate_risk_reward(payload)
    issues: list[str] = []
    score = 0

    if set(REQUIRED_TIMEFRAMES).issubset(payload.timeframes):
        score += 10
    else:
        issues.append("1D와 4H 중 누락된 시간봉이 있습니다.")
    score += 10  # timestamp and prompt version are schema-required

    score += min(5, len(payload.evidence))
    if payload.invalidation:
        score += 5
    else:
        issues.append("무효화 조건이 비어 있습니다.")
    if payload.alternate_scenario:
        score += 5
    else:
        issues.append("반대 시나리오가 비어 있습니다.")
    if payload.missing_data:
        score += 5
    else:
        issues.append("누락 데이터가 없더라도 '없음'으로 명시해야 합니다.")

    if payload.decision == ResearchDecision.NO_TRADE:
        score += 20
    elif risk_reward is None:
        issues.append("진입·손절·목표 방향이 일관되지 않아 손익비를 계산할 수 없습니다.")
    else:
        score += 15
        if risk_reward >= 2:
            score += 5
        else:
            issues.append("계산된 손익비가 파일럿 기준 2.0 미만입니다.")

    if baseline["status"] == "linked":
        score += 20
    else:
        issues.append("같은 종목의 결정론적 백테스트가 연결되지 않았습니다.")

    if payload.human_verdict != HumanVerdict.PENDING:
        score += 20
    else:
        issues.append("사람 검토가 아직 완료되지 않았습니다.")

    if payload.human_verdict == HumanVerdict.REJECTED:
        review_status = "rejected"
    elif issues:
        review_status = "needs_review" if payload.human_verdict == HumanVerdict.PENDING else "reviewed_with_gaps"
    else:
        review_status = "reviewed"

    now = captured_at or datetime.now(KST)
    if now.tzinfo is None:
        now = now.replace(tzinfo=KST)
    record = payload.model_dump(mode="json")
    record.update(
        {
            "evaluation_id": f"tvcp-{uuid4().hex[:16]}",
            "source": "tradingview_ai_chart_copilot_manual_capture",
            "analysis_as_of": _analysis_timestamp(payload.analysis_as_of),
            "captured_at": now.astimezone(KST).replace(microsecond=0).isoformat(),
            "risk_reward": risk_reward,
            "documentation_quality_score": min(100, score),
            "score_meaning": "documentation_quality_not_prediction_confidence",
            "evidence_strength": (
                "medium"
                if baseline["status"] == "linked"
                and set(REQUIRED_TIMEFRAMES).issubset(payload.timeframes)
                and payload.invalidation
                and payload.alternate_scenario
                else "low"
            ),
            "review_status": review_status,
            "issues": issues,
            "baseline": baseline,
            "investment_use": "research_only",
            "live_order_allowed": False,
        }
    )
    return record


def _parse_record_time(value: Any) -> datetime | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=KST)
    return parsed.astimezone(KST)


def build_chart_copilot_pilot_status(
    evaluations: Iterable[dict[str, Any]],
    *,
    target_tickers: Iterable[dict[str, str]] = (),
    now: datetime | None = None,
) -> dict[str, Any]:
    """Summarize cohort coverage without claiming trading accuracy."""

    targets: list[dict[str, str]] = []
    seen_targets: set[str] = set()
    for item in target_tickers:
        ticker = str(item.get("ticker") or "").strip().upper()
        if not _TICKER_RE.fullmatch(ticker) or ticker in seen_targets:
            continue
        seen_targets.add(ticker)
        targets.append({"ticker": ticker, "name": str(item.get("name") or ticker).strip() or ticker})
        if len(targets) >= PILOT_SYMBOL_TARGET:
            break

    records = [item for item in evaluations if isinstance(item, dict)]
    records.sort(key=lambda item: str(item.get("captured_at") or ""), reverse=True)
    target_set = {item["ticker"] for item in targets}
    latest_pairs: dict[tuple[str, str], dict[str, Any]] = {}
    dates: list[datetime] = []
    for item in records:
        ticker = str(item.get("ticker") or "").strip().upper()
        if target_set and ticker not in target_set:
            continue
        parsed = _parse_record_time(item.get("analysis_as_of") or item.get("captured_at"))
        if parsed is not None:
            dates.append(parsed)
        for timeframe in item.get("timeframes") or []:
            normalized = _TIMEFRAME_ALIASES.get(str(timeframe).strip().upper())
            if normalized is not None:
                latest_pairs.setdefault((ticker, normalized), item)

    coverage: list[dict[str, Any]] = []
    complete_tickers = 0
    reviewed_pairs = 0
    for target in targets:
        ticker = target["ticker"]
        frames = [timeframe for timeframe in REQUIRED_TIMEFRAMES if (ticker, timeframe) in latest_pairs]
        reviewed = [
            timeframe
            for timeframe in frames
            if str(latest_pairs[(ticker, timeframe)].get("human_verdict") or "pending") != HumanVerdict.PENDING.value
        ]
        if len(frames) == len(REQUIRED_TIMEFRAMES):
            complete_tickers += 1
        reviewed_pairs += len(reviewed)
        coverage.append({**target, "timeframes": frames, "reviewed_timeframes": reviewed, "complete": len(frames) == 2})

    today = now or datetime.now(KST)
    if today.tzinfo is None:
        today = today.replace(tzinfo=KST)
    elapsed_days = 0
    if dates:
        elapsed_days = max(1, (today.astimezone(KST).date() - min(dates).date()).days + 1)

    expected_pairs = PILOT_SYMBOL_TARGET * len(REQUIRED_TIMEFRAMES)
    captured_pairs = len(latest_pairs)
    universe_ready = len(targets) >= PILOT_SYMBOL_TARGET
    coverage_ready = complete_tickers >= PILOT_SYMBOL_TARGET
    window_ready = elapsed_days >= PILOT_MIN_DAYS
    review_ready = reviewed_pairs >= expected_pairs
    ready_for_review = universe_ready and coverage_ready and window_ready and review_ready
    if ready_for_review:
        status = "ready_for_review"
    elif elapsed_days > PILOT_MAX_DAYS:
        status = "needs_attention"
    elif records:
        status = "collecting"
    else:
        status = "not_started"

    return {
        "status": status,
        "ready_for_review": ready_for_review,
        "research_only": True,
        "target_symbol_count": PILOT_SYMBOL_TARGET,
        "available_target_count": len(targets),
        "complete_ticker_count": complete_tickers,
        "required_timeframes": list(REQUIRED_TIMEFRAMES),
        "expected_pair_count": expected_pairs,
        "captured_pair_count": captured_pairs,
        "reviewed_pair_count": reviewed_pairs,
        "elapsed_days": elapsed_days,
        "minimum_observation_days": PILOT_MIN_DAYS,
        "recommended_max_days": PILOT_MAX_DAYS,
        "coverage_percent": round(min(1.0, captured_pairs / expected_pairs) * 100, 1),
        "targets": coverage,
        "prompt_template": safe_prompt_template(),
        "prompt_version": "x10think-chart-copilot-v1",
        "official_copilot_url": OFFICIAL_COPILOT_URL,
        "message": (
            "파일럿 검토 조건을 충족했습니다. 결과는 사람 검토용이며 주문 신호가 아닙니다."
            if ready_for_review
            else "1D·4H 기록, 최소 14일 관찰, 백테스트 연결과 사람 검토를 계속 수집하세요."
        ),
    }
