# Elqovanta Charging Assistant

The driver experience combines vehicle-based charging calculations, the existing experimental noncharging-risk advisory, an optional return reminder and app queue handover. These parts retain different responsibilities. The calculator estimates a chosen battery target; the unchanged model flags possible long connected-but-not-charging time; FIFO and reported unplugging control the next offer.

## Driver journey

1. Save/select today's car and choose a charger/observed port. Enter current/target battery percentages and an assumed average power reaching the battery. The chosen port's manager-reported power, when present, and the saved car's AC/DC limit cap that assumption. Peak/nameplate power is not guaranteed average battery-delivered power.
2. Preview the duration before the session clock starts. Optionally select **I only have a limited time**, such as 30 minutes. The server calculates possible energy/percentage gain within that time and stops at the chosen target. A 60 kWh example at 40→80%, assuming 12 kW, gives two hours to target; 30 minutes gives about 6 kWh, from 40% to 50%. These are constant-average calculations, not measured energy or a learned charging curve.
3. Compare alternative chargers using the same private car/battery assumptions alongside reported queue size, connected sessions and status freshness. Known port ratings can produce different durations. Missing ratings produce an unavailable explanation instead of an invented duration. Duration excludes queue/walking/driving time and does not certify vehicle/port compatibility.
4. Confirm plugged in and start, or join the waiting list with a provisional plan. An offered driver confirms a fresh reading and plan before actual start.
5. In **Elqovanta Charging Assistant**, see the target, calculated progress, advisory, optional return reminder and waiting-driver count. The reminder remains **off until the owner explicitly enables it**. A warning can suggest planning the return, but a warning is not consent. Drivers with no warning or an unavailable advisory can also opt in.
6. Choose a lead of 5/10/15/20/30/60 minutes. The server stores consent and the target-relative due time. A new saved battery reading moves an enabled reminder to the revised target. An explicit Not now/Turn off choice persists and is never silently re-enabled by recalculation. If the lead has already begun, an enabled reminder becomes due immediately; a target already in the past requires checking/updating the reading first.
7. A restart-safe worker creates the owner's private in-app return notification once per active revision. The existing near-target/target status notices remain separate and provide anonymous updates to people waiting. Neither kind detects a full battery, automatically completes a session or releases the bay. Reporting charging finished stops pre-target reminders; only reported unplugging enables the next eligible offer.
8. **My session summaries** shows reported connected/charging/noncharging durations, the planned target/last entered reading when available, and optional reminder delivery. It does not invent measured battery completion or energy delivered for current or legacy records.

## Manager-reported power

Assigned managers can record or clear AC/DC and listed kW for each existing observed port using **Reported port power**. No rating is inferred from Level 1/2 labels or seeded into historical chargers. Incomplete type/power pairs, invalid numbers and unassigned changes are rejected. Catalogue imports retain these operational fields. Ratings carry their own update timestamp and are not live telemetry.

## Saved model and historical demonstration

The original artifact, features, history, cutoff and stored evaluation are unchanged. Battery/car/time-budget/reminder inputs never enter the model. Present-day advisory use remains clearly experimental, with no prospective accuracy claim.

The researcher workspace includes **Elqovanta Charging Assistant — historical demonstration** after a genuine 2020 prediction. Manual hypothetical battery inputs produce a calculator target anchored to that labelled historical arrival. The same saved pipeline supplies the actual warning; an optional illustrated reminder shows how that warning can support a choice. This read-only demonstration creates no live session, consent record, reminder or notification, and never backdates a real driver session. Example: HAMILTON #2 / Level 1, 15 June 2020 at 22:00 flags a warning, while 08:00 does not. Changing the hypothetical battery capacity affects the calculated duration, not the model's warning.

Reminder delivery and noncharging durations provide operational records for a future evaluation. They do **not** establish that reminders reduce noncharging occupancy; that requires a separately designed comparison with suitable consent and measurement.

## Reliability and limits

`assistant_reminders` stores one owner-scoped preference per session: consent, lead, due time, estimate revision, optimistic version and delivered timestamp. Changing requests lock user → charger → session → preference; worker delivery locks charger → session → preference and checks the current estimate. Notification creation and delivery state commit together under a unique event key. Finish, pause/resume compatibility actions, unplug, manager closure and estimate removal cancel obsolete pre-target schedules. Existing finished-but-connected return reminders retain their independent workflow.

The additive `20261030_0006` migration preserves existing users, vehicles, sessions, queues and password hashes. Free Render can sleep; schedules persist in Neon and overdue work runs after waking. Notices are in-app only, with no exact-time, external push, email or SMS guarantee. Charging can slow near full; the app has no vehicle/charger telemetry or calibrated charging curve.
