# Elqovanta EV account and dashboard redesign

Latest user-directed dashboard update (28 October 2026): the internal shell now has a green sidebar (`#24645d`), lime active navigation (`#cef695`) and a clean white content area. Driver and manager dashboards use compact summary cards, plain headings and clear lists/actions. The large car illustration, sidebar promotion and manager promotional banner were removed. The original authentication pages retain their established design. `workspace-clean.css` scopes the new presentation to the application workspace. Current screenshots and checks are recorded in `VERIFICATION.md`; the older design notes below describe the preceding version.

This records the earlier visual redesign. The approved build-brief extension now adds a separate examiner role, departure reports, reminders, help reports and deterministic alternatives. Current permissions and functionality are documented in `REQUIREMENTS.md`, `ARCHITECTURE.md` and `BUILD_BRIEF_IMPLEMENTATION.md`.

The sign-in, driver registration, driver dashboard and station-manager overview now share the homepage's white, forest-green and lime palette, local Manrope font, supplied car artwork and Elqovanta EV logo. The application shell has a white desktop sidebar, a compact account toolbar and a mobile navigation drawer.

## Design references

- [Electrify America mobile app](https://www.electrifyamerica.com/mobile-app/): give the current charging task priority, followed by useful station and history information.
- [ChargePoint Waitlist guide](https://www.chargepoint.com/drivers/support/faqs/what-can-i-do-if-all-charging-spots-are-busy): distinguish waiting, queue position and an open offer, with an action appropriate to each state.
- [Monta operator dashboards](https://montahelp.helpjuice.com/operator-dashboards-monta?kb_language=en_US) and [Hub navigation](https://montahelp.helpjuice.com/welcome-to-monta-hub?kb_language=en_US): organize the manager workspace around counters, station records and activity.
- [Monta account setup](https://monta.com/help/en_US/monta-charge-account-settings/create-monta-account): keep initial account entry focused on the details required to start.
- [W3C form labels](https://www.w3.org/WAI/tutorials/forms/labels/): use visible labels associated with each input and connect errors and hints to their fields.

These informed the information hierarchy. Branding, composition and implementation belong to this project; the screens do not copy another service's identity or claim its capabilities.

## Account pages

Desktop uses an automotive illustration beside a focused form; small screens prioritize the form. Both pages retain the existing authentication API and native autocomplete. Password controls expose a labelled visibility toggle. Registration retains the 2–80-character display name and 10–128-character password constraints, shows accessible server field errors, and creates a driver account. Manager accounts remain operator-issued. Switching between sign-in and registration retains an intended protected destination and its search parameters.

## Driver workspace

The main card reflects the current session, waiting-list position, open offer or absence of a current stop. Displayed durations, queue positions and offer deadlines come from the existing APIs. The next action opens the matching session, waiting list or charger discovery page. Saved chargers, unread counts, recent completed sessions and demonstration labels retain their source data. Failed requests show errors or unavailable values rather than invented zero counts.

Session and queue queries retain visible-page polling every five seconds. A manual refresh also reloads the summary and history. No battery state, guessed ETA, fabricated charging curve, energy total or environmental saving was added. Drivers still have no research navigation or model metadata.

## Manager workspace

The overview shows open sessions, waiting drivers, completed stops and reported noncharging minutes. Assigned chargers support name search, reported-status filters and six-record pagination. The activity feed can expand beyond its first six records. The existing add-charger request now appears in an expandable form with pending and error states; it keeps the existing capacity range of 1–20 places. The overview retains visible-page polling every ten seconds and offers manual refresh.

## Shared behavior

The application uses the homepage's forest/lime design tokens and Manrope across signed-in pages. Shared primary buttons use forest with white text. Status badges retain semantic colors and text. On mobile, the drawer locks background scrolling, traps keyboard focus, closes with Escape and restores focus to the menu button. Entry animations are brief; the system reduced-motion preference removes animation and transitions.

## Verification

Production build and all three existing frontend tests passed. Real demonstration-driver and manager sign-ins, unsuccessful sign-in feedback, manual dashboard navigation, station search, mobile Escape/focus behavior and layouts at 320, 390, 768, 1024 and 1440 pixels were checked. Desktop/mobile screenshots were inspected, including the supplied car and logo fit.

Browser-only API fixtures exercised session states, queue states, no activity, request failures, station pagination/filtering, add-charger validation, registration validation/server field errors and registration returning to an intended protected page. Those fixtures wrote no data to the server and do not ship with the application. The five-second session refresh was observed in the browser. No JavaScript exceptions occurred in the completed checks. Scripts and screenshots remain under ignored `.local/model-check/`.

Backend model artifacts, training data, research APIs and queue/session rules were not changed. The existing main-bundle size warning remains.
