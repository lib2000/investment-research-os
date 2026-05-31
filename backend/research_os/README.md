# Research OS Backend

투자 리서치 시스템의 백엔드 도메인입니다.

## 역할

- 티커 인증과 데이터 스냅샷 생성
- 7개 분석 모듈 실행
- 포트폴리오 계산과 리스크 스캔
- 정보입력, 시장일지, RAG 메모리 저장
- 외부 데이터 프로바이더 연동
- 비용/쿼터 가드

## 현재 분리된 모듈

운영 중인 모듈 경계의 기준 문서는 `docs/structure-map.md`입니다. 이 README는 백엔드 폴더 안에서 빠르게 역할을 확인하기 위한 요약입니다.

- `classification.py`: 자동 분류 시스템 태그, 출처 유형 태그, 범위/근거 태그 표준화 유틸
- `brokerage.py`: 증권사 연동 공통 클라이언트와 상태 추상화
- `customs_trade.py`: 관세청 수출입 빈 응답 비저장 품질 판정
- `daily_recommendations.py`: 매일 추천 1~3위 저장/중복 방지, 사후 추적표, 추천 후보 저장 품질 점수 보정 유틸
- `data_providers.py`: KIS, OpenDART, 가격, 외부 데이터 프로바이더 호출
- `export_utils.py`: 화면 결과 엑셀 다운로드용 순수 XLSX 생성 유틸
- `file_extraction.py`: 첨부 파일명 정리, base64 디코딩, PDF/OCR/Office/텍스트/표 본문 추출 유틸
- `kcif_reports.py`: KCIF 보고서 메타데이터 수집과 시장일지 연결
- `kiwoom_auth.py`: 키움 인증/토큰 상태 확인
- `llm_bridge_status.py`: LLM 응답 저장과 RAG 연결 상태 요약
- `market_journal.py`: 네이버 마감 시황 시장일지 출처 메타데이터
- `models.py`: API 입출력 모델과 도메인 스키마
- `portfolio_analysis_coverage.py`: 포트폴리오별 보유 종목 분석 커버리지와 보강 큐 생성
- `portfolio_import.py`: CSV/JSON/XLSX 포트폴리오 파일 파싱, 국내/해외 통화 추론
- `portfolio_performance.py`: 기간 수익 비교와 가격 갱신 요약
- `portfolio_store.py`: 포트폴리오 저장 키와 정렬 정책
- `portfolio_sync.py`: 키움 국내 잔고 반영, 해외/수동 보유 수량 보호, 동기화 이력 JSONL 저장/조회, 동기화 상태 요약
- `rag_memory.py`: RAG 문서와 thesis snapshot 색인/검색
- `regional_sources.py`: EMERiCs, CSF, KIEP 지역/중국/대외 자료 수집
- `research_memory.py`: Markdown/manifest 기반 리서치 저장소 유틸
- `security.py`: 개발 토큰과 사용자 토큰 검증
- `settings.py`: 환경변수 기반 운영 설정
- `source_url_preview.py`: 웹 본문 미리보기 응답 조립
- `storage_quality.py`: 소프트 보관 정책, 저장 데이터 품질/OCR/본문 보강 판정
- `system_health.py`: 연구 콘솔/데이터 프로바이더 상태 점검 payload 조립, OneDrive/OCR/라우트 안전 확인
- `ticker_registry.py`: 한국/미국 티커 레지스트리 캐시와 회사명 매칭
- `web_capture.py`: 웹 URL 안전성, HTML 본문 추출, 네트워크 재시도/fallback, 언어 감지, 로컬 한국어 분석 메모 변환, URL-only 보관 문구 유틸

## 장기 분리 기준

```text
research_os/
  routers/       # FastAPI 라우터
  services/      # 분석/저장/포트폴리오 서비스
  providers/     # FMP, KIS, DART, Naver, Tavily, Brave 등 외부 데이터
  repositories/  # SQLite/PostgreSQL/research_vault 접근
  schemas/       # API 입출력 모델
```

현재는 빠른 개발을 위해 일부 라우트가 `research_os_main.py`에 모여 있습니다. 새 기능은 위 구조를 기준으로 분리하는 것을 목표로 합니다.
