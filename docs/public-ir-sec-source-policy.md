# 공개 IR/SEC 수집 정책

투자 리서치 OS의 공개 IR/SEC 수집기는 로그인, 자동 전송, 웹 채팅, 유료/제한 본문 우회를 하지 않는다. 앱은 사용자가 입력한 공개 URL을 백엔드의 `POST /api/v1/public-ir-sec/collect`로 전달하고, 저장 상태는 `GET /api/v1/public-ir-sec/status`에서 확인한다.

Firecrawl Monitor 변화 감지는 공개 URL/공개 검색 결과만 대상으로 삼는다. 기본값은 비활성/dry-run이며, monitor 생성 전 registry, schedule, goal, webhook 대상, 예상 payload를 먼저 검토한다. webhook을 켤 때도 비밀 토큰은 backend secret env에만 두고 콘솔/로그에는 configured 여부만 노출한다. `FIRECRAWL_MONITOR_WEBHOOK_SECRET`은 수신 인증 준비 상태이고, registry의 monitor webhook target은 Firecrawl이 변경 이벤트를 이 시스템으로 보내는 발신 설정이므로 둘을 별도로 확인한다.

Monitor 이벤트 저장소는 변경 판단에 필요한 짧은 메타데이터만 남긴다. `monitor.page` 이벤트는 URL, 상태, goal judgment, 의미 있는 변화 요약, 짧은 diff, 라우팅 후보를 저장하고, 긴 원문/비밀키/API 응답 전체는 보관하지 않는다.

Webhook 수신 endpoint는 사용자용 bearer token을 쓰지 않고 별도 `FIRECRAWL_MONITOR_WEBHOOK_SECRET`만 허용한다. secret이 없거나 틀린 요청은 이벤트 저장소에 반영하지 않으며, 원문 payload 대신 상태/사유/짧은 hash만 감사 상태 파일에 남긴다.

## 허용 범위

- `sec.gov`의 공개 공시/문서 페이지
- 회사 공식 IR, 보도자료, 투자자 자료 공개 페이지
- 공개 PDF/HTML로 접근 가능한 투자 설명 자료
- 보유 종목과 관심종목의 회사명, 티커, 섹터가 확인되는 공개 자료

## 제한 및 URL-only 처리

- 로그인, 유료 구독, 권한 확인, 봇 차단, 스크립트 렌더링 제한으로 본문을 충분히 추출하지 못하면 본문 저장을 중단하지 않고 URL/메타데이터 중심 자료로 보관한다.
- 이런 자료에는 `needs_body_copy`, `url_text_unavailable` 같은 품질 신호를 남기고 저장 품질 대시보드와 최근 1주 자료 화면에서 보강 필요 상태를 표시한다.
- 이후 사용자가 공개 본문을 보강했거나 SEC/IR 목록 추출기가 본문을 정상 확보하면 `body_supplemented` 상태로 전환하고 추천 품질 결함에서 제외한다.
- 403/404 또는 중복 범용 자료는 삭제하지 않고 `archived` 상태로 소프트 보관해 이력은 남기되 추천/RAG 활성 자료에서는 제외한다.
- 제한 자료의 본문 전체 복제나 자동 우회 수집은 하지 않는다.

## 시스템 연결

- 저장 키: `PUBLIC_IR_SEC`
- 저장 범위: `research_vault/PUBLIC_IR_SEC`와 manifest/RAG 색인
- 최근 1주 자료: 보유/관심 회사명, 티커, 섹터와 매칭되는 공개 IR/SEC만 표시
- 오늘 한국/미국 추천 1~3위: 최근 1주 공개 IR/SEC가 종목과 직접 연결될 때만 근거 점수와 evidence source에 반영
- 품질 대시보드: 공개 IR/SEC 활성 수, 보관 수, URL-only/본문 보강 필요 수를 별도 집계
