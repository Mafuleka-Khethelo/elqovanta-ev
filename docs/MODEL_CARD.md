# Model card

## What it is

The artifact `ev_charger_bundle.joblib` is a finished scikit-learn pipeline saved with `joblib.dump(..., compress=3)`. The website loads it. It does not call `fit`, `fit_transform`, model selection or threshold tuning.

| Bundle field | Recorded value |
| --- | --- |
| `schema_version` | 1 |
| `model_name` | Random Forest |
| `pipeline` | `preprocessor`, then `classifier` |
| `warning_cutoff` | 0.17 |
| `noncharging_threshold_minutes` | 30 |
| `history_window_days` | 30 |
| `exclude_arrival_day` | true |
| `timezone` | America/Los_Angeles |
| `validation_year` | 2019 |
| `test_year` | 2020 |

The classifier that was selected has 200 trees, `max_depth=None`, `min_samples_leaf=20` and `random_state=42`. If the loaded file does not match this contract, prediction stays unavailable.

## Question the model answers

For a historical Palo Alto session, was the time connected but not charging **greater than** 30 minutes?

`long_noncharging = (total_minutes - charging_minutes) > 30`

Exactly 30 minutes is class 0. Thirty minutes is a project research threshold, not an official parking rule.

The warning shown in the lab is a second, separate rule: probability of class 1 **greater than** 0.17. Exactly 0.17 is not a warning. The probability is not a guarantee that the outcome will happen.

## Inputs

The server builds these seven fields, in this order, and passes that one-row table to the saved pipeline. The browser cannot submit the counts or the rate.

1. `Station Name` — the exact historical name
2. `Port Type` — an observed type that appears with that name in the history
3. `arrival_hour` — integer 0–23
4. `arrival_day` — English weekday name
5. `arrival_month` — integer 1–12
6. `station_sessions_30d` — count of earlier sessions at that exact name
7. `station_long_rate_30d` — average of their labels, or missing if the count is zero

The first five were categorical during training. The last two were numeric. The fitted preprocessor does the encoding. The website does not encode them again in JavaScript.

History is grouped by charger name only, not by port type. A session enters the window when it has **ended**, not when it started. The entire selected arrival day is excluded, even for an evening arrival. Later completions, and the queried session itself, are not inputs. Sessions recorded in Elqovanta EV are not inputs.

The lab accepts arrival dates from 1 January 2020 through 31 December 2020 only. Earlier completed 2020 sessions may inform a later 2020 arrival. The pipeline itself stays frozen. The separate experimental driver preview accepts Now or a planned station-local arrival within seven days; it converts the instant to the original model time zone. This does not expand the evaluated period or validate present/future accuracy. Plans never replace real session times. See `DRIVER_ADVISORY.md`.

## How it was evaluated

Training used sessions from before 2019. Validation used 2019. The final test used 2020. The stored `test_comparison` table and `test_confusion_matrix` are the authoritative numbers. The project reference, which the server checks against those objects, is:

| 2020 test measure | Recorded result |
| --- | --- |
| Sessions | 20,094 |
| Precision | about 14.43% |
| Recall | about 70.43% |
| F1 | about 0.2396 |
| ROC AUC | about 0.5906 |
| Average precision | about 0.1741 |
| True negatives | 7,175 |
| False positives | 10,423 |
| False negatives | 738 |
| True positives | 1,758 |

In plain language: about 14 of every 100 warnings were correct, and the model detected about 70 of every 100 actual long noncharging sessions. Most warnings were false alarms. Always warning had an F1 around 0.2210, so the improvement is modest. Recall is not accuracy.

## Software required to load it

`model_environment.json` records Python 3.13.9 and:

- scikit-learn 1.7.2
- pandas 2.3.3
- numpy 2.3.5
- scipy 1.16.3
- joblib 1.5.2
- threadpoolctl 3.5.0

A different scikit-learn version can fail to unpickle the pipeline or can change a probability. The server compares the installed versions with the manifest and refuses to predict if they differ. It does not retrain.

The bundle is loaded once per process. Prediction runs in a worker thread with a small concurrency limit. The file is not exposed as a download, and the API does not accept an uploaded pickle.

## Limitations

- The data are Palo Alto sessions from 2011–2020, tested on 2020. They do not describe another city or a later year.
- The result is not live availability, a predicted departure, or a guaranteed wait.
- False alarms are the common case at this cutoff.
- The model must not reorder a queue, remove a driver, or justify a fee.
- A prospective deployment would need a new data agreement, a defined decision, monitoring of calibration, and a fresh evaluation on data the model has not already seen. The frozen 2020 test must not be updated with Elqovanta EV’s own sessions.

## Where this is shown

The Historical Prediction Lab, Historical insights and About the model require the separate `researcher` role in both the interface and API. Manager access does not include research. The protected lab reports the unchanged probability, strict cutoff, historical features/window, artifact identity, stored evaluation and limitations. It compares all 24 arrival hours and recent submitted scenarios.

Following the user's subsequent product update, ordinary registered drivers receive automatic **experimental** advisories for supported exact charger/port pairs. They do not need an examiner assignment. The adapter uses their actual current arrival, or an active session's actual plugged-in time and saved port. Before starting/accepting, a warning offers Continue anyway or Go back. Driver DTOs contain no probability, cutoff, feature values, artifact identifier or evaluation details. Unavailable guidance does not disable manual coordination/reminders.

Current-day use is outside the 2020 evaluation and is labelled accordingly. The exact previous-30-day completion history is still used: after the history ends, count is zero and rate remains missing, not a substituted current-data statistic. This is not evidence of current predictive validity. Results cache by artifact, station, port, local date and hour. Polling unchanged inputs reuses them. Current operational timestamps are never backdated; website sessions are never appended to frozen history. See `DRIVER_ADVISORY.md` for the current policy.

Login, arrival minutes and current application events are not model features. Identical historical inputs reproduce the same probability; some different inputs can also reach the same tree leaves. This is inference, with no training, tuning, calibration or replacement weights. `MODEL_CHECK.md` retains independent examples and `DEMO_SCRIPT.md` explains the separated presentation.
