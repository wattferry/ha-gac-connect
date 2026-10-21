# GAC Connect for Home Assistant (unofficial)

> **Beta. Use at your own risk.** Remote commands physically act on your vehicle
> (A/C, locks, windows, boot, charging). Review what an automation can do before
> letting it touch the car.
>
> Not affiliated with, endorsed by or supported by GAC. GAC and AION are trademarks
> of their respective owners. Use it with a vehicle you own, on your own account.

Monitor and control a **GAC / AION** vehicle from Home Assistant: battery, range,
charging and charge scheduling, climate and seats, doors, windows, boot and
location.

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=wattferry&repository=ha-gac-connect&category=integration)

## Requirements

- Home Assistant 2025.3 or newer. Tested on 2025.3.0 and 2026.10.2; a current release is
  recommended, as it carries Home Assistant's latest security fixes.
- A GAC International app account (or My AION in the United Kingdom) and the mobile
  number it uses.

## Install

**HACS:** use the badge above, or:

1. HACS → three-dot menu → **Custom repositories**.
2. Add this repository with category **Integration**.
3. Install **GAC Connect (unofficial, beta)** and restart Home Assistant.

Releases are pre-releases while in beta: enable **Show beta versions** on the
integration's HACS page.

**Manually:** copy `custom_components/gac_connect` into your Home Assistant
`config/custom_components/` folder and restart.

Home Assistant installs the [`gac-connect`](https://pypi.org/project/gac-connect/) library,
which brings `aiomqtt` for the optional push feed (see **Allow unencrypted push connections**).

## Set up

**Settings → Devices & services → Add integration → GAC Connect.**

1. Choose your region and enter your mobile number.
2. Solve the slide puzzle that opens (drag the piece into the gap, then Verify;
   arrow keys move it one pixel). A miss shows a new puzzle.
3. Enter the SMS code. A mistyped code can be entered again; if it has expired,
   start again for a new one.
4. Choose the vehicle, and whether to allow remote unlocking, charging connector unlock and remote shutdown.

Regions: Australia, Brazil, Cambodia, Finland, Greece, Hong Kong, Indonesia,
Israel, Kuwait, Macau, Mexico, New Zealand, Philippines, Poland, Portugal, Russia,
Saudi Arabia, Singapore, Spain, Thailand, United Arab Emirates, United Kingdom.

Signing in here signs the official app out once. Sign the app back in and both keep
working: the car's controls and readings use a vehicle session that survives the app
signing in. GAC's **account** keeps only one session, though, so the optional GAC
alerts (see **Allow GAC account alerts**) stop whenever the app signs in after Home
Assistant. To sign Home Assistant in again: the integration's three-dot menu →
**Reconfigure**.

## Which entities appear

Entities are matched to the car. At setup the integration reads the car's
capability list from GAC's service, and uses the car's reports where the list says
nothing. **Always show** and **Omit** in the options (or the
`gac_connect.set_entity_visibility` action) override either. Lights appear once the
car has reported them on.

## Entities

### How commands report back

A control shows the requested state straight away. GAC accepts a command before the car
acts on it; Home Assistant then waits up to about 10 seconds for the car's own answer
(from the push feed, or by asking GAC at 2, 5 and 10 seconds without it). A refusal in
that time fails the action with the car's reason. An answer that comes later, or none,
leaves the action successful: **Last command** then shows whether the car's next report
matched (Requested state reported), the car refused it (Vehicle rejected request), or
neither happened within 3 minutes (Not confirmed in time).

### Controls

| Entity | Type | Description |
|---|---|---|
| Climate | climate | Modes Off, On (heat/cool to target) and Fan only (blower without compressor). Target temperature, fan speeds and airflow choices follow the car's capability list. Fan Off stops the A/C; airflow changes need the car switched on. Presets Heating (Auto at the highest target) and Cooling (Auto at the lowest). Each remote start runs for the Pre-conditioning run time. |
| A/C | switch | On while the cabin A/C runs, however it was started. Turning it on starts a remote run for the Pre-conditioning run time. |
| Pre-conditioning run time | number (configuration) | How long a remote A/C start runs before the car ends it, within the car's capability list (default 30 minutes). Once the car is switched on, its own climate control takes over. |
| Recirculation | switch | On recirculates, off draws fresh air. Changes only while the A/C runs. Shown when the car's capability list offers both. |
| Scheduled charging | switch | On follows the car's charging schedule. Off charges whenever plugged in, as Charge now does. |
| Smart battery temp | switch | Starts or cancels warming or cooling the battery, as in the app; the car runs it for up to 1.5 hours. |
| Sterilisation | switch | Runs the A/C's hot-air cabin sterilisation for 30 minutes. The car must be switched off and locked, with the windows closed. |
| Steering wheel heat | switch | On or off. |
| Ventilation | switch | Lowers the windows 2–3 cm and runs fresh-air circulation. On once started from Home Assistant, until it is turned off or a window closes: windows opened another way are not Ventilation. The car reports neither the mode nor how far a window is down, so Ventilation started in the GAC app shows off. Off closes the windows. |
| Flash lights | switch | Flashes the lights. |
| Driver seat ventilation | select | Off and the levels the car's capability list offers (up to Low, Medium, High). Choosing a level replaces the console's Smart mode. |
| Front passenger seat ventilation | select | As for the driver seat. |
| Doors | lock | Locks. Unlocks only when **Allow remote unlocking** is on. Locked needs all four doors reported locked and the boot shut; with the boot open the lock reads Open. |
| Windows | cover | Open or close all windows. |
| Sunroof | cover | Open or close. |
| Boot | cover | Open or close. |
| Charge now | button | Charges whenever plugged in (switches the schedule off). GAC has no start command: once a charge has ended (a one-time window finished, or the connector was unlocked) the car will not start another by itself, so Charge now first sends a one-time window to the charge limit starting at the next minute, then switches the schedule off a minute or two later, once the car reports charging. A charging request made in the meantime takes precedence. A repeating schedule is never replaced this way. |
| Unlock charging connector | button | Releases the charging connector so the cable can be pulled out, and stops charging. There is no remote lock command; the car locks it again when charging restarts. Only with **Allow remote charging connector unlock**. |
| Sound horn | button | Sounds the horn. |
| Refresh | button | Reads the car's status now. |
| Turn vehicle off | button | Switches the car off. Only with **Allow remote vehicle shutdown**. |
| Fridge | switch | Fridge on or off (cars with a fridge). |
| Fridge mode | select | Off and the modes the car's capability list offers: Refrigerate, Heat, Freeze. |
| Fridge temperature | number | Each mode's range from the car's capability list; otherwise Refrigerate 0–20 °C, Heat 35–50 °C, Freeze −15 to −1 °C. |
| Location | device_tracker | Home/away and map position. Optional. |

### Settings entities

Every option (see **Options**) and the charging-window editor also appear as entities in
the device's **Configuration** section, so a dashboard can manage them: the Allow and
location-tracking switches, Allow unencrypted push connections, Quiet hours with its
start and end times, Poll interval, and **Refresh vehicle capabilities**.

The charging window is prepared with **Charge window start / stop**, **Charge on Monday …
Sunday** (no days is one time) and **Stop at charge limit**, then sent with **Send charge
window**. They start from the window the car reports. A one-time window already open is
sent starting at the next minute, as the car never starts a start that has passed; one
that would end before then is refused with that reason.

### Sensors

| Entity | Description |
|---|---|
| Battery | State of charge, %. |
| Range | Remaining range, km. |
| Odometer | km. |
| Trip consumption | Average consumption of the drive under way, or else the last one, kWh/100 km, as the car's Trip computer shows it (within a few tenths). |
| Charging schedule | Scheduled charging, Whenever plugged in, or Not set, won't charge (the car waits after a one-time window); the reported window and days as attributes. |
| Reported charge window start / stop | Window times as the car reports them. |
| Charge power, Charge current, Charge voltage | While charging. |
| Estimated charge time | Minutes of charging remaining. |
| Cabin temperature | °C. |
| Outside temperature | °C. |
| Cabin PM2.5 | µg/m³. |
| 12V battery | Auxiliary battery voltage. |
| Battery temperature | Battery temperature as the car reports it (most likely the main battery). |
| Cabin fan strength | Blower speed as reported (0–10). |
| Tyre 1–4 pressure, Tyre 1–4 temperature | kPa and °C, where the car reports them. |
| GPS coordinates | Latitude and longitude. Optional. |
| Fridge after leaving | Timed or Unlimited. |
| Fridge time left | Minutes left on a timed setting. |
| Last GAC alert | The newest alert in GAC's alert list, or Signed out (see **Allow GAC account alerts**). Only with that option. |
| Last report | When the car last reported. |
| Data freshness | Recent report, Old report, Report time unknown or Report clock ahead. |
| Last cloud refresh | When Home Assistant last read the status. |
| Polling status | Polling normally, Quiet hours, Waiting for request limit, Refresh failed or Sign in again. |
| Last command | Outcome of the latest command (see **How commands report back**); failure reason, result code and the car's reported causes as attributes. |
| Entity choices | How many entities have an Always show or Omit choice; the choices and every entity key as attributes (diagnostic). |

### Binary sensors

| Entity | On means |
|---|---|
| Vehicle power | Car switched on. |
| Online | Car connected to the service. |
| Plugged in | Charging cable connected. |
| Charging | Charging. |
| Charger lock | Charging connector unlocked. |
| Lock | Unlocked, or the boot open. |
| Door, Window | A door, or a window, open. |
| Front left / Front right / Rear left / Rear right door | That door open. |
| Front left / Front right / Rear left / Rear right window | That window open. |
| Boot | Boot open. |
| Hood | Hood (bonnet) open. |
| Headlights, High beams, Rear fog light, Brake lights | That light on. |
| Turn indicators | Either indicator, or the hazard lights, on. They flash, so a report can catch them off. |
| Brake fluid | Problem when the car reports a brake-fluid alarm, as the app's Brake fluid check does. |
| A/C auto mode | A/C in Auto. |
| A/C compressor | Compressor selected (off in Fan only). |
| Anti-theft enabled | Alarm armed. |
| Driver / Front passenger / Rear left / Rear right seat ventilation state | Seat fan running; level as an attribute. |

### Events

| Entity | Fires |
|---|---|
| Car alert | From the car's reports, for everyone: charging stopped (with the cable still in), sterilisation finished, Smart battery temp finished; and, five minutes after the car is switched off, left unlocked, left open (doors, boot, bonnet) and window left open (which windows as an attribute). |
| GAC alert | Each new alert in GAC's own alert list (charging, battery, security, openings, someone left in the car, lights, fridge and others). Only with **Allow GAC account alerts**; alerts already listed when it starts are history. |

## Dashboard cards

Six cards, each with one job, narrow enough for a three-column desktop or a phone:

| Card | Shows |
|---|---|
| GAC Vehicle | Battery and range, a plan of the car with what is open, tyres, and quick actions. |
| GAC Climate | Cabin and target temperature, A/C, fan, airflow, seats and comfort features, and the fridge where fitted. |
| GAC Charging | Charging state, Charge now, and the charging window with its days. |
| GAC Location | Where the car is, on Home Assistant's map, and location tracking. |
| GAC Activity | Connection, the last command and its answer, and commands and alerts over two days. |
| GAC Settings | Permissions, tracking, alerts, polling, quiet hours and entity choices. |

Each card finds the car's entities itself and shows only what the car has. A command shows
as in progress until the car answers, then whether it confirmed or refused it. Each card's
footer says when the car last reported, and its refresh button reads the car now. Unlocking,
opening the boot or windows, sounding the horn, releasing the cable and switching the car off
need a held press; for half a minute after the horn sounds, one tap stops it. Times and the
first day of the week follow your Home Assistant profile's language and time format.

The cards are optional and off by default: until you install them, GAC Connect adds nothing
to Home Assistant's pages. **At setup**, answer **Install dashboard cards?** and choose the
cards for the car's dashboard (all six by default): GAC Connect creates a dashboard named
after the car, in the sidebar, holding them. Pick none to install the cards for your own
dashboards only. Each car gets its own. Change either choice later under **Configure →
Dashboard cards**, which also says where the dashboard is. Picking none, or uninstalling the
cards, removes the dashboard after you confirm. Refresh the browser after a change.

The generated dashboard stays GAC Connect's only while it is unchanged. Edit it as you like:
once edited it is yours, and GAC Connect will neither change nor remove it. Delete it and it is
not recreated.

If a card says **Custom element doesn't exist** after installing or updating, the browser is
still using its stored copy of Home Assistant's page: reload it, and if that is not enough,
clear the browser's stored data for your Home Assistant address (in the Companion app:
Settings → Companion app → Debugging → Reset frontend cache).

**On your own dashboard:** Edit dashboard → Add card → search for **GAC**. Each card shows one
car: with several cars, pick the car in the card's editor and add a card for each (with one
car there is nothing to pick). The Vehicle card can also take a body style for its drawing, a
photo of your car, a tyre pressure to warn below, and which actions to show.

## Options

**Settings → Devices & services → GAC Connect → Configure.**

**Vehicle settings**

| Setting | Default | Description |
|---|---|---|
| Allow unencrypted push connections | off | Receive command results through GAC's push feed where its broker is unencrypted. The broker credentials and topic names then travel without encryption; on GAC's Southeast Asia service they include an account number, but not the VIN or phone number. Without it, the integration asks GAC for each command's result instead (see **How commands report back**). |
| Poll interval | 300 s | Minimum 60 s. Lengthened automatically when several vehicles share the request budget. Applies at once. |
| Enable location tracking when parked | off | Show the location while the car is switched off. |
| Enable location tracking when moving | off | Show the location while the car is switched on. A change hides or shows the position at once; positions already recorded stay in Home Assistant's history. |
| Allow remote unlocking | off | Lets the Doors lock unlock the car. |
| Allow remote charging connector unlock | off | Shows Unlock charging connector. |
| Allow GAC account alerts | off | Reads GAC's alert list every 10 minutes for the GAC alert event and Last GAC alert. It needs GAC's account session, which the official app takes over whenever it signs in after Home Assistant: the alerts then show Signed out until you Reconfigure (which signs the app out once). |
| Allow remote vehicle shutdown | off | Shows Turn vehicle off. |
| Always show | none | Show entities even if the car does not appear to have them. |
| Omit unsupported entities | none | Hide entities even if the car has them. |
| Quiet hours start / end | none | No polling between these times (HH:MM). |

**Detected equipment** lists which entities are shown and why, starting with your
Always show and Omit choices.

**Refresh vehicle capabilities** reads the car's capability list again, for example
after a software update.

**Charging schedule** shows the reported schedule and can set a charging window,
charge now or refresh.

## Actions

| Action | Fields | Description |
|---|---|---|
| `gac_connect.charge_now` | `vin`, `until_soc` | Charge whenever plugged in, as the Charge now button does. |
| `gac_connect.set_charge_window` | `vin`, `start`, `stop`, `weekly`, `until_soc` | Charge only between `start` and `stop` (HH:MM; a stop before the start runs overnight). `weekly`: Mon=1, Tue=2 … Sun=64; 127 every day; 0 or omitted once. `stop` is not needed with `until_soc`. |
| `gac_connect.send_command` | `vin`, `command`, `params` | Send a command by name, for example `horn-on` or `aircon-manual-on`, with optional parameters. Unlock, connector unlock and shutdown need their options; PIN commands are refused. |
| `gac_connect.get_control_capabilities` | `vin` | Return the car's capability list (numeric fields only). |
| `gac_connect.get_position` | `vin` | Return the car's separate position report, with location values masked. |
| `gac_connect.get_alerts` | `vin`, `page` | Return one page of 20 entries from GAC's alert list, newest first. Needs the account session (see **Allow GAC account alerts**). |
| `gac_connect.get_departure_plans` | `vin` | Return the departure plans saved in the GAC app. |
| `gac_connect.set_entity_visibility` | `vin`, `entity`, `visibility` | Set an entity (a key such as `binary_sensor:front_left_door`, listed by Entity choices) to `automatic`, `always` or `omit`. Reloads the integration. |

`vin` is needed only with more than one vehicle. `until_soc` stops at the car's
own target charge level instead of the stop time, like the app's "Charge cutoff SOC".
No stop time is sent then, and the car keeps its saved one. The `get_…` actions return
their result as a response and send nothing to the car.

## Events

`gac_connect_command_result` fires for each command result:

| Field | Description |
|---|---|
| `device_id` | Vehicle device. |
| `ok` | `true` applied, `false` refused. |
| `code` | Result code. |
| `reason` | Meaning of a refusal code. |
| `details` | What the car reported as the cause, for example `["Driver door ajar"]`; empty if nothing. |
| `event` | Command type, for example `control_air_condition`. |
| `session_id` | Identifies the command. |

## Examples

- [`docs/example-automations.yaml`](docs/example-automations.yaml): alerts for low
  tyre pressure, low 12 V battery, car left unlocked, and doors, windows, boot or
  hood left open.
- [`docs/example-trips.yaml`](docs/example-trips.yaml): weekly, monthly and yearly
  distance and estimated consumption from odometer and battery readings.

## Request limits

All GAC Connect entries share one request budget:

- one request at a time, at least 1 s apart;
- at most 20 a minute, 240 an hour and 3000 a day;
- commands: at most 6 a minute and 60 an hour;
- after a "too many requests" answer, nothing is sent for at least a minute (up to
  a day if the service asks).

A held-back request is not sent: entities keep their last reading and a command
fails with an error. The budget survives restarts. If its saved state is
unreadable, requests pause for a day; delete `.storage/gac_connect.request_limits`
and restart to reset it.

## Limitations

- Sign-in needs a person: a slide puzzle and an SMS code.
- If the car's session ends, it is renewed from the saved account session; if that
  fails, Home Assistant asks you to sign in again.
- Engine start and stop need the car's remote-control PIN and are not supported.
- There is no remote stop-charging command: unlocking the charging connector stops a
  charge, and Charge now starts another.
- Battery reserve, the charge port door and the target charge level are not in the
  car's reports.
- Only the driver and front passenger seats have level controls; rear seats have
  readings and `send_command`.

## Acknowledgements

This project stands on the shoulders of the community projects that brought other
EV brands into Home Assistant and Python, among them:

- [AwangYes/BYD-re](https://github.com/AwangYes/BYD-re) — BYD
- [Hyundai-Kia-Connect/kia_uvo](https://github.com/Hyundai-Kia-Connect/kia_uvo) — Hyundai / Kia
- [bimmerconnected/bimmer_connected](https://github.com/bimmerconnected/bimmer_connected) — BMW / Mini
- [SAIC-iSmart-API/saic-python-client-ng](https://github.com/SAIC-iSmart-API/saic-python-client-ng) — MG / SAIC
- [kvanbiesen/bmw-cardata-ha](https://github.com/kvanbiesen/bmw-cardata-ha) — BMW CarData

Thanks to their authors for showing what a good community integration looks like.

## Changes

- **0.5.0** — admin settings as entities (every option and the charging-window editor),
  and the `set_entity_visibility`, `get_position`, `get_alerts` and `get_departure_plans`
  actions. Charge now starts a new charge after a one-time window ends or the connector
  is unlocked. One-time charging windows use the app's format and start on time. New
  Trip consumption, Brake lights, High beams, Rear fog light, Turn indicators and
  per-door and per-window sensors; Car alert and GAC alert events; the car's refusal
  causes in errors and in `gac_connect_command_result`. Ventilation reads the windows;
  a new poll interval applies at once. A newer charging choice is
  never overwritten by Charge now's follow-up; a new sign-in is not lost to a refresh
  in progress; partial reports no longer read as locked; command outcomes need the full
  target and a fresh report, and the car's refusal wins; undecryptable or refused
  replies are errors. Sign-in uses the library's puzzle page. The car-picture option,
  bundled pictures and example dashboard were removed. Requires Home Assistant 2025.3+.

- **0.4.0b3** — **UK (`GB`) sign-in is confirmed working end to end** on a real
  My AION account and AION V: all entities create and state of charge and the
  rest populate. Requires `gac-connect` 0.4.0b6, which fixes the last step of
  the UK sign-in (the IoV session exchange). Also fixes a crash during entity
  setup on the UK backend, which reports the vehicle model as a numeric code
  rather than a name; an unrecognised code now stops setup with a clear
  message instead of crashing, and a recognised one (currently the AION V) is
  shown normally. No change for other regions.

- **0.4.0b2** — fixes **UK (`GB`) sign-in**, which failed at the very first step
  with a signature error and never showed the slide puzzle. The integration was
  loading GAC International's key material for every region instead of the one the
  region's own app uses, so UK requests were signed with the wrong key and the
  backend rejected them. `GB` now signs with the My AION material. No change for
  other regions. Still requires `gac-connect` 0.4.0b1 and Home Assistant 2025.2+.

- **0.4.0b1** — requires `gac-connect` 0.4.0b1, which adds support for markets that
  run a separate national app. **United Kingdom (`GB`)** now works, using the
  My AION app and its own backend; select `GB` when adding the integration. Israel
  (`IL`) is added to the region list too. UK sign-in is still being confirmed by a
  UK user, so treat `GB` as best-effort for now. Requires Home Assistant 2025.2+.

- **0.3.0b1** — requires `gac-connect` 0.3.0b1, which stops the official app and
  this integration from signing each other out. After you sign in, a later app
  sign-in no longer ends the session; signing in here still signs the app out
  once, and you sign the app back in. If the integration was signing out whenever
  you used the phone app, **re-authenticate once** to pick up the fix. The library
  also now supports every region the service supports. Requires Home Assistant 2025.2 or newer.

- **0.2.0b12** — community contributions from @panosru: Greece (`GR`) region;
  an option to hide the fridge controls (for trims that report a fridge but have
  none); the location tracker now shows a picture of the car on the map (a
  bundled AION V render or your own image); and an example trips-and-consumption
  package (`docs/example-trips.yaml`). Requires `gac-connect` 0.2.0b10 and
  Home Assistant 2025.2 or newer.

- **0.2.0b11** — request limits: every request goes through the library's shared
  limiter (one at a time, rolling budgets, a pause after any "too many requests"
  answer); refreshes triggered by command results are at least 10 seconds apart;
  a refresh held back by the limits keeps the last reading instead of going
  unavailable; a stored poll interval under a minute is raised to one minute; the
  limits are kept across restarts.
  Signing in again after the session expires now updates the existing entry (it
  used to stop at "already set up"). Sign-in shows a clear message when requests
  are being held back. Quiet hours follow Home Assistant's time zone. The example
  dashboard's Fridge section notes which tiles send commands and shows Time left
  only with a timed setting. Requires `gac-connect` 0.2.0b9.

- **0.2.0b10** — two fridge sensors: *Fridge after leaving* (the car's
  keep-running setting, timed or unlimited) and *Fridge time left* (minutes left
  on a timed setting). Requires `gac-connect` 0.2.0b8. Added to the example
  dashboard's Fridge section.

- **0.2.0b9** — fridge / warmer box on cars that have one: switch, mode
  selector and target temperature, sharing one command queue and remembering the
  last mode and temperatures across restarts. Requires `gac-connect` 0.2.0b7. The
  example dashboard gains a Fridge section.

- **0.2.0b8** — docs only, no code change. The example dashboard now covers the
  sensors added since 0.2.0b2 (charge power and voltage, last report, charger
  lock, cabin PM2.5, tyre temperatures, refresh and battery-preconditioning
  buttons, location tile). The charging switch tile is named for what it does:
  on charges whenever the car is plugged in, off waits for the car's own
  schedule. Tyres are numbered rather than assigned corners.

- **0.2.0b7** — climate: the mode selector in the more-info dialog now works (`set_hvac_mode` was missing; heat_cool starts the A/C at the setpoint, off stops it).

## License

MIT. Uses the [`gac-connect`](https://github.com/wattferry/gac-connect)
library.
