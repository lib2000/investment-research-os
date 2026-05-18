# Folder Policy

InvestmentJournalApp의 활성 작업 루트는 아래 하나로 고정한다.

```text
C:\Users\lib20\InvestmentJournalApp
```

## 원칙

- OneDrive 경로에서는 서버 실행, 코드 수정, 생성 파일 저장을 하지 않는다.
- Codex, PowerShell, Expo, FastAPI 작업은 항상 활성 프로젝트 루트 아래에서 실행한다.
- OneDrive 경로는 사용자가 명시적으로 마이그레이션을 요청한 경우에만 읽기 대상으로 취급한다.
- 삭제가 필요한 임시/백업 폴더는 먼저 후보를 확인하고, 명시 확인 후 정리한다.

## 실행 전 검증

```powershell
cd C:\Users\lib20\InvestmentJournalApp
.\tools\assert_project_root.ps1 -PassThru
```

## 정리 후보 확인

아래 명령은 삭제하지 않고 후보만 보여준다.

```powershell
cd C:\Users\lib20\InvestmentJournalApp
.\tools\list_cleanup_candidates.ps1
```

## 현재 정리 후보

- `.codex_migration_backup_*`: 마이그레이션 백업 후보
- `research_vault_*_tmp`: 테스트 임시 폴더 후보
- `__pycache__`: Python 캐시 후보
- `.expo-export-check`: Expo export 검증 임시 출력 후보
