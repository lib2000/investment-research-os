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

- `models.py`: API 입출력 모델과 도메인 스키마
- `research_memory.py`: Markdown/manifest 기반 리서치 저장소 유틸
- `rag_memory.py`: RAG 문서와 thesis snapshot 색인/검색
- `data_providers.py`: 외부 데이터 프로바이더 클라이언트
- `export_utils.py`: 화면 결과 엑셀 다운로드용 순수 XLSX 생성 유틸
- `web_capture.py`: 웹 URL 안전성, URL-only 보관 문구, 본문 추출 실패 판정 유틸

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
