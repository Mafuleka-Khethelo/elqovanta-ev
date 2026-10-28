# Homepage redesign — 28 October 2026

The public homepage uses a white studio-style automotive composition, supplied transparent car illustrations, large typography and restrained motion. It introduces charger coordination, then leads visitors into the account and charger-discovery flows. Homepage styling is scoped to `.cc-home`. The account pages and application workspace now share this palette and typography; see `WORKSPACE_DESIGN.md` for that redesign.

## Palette and typography

| Use | Colour |
| --- | --- |
| Main background | White `#FFFFFF` |
| Secondary surface | Soft stone `#F3F4F0` |
| Primary text, buttons and station section | Deep forest `#173D36` |
| Calls to action and accents | Electric lime `#D4F56A` |

Manrope is self-hosted under `frontend/public/fonts/` with its SIL Open Font License. There is no runtime font-service dependency.

## Visual research

- [Porsche Taycan](https://www.porsche.com/usa/models/taycan/taycan-models/taycan/): vehicle-led presentation and clear image hierarchy.
- [Rivian R2](https://rivian.com/r2): an aspirational opening followed by distinct, focused chapters.
- [Electrify America](https://www.electrifyamerica.com/): charger discovery as a primary visitor action.
- [Lucid Air](https://lucidmotors.com/air): product details and image-led explanations.

These informed the composition and content hierarchy; the implementation does not copy their branding or claim their vehicle specifications, customer counts, coverage or charging capabilities. The user's automotive references guided the cutout-car direction.

## Page progression and interactions

1. A white header and large two-line hero introduce the product. The hero selector cycles through all five supplied cars, including colour swatches and previous/next controls.
2. A station-name search and connector filter lead into the existing charger list. Unauthenticated visitors sign in first. The route guard now retains the complete path and query, so both filters survive sign-in.
3. An interactive three-step walkthrough explains discovery, waiting lists and sessions. Its map and session visuals are explicitly marked as illustrative previews. Arrow keys, Home and End operate the vertical tabs.
4. Driver and station-team sections explain distinct features and lead to registration, the signed-in dashboard or manager sign-in.
5. Accessible FAQ disclosures explain accounts, first-come offers and the distinction between app coordination and physical bay reservations.
6. A final call to action and footer provide working navigation and an animation control.

The five original PNGs in the project root are unchanged. Web copies are under `frontend/public/cars/`. The hero uses the teal coupe by default; the yellow and crimson illustrations also appear farther down the page. The page does not advertise a live wait-time estimator or expose model research to drivers.

## Motion

The initial composition uses staggered headline, copy and vehicle entrances. Pointer and scroll motion use one scheduled animation frame, with small foreground offsets. A single IntersectionObserver reveals sections once. The visual walkthrough has short state transitions; decorative orbit and route animations can be paused from the footer.

System reduced-motion settings disable animation, parallax and smooth scrolling and leave every section visible. Motion listeners and observers are removed when the homepage unmounts. No additional animation package was installed.

Guidance: [animation performance](https://web.dev/articles/animations-guide), [IntersectionObserver](https://developer.mozilla.org/en-US/docs/Web/API/Intersection_Observer_API), and [reduced motion](https://developer.mozilla.org/en-US/docs/Web/CSS/@media/prefers-reduced-motion).

## Verification

The production build and existing three frontend tests passed. Browser checks covered the five vehicle assets, pointer motion, walkthrough tabs and keyboard navigation, all five FAQs, animation controls, reduced motion, and layouts at 320, 360, 390, 768, 1024 and 1440 pixels. No page-width overflow or clipped headline was observed at those widths.

A real demonstration-driver sign-in confirmed that a `HAMILTON #2` search with `Level 2` selected reaches the matching charger after authentication. Complete desktop/mobile screenshots were inspected. The tested journey produced no JavaScript exceptions. Verification scripts and screenshots remain local under the ignored `.local/model-check/` directory.
