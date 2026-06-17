"""Market journal Markdown rendering helpers."""

from __future__ import annotations


def render_market_close_markdown(runtime, response, storage_date) -> str:
    entry = response.entry
    return f"""---
ticker: {runtime.market_research_key(entry.market)}
type: market-close-review
date: {storage_date.isoformat()}
module: market_close_review
market: {entry.market}
session_date: {entry.session_date}
sentiment: {entry.sentiment}
risk_level: {entry.risk_level}
regime: {entry.regime}
tags: {", ".join(entry.tags)}
---

# {entry.market} 폐장 후 시장 리뷰: {entry.session_date}

## 핵심 평가

- 시장 심리: {entry.sentiment}
- 리스크 레벨: {entry.risk_level}
- 장세 판정: {entry.regime}
- 누적 기록 수: {response.history_count}

## 오늘의 핵심 동인

{chr(10).join(f"- {item}" for item in entry.key_drivers)}

## 네이버 증권 보조 지수

{chr(10).join(f"- {item}" for item in entry.market_index_snapshot) if entry.market_index_snapshot else "- 해당 없음"}

## 섹터/테마 시사점

{chr(10).join(f"- {item}" for item in entry.sector_implications)}

## 시스템 자동 활용 초점

{chr(10).join(f"- {item}" for item in entry.auto_utilization_focus)}

## 관심목록 영향

{chr(10).join(f"- {item}" for item in entry.interest_implications)}

## 포트폴리오 활용

{chr(10).join(f"- {item}" for item in entry.portfolio_actions)}

## 누적 패턴

{chr(10).join(f"- {item}" for item in response.cumulative_patterns)}

## 다음 장 체크포인트

{chr(10).join(f"- {item}" for item in entry.next_session_watch)}

## 첨부 파일

{chr(10).join(f"- {key}: {value}" for key, value in (entry.attachment or {}).items() if key != "extracted_text") if entry.attachment else "- 첨부 파일 없음"}

## 정제된 시장 요약

{entry.raw_summary}
"""
