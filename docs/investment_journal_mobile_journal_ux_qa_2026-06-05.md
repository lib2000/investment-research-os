# InvestmentJournalApp 모바일 일지 UX 검증 기록 - 2026-06-05

## 범위

- Expo 모바일 웹 미리보기 실제 화면 검증
- 일지 초안 `대기 / 전체` 전환 확인
- 작성 완료 일지의 `연결된 체결 상세` 표시 확인
- 360px/390px 모바일 폭 레이아웃 확인

## 실행 환경

- 프로젝트 루트: `C:\Users\lib20\InvestmentJournalApp`
- 백엔드: WSL/Windows 접근용 FastAPI `http://172.17.210.136:8020`
- Expo 웹 미리보기: `http://172.17.210.136:8085`
- 참고: `8085`는 모바일 웹 표준 포트로 정리했다. 기존 `8082`는 외부 WSL 로컬 LLM 브리지 프로세스가 자동 점유한다.

## 확인 결과

- `일지 초안` 기본 화면은 복기 대기 초안만 표시하고, 현재 실데이터 기준 `0건`으로 표시된다.
- `전체` 전환 시 전체 초안 `2건`이 표시된다.
- `order_execution` 초안은 `체결 상세 · 완료 일지에 연결`, 버튼 라벨은 `연결됨`으로 표시된다.
- `trade_journal` 초안은 `매매 요약 · 작성 완료`, 버튼 라벨은 `완료`로 표시된다.
- `작성 완료 일지` 화면은 `연결된 체결 상세 1건`을 표시한다.
- 연결 체결 상세에는 체결 시간, 매매구분/상태, 체결단가, 체결수량이 표시된다.
- 360px 모바일 폭에서 `documentElement.scrollWidth`, `body.scrollWidth`가 모두 `360`으로 확인되어 가로 overflow가 없다.

## 증거 이미지

- `output/playwright/mobile-drafts-all-360.png`
- `output/playwright/mobile-entry-linked-detail-360.png`
- `output/playwright/mobile-entry-linked-detail-390.png`

## 추가 검증

- `npm run typecheck` in `apps/mobile`: 통과
- `python -m unittest tests.test_backend_regressions`: 118개 통과

## 남은 메모

- 현재 검증은 Expo 웹 기준이며, 실제 Expo Go 기기 검증은 별도 수행해야 한다.

## 2026-06-06 포트 정리

- 8082 자동 점유 원인: `/home/lib2000/.openclaw/local-llm/ollama_qwen25_coder_bridge_8082.py`가 `systemd --user` 아래에서 계속 실행된다.
- InvestmentJournalApp 모바일 웹 표준 포트를 `8085`로 정리했다.
- Windows 브라우저 기준 확인 URL은 `http://172.17.210.136:8085`다.
- Windows PowerShell에서 `http://172.17.210.136:8085`, `http://172.17.210.136:8020`, `journal/drafts` API가 모두 HTTP 200으로 확인됐다.
- Playwright에서 일지 탭 진입, `연결된 체결 상세 1건` 표시, 콘솔 에러 0개를 재확인했다.
