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

Iteration 4 - underperformance feedback loop:
- Bottleneck: score coverage was complete, but realized `tracked_outcome` hit rate stayed below target.
- Change: daily recommendation candidate scoring now applies a performance feedback penalty when prior completed milestones show repeated underperformance for the same ticker.
- Current feedback candidates from the store: `OTLY=-12`, `112610=-12`, `033500=-6`, `003230=-6`, `253450=-6`, `071050=-6`.
- Result: historical eval score remains `84.74/100` because past outcomes are not rewritten.

Post-change failures:
- `tracked_outcome: hit_rate 0.24 / 목표 0.50`

Remaining risk:
- The next score move now depends on future recommendations avoiding repeat underperformers and subsequent milestones completing with stronger outcomes.

Iteration 5 - outcome breakdown diagnostics:
- Bottleneck: the eval reported aggregate `hit_rate` failure but did not show enough structure to choose the next bottleneck.
- Change: `evaluate_daily_recommendation_accuracy.py` now reports underperforming tickers and milestone-level outcome breakdowns in both JSON and text output.
- Current worst ticker groups: `112610 씨에스윈드` hit rate `0.00`, average `-14.7%`, `n=10`; `OTLY` hit rate `0.00`, average `-13.2%`, `n=3`.
- Current worst horizon: `15d` hit rate `0.11`, average `-7.4%`, `n=18`.
- Result: score remains `84.74/100`; diagnostics now identify the next optimization target.

Post-change failures:
- `tracked_outcome: hit_rate 0.24 / 목표 0.50`

Remaining risk:
- The likely next fix should target 15-day deterioration and repeated weak tickers, but changing the scoring rule should be validated with replay/backtest rather than by rewriting past outcomes.

Iteration 6 - horizon-aware underperformance penalty:
- Bottleneck: the `15d` horizon was the weakest completed milestone group, but recommendation feedback used only ticker-wide averages.
- Change: tracking feedback now stores milestone breakdowns per ticker and adds a `+4` penalty when the `15d` group has at least 2 completed outcomes, hit rate below `0.25`, and average return at or below `-5.0%`.
- Current affected feedback totals from the store: `112610=-16`, `033500=-10`, `003230=-10`; `OTLY` remains `-12` because it has only one completed `15d` sample.
- Result: historical eval score remains `84.74/100`; future ranking now penalizes repeat 15-day deterioration more directly.

Post-change failures:
- `tracked_outcome: hit_rate 0.24 / 목표 0.50`

Remaining risk:
- The penalty is deliberately conservative; stronger exclusion rules should wait for replay/backtest evidence that they improve future hit rate without overfitting to a small sample.

Iteration 7 - severe repeat-underperformer top3 hold:
- Bottleneck: after the horizon-aware penalty, a high-scoring repeat underperformer could still remain in the generated top 3.
- Change: candidates now keep a structured `tracking_feedback_profile`; when a candidate has at least 3 completed outcomes, hit rate at or below `5%`, average return at or below `-5.0%`, and feedback penalty at least `12`, ranking holds it out of top 3 if enough alternatives exist.
- Dry-run candidate generation: top 3 changed from including `OTLY` to `ABSI`, `033500`, `105630`; warning now starts with `반복 부진 top3 보류: OTLY, 112610`.
- Result: historical eval score remains `84.74/100` because saved outcomes are not rewritten; future generated recommendations now avoid the clearest repeat-underperformer exposure.

Post-change failures:
- `tracked_outcome: hit_rate 0.24 / 목표 0.50`

Remaining risk:
- `033500` remains in the top 3 with a weaker but non-zero hit rate; broader exclusion should wait for more replay evidence or a separate rule for horizon-only deterioration.
