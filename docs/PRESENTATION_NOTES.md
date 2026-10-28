# Elqovanta EV presentation - 30 October 2026

Live app: **https://elqovanta-ev.onrender.com**. Aim for an 8-10 minute presentation, followed by questions. The complete interaction walkthrough is in [DEMO_SCRIPT.md](DEMO_SCRIPT.md).

## Suggested slides and speaking points

1. **The problem.** Drivers need a clear way to coordinate charging and their return. A vehicle can remain connected while it is no longer charging, delaying the next participant.
2. **The solution.** Elqovanta EV brings together charger search, reported charging sessions, waiting lists, return reminders and private communication with a station manager.
3. **The driver journey.** Find a charger, choose a port and arrival time, read the advisory, then start charging or join the queue. Show the clean driver dashboard and the next action. Drivers need no examiner assignment.
4. **The model's role.** The existing saved Random Forest advises about more than 30 minutes connected without charging over a session, including pauses and time after charging finishes. It does not estimate waiting minutes or physical availability. Current/future advisories are labelled experimental because the stored evaluation used 2020 data.
5. **Coordination in action.** Show two drivers: one charging and another waiting. Finish charging, set an optional reminder, then report unplugged. The next driver receives a ten-minute offer and can accept it. Show a private manager message or help report.
6. **Evidence and model illustration.** In the separate Model lab compare Hamilton #2, Level 1, 15 June 2020 at 07:00 and 22:00. These real saved-model results have opposite warning flags. Explain the stored evaluation honestly, including false alarms and missed cases. Show the evaluation screen instead of inventing accuracy claims.
7. **Deployment and limits.** One Render website serves React, FastAPI and the original model; Neon persists accounts and activity. The tested Linux image passed 70 backend tests and 144 independent probability comparisons. Real live journeys also passed. Status is participant-reported, reminders are in-app, and the free host can sleep.

## Before presenting

- Open the live site 10 minutes early and confirm you can sign in. A sleeping free service may take about a minute to wake.
- Use separate browser profiles for Driver A, Driver B and the manager. Tabs in the same profile share a login. Keep the Model lab account in a fourth profile, or sign out before switching roles.
- Use the existing private [driver login guide](../.local/showcase/DRIVER_ACCOUNTS.md). Passwords belong in your private notes, not on slides or in the source repository.
- Check the chosen station's current app capacity, queue and reported status. Existing activity was retained; the ten drivers are not reset automatically. Finish only sessions belonging to your presentation participants.
- Read the station time zone beside the arrival input. Palo Alto uses America/Los_Angeles, which differs from South African time.
- For a predictable model comparison, use the historical Model lab example above. The driver screen uses the actual current/planned time; a changed time can legitimately produce the same warning.
- Keep the local app available at **http://127.0.0.1:8000** while the local backend and PostgreSQL are running. Its data is a separate copy and does not track later live changes. Keep the verified screenshots as a fallback for a network failure.

## Short answers for likely questions

**Does the model learn from new sessions?** No. New sessions update the app's operational records. The original model and its 259,366-row frozen history remain unchanged. Retraining was outside this project's approved scope.

**Why can the result stay the same?** The model uses station, port, time and historical features. Minutes within an hour do not change its hour feature, and different probabilities can still fall on the same side of the warning threshold. Reopening the page alone does not supply different inputs.

**What happens after a warning?** The driver may go back or continue anyway. Capacity and queue rules still apply. A warning does not block the driver or book a physical bay.

**What does unavailable mean?** The saved model cannot cover that station/port or a result could not be obtained. Normal charging coordination remains available; the app shows the limitation.

**Does a low-risk result mean a free charger?** No. The model concerns extended time connected without charging. The app separately shows participant-reported status and coordination counts.

**Will reminders arrive with the browser closed?** The backend saves an in-app notification when due while the service is awake. Saved overdue reminders are processed after waking. Free-host sleeping and lack of external push mean delivery is not guaranteed at the exact chosen time.

**Can the manager read everyone's messages?** Managers see conversations and reports for stations assigned to them. Drivers see their own records. The researcher role grants no station-management or private-message access.

After the demonstration, unplug your own active presentation sessions and sign out. Preserve other participants' activity.
