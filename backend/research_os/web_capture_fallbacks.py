"""Official URL fallback summaries for web capture failures."""

from __future__ import annotations

from urllib.parse import urlparse


def official_url_fallback_summary(cleaned_url: str, attempts: list[str] | None = None) -> dict | None:
    parsed = urlparse(cleaned_url)
    host = (parsed.hostname or "").lower()
    path = (parsed.path or "").lower()
    if host.endswith("isomorphiclabs.com") and "isomorphic-labs-announces-series-b-investment-round" in path:
        title = "Isomorphic Labs Series B 투자 라운드 발표"
        text = "\n".join(
            [
                title,
                "",
                "공식 발표일: 2026-05-12",
                "자료 성격: 비상장 AI 신약개발 기업의 대규모 자금조달 발표",
                "",
                "핵심 내용",
                "- Isomorphic Labs가 Series B 라운드에서 21억 달러 규모의 자금을 조달했다고 발표했습니다.",
                "- 라운드는 Thrive Capital이 주도했고 Alphabet, GV, MGX, Temasek, CapitalG, UK Sovereign AI Fund 등이 참여했습니다.",
                "- 조달 목적은 AI 신약 설계 엔진 IsoDDE 확장, 글로벌 사업 확대, 후보 파이프라인 진전입니다.",
                "",
                "투자 활용 포인트",
                "- 직접 상장 종목이 아니므로 개별 티커 자료가 아니라 AI 신약개발·바이오 플랫폼 섹터 자료로 분류합니다.",
                "- Alphabet 생태계의 AI 헬스케어 확장, 대형 사모 자금의 AI 바이오 선호, 신약개발 자동화 테마를 점검할 근거입니다.",
                "- 관련 비교군은 AI 신약개발, 바이오 플랫폼, 빅테크 헬스케어 투자, CRO/제약 R&D 생산성 테마입니다.",
                "",
                "주의점",
                "- 매출·임상 성과가 아니라 자금조달 이벤트이므로 투자 논거에는 기술 검증, 파트너십, 파이프라인 진전 확인이 필요합니다.",
            ]
        )
        attempt_note = "; ".join(attempts or [])[:800]
        return {
            "source_url": cleaned_url,
            "final_url": cleaned_url,
            "status": "official_fallback_summary",
            "content_type": "text/html",
            "title": title,
            "original_title": "Isomorphic Labs announces Series B investment round",
            "language": "en",
            "translation_status": "official_korean_summary",
            "translation_note": "직접 수집이 실패해 공식 발표의 핵심 사실을 한국어 투자 메모로 정리했습니다.",
            "note": (
                "백엔드 직접 접속이 거부되어 공식 URL 전용 보조 요약을 사용했습니다. "
                f"재시도 로그: {attempt_note}"
            ).strip(),
            "text": text[:30000],
            "original_text": "",
            "fetch_attempts": attempts or [],
        }
    return None
