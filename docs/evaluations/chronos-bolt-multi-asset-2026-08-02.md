# Chronos-Bolt 대체 모델 벤치마크 (2026-08-02)

## 목적

기존 Kronos 후보와 동일한 데이터·워크포워드 규칙으로 Amazon Chronos-Bolt를 비교하고,
운영 모델로 승격할 근거가 있는지 확인한다. 이 평가는 연구 전용이며 주문·추천·자동화 경로에
연결하지 않는다.

## 재현 조건

- 공식 저장소/문서: [amazon-science/chronos-forecasting](https://github.com/amazon-science/chronos-forecasting)
- 모델: `amazon/chronos-bolt-mini` (Chronos-Bolt, 21M급 경량 모델)
- 공식 파이프라인: `chronos.ChronosBoltPipeline`
- 데이터: Yahoo Finance via yfinance, `auto_adjust=True`, 일봉 365행, 10개 한국 종목
- 입력: 종가만 사용 (Chronos-Bolt는 이 실험에서 OHLCV를 직접 예측하지 않음)
- 워크포워드: lookback 120일, horizon 5일, step 5일, 시간순 분할
- 비교 기준: 마지막 종가 반복(last-close) 및 기존 로그수익률 drift 기준
- 실행 환경: 격리된 D: 드라이브 가상환경, CPU `torch 2.13.0+cpu`
- 결과 원본: `D:\workspace\_third_party\kronos-eval\chronos_bolt\walk_forward_multi_asset.json`

## 결과

| 모델/기준 | 평균 개선율 vs last-close | 평균 방향 정확도 | 수리 | 판정 |
|---|---:|---:|---:|---|
| Chronos-Bolt-mini (10종목) | **-7.199%** | 48.57% | 0 | 보류 |
| Kronos-small (동일 조건) | -21.935% | 51.43% | 191 | 보류 |
| 로그수익률 drift 기준 | -2.624% | 51.02% | 0 | 기준선 |

Chronos-Bolt-mini는 마지막 종가 기준보다 평균 MAE가 7.199% 악화했고 방향 정확도도
50% 미만이었다. 따라서 현재 데이터·기간에서는 기존 단순 기준선보다 우월하다고 볼 수 없다.

## 승격 게이트 적용

공통 게이트(`docs/evaluations/model-benchmark-contract.md`)의 기본값은 다음과 같다.

- 평균 개선율 `>= 0%`
- strict 실패 0건
- 출력 수리율 0%
- 복수 종목·기간 재검증 및 사람 검토

Chronos-Bolt-mini는 strict 실패와 수리는 없지만 평균 개선율이 음수이므로 `hold_research_only`다.
이 모델을 투자 추천, 매매 전략, 예약 작업, Telegram 발송에 연결하지 않는다.

## 해석과 한계

- 종가 단변량 실험이므로 OHLCV 전체 예측 성능이나 포트폴리오 성과를 의미하지 않는다.
- 365일·10종목·5일 예측만 사용했으며, 시장 국면·수수료·슬리피지·유동성·실행 가능성을
  반영하지 않았다.
- 사전학습 모델의 통계적 결과일 뿐 미래 수익을 보장하지 않는다.
- 최신 날짜를 추가한 롤링 검증과 기간별 분할을 통과하기 전에는 모델 선택을 바꾸지 않는다.

## 다음 사람 검토 항목

1. 동일 종목의 더 긴 조정주가 구간과 별도 기간 holdout을 추가한다.
2. 단순 기준선 대비 개선이 재현되는지 확인한다.
3. 개선이 확인되더라도 비용·슬리피지·리스크 한도를 포함한 백테스트와 사람 승인을 거친다.
