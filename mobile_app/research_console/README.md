# Classic Research Console

이 폴더는 현재 운영 중인 정적 HTML/JavaScript 리서치 콘솔입니다. 공식 명칭은 **Classic Research Console**입니다.

폴더 경로에 `mobile_app`이 포함되어 있지만, 현재 역할은 모바일 앱이 아니라 데스크톱/브라우저 기반 웹 콘솔입니다.

## 운영 원칙

- 사용자가 실제로 쓰는 화면이므로 기능 안정성을 최우선으로 둡니다.
- API 호출 계약은 `api.js`와 `backend\research_os_main.py` 기준으로 유지합니다.
- 저장, 분석, 외부 데이터 조회, RAG 처리는 백엔드 API를 통해 수행합니다.
- `research_vault` 파일을 프론트엔드에서 직접 수정하지 않습니다.
- React 이관은 `apps\research-console`에서 화면 단위로 진행합니다.

## 실행

```powershell
cd C:\Users\lib20\InvestmentJournalApp
.\scripts\open-research-console.ps1
```

브라우저 주소:

```text
http://127.0.0.1:5500/index.html
```
