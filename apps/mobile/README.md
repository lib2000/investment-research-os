# Mobile App

이 폴더는 Expo/React Native 모바일 앱 이관 대상입니다.

현재 웹 미리보기 코드는 `mobile_app`에 남아 있으며, 이 폴더는 네이티브 앱 전환을 위한 Expo + TypeScript + TanStack Query 골격입니다. 모바일 앱은 백엔드 API만 호출하고, 증권사 키나 외부 API 키를 저장하지 않습니다.

## 실행

```powershell
cd C:\Users\lib20\InvestmentJournalApp
.\tools\start_backend.ps1
.\tools\start_mobile_web.ps1
```

웹 미리보기 주소는 `http://localhost:8082`입니다. `start_mobile_web.ps1`은 프로젝트 루트 검증 후 `EXPO_PUBLIC_API_BASE_URL=http://127.0.0.1:8010`을 설정해서 Expo를 실행합니다.

빈 화면이 보이거나 8082 포트가 이미 사용 중이면 Metro 잔류 프로세스와 캐시를 같이 정리해서 실행합니다.

```powershell
cd C:\Users\lib20\InvestmentJournalApp
.\tools\start_mobile_web.ps1 -StopExistingPortProcess -ClearCache
```

서버와 웹 미리보기가 떠 있는지 빠르게 확인합니다.

```powershell
cd C:\Users\lib20\InvestmentJournalApp
.\tools\smoke_mobile_web.ps1
```

이 스모크 테스트는 백엔드 루트, 포트폴리오, 분석, CSV 템플릿 API, 모바일 root HTML을 함께 확인합니다.
CSV 템플릿 API만 404인 경우에는 오래된 백엔드가 8010 포트를 잡고 있을 가능성과 복구 명령을 함께 안내합니다.

빈 화면, 404, 포트 충돌처럼 원인이 헷갈릴 때는 현재 포트 주인과 핵심 API 응답을 먼저 확인합니다. CSV 템플릿 API도 함께 확인하므로 오래된 백엔드 프로세스가 새 라우트를 반영하지 못한 상태를 찾기 쉽습니다.

```powershell
.\tools\status_dev_servers.ps1
```

자동화나 엄격한 점검에서 실패 exit code가 필요하면 `-Strict`를 붙입니다.

```powershell
.\tools\status_dev_servers.ps1 -Strict
```

8010의 오래된 백엔드 프로세스를 정리하고 새 라우트까지 검증하며 다시 띄우려면 아래 스크립트를 사용합니다.

```powershell
.\tools\restart_backend_verified.ps1
```

개발 서버를 정리할 때는 아래 스크립트로 8010/8082 포트만 종료합니다.

```powershell
.\tools\stop_dev_servers.ps1
```

실제 종료 전에 어떤 프로세스가 잡히는지만 보려면 `-DryRun`을 붙입니다. 기본 개발 포트가 아닌 포트를 직접 지정한 경우에는 `python`, `node`, `pwsh`, `powershell` 같은 개발 프로세스만 종료 대상이 되며, 다른 프로세스를 강제로 종료하려면 `-ForceAnyProcess`를 명시해야 합니다.

```powershell
.\tools\stop_dev_servers.ps1 -DryRun
```

분석 차트용 샘플 데이터 집계도 확인할 수 있습니다. 기본 실행은 임시 CSV 샘플을 가져온 뒤 바로 삭제합니다.

```powershell
cd C:\Users\lib20\InvestmentJournalApp
.\tools\smoke_mobile_analytics_sample.ps1
```

CSV 가져오기와 분석 집계의 백엔드 계약만 빠르게 확인하려면 아래 회귀 테스트를 실행합니다. 실제 DB 대신 임시 SQLite DB를 사용합니다.

```powershell
python -m unittest tests.test_backend_regressions.InvestmentJournalManualImportTests
```

모바일 스택 전체 검증은 통합 스크립트로 실행할 수 있습니다. 서버가 떠 있지 않은 상태에서 코드/빌드 검증만 할 때는 `-SkipLiveSmoke`를 사용합니다.

```powershell
.\tools\verify_mobile_stack.ps1
.\tools\verify_mobile_stack.ps1 -SkipLiveSmoke
```

통합 검증에는 모바일 `testID` 정적 점검도 포함됩니다. CSV 가져오기, 분석 기간/기준 전환, 분석 빈 상태, 차트 블록의 자동화 타깃이 빠지면 실패합니다.
개발 스크립트 계약 점검도 포함됩니다. 백엔드 검증 재시작, 상태 점검 Strict 모드, CSV 템플릿 스모크, 임의 포트 종료 안전장치가 빠지면 실패합니다.

`npm audit`는 high/critical 이상을 실패 기준으로 봅니다. Expo 내부 개발 도구 체인의 `uuid` moderate 경고는 강제 수정 시 Expo 다운그레이드가 필요하므로 자동 수정하지 않습니다.

브라우저 자동화 검증용 `testID`:

- 탭: `tab-portfolio`, `tab-drafts`, `tab-entries`, `tab-manual`, `tab-analytics`
- 분석 기간: `analytics-range-1m`, `analytics-range-3m`, `analytics-range-6m`, `analytics-range-1y`, `analytics-range-all`
- 수익 기준: `analytics-profit-basis-monthly`, `analytics-profit-basis-quarterly`, `analytics-profit-basis-annual`
- 비중 기준: `analytics-allocation-basis-ticker`, `analytics-allocation-basis-type`, `analytics-allocation-basis-account`
- 분석 빈 상태: `analytics-empty-range`, `analytics-profit-empty`, `analytics-trend-empty`, `analytics-allocation-empty`, `analytics-dividend-empty`, `analytics-cost-empty`
- CSV 가져오기: `manual-csv-input`, `manual-csv-template-button`, `manual-csv-pick-file-button`, `manual-csv-fill-sample-button`, `manual-csv-import-button`
- 차트 블록: `analytics-profit-chart`, `analytics-trend-chart`, `analytics-allocation-chart`, `analytics-dividend-chart`, `analytics-cost-chart`

실제 휴대폰에서 Expo Go로 테스트할 때는 `.env`의 `EXPO_PUBLIC_API_BASE_URL`을 개발 PC의 내부 IP와 8010 포트로 바꿉니다.

```env
EXPO_PUBLIC_API_BASE_URL=http://<PC의_내부_IP>:8010
EXPO_PUBLIC_DEV_USER_TOKEN=dev-local-token
```

Android 에뮬레이터는 보통 다음 값을 사용합니다.

```env
EXPO_PUBLIC_API_BASE_URL=http://10.0.2.2:8010
```

## 역할

- 보유 포트폴리오와 매매일지 조회
- 시장일지와 정보 입력의 모바일 입력 화면
- 저장된 리서치와 체크리스트 확인

## 기술 스택

- Expo SDK 55
- React Native 0.83
- React 19.2
- TypeScript
- TanStack Query 5
- react-native-gifted-charts

## 현재 구현된 화면

- 포트폴리오
- 일지 초안
- 일지
- 수동 입력
- 분석

각 화면은 `@tanstack/react-query` 훅으로 백엔드 API를 호출합니다.

수동 입력 화면은 모바일에서 거래 저장과 삭제를 지원합니다. 저장/삭제 후 `manual-transactions`와 `journal-analytics` Query를 다시 불러와 목록과 분석 차트가 갱신됩니다.

수동 입력 화면은 타 증권사 거래내역 CSV 템플릿 불러오기, 파일 선택, 붙여넣기 가져오기를 지원합니다. 템플릿은 `GET /api/v1/manual-transactions/import.csv/template`에서 받은 한글 헤더 CSV를 입력칸에 채웁니다. 파일 선택은 원본 인코딩 보존을 위해 `multipart/form-data`로 전송하고, 붙여넣기는 `text/csv`로 `POST /api/v1/manual-transactions/import.csv`에 전송합니다. 가져오기 후 `manual-transactions`와 `journal-analytics` Query를 다시 불러옵니다.

일지 초안 화면은 초안 선택 후 복기 내용을 입력하고 `일지 작성 완료`로 저장할 수 있습니다. 기본 목록은 `needs_review` 복기 대기 초안만 보여주며, `전체` 전환으로 `completed`, `linked` 상태까지 확인할 수 있습니다. 저장 후 `journal-drafts`, `journal-entries`, `journal-analytics` Query를 다시 불러와 복기 대기 목록과 분석 차트가 갱신됩니다.

일지 화면은 작성 완료 일지 조회, 수정, 삭제를 지원합니다. 키움 체결 상세(`order_execution`)는 별도 복기 건으로 중복 표시하지 않고 완료 일지의 `연결된 체결 상세` 영역에 붙여 보여줍니다. 삭제된 일지는 연결된 초안이 다시 복기 대기 상태로 돌아갑니다.

분석 화면 차트는 `react-native-gifted-charts`로 구현합니다.

- `BarChart`: 월간 수익
- `LineChart`: 누적 손익 추이
- `PieChart`: 종목별 비중

분석 화면은 `1개월`, `3개월`, `6개월`, `1년`, `전체` 기간 필터를 제공하고, 선택한 기간을 `/api/v1/journal/analytics`의 `start_date`, `end_date` 쿼리로 전달합니다.

추가 분석 전환:

- 수익 기준: `월간`, `분기`, `연간`
- 비중 기준: `종목별`, `유형별`, `계좌별`
- 부가 차트: 배당, 세금, 수수료

실기기 확인 체크포인트:

- 분석 탭에서 모든 차트가 빈 화면 없이 렌더링되는지 확인
- 기간 필터와 수익/비중 기준 전환 버튼이 작은 화면에서 겹치지 않는지 확인
- 데이터가 없을 때 선택 기간, 수익, 추이, 비중, 배당, 세금/수수료별 빈 상태 문구가 구체적으로 보이는지 확인
- 수익이나 누적 손익 값이 전부 0원일 때는 축만 있는 빈 그래프 대신 빈 상태 문구가 보이는지 확인

## 금지

- 증권사 API 키 저장
- 외부 데이터 API 키 저장
- `research_vault` 직접 파일 수정
