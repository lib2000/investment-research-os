# 테스트 가이드

이 프로젝트는 문법 검사만으로 회귀를 막기 어렵기 때문에, 빠르게 돌릴 수 있는 표준 검증 명령을 분리해 둡니다.

## 백엔드 회귀 테스트

```powershell
python -m unittest discover -s tests -p "test_*.py"
```

현재 백엔드 테스트는 외부 API나 실제 개인 데이터에 의존하지 않고 다음 경계를 확인합니다.

- 웹 본문 추출 표시 헬퍼가 URL, 언어, 번역 상태, 본문 보강 안내를 보존하는지
- Tesseract 미설치 상태의 이미지 업로드가 중단되지 않고 명확한 OCR 경고와 메타데이터를 남기는지
- 레거시 리서치 자료 정책이 하드 삭제가 아닌 소프트 보관을 기본으로 하는지
- 포트폴리오 기간 수익 비교가 재계산/캐시 정책과 해외 가격 히스토리 한계를 결과에 표시하는지
- 설정/상태 API가 실제 secret 대신 마스킹 값과 설정 여부만 노출하는지
- DART 공시 일일 감시 대상이 보유종목과 관심종목에서 함께 산출되는지

## 백엔드 문법 검사

```powershell
python -m py_compile backend\research_os_main.py backend\research_os\web_capture.py backend\research_os\file_extraction.py
```

## 기존 콘솔 검증

```powershell
python tools\update_console_asset_hashes.py --check
node --check mobile_app\research_console\console.js
```

## React 콘솔 검증

```powershell
cd apps\research-console
npm run check
npm run test:portfolio
npm run test:portfolio-api
```

`npm run verify`는 위 검증과 빌드를 함께 실행합니다.
