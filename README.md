# GAC Connect for Home Assistant (unofficial)

Monitor and control a **GAC / Aion** vehicle in Home Assistant — battery, range,
odometer, charging, doors and windows, tyres, and charge control.

> Not affiliated with, endorsed by, or supported by GAC. Use it with a vehicle
> you own, on your own account.

Verified for **Australia and New Zealand**. Other regions appear in the list but
are unverified.

## Install (HACS)

1. HACS → three-dot menu → **Custom repositories**.
2. Add this repository, category **Integration**.
3. Install **GAC Connect (unofficial)**, then restart Home Assistant.
4. **Settings → Devices & Services → Add Integration → GAC Connect.**

## Set-up

You sign in with the mobile number on your GAC account:

1. Choose your region and enter your mobile number.
2. A window opens with a **slide puzzle** — drag the piece into the gap and press
   Verify (arrow keys nudge it a pixel).
3. Enter the **SMS code** sent to your phone.
4. Pick your vehicle. Done.

If the puzzle is off by a little it just shows a new one — keep going until it
takes.

## Entities

Battery, range, odometer, cabin temperature, 12 V battery, charge status and
estimated time, and per-tyre pressure and temperature; plugged-in, charging,
door / window / boot, lock and online as binary sensors; a location tracker
(off by default — enable it in the integration's options); buttons for charge
now / pause / refresh; and a scheduled-charging switch.

## Example dashboard

A ready-made car view using only built-in cards (no extra installs) is in
[`docs/example-dashboard.yaml`](docs/example-dashboard.yaml). Replace the
`aion_v` entity prefix with your vehicle's, then paste it as a new view via
Dashboards → Edit → Raw configuration editor.

## Services

`gac_connect.charge_now`, `charge_pause`, `set_charge_window`, and `send_command`
(advanced, for the confirmed non-PIN commands).

## Options

Poll interval, quiet hours (skip polling overnight to spare the 12 V battery),
and whether the location tracker is enabled.

## Notes

- Sign-in needs a human (a slide puzzle and an SMS code); there is no headless login.
- Remote lock/unlock, engine and charger-release need a PIN this integration does
  not yet support, and are not offered.
- Using the official app and this integration on the same account at the same time
  can occasionally sign one of them out.

## License

MIT. Built on the [`gac-connect`](https://pypi.org/project/gac-connect/) library.
