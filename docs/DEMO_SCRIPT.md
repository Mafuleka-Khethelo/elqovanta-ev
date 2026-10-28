# Elqovanta EV presentation walkthrough

Use separate browser profiles for two drivers, the assigned station manager and the optional Model lab account. The ten current driver login details are in the private guide linked from `ACCOUNT_SCENARIOS.md`. No driver needs an examiner assignment.

## 1. Normal driver registration and dashboard

Register or sign in as a driver. Show the compact counts, current stop and next action. Research metrics are absent. Search for an app-enabled charger, such as PALO ALTO CA / HAMILTON #2, and choose an observed port type. Status is driver/manager-reported, with its own source and timestamp.

## 2. Automatic model advisory

Open **Plan your arrival** from the dashboard and choose a charger and port. The top **When will you arrive?** card checks **Now** automatically. Select **Later**, choose a future date/time within seven days in the displayed station time zone, then press **Check arrival**. Change the time: the old result disappears until rechecked. Show the selected arrival, Experimental badge and visible accuracy limitation. The result may be a warning or No warning flagged; do not force a warning or claim a negative result means a free bay or zero risk. Planning creates no queue place or reservation; starting/accepting checks now again. Minute-only changes within an hour need not change the result.

If flagged, Start charging opens Continue anyway / Go back. Going back creates nothing; continuing uses normal station/queue checks. The same confirmation applies when accepting an offer. If the model does not cover a station/port or is unavailable, show that state and continue the normal coordination workflow.

Explain the limit candidly: this is a historical model evaluated on 2020, so current-day use is experimental. Actual current inputs are used; dates are not mapped to 2020. A current frozen-history 30-day window normally contains zero records and a missing rate. No new app sessions feed or retrain the model. Details are available on demand, with technical scores only in the Model lab.

## 3. Charging, departure and queue

Start at a charger with a configured free app slot. The driver can pause/resume, finish charging while still connected, and report unplugged. Connected/charging/noncharging totals derive from server timestamps and reported intervals.

Share an expected unplug time. A second driver joins the same station's waiting list and sees the anonymous estimate. It can expire or change and does not release the slot. Compare alternatives using the app's stated sorting rules. Switching requires confirmation and preserves the old place on failure; choose the target port where needed.

## 4. Return reminders and handover

After reporting charging finished, choose a return reminder. Cancel, replace or snooze it. The reminder is optional regardless of model result. Close the driver tab: the backend worker still saves one in-app notification when due. No SMS, email or OS push is claimed.

Unplugging ends the session, cancels pending reminders/departure and releases the app slot. The first waiting driver gets a ten-minute offer. Accept once; a model warning can be reviewed without losing the server's capacity, FIFO or expiry rules.

## 5. Private help, messages and saved information

Report a blocked entrance or faulty charger privately. The assigned manager acknowledges/resolves and replies. This does not automatically change public station status. Demonstrate a private conversation, favourite add/remove, vehicle editing and history persistence after sign-in/refresh. Other drivers cannot read the conversation/report.

## 6. Independent Model lab illustration

Sign in to the separate researcher account and open Prediction lab. It no longer selects or enables drivers. Choose exact supported station PALO ALTO CA / HAMILTON #2, Level 1, 15 June 2020. Compare 07:00 and 22:00; the real saved model produces different results, including opposite warning flags for these examples. Change to 1 January 2020 to illustrate month/day/history changes. The chart compares all 24 arrival hours; changing minutes alone should not change the model result.

These are explicit historical 2020 scenarios, separate from the driver's current-day experiment. Show original stored evaluation honestly: performance is modest and most warnings were false alarms. Keep raw scores, threshold, features and evaluation in this workspace. No model has been created, retrained, replaced or converted into a waiting-time predictor.

## 7. Offline and permissions

Disconnect the browser while viewing known data. Last loaded information stays visible and changes are disabled. A warning can still be closed offline. Reconnect and recover. Check the mobile menu and readable card layout. Driver/manager research requests are forbidden; research access does not grant station management or private-message access.

Finish only presentation-owned sessions and sign out. Leave other people's participation intact.
