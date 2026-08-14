# 실적 일정·DART·IR·Dossier 통합 점검

실적 일정, DART 공시, 공개 IR/SEC, 리서치 자동화, Dossier 후보는 모두 사용자 인증이 필요한 보호 API다. 운영 점검이나 OpenClaw 답변에서는 개별 URL을 추측해 호출하지 않고 다음 통합 점검기를 사용한다.

```powershell
python tools\check_research_evidence_pipeline.py --json --strict
```

점검과 안전한 데이터 갱신을 함께 수행하려면 다음 명령을 사용한다. 이 작업은 리서치 자료만 갱신하며 주문이나 외부 메시지를 실행하지 않는다.

```powershell
python tools\check_research_evidence_pipeline.py --refresh --write-state --json --strict
```

점검기는 `INVESTMENT_RESEARCH_DEV_USER_TOKEN`, `DEV_USER_TOKEN`, `backend/.env` 순으로 개발 토큰을 찾고 모든 보호 API에 `Authorization: Bearer ...`를 자동으로 첨부한다. 토큰 값은 출력하거나 상태 파일에 저장하지 않는다.

정식 경로는 다음과 같다.

- 실적 일정: `GET /api/v1/earnings-calendar/status`, `POST /api/v1/earnings-calendar/refresh`
- DART: `GET /api/v1/dart/filings/status`, `POST /api/v1/dart/filings/refresh`
- 기업 IR: `GET /api/v1/company-ir-sources/watch?refresh=false`, `POST /api/v1/company-ir-sources/refresh`
- 공개 IR/SEC: `GET /api/v1/public-ir-sec/status`
- 자동화: `GET /api/v1/research-automation/status`
- Dossier 중복 리뷰/후보: `GET|POST /api/v1/research-automation/dedupes/review`, `POST /api/v1/research-automation/dedupes/refresh-dossiers`

과거 호출자가 사용하던 `/api/v1/dart-filings/status`, `/api/v1/dart-filings/refresh`, `/api/v1/company-ir-sources/status`는 인증을 유지한 호환 경로로 제공한다. 신규 코드는 반드시 정식 경로를 사용한다.

## 상태 판정

- `not_applicable`: ETF/ETN/펀드처럼 개별 기업 실적 일정이 적용되지 않는 자산의 정상 분류다.
- `fallback_unavailable`: 국내 기업 실적 일정을 외부 공급자와 DART fallback 모두에서 확보하지 못한 차단 문제다.
- IR 원천 일부의 `403` 또는 timeout: 저장된 관련 IR 자료가 있으면 경고로 보고하며, 전체 IR 상태를 조회 실패로 오판하지 않는다.
- Dossier `candidate_count=0`: 후보 확인 불가가 아니라 현재 재합성 대기 후보가 없다는 뜻이다.

비밀정보가 제거된 최신 결과는 `research_vault/_system/research_evidence_pipeline_status.json`에 저장되고 OpenClaw 첫 읽기 패킷에 포함된다.
