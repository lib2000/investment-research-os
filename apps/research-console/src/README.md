# React 이관 소스 구조

이 폴더는 현재 운영 콘솔(`mobile_app/research_console`)을 React 기반으로 옮길 때 사용할 기준 구조입니다.

```text
src/
  app/          # 라우팅, 전역 상태, 앱 레이아웃
  shared/       # API 클라이언트, 공통 포맷터, 공통 UI
  features/     # 대시보드, 포트폴리오, 정보입력 등 기능 화면
  styles/       # 디자인 토큰, 전역 스타일
```

현재는 기존 운영 화면을 유지합니다. 새 기능을 React로 만들 때만 이 구조 아래에 추가합니다.
