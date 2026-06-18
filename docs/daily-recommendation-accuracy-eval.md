# Daily Recommendation Accuracy Eval Log

## 2026-06-18

Goal: 추천 정확도 평가 점수 개선.

Setup:
- Project root: `C:\Users\lib20\InvestmentJournalApp`
- `AGENTS.md`: not present in this checkout.
- Primary eval: `python tools\evaluate_daily_recommendation_accuracy.py`
- Existing validation: `python tools\check_daily_recommendations_store.py --require-milestones`, `python tools\check_daily_recommendation_citations.py`

Baseline:
- Score: `80.00/100`
- Subscores: `latest_quality=80.0`, `tracked_outcomes=0.0`
- Failures:
  - `3위 동성화인텍: score_alignment 저장 154 / 구성 156`
  - `tracked_outcome: 가격 확인 불가 마일스톤 45개`
  - `tracked_outcome: hit_rate 0.17 / 목표 0.50`

Iteration 1 - eval penalty parser:
- Bottleneck: the eval script did not parse string score penalties such as `최근 자료 신선도 보강 필요 (-2)`.
- Change: count string penalties and fall back to `score_explanation.penalty_points` when needed.
- Result: false `score_alignment` failure removed; score stayed `80.00/100` because latest quality was already capped at 80 points.

Iteration 2 - tracking price fallback:
- Bottleneck: tracking used only live provider price lookups, leaving due milestones as `price_unavailable` even when `user_portfolios.json` had fresh saved prices.
- Change: added a saved portfolio current-price fallback for daily recommendation tracking.
- Dry-run on a temporary vault: `price_unavailable` `45 -> 2`, score `80.00 -> 83.91`.
- Applied tracking refresh to the local operational store, without committing operational JSON.
- Result: score `83.91/100`, subscores `latest_quality=80.0`, `tracked_outcomes=3.91`.

Post-change failures:
- `tracked_outcome: 가격 확인 불가 마일스톤 2개`
- `tracked_outcome: hit_rate 0.25 / 목표 0.50`

Remaining risk:
- The 2 unavailable milestones are both `071050 한국금융지주` from `2026-06-03`; no saved portfolio fallback price was available.
- The score is still capped by real recommendation outcome quality: completed hit rate is `0.25`, below the `0.50` target.

Iteration 3 - domestic non-portfolio price fallback:
- Bottleneck: the remaining unavailable milestones were `071050 한국금융지주`, a domestic ticker not present in saved portfolios.
- Change: daily recommendation tracking now uses Naver domestic stock basic price as a final fallback for Korean tickers, and prefers it over ambiguous mock-like domestic provider prices.
- Operational refresh: `price_unavailable` `2 -> 0`.
- Result: score `84.74/100`, subscores `latest_quality=80.0`, `tracked_outcomes=4.74`.

Post-change failures:
- `tracked_outcome: hit_rate 0.24 / 목표 0.50`

Remaining risk:
- Price coverage is now complete for due milestones, so the next bottleneck is the actual realized recommendation hit rate rather than missing data.
