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

- `analysis_context.py`: 저장 리포트, 논거 스냅샷, RAG 검색 결과를 분석 입력 context로 주입하는 helper
- `analysis_labels.py`: 분석 출력 출처/데이터/매매스타일 표시 라벨과 분석 저장 키 생성 helper
- `classification.py`: 자동 분류 시스템 태그, 출처 유형 태그, 범위/근거 태그 표준화 유틸
- `brokerage.py`: 증권사 연동 공통 클라이언트와 상태 추상화
- `customs_trade.py`: 관세청 수출입 스냅샷 구성, 마크다운 렌더링, 일일 참고자료, 빈 응답 비저장 품질 판정
- `customs_data_provider.py`: 관세청 품목별/총괄 수출입 API client, 응답 파싱, row 정규화/캐시
- `dart_filing_watch.py`: DART 공시 감시 대상 universe, cache/signal, 일일 점검 상태, refresh orchestration
- `dart_watch_exclusions.py`: DART 감시 제외 사유와 중복 제외 entry helper
- `dart_filing_metadata.py`: DART 공시명 기반 중요도/분기 label/cache key/마크다운/refresh 오류 분류 helper
- `dossier_capture_quality.py`: Dossier 입력 캡처 실패 판정과 본문/첨부/URL 품질 상태 helper
- `dossier_similarity.py`: Dossier 중복 판정용 content hash, token set, Jaccard similarity helper
- `dossier_synthesis.py`: Dossier 합성 payload 구성과 Markdown 렌더링 helper
- `daily_recommendation_store.py`: 매일 추천 저장소 경로, JSON 읽기/쓰기, 실행 시각 판정, 추천 record ID 유틸
- `daily_recommendation_evidence.py`: 매일 추천 RAG 근거 문서 정규화, claim 매칭, evidence document 선별 helper
- `daily_recommendation_recent.py`: 매일 추천 최근 1주 자료 인덱스, evidence document 변환, 묶음 표시 helper
- `daily_recommendation_tracking.py`: 매일 추천 사후 추적 milestone, 성과 요약, 투자 상황 문구 helper
- `daily_recommendations.py`: 매일 추천 1~3위 저장/중복 방지, 추천 후보 저장 품질 점수 보정 유틸
- `dashboard_helpers.py`: 종목 대시보드 리포트 요약, tooltip compact, watch item 표시 helper
- `automation_digest_helpers.py`: 리서치 자동화 대시보드 digest 표시 카드, 다음 액션, 우선순위 helper
- `data_provider_utils.py`: 외부 데이터 프로바이더 공통 값 파싱, 비밀값 구성 판정, 오류 메시지 마스킹 유틸
- `data_provider_status_messages.py`: KIS/FMP/외부 보강 provider 상태 표시 문구 helper
- `financial_datasets_data_provider.py`: Financial Datasets 재무 API client와 해외 재무 snapshot provider
- `fmp_data_provider.py`: Financial Modeling Prep API client와 시장/재무 provider
- `finnhub_data_provider.py`: Finnhub 현재가, 실적 캘린더, 회사 뉴스 provider
- `provider_usage.py`: Tavily/Brave 등 외부 프로바이더 무료 한도 사용량 파일 기록 helper
- `data_provider_core.py`: provider 공통 interface, 상태 객체, mock/empty/composite wrapper
- `nps_data_provider.py`: 국민연금 ODCLOUD 보유/대량보유 API client, 캐시, 기관 수급 신호 변환
- `opendart_data_provider.py`: OpenDART corp-code/공시/재무 API client와 한국 종목 재무 provider
- `data_providers.py`: KIS, OpenDART, 가격, NPS와 검색/보강 데이터 프로바이더 호출
- `export_utils.py`: 화면 결과 엑셀 다운로드용 순수 XLSX 생성 유틸
- `file_attachment_utils.py`: 첨부 파일명 정리, base64 디코딩, PDF/이미지 MIME 판정 helper
- `file_image_metadata.py`: PNG/JPEG/WEBP 첨부 이미지 크기 감지 helper
- `file_ocr_runtime.py`: Tesseract OCR 실행 파일/언어팩 탐지와 OCR 처리 제한 상태 helper
- `file_spreadsheet_extraction.py`: XLSX shared string, inline string, 셀 좌표 기반 표 텍스트 추출 helper
- `file_text_extraction.py`: 텍스트/CSV/TSV 첨부 디코딩과 표 미리보기 helper
- `file_extraction_profile.py`: 첨부 본문 추출 결과의 품질/분석 준비도 profile helper
- `file_extraction.py`: PDF/OCR/Office/텍스트/표 본문 추출과 첨부 추출 profile 유틸
- `kcif_report_parsing.py`: KCIF 목록 HTML에서 보고서 메타데이터만 추출하는 parser
- `kcif_reports.py`: KCIF 보고서 수집/상세 신호 분석과 시장일지 연결
- `kiwoom_auth.py`: 키움 인증/토큰 상태 확인
- `kis_data_provider.py`: KIS 토큰/시세 client, 국내·해외 현재가 provider, 한국 종목코드 판정 helper
- `llm_bridge_status.py`: LLM 응답 저장과 RAG 연결 상태 요약
- `market_journal.py`: 네이버 마감 시황 시장일지 출처 메타데이터
- `market_journal_analysis.py`: 시장일지 텍스트 정리, 감정/리스크/태그/행동 가이드 helper
- `market_journal_patterns.py`: 시장일지 누적 패턴/반복 테마 요약 helper
- `news_market_journal.py`: 뉴스 인박스 시장일지 승격, 관심목록 영향, 저장 orchestration
- `market_journal_rendering.py`: 시장일지 저장 Markdown 렌더링 helper
- `naver_market_close_automation.py`: 네이버 국내 마감 시황 자동 반영, 중복 방지, 작업 상태 조립
- `company_ir_config.py`: 공개 IR/SEC 소스 JSON 확장 설정 파싱과 중복 제거 helper
- `telegram_market_journal.py`: 텔레그램 @ehdwl 공개 채널의 미국 시장일지 후보 파싱/선정
- `telegram_market_close_automation.py`: 텔레그램 미국 시장일지 자동 반영, 소급 저장, 중복 방지, 작업 상태 조립
- `web_search_data_provider.py`: Tavily/Brave 검색 기반 보강 데이터 provider와 무료 한도 guard
- `models.py`: API 입출력 모델과 도메인 스키마
- `portfolio_analysis_coverage.py`: 포트폴리오별 보유 종목 분석 커버리지와 보강 큐 생성
- `portfolio_import.py`: CSV/JSON/XLSX 포트폴리오 파일 파싱, 국내/해외 통화 추론
- `portfolio_performance.py`: 기간 수익 비교, 가격 갱신 요약, 목표가 통화/이상치/출처 판정 헬퍼
- `portfolio_policy.py`: 강화학습형 포트폴리오 정책 상태/행동/보상 scaffold와 비중 조정 helper
- `portfolio_store.py`: 포트폴리오 저장 JSON 읽기, 저장 키와 정렬 정책
- `portfolio_sync.py`: 키움 국내 잔고 반영, 해외/수동 보유 수량 보호, 동기화 이력 JSONL 저장/조회, 동기화 상태 요약
- `rag_memory.py`: RAG 문서와 thesis snapshot 색인/검색
- `rag_memory_utils.py`: RAG 문서 ID, JSON/safe 변환, manifest 본문 읽기, 문서 품질 판정 helper
- `rag_search_results.py`: RAG 검색 결과 중복 보고서 compact와 match strength 표시 helper
- `rag_synthesis.py`: 전체 저장 데이터 검색 결과 합성, Markdown 보고서 렌더링, 투자 논거 스냅샷 helper
- `recent_activity.py`: 최근 1주 자료 compact, DART/추천 근거 링크, 저장 데이터 탐색 힌트 helper
- `recent_activity_public_ir.py`: 최근 1주 공개 IR/SEC 자료 compact와 추천 반영 품질 guard helper
- `recent_activity_groups.py`: 최근 1주 자료 category group, 출처 family, 타깃 digest 계산 helper
- `regional_sources.py`: EMERiCs, CSF, KIEP 지역/중국/대외 자료 수집
- `research_memory.py`: Markdown/manifest 기반 리서치 저장소 유틸
- `research_memory_files.py`: 저장 리포트 목록/카드 조립, manifest/sidecar 경로 해석, 마크다운 tail section 갱신 helper
- `security.py`: 개발 토큰과 사용자 토큰 검증
- `settings.py`: 환경변수 기반 운영 설정
- `state_store.py`: `_system` 상태 파일 경로, KST 기준 저장 시각, JSON/JSONL 상태 저장 헬퍼
- `source_url_preview.py`: 웹 본문 미리보기 응답 조립
- `storage_quality.py`: 소프트 보관 정책, 저장 데이터 품질/OCR/본문 보강 판정
- `system_health.py`: 연구 콘솔/데이터 프로바이더 상태 점검 payload 조립, OneDrive/OCR/라우트 안전 확인
- `ticker_registry.py`: 한국/미국 티커 레지스트리 캐시와 회사명 매칭
- `thesis_impact.py`: 투자 논거 영향도 신뢰도 보정, 판정, watch item signal, 마크다운 렌더링 helper
- `thesis_signal_words.py`: 투자 논거 영향도/뉴스 영향 판정에 쓰는 긍정·부정 signal word helper
- `web_capture.py`: 웹 URL 안전성, 네트워크 재시도/fallback, URL-only 보관 문구 유틸
- `web_capture_translation.py`: 해외 웹 본문 언어 감지, 로컬 용어 사전 기반 한국어 분석 digest helper
- `web_article_cleaning.py`: 웹 기사 제목/본문 노이즈 제거와 중복 라인 정리 helper
- `web_text_extraction.py`: HTML/JSON-LD 기사 본문 추출, 제목 정제, 표/실적 행 텍스트화, 기사 노이즈 제거

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
