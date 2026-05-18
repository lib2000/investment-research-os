# Mobile App

이 폴더는 Expo/React Native 모바일 앱 이관 대상입니다.

현재 웹 미리보기 코드는 `mobile_app`에 남아 있으며, 이 폴더는 네이티브 앱 전환을 위한 Expo + TypeScript + TanStack Query 골격입니다. 모바일 앱은 백엔드 API만 호출하고, 증권사 키나 외부 API 키를 저장하지 않습니다.

## 실행

```powershell
cd C:\Users\lib20\InvestmentJournalApp\apps\mobile
Copy-Item .env.example .env
npm install
npm run start
```

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

일지 초안 화면은 초안 선택 후 복기 내용을 입력하고 `일지 작성 완료`로 저장할 수 있습니다. 저장 후 `journal-drafts`와 `journal-analytics` Query를 다시 불러와 복기 대기 목록과 분석 차트가 갱신됩니다.

일지 화면은 작성 완료 일지 조회, 수정, 삭제를 지원합니다. 삭제된 일지는 연결된 초안이 다시 복기 대기 상태로 돌아갑니다.

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
- 데이터가 없을 때 `표시할 차트 데이터가 없습니다.` 문구가 보이는지 확인

## 금지

- 증권사 API 키 저장
- 외부 데이터 API 키 저장
- `research_vault` 직접 파일 수정
