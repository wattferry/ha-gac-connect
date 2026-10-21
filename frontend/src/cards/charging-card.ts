import { css, html, nothing, TemplateResult } from "lit";
import { GacCard } from "../base";
import { clock, duration, firstWeekday, formatNumber, hourCycle, isOn, known, moreInfo, num, timeOfDay,
         weekdayName } from "../ha";
import { mark } from "../icons";
import { dayRoad } from "../roads";
import { Vehicle } from "../vehicle";
import { batteryBlock } from "./vehicle-card";

/** The day switches' keys, the English short names the car's report uses, and the weekday (0 Sunday). */
const DAYS = [
  ["mon", "Mon", 1], ["tue", "Tue", 2], ["wed", "Wed", 3], ["thu", "Thu", 4], ["fri", "Fri", 5], ["sat", "Sat", 6],
  ["sun", "Sun", 0],
] as const;

const SCHEDULE: Record<string, string> = {
  unrestricted: "Whenever plugged in", scheduled: "Scheduled charging", not_set: "Not set, won't charge",
  not_reported: "Not reported",
};

/** "23:30", "23:30:00" or a time entity's state, as minutes after midnight. */
function minutes(value: unknown): number | undefined {
  if (typeof value !== "string") return undefined;
  const match = /^(\d{1,2}):(\d{2})/.exec(value);
  return match ? Number(match[1]) * 60 + Number(match[2]) : undefined;
}

function hhmm(total: number | undefined): string {
  if (total === undefined) return "––:––";
  return `${String(Math.floor(total / 60)).padStart(2, "0")}:${String(total % 60).padStart(2, "0")}`;
}

export class GacChargingCard extends GacCard {
  protected readonly cardTitle = "Charging";
  protected readonly glyph = "plug";

  static override styles = [...GacCard.styles, css`
    .state .lab {
      display: flex;
      align-items: center;
      gap: 6px;
    }
    .state .fig {
      margin-top: 6px;
    }
    .state .fig small + small {
      margin-left: 0;
    }
    .battery .fig {
      font-size: 32px;
    }
    .cells {
      display: grid;
      grid-template-columns: repeat(3, 1fr);
    }
    .cells > button {
      display: flex;
      flex-direction: column;
      gap: 2px;
      padding-left: 12px;
      border-left: 1px solid var(--gac-hair);
    }
    .cells > button:first-child {
      padding-left: 0;
      border-left: 0;
    }
    .state .when {
      display: block;
      margin-top: 6px;
      font-size: 13px;
      color: var(--gac-muted);
    }
    .reading {
      font-size: 22px;
      font-weight: 600;
    }
    button.row {
      width: 100%;
    }
    .cells .num {
      font-size: 22px;
      font-weight: 600;
    }
    .window {
      font: 600 30px/1 var(--gac-label);
      font-variant-numeric: tabular-nums;
      letter-spacing: 0.01em;
      margin: 2px 0 6px;
    }
    .schedule .head .lab:last-child {
      color: var(--gac-ink);
    }
    .days {
      display: grid;
      grid-template-columns: repeat(7, 1fr);
      gap: 4px;
      margin-top: 10px;
    }
    .days button {
      height: 44px;
      padding: 0;
      font: 600 14px/1 var(--gac-label);
      letter-spacing: 0.04em;
      color: var(--gac-muted);
      background: none;
      border: 1px solid var(--gac-hair);
      border-radius: 2px;
      cursor: pointer;
    }
    .days button[aria-pressed="true"] {
      background: var(--gac-mw);
      border-color: var(--gac-mw-case);
      color: var(--gac-mw-ink);
    }
    .days button:focus-visible {
      outline: 2px solid var(--gac-mw);
      outline-offset: 1px;
    }
    .days button:disabled {
      cursor: wait;
      opacity: 0.6;
    }
    .send {
      margin-top: 10px;
    }
    .differs {
      margin-top: 10px;
    }
    .row gac-switch {
      margin-right: -6px;
    }
  `];

  override getCardSize(): number {
    return 12;
  }

  private statusBlock(vehicle: Vehicle): TemplateResult | typeof nothing {
    if (!vehicle.has("binary_sensor.plugged") && !vehicle.has("binary_sensor.charging")) return nothing;
    const plugged = isOn(vehicle.get("binary_sensor.plugged"));
    const charging = isOn(vehicle.get("binary_sensor.charging"));
    const power = num(vehicle.get("sensor.charge_power"));
    const left = num(vehicle.get("sensor.charge_time"));
    const schedule = vehicle.get("sensor.charge_schedule");
    const kind = charging ? "ok" : plugged ? "info" : "off";
    const word = charging ? "Charging" : plugged ? "Plugged in" : plugged === false ? "Not plugged in" : "Plug unknown";
    const time = left !== undefined && charging ? duration(left) : undefined;
    const released = isOn(vehicle.get("binary_sensor.charger_locked"));
    const connector = plugged && released !== undefined ? (released ? "Connector released" : "Connector locked")
      : undefined;
    return html`<div class="sec duo state">
      <button class="tap" @click=${() => moreInfo(this, vehicle.id("binary_sensor.charging"))}>
        <span class="lab">${mark(kind)}${word}</span>
        ${charging && power !== undefined
          ? html`<span class="fig">${formatNumber(this.hass!, power, power < 10 ? 1 : 0)}<small>&nbsp;kW</small></span>`
          : html`<span class="fig muted">${charging ? "–" : plugged ? "Waiting" : "–"}</span>`}
        ${connector ? html`<span class="when">${connector}</span>` : nothing}
      </button>
      <button class="tap" @click=${() => moreInfo(this, vehicle.id(charging ? "sensor.charge_time"
                                                                     : "sensor.charge_schedule"))}>
        <span class="lab">${charging ? "Time left" : "Schedule"}</span>
        ${charging
          ? html`<span class="fig">${time ? this.splitDuration(time) : "–"}</span>`
          : html`<span class="fig" style="font-size:22px;margin-top:6px">${
              known(schedule) ? SCHEDULE[schedule.state] ?? schedule.state : "–"}</span>`}
      </button>
    </div>`;
  }

  /** "1 h 40 min" with the units set small. */
  private splitDuration(text: string): TemplateResult[] {
    return text.split(" ").map((part) => /^\d+$/.test(part) ? html`${part}` : html`<small>&nbsp;${part}&nbsp;</small>`);
  }

  private cells(vehicle: Vehicle): TemplateResult | typeof nothing {
    if (!isOn(vehicle.get("binary_sensor.charging"))) return nothing;
    const cells = [["Current", "sensor.charge_current", 0], ["Voltage", "sensor.charge_voltage", 0]] as const;
    const shown = cells.filter(([, key]) => vehicle.has(key));
    if (!shown.length) return nothing;
    return html`<div class="sec cells" style="grid-template-columns:repeat(${shown.length},1fr)">${shown.map(
      ([label, key, digits]) => {
      const entity = vehicle.get(key);
      const value = num(entity);
      return html`<button class="tap" @click=${() => moreInfo(this, entity?.entity_id)}>
        <span class="lab">${label}</span>
        <span class="num">${value === undefined ? "–" : formatNumber(this.hass!, value, digits)}<span
          class="unit">&nbsp;${entity?.attributes.unit_of_measurement ?? ""}</span></span></button>`;
    })}</div>`;
  }

  /** The battery's own temperature, and warming or cooling it ahead of charging or driving. */
  private battery(vehicle: Vehicle): TemplateResult | typeof nothing {
    const temp = vehicle.get("sensor.battery_temp");
    const smart = vehicle.get("switch.precondition_battery");
    if (!temp && !smart) return nothing;
    const value = num(temp);
    const on = smart?.state === "on";
    return html`<div class="sec">
      ${temp ? html`<button class="tap row" @click=${() => moreInfo(this, temp.entity_id)}>
        <div class="what"><div class="title">Battery temperature</div></div>
        <span class="num reading">${value === undefined ? "–" : formatNumber(this.hass!, value)}<span class="unit">&nbsp;${
          temp.attributes.unit_of_measurement ?? "°C"}</span></span></button>` : nothing}
      ${smart ? html`<div class="row"><div class="what"><div class="title">Smart battery temp</div>
        <div class="desc">Warms or cools the battery for charging or driving, for up to 1.5 hours.</div></div>
        <gac-switch label="Smart battery temp" .checked=${on} .pending=${vehicle.pending(["battery-precondition"])}
          ?disabled=${!known(smart)}
          @change=${() => vehicle.call("switch", on ? "turn_off" : "turn_on", "switch.precondition_battery")}>
        </gac-switch></div>` : nothing}
      ${this.commandNote(vehicle, ["battery-precondition"])}
    </div>`;
  }

  /** The car's own alert when charging stopped with the cable still in, while it is recent. */
  private stopped(vehicle: Vehicle): TemplateResult | typeof nothing {
    const alert = vehicle.get("event.car_alert");
    if (!known(alert) || alert.attributes.event_type !== "charging_stopped") return nothing;
    if (isOn(vehicle.get("binary_sensor.charging")) || isOn(vehicle.get("binary_sensor.plugged")) === false) return nothing;
    const at = new Date(alert.state);
    if (Number.isNaN(at.getTime()) || Date.now() - at.getTime() > 6 * 3600_000) return nothing;
    return html`<div class="sec"><p class="note">${mark("warn")}<span>Charging stopped at ${clock(this.hass!, at)}
      with the cable still in.</span></p></div>`;
  }

  /** The window being dragged, shown in the readout before it is sent. */
  private live?: { start?: number; stop?: number };

  private sendTimes(vehicle: Vehicle, detail: { start?: number; stop?: number; which: "start" | "stop" }): void {
    const minutes = detail[detail.which];
    if (minutes !== undefined) {
      vehicle.call("time", "set_value", `time.charge_window_${detail.which}`, { time: `${hhmm(minutes)}:00` });
    }
  }

  private schedule(vehicle: Vehicle): TemplateResult | typeof nothing {
    const schedule = vehicle.get("sensor.charge_schedule");
    const startEntity = vehicle.get("time.charge_window_start");
    const stopEntity = vehicle.get("time.charge_window_stop");
    if (!schedule && !startEntity) return nothing;
    const editing = startEntity !== undefined && stopEntity !== undefined;
    const reportedStart = minutes(schedule?.attributes.reported_start);
    const reportedStop = minutes(schedule?.attributes.reported_stop);
    const draftStart = editing ? minutes(startEntity!.state) : reportedStart;
    const draftStop = editing ? minutes(stopEntity!.state) : reportedStop;
    const shownStart = this.live?.start ?? draftStart;
    const shownStop = this.live?.stop ?? draftStop;
    const untilSoc = vehicle.get("switch.charge_window_until_soc");
    const toLimit = untilSoc?.state === "on";
    const unrestricted = schedule?.state === "unrestricted";
    const now = new Date();
    const dayEntities = DAYS.map(([key]) => vehicle.get(`switch.charge_window_${key}`));
    // Chips run from the first day of the owner's week.
    const first = firstWeekday(this.hass!);
    const weekOrder = [0, 1, 2, 3, 4, 5, 6].map((n) => DAYS.findIndex(([, , day]) => day === (first + n) % 7));
    const days = DAYS.filter((_, i) => dayEntities[i]?.state === "on").map(([, short]) => short);
    const draftDays = days.length === 7 ? "Every day" : days.length ? days.join(", ") : "One time";
    const reportedDays: string | undefined = schedule?.attributes.reported_days;
    const differs = editing && schedule && !unrestricted
      && (draftStart !== reportedStart || (!toLimit && draftStop !== reportedStop)
          || (reportedDays !== undefined && reportedDays !== "Not reported"
              && reportedDays.replace(/\s/g, "") !== draftDays.replace(/\s/g, "")));
    const sending = vehicle.pending(["charge-window", "charge-schedule"]);
    return html`<div class="sec schedule">
      <div class="head"><span class="lab">${editing ? "Charging window" : "Reported window"}</span>
        <span class="lab">${known(schedule) ? SCHEDULE[schedule.state] ?? "" : ""}</span></div>
      <div class="window" aria-live="polite">${unrestricted && !editing ? "Any time"
        : `${timeOfDay(this.hass!, shownStart)} – ${toLimit ? "charge limit" : timeOfDay(this.hass!, shownStop)}`}</div>
      ${editing ? html`<gac-day-range .start=${draftStart} .stop=${draftStop} ?open-ended=${toLimit}
          ?twelve=${hourCycle(this.hass!)}
          .now=${now.getHours() * 60 + now.getMinutes()} ?pending=${sending}
          start-label="Charging starts" stop-label="Charging stops"
          @input=${(e: CustomEvent) => { this.live = { start: e.detail.start, stop: e.detail.stop };
                                         this.requestUpdate(); }}
          @change=${(e: CustomEvent) => { this.live = undefined; this.sendTimes(vehicle, e.detail); }}>
        </gac-day-range>`
        : dayRoad({ width: this.inner, tone: unrestricted ? "green" : "road", start: unrestricted ? 0 : draftStart,
                    stop: unrestricted ? 0 : toLimit ? undefined : draftStop,
                    now: now.getHours() * 60 + now.getMinutes(), dashed: sending })}
      ${editing ? html`
        ${dayEntities.some((e) => e) ? html`<div class="days" role="group" aria-label="Repeat on">
          ${weekOrder.map((i) => {
            const [key, , weekday] = DAYS[i];
            const entity = dayEntities[i];
            if (!entity) return nothing;
            const on = entity.state === "on";
            return html`<button aria-pressed=${on ? "true" : "false"} aria-label=${weekdayName(this.hass!, weekday, "long")}
              @click=${() => vehicle.call("switch", on ? "turn_off" : "turn_on", `switch.charge_window_${key}`)}>${
              weekdayName(this.hass!, weekday, "short")}</button>`;
          })}
        </div>` : nothing}
        ${untilSoc ? html`<div class="row">
          <div class="what"><div class="title">Stop at charge limit</div>
            <div class="desc">Stops at the car's own target level instead of a stop time.</div></div>
          <gac-switch .checked=${toLimit} label="Stop at charge limit" @change=${() => vehicle.call("switch",
            toLimit ? "turn_off" : "turn_on", "switch.charge_window_until_soc")}></gac-switch>
        </div>` : nothing}
        ${differs ? html`<p class="note differs">${mark("info")}<span>The car has ${
          timeOfDay(this.hass!, reportedStart)} – ${timeOfDay(this.hass!, reportedStop)}, ${reportedDays}. Send to
          change it.</span></p>` : nothing}
        ${vehicle.has("button.send_charge_window") ? html`<gac-action class="send" label=${sending
          ? "Sending…" : "Send window to car"} icon="check" .state=${this.actionState(vehicle, ["charge-window",
          "charge-schedule"])} @activate=${() => vehicle.call("button", "press", "button.send_charge_window")}>
          </gac-action>` : nothing}
      ` : html`<p class="note">${mark("off")}<span>${reportedDays ?? "Days not reported"}</span></p>`}
    </div>`;
  }

  private actions(vehicle: Vehicle): TemplateResult | typeof nothing {
    const scheduled = vehicle.get("switch.charging");
    const items: TemplateResult[] = [];
    if (vehicle.has("button.charge_now")) {
      const charging = isOn(vehicle.get("binary_sensor.charging")) === true;
      const state = this.actionState(vehicle, ["charge-now"]);
      items.push(html`<gac-action label=${charging ? "Charging" : "Charge now"} icon="bolt"
        .state=${charging && state !== "pending" ? "unavailable" : state}
        hint=${charging ? "The car is charging." : "Charges whenever plugged in and switches the schedule off."}
        @activate=${() => !charging && vehicle.call("button", "press", "button.charge_now")}></gac-action>`);
    }
    if (vehicle.has("button.charger_unlock")) {
      // Only a locked-in cable can be released. Without a plug or lock reading, the car decides.
      const plugged = isOn(vehicle.get("binary_sensor.plugged"));
      const released = isOn(vehicle.get("binary_sensor.charger_locked"));
      const state = this.actionState(vehicle, ["charger-unlock"]);
      const [label, hint, usable] = plugged === false
        ? ["Release cable", "No cable is plugged in.", false]
        : released === true
          ? ["Cable released", "The connector is unlocked; the cable can be pulled out.", false]
          : ["Release cable", "Unlocks the charging connector so the cable can be pulled out. This stops charging.", true];
      items.push(html`<gac-action label=${label} icon="connector" .hold=${usable}
        .state=${usable || state === "pending" ? state : "unavailable"} hint=${hint}
        @activate=${() => usable && vehicle.call("button", "press", "button.charger_unlock")}></gac-action>`);
    }
    const toggle = scheduled ? html`<div class="row">
      <div class="what"><div class="title">Use charging schedule</div>
        <div class="desc">Off charges whenever the car is plugged in.</div></div>
      <gac-switch .checked=${scheduled.state === "on"} label="Use charging schedule"
        .pending=${vehicle.pending(["charge-resume", "charge-now"])}
        @change=${() => vehicle.call("switch", scheduled.state === "on" ? "turn_off" : "turn_on", "switch.charging")}>
      </gac-switch></div>` : nothing;
    if (!items.length && !scheduled) return nothing;
    return html`<div class="sec">
      ${toggle}
      ${items.length ? html`<div class="grid2" style="margin-top:${scheduled ? 8 : 0}px">${items}</div>` : nothing}
      ${this.commandNote(vehicle, ["charge-now", "charge-resume", "charge-window", "charge-schedule",
                                   "charger-unlock"])}
    </div>`;
  }

  protected body(vehicle: Vehicle): TemplateResult {
    return html`
      ${this.statusBlock(vehicle)}
      ${vehicle.has("sensor.soc") ? html`<div class="sec">${batteryBlock(this, vehicle, this.inner, "chg")}</div>`
        : nothing}
      ${this.stopped(vehicle)}
      ${this.cells(vehicle)}
      ${this.battery(vehicle)}
      ${this.schedule(vehicle)}
      ${this.actions(vehicle)}
    `;
  }
}
