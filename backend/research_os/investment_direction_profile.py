"""User-defined investment direction profile for daily recommendation scoring."""

from __future__ import annotations

from typing import Any


PROFILE_SOURCE_ID = "user-pasted-research-2026-06-14"


INVESTMENT_DIRECTION_THEMES: list[dict[str, Any]] = [
    {
        "key": "ai_power_bottleneck",
        "label": "AI 전력 병목",
        "points": 8,
        "keywords": [
            "aidc",
            "bloom",
            "oracle",
            "orcl",
            "sofc",
            "fuel cell",
            "microgrid",
            "gas turbine",
            "data center power",
            "데이터센터",
            "전력",
            "전력망",
            "가스터빈",
            "연료전지",
            "마이크로그리드",
            "블룸",
            "오라클",
            "두산퓨얼셀",
            "미코",
            "한선엔지니어링",
            "지엔씨에너지",
            "sk이터닉스",
            "sk에코플랜트",
        ],
        "reason": "AI 데이터센터의 병목이 GPU에서 전력 확보와 현장발전으로 확장되는 투자 방향과 연결됩니다.",
        "evidence": "첨부 투자 방향: 전력·가스·SOFC·마이크로그리드가 AI 토큰 팩토리의 1차 병목으로 분류됨",
        "risk": "체크포인트: 가스터빈 납기 단축, 전력망 접속 지연 완화, 천연가스 가격 급등 시 전력 병목 프리미엄을 재검토하세요.",
    },
    {
        "key": "ai_semiconductor_bottleneck",
        "label": "AI 반도체 2차 병목",
        "points": 8,
        "keywords": [
            "hbm",
            "cowos",
            "300mm",
            "wafer",
            "silicon photonics",
            "cpo",
            "advanced packaging",
            "sumco",
            "shin-etsu",
            "resonac",
            "mitsubishi gas chemical",
            "mitsui kinzoku",
            "웨이퍼",
            "실리콘 포토닉스",
            "첨단 패키징",
            "패키징",
            "신에쓰",
            "레조낙",
            "sk실트론",
            "sk하이닉스",
            "삼성전자",
            "한솔케미칼",
            "동진쎄미켐",
            "티씨케이",
        ],
        "reason": "AI 수요가 HBM·CoWoS·300mm 웨이퍼·패키징 소재 소비를 동시에 늘리는 2차 AI 수혜 방향과 연결됩니다.",
        "evidence": "첨부 투자 방향: GPU 완제품보다 웨이퍼·HBM·CoWoS·패키징 소재 같은 물리 공급망 병목을 우선 점검",
        "risk": "체크포인트: AI CAPEX 둔화, 웨이퍼 증설 가속, 엔화 강세와 소재 가격 하락 신호를 함께 확인하세요.",
    },
    {
        "key": "supply_chain_inflation",
        "label": "공급망 인플레 방어",
        "points": 5,
        "keywords": [
            "gscpi",
            "ppi",
            "stage 1",
            "stage 3",
            "stage 4",
            "inflation",
            "supply chain",
            "treasury yield",
            "oil",
            "국채금리",
            "금리",
            "인플레",
            "공급망",
            "원자재",
            "유가",
            "가격 전가",
            "가격결정력",
        ],
        "reason": "국채금리 상승과 공급망 물가 전이가 재개될 때 가격 전가력과 병목 공급자를 우선하는 방향과 연결됩니다.",
        "evidence": "첨부 투자 방향: GSCPI, PPI Stage gap, 장기금리와 유가를 매일 리스크 트리거로 점검",
        "risk": "체크포인트: 미국 30년물 금리, 유가, GSCPI, PPI Stage 1-4 격차가 동시에 상승하면 장기 듀레이션 노출을 낮추세요.",
    },
    {
        "key": "china_compute_factor",
        "label": "중국 산력 금융화",
        "points": 5,
        "keywords": [
            "maas",
            "vpp",
            "token",
            "compute exchange",
            "compute power",
            "baidu",
            "alibaba",
            "tencent",
            "산력",
            "토큰",
            "컴퓨팅 파워",
            "바이두",
            "알리바바",
            "텐센트",
            "중국 ai",
        ],
        "reason": "AI 인프라가 GPU 보유에서 산력 유통·가격 발견·API 수익화 레이어로 이동하는 방향과 연결됩니다.",
        "evidence": "첨부 투자 방향: 중국 AI 산력은 GPU보다 MaaS·AIDC·VPP·토큰 수익화 지표를 우선 확인",
        "risk": "체크포인트: 미중 AI 칩 수출 규제, 토큰 수요의 매출 전환 속도, AIDC 가동률과 전력 원가를 확인하세요.",
    },
]


def _candidate_profile_text(candidate: dict[str, Any]) -> str:
    parts: list[str] = [
        str(candidate.get("ticker") or ""),
        str(candidate.get("company_name") or ""),
    ]
    for field in ("reasons", "evidence_sources", "risk_notes", "portfolio_context", "quality_flags"):
        values = candidate.get(field)
        if isinstance(values, list):
            parts.extend(str(value or "") for value in values)
        elif values:
            parts.append(str(values))
    return " ".join(parts).lower()


def matched_investment_direction_themes(candidate: dict[str, Any]) -> list[dict[str, Any]]:
    haystack = _candidate_profile_text(candidate)
    matches: list[dict[str, Any]] = []
    for theme in INVESTMENT_DIRECTION_THEMES:
        keywords = [str(keyword).lower() for keyword in theme.get("keywords", [])]
        matched_keywords = [keyword for keyword in keywords if keyword and keyword in haystack]
        if matched_keywords:
            matches.append({**theme, "matched_keywords": matched_keywords[:5]})
    return matches


def apply_investment_direction_profile(candidate: dict[str, Any]) -> dict[str, Any]:
    """Attach the pasted investment direction profile to matching candidates."""
    themes = matched_investment_direction_themes(candidate)
    if not themes:
        return candidate

    total_points = 0
    for theme in themes[:3]:
        points = int(theme.get("points") or 0)
        total_points += points
        candidate["score"] = int(candidate.get("score") or 0) + points
        candidate.setdefault("score_components", []).append(
            {"label": f"첨부 투자 방향: {theme['label']}", "points": points}
        )
        candidate.setdefault("reasons", []).append(str(theme.get("reason") or ""))
        candidate.setdefault("evidence_sources", []).append(str(theme.get("evidence") or ""))
        candidate.setdefault("risk_notes", []).append(str(theme.get("risk") or ""))

    candidate["investment_direction_profile"] = {
        "source_id": PROFILE_SOURCE_ID,
        "summary": "AI 물리 병목, 공급망 인플레, 중국 산력 금융화 프레임을 일일 추천 후보 평가에 반영",
        "matched_theme_count": len(themes),
        "score_bonus": total_points,
        "themes": [
            {
                "key": theme.get("key"),
                "label": theme.get("label"),
                "matched_keywords": theme.get("matched_keywords") or [],
            }
            for theme in themes[:4]
        ],
        "watch_triggers": [
            "미국 30년물 금리와 유가가 동시에 상승하면 장기 듀레이션·고PER 노출 축소",
            "가스터빈 납기 정상화 또는 전력망 접속 완화 시 SOFC/현장발전 프리미엄 재점검",
            "AI CAPEX 둔화 또는 웨이퍼 증설 가속 시 2차 AI 소재 비중 재검토",
            "GSCPI와 PPI Stage 1-4 격차가 동반 상승하면 공급망 인플레 방어 모드 강화",
        ],
    }
    candidate.setdefault("quality_flags", []).append("첨부 투자 방향 프로필 반영")
    return candidate
