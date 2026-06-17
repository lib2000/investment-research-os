from __future__ import annotations


def cumulative_market_patterns(entries: list, market: str) -> tuple[list[str], str]:
    recent = [entry for entry in entries if entry.market == market][-20:]
    if not recent:
        return ["누적 기록이 아직 부족합니다. 오늘 기록을 기준점으로 저장했습니다."], "첫 기록 또는 초기 축적 단계입니다."

    sentiment_counts = {
        name: sum(1 for entry in recent if entry.sentiment == name)
        for name in ["긍정", "혼합", "부정"]
    }
    risk_counts = {
        name: sum(1 for entry in recent if entry.risk_level == name)
        for name in ["낮음", "보통", "높음"]
    }
    tag_counts: dict[str, int] = {}
    for entry in recent:
        for tag in entry.tags:
            tag_counts[tag] = tag_counts.get(tag, 0) + 1
    top_tags = sorted(tag_counts.items(), key=lambda item: item[1], reverse=True)[:5]
    patterns = [
        f"최근 {len(recent)}개 {market} 폐장 기록 기준: 긍정 {sentiment_counts['긍정']}회, 혼합 {sentiment_counts['혼합']}회, 부정 {sentiment_counts['부정']}회입니다.",
        f"리스크 레벨은 낮음 {risk_counts['낮음']}회, 보통 {risk_counts['보통']}회, 높음 {risk_counts['높음']}회로 누적되었습니다.",
    ]
    if top_tags:
        patterns.append(
            "반복 출현 테마: "
            + ", ".join(f"{tag} {count}회" for tag, count in top_tags)
        )
    if risk_counts["높음"] >= 3:
        patterns.append("고위험 장세 기록이 반복되고 있어 신규 포지션은 더 작은 단위로 검증하는 편이 좋습니다.")
    if sentiment_counts["긍정"] >= max(3, sentiment_counts["부정"] + 2):
        patterns.append("긍정 기록이 우세합니다. 다만 과열 신호와 주도주 쏠림을 함께 추적하세요.")
    summary = (
        f"{market} 최근 {len(recent)}회 누적: "
        f"주요 테마 {', '.join(tag for tag, _ in top_tags[:3]) or '미확정'}, "
        f"우세 심리 {max(sentiment_counts, key=sentiment_counts.get)}"
    )
    return patterns, summary
