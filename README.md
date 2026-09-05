# GAC Connect for Home Assistant (unofficial)

> **⚠️ BETA — not fully tested, use entirely at your own risk.** This is an
> unofficial integration with no relationship to GAC. Expect bugs; things that
> worked yesterday may not work tomorrow. Remote commands physically act on your
> vehicle (A/C, locks, windows, tailgate, charging) and may misbehave or fail;
> using it alongside the official app may sign one of them out. Nothing here is
> warranted to work, keep working, or be safe. Review what an automation can do
> before you let it touch the car.

Monitor and control a **GAC / Aion** vehicle in Home Assistant — battery, range,
odometer, charging, doors and windows, tyres, and charge control.

> This project is not affiliated with, endorsed by, or supported by GAC or its
> affiliates. GAC and AION are third-party trademarks of their respective
> owners. Use it with a vehicle you own, on your own account.

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=wattferry&repository=ha-gac-connect&category=integration)


Supports **Australia and New Zealand**. Other regions appear in the list but
are best-effort.

## Install (HACS)

Releases are published as **pre-releases** while the project is in beta. In
HACS, open the integration's page and enable *Show beta versions* to see them.

Click the badge above for one-click add, or add it manually:


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

- **Sensors**: battery, range, odometer, cabin temperature and PM2.5, 12 V battery,
  charge current and estimated time, per-tyre pressure and temperature, and the
  time of the car's last report (the reported charge window is available as
  disabled-by-default diagnostics).
- **Binary sensors**: plugged-in, charging, door / window / boot open, lock,
  charger lock, online.
- **Climate**: cabin pre-conditioning (A/C, auto mode) with a target temperature;
  a run lasts the "A/C run time" option (default 30 minutes).
- **Lock**: lock the doors from Home Assistant (unlocking needs the car's
  remote-control PIN, which is not supported yet, and reports an error).
- **Covers**: windows, and sunroof / tailgate where the car has them. Opening
  really opens them — treat automations that touch these with care.
- **Switches**: scheduled charging (the charge gate), steering-wheel heat, cabin
  ventilation.
- **Buttons**: charge now / pause, flash lights, precondition battery, refresh.
- **Location tracker** (off by default — enable it in the integration's options).

## Example dashboard

A ready-made car view using only built-in cards (no extra installs) is in
[`docs/example-dashboard.yaml`](docs/example-dashboard.yaml). Replace the `aion_v`
entity prefix with your vehicle's, then paste the whole file into a new
dashboard via Dashboards → Add Dashboard → Edit → Raw configuration editor.

## Services

`gac_connect.charge_now`, `charge_pause`, `set_charge_window` (a daily
start/stop window, optionally on selected days) and `send_command` (advanced, for
the non-PIN commands by name). Climate and lock are ordinary `climate.*` /
`lock.*` actions on their entities.

Example alerts — low tyre pressure, low 12 V battery, left unlocked at home,
door / window / boot left open — are in
[`docs/example-automations.yaml`](docs/example-automations.yaml).

## Options

Poll interval, quiet hours (skip polling overnight to spare the 12 V battery),
whether the location tracker is enabled, and how long an A/C run lasts.

## Notes

- Sign-in needs a human (a slide puzzle and an SMS code); there is no headless login.
- Unlock, remote power and charger-release need the car's remote-control PIN,
  which this integration does not support yet; those commands report an error.
- Using the official app and this integration on the same account at the same time
  can occasionally sign one of them out.

## Acknowledgements

This project stands on the shoulders of the community projects that brought other
EV brands into Home Assistant and Python, among them:

- [AwangYes/BYD-re](https://github.com/AwangYes/BYD-re) — BYD
- [Hyundai-Kia-Connect/kia_uvo](https://github.com/Hyundai-Kia-Connect/kia_uvo) — Hyundai / Kia
- [bimmerconnected/bimmer_connected](https://github.com/bimmerconnected/bimmer_connected) — BMW / Mini
- [SAIC-iSmart-API/saic-python-client-ng](https://github.com/SAIC-iSmart-API/saic-python-client-ng) — MG / SAIC
- [kvanbiesen/bmw-cardata-ha](https://github.com/kvanbiesen/bmw-cardata-ha) — BMW CarData

Thanks to their authors for showing what a good community integration looks like.

## License

MIT. Built on the [`gac-connect`](https://pypi.org/project/gac-connect/) library.
