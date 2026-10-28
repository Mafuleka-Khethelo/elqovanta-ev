# Model behaviour checked on 22 October 2026

**Current policy - subsequent user update, 28 October 2026:** ordinary registered drivers receive automatic experimental advisories for supported charger/port pairs, without an examiner assignment. They use actual current arrival inputs and may continue after a warning. The independent Model lab remains 2020-only, with technical results restricted to researchers. Current-day use is outside that evaluation; the original history protocol remains unchanged. See `DRIVER_ADVISORY.md`.

The model is working: the website runs `predict_proba` on the original saved Random Forest. Its probabilities change with historical scenarios. Logging in again does not change its seven inputs and should not change a prediction.

The previous charger card chose a port automatically, placed the current Palo Alto month/day/hour in 2020, and rounded the result to a whole percentage. It did not provide input controls or regularly recompute while the page stayed open. That made a real model look like a fixed charger score. The updated card uses an explicit historical scenario, date and port controls, two decimal places, an hourly comparison, and a computation timestamp.

## Verified examples

All examples below use the observed **Level 1** port label. These are predictions for historical sessions, not present-day availability. The warning rule is strictly probability >17%.

| Charger | Historical date | Earlier sessions | Lowest hourly score | Highest hourly score |
| --- | --- | --- | --- | --- |
| PALO ALTO CA / HAMILTON #2 | 15 June 2020 | 64 | 07:00 — 5.0679% | 22:00 — 20.3885% |
| PALO ALTO CA / HAMILTON #2 | 1 January 2020 | 304 | 20:00 — 4.8046% | 00:00 — 18.7125% |
| PALO ALTO CA / HAMILTON #2 | 22 October 2020 | 151 | 08:00 — 3.1534% | 22:00 — 18.7259% |
| PALO ALTO CA / BRYANT #1 | 15 June 2020 | 3 | 08:00 — 5.4461% | 22:00 — 24.4218% |
| PALO ALTO CA / BRYANT #1 | 1 January 2020 | 63 | 07:00 — 5.0043% | 22:00 — 28.1138% |
| PALO ALTO CA / BRYANT #1 | 22 October 2020 | 0 | 08:00 — 4.4965% | 22:00 — 26.8454% |

The zero-session example keeps the historical rate missing, rather than replacing it with zero. The fitted pipeline handles that missing value.

## Evidence and repeatability

`scripts/check_model.py` compared 144 application predictions with direct calls to the pipeline using independently constructed inputs. All agreed within absolute tolerance `1e-12`. Repeated inference with identical inputs also agreed within that tolerance. Small differences around `1e-16` can occur from floating-point summation and do not affect displayed results.

The loaded artifact matched the original project-root model:

```text
b1cfde621dd23950b18c73cddf7bee97072f334e8e1355920abeb85318cac626
```

The frozen history contains 259,366 rows. The stored evaluation matches the project reference. No training, threshold tuning, history changes or replacement weights were used.

Re-run the independent check from the project root:

```powershell
backend\.venv\Scripts\python scripts\check_model.py
```

## What to explain in the presentation

- **Training** produced a saved model. **Inference** applies that model to a scenario; it does not need to learn again on every login.
- A prediction uses charger name, port type, arrival hour, weekday, month, and the earlier 30-day session count and long-session rate. The browser cannot invent the two history features.
- Changing only minutes, account, queue activity or app-reported status will not change those model features. A different valid input may also land in the same tree leaves and produce the same score.
- The hourly comparison holds station, port, date and prior history constant and varies arrival hour. This demonstrates sensitivity to an input; it does not establish a causal effect or advise when a physical bay will be free.
- Responsiveness does not prove predictive quality. About the model shows the held-out 2020 evaluation: approximately 14.43% precision and 70.43% recall at the chosen warning cutoff. Most warnings were false alarms.

See `DEMO_SCRIPT.md` for the separated driver and examiner walkthrough.
