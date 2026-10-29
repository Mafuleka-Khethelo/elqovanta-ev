# Car-specific charging estimates

This update adds a calculation alongside the original saved model. It does not train, replace or change that model, its seven inputs, frozen history, threshold or evaluation.

Drivers can save a model/version label, **usable** battery capacity in kWh and optional AC/DC vehicle charging limits. At each charge they enter the current battery percentage, their target and an **assumed average power reaching the battery** in kW. The estimate uses the smaller of that assumed average and the applicable saved vehicle limit. The app does not infer power from a Level 1/2 label or invent manufacturer specifications. Vehicle data is entered by its owner; it is not a verified manufacturer catalogue.

```
Energy needed (kWh) = usable capacity × (target % − current %) / 100
Time (hours) = energy needed / assumed average battery-delivered power
```

For example, 60 kWh, 40% to 80%, at an assumed average 12 kW reaching the battery gives 24 kWh and approximately two hours. Grid/nameplate power is not necessarily average battery-delivered power. Peak charging power should not be treated as a guaranteed average. This first version uses an explicit constant-average assumption, not an invented charging curve, calibrated uncertainty interval or learned charging-time model. Users can enter a newer battery reading and power assumption to recalculate from the server's current time. Reaching 100% can take longer as charging slows; drivers should follow their vehicle's guidance.

The server saves immutable calculation revisions with a single active revision per session, version checks, request keys and actual server timestamps. A preview creates no participation or scheduled alerts. Starting can attach the checked inputs atomically; existing sessions and accepted offers can add details from My session. Older sessions without estimates keep working. Battery/vehicle details remain private; other participants see only anonymous estimated target times or a driver-reported finished state. A charger may have several connected sessions with different target times; missing estimates are explicitly counted rather than filled with invented waiting minutes.

The existing durable worker checks active revisions and sends persistent **in-app** alerts about ten minutes before the estimated target and when the estimated time arrives. Recipients are the charging driver and drivers currently waiting/offered at that charger. Keys, worker locks and notification phase flags prevent duplicates; a ten-minute per-session/phase cooldown limits revised-reading spam. Revised or removed estimates, completed charging and unplugged sessions stop obsolete alerts. Late joins see the current shared summary rather than receiving a history of alerts.

Messages say **estimated target time**, not confirmed battery full. An 80% target is not a full battery. Driver-reported completion generates a separate queue update. Completion never releases an app slot or skips FIFO: the next offer follows an unplug report. Normal driver controls are Start, Report charging finished and Report unplugged. Pause/Resume buttons are removed. Historical pauses and intervals remain intact; deprecated compatibility endpoints support old clients and cancel an obsolete estimate if used. Manager station closure is separately labelled as coordination closed.

Free Render hosting can sleep. Notification schedules survive in Neon and overdue work is handled after waking, but exact-time background delivery is not guaranteed. There is no vehicle/charger telemetry, external push, SMS or email integration.

Technical basis: [US Department of Energy charging factors](https://afdc.energy.gov/fuels/electricity-stations?lv=true), [Tesla on charging slowing near full](https://www.tesla.com/support/charging/supercharging), [Render free-service behaviour](https://render.com/docs/free).
