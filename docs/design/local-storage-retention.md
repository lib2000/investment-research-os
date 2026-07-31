# 로컬 저장공간 정리 정책

- 상태: 적용
- 목적: C 드라이브의 이전 작업본을 제거하고, 활성 D 드라이브 프로젝트의 재생성 가능한 파일만 정기 정리한다.

## 보존 대상

- `research_vault/`, 데이터베이스, 환경 파일, 자격 증명, 사용자 산출물, `backups/`
- Git 이력과 소스 파일

## 정리 대상

- Python 캐시: `__pycache__`, `.pytest_cache`, `.ruff_cache`, `.mypy_cache`
- 14일보다 오래된 `tmp/` 및 `.test-tmp/` 파일
- 30일보다 오래된 로그 파일과 과거 마이그레이션 임시 폴더

결과 JSON·스크린샷·환경 파일은 자동 삭제하지 않는다.

## 실행 방식

- `InvestmentResearchOS Local Cleanup`은 매일 03:30에 실행한다.
- 꺼져 있던 PC는 다음 로그인 후 실행하며, 배터리 상태에서도 동작한다.
- 중복 실행은 막고, 실행 결과는 `tmp/local_cleanup_state.json`에 남긴다.
- 기본 실행은 미리보기이며, 예약 작업만 `-Apply`로 실제 정리를 수행한다.
