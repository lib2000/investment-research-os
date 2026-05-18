# Folder Cleanup Report

작성일: 2026-05-17
기준 루트: `C:\Users\lib20\InvestmentJournalApp`

## 적용한 정리

- 폴더 정책 문서 추가: `docs\folder-policy.md`
- 공통 루트 검증 스크립트 추가: `tools\assert_project_root.ps1`
- 정리 후보 확인 스크립트 추가: `tools\list_cleanup_candidates.ps1`
- 투자일지 백엔드 실행 스크립트에 루트 검증 연결: `tools\start_backend.ps1`
- Research OS 백엔드 실행 스크립트에 루트 검증 연결: `scripts\start-research-backend.ps1`
- 리서치 콘솔 실행 스크립트에 루트 검증 연결: `scripts\open-research-console.ps1`
- README와 작업 요약 문서에 폴더 정책 기준 반영

## 폴더 정책

- 활성 프로젝트 루트는 `C:\Users\lib20\InvestmentJournalApp` 하나로 고정한다.
- OneDrive 경로에서는 서버 실행, 코드 수정, 생성 파일 저장을 하지 않는다.
- 작업 전 아래 명령으로 루트를 검증한다.

```powershell
cd C:\Users\lib20\InvestmentJournalApp
.\tools\assert_project_root.ps1 -PassThru
```

## 정리 후보

아래 항목은 `tools\list_cleanup_candidates.ps1`로 확인된 후보이다. 이번 작업에서는 삭제하지 않았다.

확인 후 삭제 후보:

- `.codex_migration_backup_20260508-204736`
- `research_vault_customs_test_tmp`
- `research_vault_workflow_test_tmp`

일반적으로 삭제 가능한 생성물 후보:

- `backend\__pycache__`
- `backend\app\__pycache__`
- `backend\research_os\__pycache__`
- `apps\mobile\.expo-export-check`

## 검증 결과

- `tools\assert_project_root.ps1 -PassThru` 통과
- `tools\list_cleanup_candidates.ps1` 실행 확인
- PowerShell 스크립트 문법 확인 통과
  - `tools\assert_project_root.ps1`
  - `tools\list_cleanup_candidates.ps1`
  - `tools\start_backend.ps1`
  - `scripts\start-research-backend.ps1`
  - `scripts\open-research-console.ps1`

## 다음 정리 단계

삭제를 진행하려면 먼저 위 후보 중 삭제할 항목을 확정한다. 백업/테스트 임시 폴더는 사용자 확인 후 삭제하고, `__pycache__`와 `.expo-export-check`는 생성 캐시로 분류해 별도 캐시 정리 스크립트로 처리하는 것이 안전하다.
