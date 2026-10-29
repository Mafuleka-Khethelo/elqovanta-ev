# Elqovanta EV presentation walkthrough

For the updated charging-time journey: open **My vehicles**, search a model (or type a missing one), confirm usable capacity and save it. Add another car to show the vehicle selector and default. Choose today's car, find a charger, enter current/target percentages and an assumed average battery-delivered power, then **Calculate charging time**. Show the duration before any timer starts (60 kWh, 40→80%, 12 kW = two hours). Confirm being plugged in and start; show the actual target/reminders in My session. A second driver can join with their own provisional plan. On their offer they confirm a fresh reading, calculate again and confirm plugged in before acceptance. Timer alerts do not confirm full or release the bay; finish and unplug remain driver reports. Use an isolated charger for any accelerated rehearsal, never edit someone else's live session.

Use separate browser profiles for two drivers, the assigned station manager and the optional Model lab account. The ten current driver login details are in the private guide linked from `ACCOUNT_SCENARIOS.md`. No driver needs an examiner assignment.

## 1. Normal driver registration and dashboard

Register or sign in as a driver. Show the compact counts, current stop and next action. Research metrics are absent. Search for an app-enabled charger, such as PALO ALTO CA / HAMILTON #2, and choose an observed port type. Status is driver/manager-reported, with its own source and timestamp.

## 2. Car-specific charging-time calculation

In My profile save an example vehicle and its usable battery capacity, plus AC/DC limits if known. On a charger page choose Add battery details, pick the vehicle, and enter the current battery percentage, target and an assumed average power reaching the battery. For a clearly labelled calculation example use 60 kWh, 40% to 80%, and 12 kW with no lower saved AC limit: 24 kWh and approximately two hours. Explain that a peak charger rating is not a guaranteed average.

Calculate, then start normally. My session shows the estimated target time, countdown and explicitly calculated progress. Update the actual battery reading to recalculate from now. An accepted waiting-list offer can add battery details from My session. A second waiting driver sees anonymous completion context and receives near-target/target estimated-time notices alongside the charging driver. A timer never confirms the battery is full; follow the car and confirm charging finished yourself. Report unplugged before an app slot is released. Car-specific calculations are independent of the unchanged saved ML model.

## 3. Automatic model advisory

Open **Plan your arrival** from the dashboard and choose a charger and port. The top **When will you arrive?** card checks **Now** automatically. Select **Later**, choose a future date/time within seven days in the displayed station time zone, then press **Check arrival**. Change the time: the old result disappears until rechecked. Show the selected arrival, Experimental badge and visible accuracy limitation. The result may be a warning or No warning flagged; do not force a warning or claim a negative result means a free bay or zero risk. Planning creates no queue place or reservation; starting/accepting checks now again. Minute-only changes within an hour need not change the result.

If flagged, Start charging opens Continue anyway / Go back. Going back creates nothing; continuing uses normal station/queue checks. The same confirmation applies when accepting an offer. If the model does not cover a station/port or is unavailable, show that state and continue the normal coordination workflow.

Explain the limit candidly: this is a historical model evaluated on 2020, so current-day use is experimental. Actual current inputs are used; dates are not mapped to 2020. A current frozen-history 30-day window normally contains zero records and a missing rate. No new app sessions feed or retrain the model. Details are available on demand, with technical scores only in the Model lab.

## 4. Charging, departure and queue

Start at a charger with a configured free app slot. The driver reports charging finished while still connected, then reports unplugged. Pause/Resume controls are removed; earlier history remains preserved. Connected/charging/noncharging totals derive from server timestamps and recorded intervals.

Share an expected unplug time. A second driver joins the same station's waiting list and sees the anonymous estimate. It can expire or change and does not release the slot. Compare alternatives using the app's stated sorting rules. Switching requires confirmation and preserves the old place on failure; choose the target port where needed.

## 5. Return reminders and handover

After reporting charging finished, choose a return reminder. Cancel, replace or snooze it. The reminder is optional regardless of model result. Close the driver tab: the backend worker still saves one in-app notification when due. No SMS, email or OS push is claimed.

Unplugging ends the session, cancels pending reminders/departure and releases the app slot. The first waiting driver gets a ten-minute offer. Accept once; a model warning can be reviewed without losing the server's capacity, FIFO or expiry rules.

## 6. Private help, messages and saved information

Report a blocked entrance or faulty charger privately. The assigned manager acknowledges/resolves and replies. This does not automatically change public station status. Demonstrate a private conversation, favourite add/remove, vehicle editing and history persistence after sign-in/refresh. Other drivers cannot read the conversation/report.

## 7. Independent Model lab illustration

Sign in to the separate researcher account and open Prediction lab. It no longer selects or enables drivers. Choose exact supported station PALO ALTO CA / HAMILTON #2, Level 1, 15 June 2020. Compare 07:00 and 22:00; the real saved model produces different results, including opposite warning flags for these examples. Change to 1 January 2020 to illustrate month/day/history changes. The chart compares all 24 arrival hours; changing minutes alone should not change the model result.

These are explicit historical 2020 scenarios, separate from the driver's current-day experiment. Show original stored evaluation honestly: performance is modest and most warnings were false alarms. Keep raw scores, threshold, features and evaluation in this workspace. No model has been created, retrained, replaced or converted into a waiting-time predictor.

## 8. Offline and permissions

Disconnect the browser while viewing known data. Last loaded information stays visible and changes are disabled. A warning can still be closed offline. Reconnect and recover. Check the mobile menu and readable card layout. Driver/manager research requests are forbidden; research access does not grant station management or private-message access.

Finish only presentation-owned sessions and sign out. Leave other people's participation intact.
