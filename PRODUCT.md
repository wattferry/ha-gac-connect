# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Stack

Home Assistant custom integration (Python). The dashboard cards are Lit + TypeScript web
components, built to one bundle that is committed inside `custom_components/gac_connect`
and registered by the integration when it loads, so one HACS install brings both. CI checks
the committed bundle matches its source, as it already does for the bundled library.

## Users

Home Assistant users who own a GAC vehicle (AION, Hyptec, Trumpchi/GS, M8/GN8 and any
other model GAC's app serves, in any of the integration's 22 regions), using their own GAC
account. They glance at the car from a desktop dashboard (three columns), a wall tablet or
a phone (one column), and act on it remotely: warm or cool the cabin, lock it, start or
schedule a charge, find it.

Secondary: the owner as the integration's administrator, adjusting permissions, tracking,
quiet hours, polling and which entities appear.

## Product Purpose

Six narrow Lovelace cards, each with one job, that let an owner monitor and control their
car without wiring entities by hand: Vehicle, Climate, Charging, Location, Activity and
Settings. A user picks the car once in each card's editor; the card finds that car's
entities itself. Success is a dashboard an owner trusts at a glance and can act from
without opening Home Assistant's entity dialogs.

## Positioning

Unofficial and capability-driven. The integration reads each car's capability list, so the
cards show only what this car actually has, on every GAC model, including ones never
tested. Commands are honest: a control shows the requested state, then whether the car
confirmed it, refused it (with the car's own reason) or never answered.

## Operating Context

- Cards sit in Home Assistant dashboards (masonry or sections view), on desktop browsers,
  wall tablets and the Companion apps on iOS and Android. Each card must work from about
  300 to 420 px wide.
- They follow the user's Home Assistant theme, light or dark.
- Commands go through GAC's cloud: the car's answer takes up to about 10 seconds;
  confirmation from the car's next report can take up to 3 minutes.
- Readings arrive by polling (default every 5 minutes, paused in quiet hours) or GAC's push
  feed, so data can be minutes old. Last report, Data freshness and Polling status say how
  old and why.

## Capabilities and Constraints

- Entities exist only where the car's capability list (or its reports) says so; Always show
  and Omit choices override. Cards must render well with any subset missing.
- Entities are found by device and translation key (unique ID is `<VIN>_<key>`), never by
  entity ID, so renamed entities keep working.
- Unlock, charging connector unlock and vehicle shutdown exist only when their Allow
  options are on. Location is off by default (parked and moving are separate choices).
- No remote stop-charging command (unlocking the connector stops a charge); no engine
  start; PIN commands are refused.
- A shared request budget: at most 6 commands a minute and 60 an hour. A held-back command
  fails with an error.
- Changing an entity's visibility reloads the integration.
- Body styles to draw: hatch/crossover, SUV, coupé-SUV and MPV with sliding rear doors;
  PHEVs as well as EVs.
- Terminology follows the integration (British English): Boot, Bonnet, Tyre, Charge now,
  Scheduled charging, Smart battery temp, Sterilisation, Pre-conditioning run time; command
  outcomes Requested state reported, Vehicle rejected request, Not confirmed in time.

## Brand Commitments

- Name: GAC Connect (unofficial, beta). Not affiliated with or endorsed by GAC; GAC, AION
  and Hyptec are trademarks of their owners. No GAC logos, renders or 3D assets ship with
  the project.
- Car imagery is original line art drawn for the project, per body style, plus an optional
  photo the owner supplies.
- User-facing docs and examples are model-neutral: written for every GAC owner, never
  naming one model as the reader's car.

## Evidence on Hand

- The full entity list and behaviour in `README.md` and `custom_components/gac_connect`.
- `models/` holds GAC's showroom scenes and renders recovered for research. They are
  git-ignored and must not ship or be traced.
- No screenshots of real owners' dashboards exist; demonstration data is synthetic and
  labelled as such.

## Product Principles

1. Show only what this car has; a missing capability leaves no gap, no greyed-out control.
2. Be honest about time: stale readings and commands in flight are always visible.
3. Make consequential actions deliberate: unlocking, opening the boot, shutting the car
   down and releasing the connector take a held press, never a stray tap.
4. One choice configures a card: pick the car, and everything else is found.
5. Every GAC model is first-class.

## Accessibility & Inclusion

Touch targets at least 44 px for wall tablets and phones; full keyboard use and visible
focus; every control and state named for screen readers; state never carried by colour
alone; reduced-motion respected; contrast holds in both light and dark themes.
