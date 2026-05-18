# Classic Research Console 캐시 버스팅

`mobile_app\research_console`은 별도 번들러 없이 정적 HTML로 실행할 수 있는 콘솔입니다. 브라우저 캐시 문제를 줄이기 위해 `index.html`과 `console.js`의 자산 참조는 수동 버전 문자열이 아니라 파일 내용 기반 SHA-256 짧은 해시를 사용합니다.

## 갱신 명령

콘솔의 `styles.css`, `console.js`, `api.js`를 수정한 뒤 다음 명령을 실행합니다.

```powershell
python tools\update_console_asset_hashes.py
```

이 스크립트는 다음 참조를 자동 갱신합니다.

- `index.html`의 `styles.css?v=<hash>`
- `index.html`의 `console.js?v=<hash>`
- `console.js`의 `api.js?v=<hash>`

## 검증 명령

```powershell
python tools\update_console_asset_hashes.py --check
```

`--check`는 파일을 수정하지 않고 현재 HTML/JS 참조가 실제 파일 해시와 맞는지만 확인합니다. 콘솔 자산을 수정했는데 이 검증이 실패하면 갱신 명령을 먼저 실행하세요.

## 주의

- `?v=20260518-...`처럼 사람이 직접 붙이는 날짜/작업명 버전은 쓰지 않습니다.
- React 콘솔(`apps\research-console`)은 Vite 빌드 산출물의 파일명 해시를 사용하므로 이 스크립트 대상이 아닙니다.
