# 개발 서버 포트 예약표

여러 앱을 동시에 작업할 때 포트 충돌을 피하기 위한 로컬 예약표입니다. 새 서버를 띄울 때는 이 표의 포트를 우선 사용하고, 기본 포트(3000, 5173, 8000, 8081)는 앱별 고정 포트로 바꿔 실행합니다.

## 원칙

- OneDrive는 기본 작업 루트로 쓰지 않습니다.
- 각 앱은 자기 예약 포트만 사용합니다.
- 이미 떠 있는 포트를 덮어쓰지 않고 먼저 `tools\show_dev_server_ports.ps1`로 확인합니다.
- 모바일/백엔드 통합 검증은 기본적으로 `tools\verify_mobile_stack.ps1` 안에서 예약 포트 충돌을 먼저 확인합니다.
- Expo/Metro 기본 포트 `8081`은 충돌이 잦으므로 직접 쓰지 않고 앱별 전용 포트로 지정합니다.
- 백엔드와 프론트가 모두 있는 앱은 같은 100번대 포트 블록을 씁니다.

## 예약표

| 앱 | 루트 | 백엔드/API | 웹/콘솔 | 모바일/Expo | 비고 |
|---|---|---:|---:|---:|---|
| 투자 리서치 OS | `C:\Users\lib20\InvestmentJournalApp` | `8001`, `8010` / fallback `8020` | `5173`, `8082` | `8082` | 연구 콘솔은 `8001`, 모바일 API는 `8010` 우선, 오래된 점유가 있으면 `8020` 사용 |
| 스포츠 분석 플랫폼 | `C:\Users\lib20\projects\sports-analysis-platform` | `8101` | `8181` |  | 원본 master 직접 수정 금지 시 worktree 사용 |
| 스포츠 분석 플랫폼 worktree | `C:\Users\lib20\projects\sports-analysis-platform-worktree` | `8102` | `8182` |  | `codex/investigation` 전용 |
| 우리집 통역사 | `C:\Projects\FamilyTranslatorApp` | `8201` | `8281` | `8282` | Tailscale 테스트 시 API URL 별도 확인 |
| 가족 뉴스/아카이브 | `C:\Projects\FamilyNewsApp` | `8301` | `8381` | `8382` | 모바일 검증은 전용 Expo 포트 사용 |
| KoreaTravel | `C:\Projects\KoreaTravel_RN_review` |  | `8481` | `8482` | EAS/WSL 빌드와 로컬 미리보기 분리 |
| Monocut Web | `C:\AI\앱 제작\monocut` |  | `8501` |  | 배포 전 로컬 웹 확인 |
| Monocut Mobile | `C:\AI\앱 제작\monocut-mobile` |  |  | `8582` | 웹뷰 래퍼/Expo 전용 |

## 투자 리서치 OS 실행 예

```powershell
cd C:\Users\lib20\InvestmentJournalApp
.\scripts\start-research-backend.ps1 -Port 8001
```

주의: `8001` 연구 콘솔은 `research_os_main:app` 진입점입니다. `tools\restart_backend_verified.ps1`는 `main:app` 기반 모바일/API 백엔드 검증용이므로 연구 콘솔 8001 재시작에는 사용하지 않습니다.

연구 콘솔 백엔드가 정상인지 빠르게 볼 때는 읽기 전용 헬스 엔드포인트를 확인합니다.

```powershell
Invoke-RestMethod http://127.0.0.1:8001/api/v1/system/health
```

콘솔 HTML과 저장소 품질까지 함께 확인하려면 전용 상태 스크립트를 사용합니다.

```powershell
cd C:\Users\lib20\InvestmentJournalApp
.\tools\status_research_console.ps1 -Strict
```

모바일 API/앱 스택:

```powershell
cd C:\Users\lib20\InvestmentJournalApp
.\tools\start_backend.ps1 -Port 8010 -StopExistingPortProcess
.\tools\start_mobile_web.ps1 -Port 8082 -ApiBaseUrl http://127.0.0.1:8010 -StopExistingPortProcess
```

`8010`에 오래된 게이트웨이가 남아 최신 라우트가 없으면 강제로 덮어쓰지 말고 검증된 fallback을 사용합니다.

```powershell
cd C:\Users\lib20\InvestmentJournalApp
.\tools\restart_backend_verified.ps1 -Port 8010 -FallbackPorts @(8020,8021,8022)
.\tools\start_mobile_web.ps1 -Port 8082 -ApiBaseUrl http://127.0.0.1:8020 -StopExistingPortProcess
```

기본 상태 점검은 `8010`이 오래된 서버로 남아 최신 라우트가 없을 때 `8020`, `8021`, `8022`를 순서대로 확인합니다.

```powershell
cd C:\Users\lib20\InvestmentJournalApp
.\tools\status_dev_servers.ps1 -Strict
```

특정 포트만 확인하려면 `ApiBaseUrl`을 함께 지정합니다. 이 경우 fallback을 적용하지 않아 오래된 서버 문제를 그대로 드러냅니다.

```powershell
.\tools\status_dev_servers.ps1 -ApiPort 8010 -ApiBaseUrl http://127.0.0.1:8010 -Strict
.\tools\status_dev_servers.ps1 -ApiPort 8020 -ApiBaseUrl http://127.0.0.1:8020 -Strict
```

React 연구 콘솔:

```powershell
cd C:\Users\lib20\InvestmentJournalApp\apps\research-console
npm run dev -- --host 127.0.0.1 --port 5173
```

## 점검

```powershell
cd C:\Users\lib20\InvestmentJournalApp
.\tools\show_dev_server_ports.ps1
```

`Conflict=True`가 나오면 같은 포트에 여러 프로세스가 붙어 있는 상태입니다. 해당 앱의 포트를 정리한 뒤 다시 실행합니다.

`tools\start_backend.ps1`는 시작 전에 대상 포트가 비어 있는지 확인합니다. 이미 사용 중인 포트면 새 서버를 띄우지 않고 어떤 PID가 점유 중인지 먼저 안내합니다.

`unknown` PID가 포트를 잡고 있으면 일반 사용자 권한으로 정상 종료하기 어려운 상태일 수 있습니다. 이 경우 기본 시작 스크립트는 강제 종료하지 않으며, 관리자 권한 정리나 PC 재부팅 또는 `restart_backend_verified.ps1 -FallbackPorts @(8020,8021,8022)`를 사용합니다.
