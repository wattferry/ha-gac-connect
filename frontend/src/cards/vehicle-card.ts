import { css, html, nothing, TemplateResult } from "lit";
import { GacCard } from "../base";
import { BodyStyle, guessBody, plan, PlanState, Position } from "../car-plan";
import { ActionState } from "../controls";
import { formatNumber, HassEntity, isOn, known, moreInfo, num } from "../ha";
import { mark } from "../icons";
import { gauge, Tone } from "../roads";
import { Vehicle } from "../vehicle";

export const ACTION_CHOICES = [
  { value: "lock", label: "Lock and unlock" },
  { value: "climate", label: "A/C" },
  { value: "ventilation", label: "Ventilation" },
  { value: "boot", label: "Boot" },
  { value: "horn", label: "Sound horn" },
  { value: "lights", label: "Flash lights" },
  { value: "windows", label: "Windows" },
  { value: "sunroof", label: "Sunroof" },
  { value: "charge_now", label: "Charge now" },
  { value: "refresh", label: "Refresh" },
];

const DEFAULT_ACTIONS = ["lock", "climate", "ventilation", "windows", "boot", "sunroof", "horn", "lights"];
const MAX_ACTIONS = 9;
/** How long after a horn command the button offers to stop it. */
const HORN_SECONDS = 30;

interface Action {
  key: string;
  label: string;
  icon: string;
  state: ActionState;
  hold?: boolean;
  hint?: string;
  run: () => void;
}

const POSITIONS: Position[] = ["front_left", "front_right", "rear_left", "rear_right"];
const PLACE: Record<Position, string> = {
  front_left: "Front left", front_right: "Front right", rear_left: "Rear left", rear_right: "Rear right",
};

/** Battery colour: charging is a primary route; low charge takes the warning road classes. */
export function batteryTone(soc: number | undefined, charging: boolean | undefined): Tone {
  if (charging) return "green";
  if (soc !== undefined && soc <= 10) return "red";
  if (soc !== undefined && soc <= 20) return "yellow";
  return "road";
}

export function batteryBlock(card: GacCard & { hass: any }, vehicle: Vehicle, width: number, id: string) {
  const soc = num(vehicle.get("sensor.soc"));
  const rangeEntity = vehicle.get("sensor.range");
  const range = num(rangeEntity);
  const charging = isOn(vehicle.get("binary_sensor.charging"));
  return html`<div class="battery">
    <div class="head">
      <span class="lab">Battery</span>
      <button class="tap fig" @click=${() => moreInfo(card, vehicle.id("sensor.soc"))}
        aria-label="Battery ${soc ?? "unknown"} per cent">${soc !== undefined ? Math.round(soc) : "–"}<small>&nbsp;%</small></button>
    </div>
    ${gauge({ width, fraction: soc === undefined ? undefined : soc / 100, tone: batteryTone(soc, charging),
              flowing: charging === true, id,
              marker: range !== undefined ? formatNumber(card.hass, range) : undefined,
              markerLabel: "RANGE", markerUnit: rangeEntity?.attributes.unit_of_measurement ?? "km" })}
    ${range !== undefined ? html`<span class="sr">Range ${Math.round(range)}
      ${rangeEntity?.attributes.unit_of_measurement ?? "km"}</span>` : nothing}
  </div>`;
}

export class GacVehicleCard extends GacCard {
  protected readonly cardTitle = "Vehicle";
  protected readonly glyph = "car";

  static override styles = [...GacCard.styles, css`
    .battery .head {
      align-items: flex-end;
      margin-bottom: 2px;
    }
    .battery .fig {
      font-size: 48px;
    }
    .photo {
      display: block;
      width: 100%;
      height: 148px;
      object-fit: cover;
      border-bottom: 1px solid var(--gac-hair);
    }
    .car {
      display: grid;
      grid-template-columns: minmax(170px, 200px) 1fr;
      gap: 0 16px;
      align-items: stretch;
    }
    .plan {
      display: block;
      width: 100%;
      height: auto;
    }
    .side {
      display: flex;
      flex-direction: column;
      justify-content: space-between;
      gap: 12px;
      min-width: 0;
      border-left: 1px solid var(--gac-hair);
      padding-left: 16px;
    }
    .status {
      list-style: none;
      margin: 0;
      padding: 4px 0 0;
      display: flex;
      flex-direction: column;
      gap: 8px;
      font-size: 14px;
      line-height: 1.3;
    }
    .status li {
      display: flex;
      align-items: flex-start;
      gap: 7px;
    }
    .status .mark {
      margin-top: 2px;
    }
    .temps {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 10px 8px;
      border-top: 1px solid var(--gac-hair);
      padding-top: 10px;
    }
    .temps button {
      display: flex;
      flex-direction: column;
      gap: 2px;
      min-width: 0;
    }
    .temps .num {
      font-size: 22px;
      font-weight: 600;
      line-height: 1.05;
      overflow-wrap: anywhere;
    }
    .temps .unit {
      font-size: 13px;
    }
    /* Odometer and trip: a full-width row each, so their longer values keep the unit beside them. */
    .temps .long {
      grid-column: 1 / -1;
      flex-direction: row;
      flex-wrap: wrap;
      justify-content: space-between;
      align-items: baseline;
      column-gap: 8px;
    }
    .temps .long .num {
      font-size: 17px;
    }
    .temps .long .unit {
      font-size: 12px;
    }
    .tyres {
      display: grid;
      grid-template-columns: repeat(4, 1fr);
      margin-top: 6px;
    }
    .tyres button {
      display: flex;
      flex-direction: column;
      align-items: flex-start;
      gap: 2px;
      padding: 2px 0 2px 10px;
      border-left: 1px solid var(--gac-hair);
    }
    .tyres button:first-child {
      border-left: 0;
      padding-left: 0;
    }
    .tyres .num {
      font-size: 24px;
      font-weight: 600;
      line-height: 1;
    }
    .tyres .low {
      color: var(--gac-red-ink);
    }
    .tyres .heat {
      font: 500 14px/1.2 var(--gac-label);
      font-variant-numeric: tabular-nums;
      color: var(--gac-muted);
    }
    .tyres .lab {
      display: flex;
      align-items: center;
      gap: 4px;
    }
    .actions .note {
      margin-top: 10px;
    }
    @container (max-width: 380px) {
      .car {
        grid-template-columns: 1fr;
      }
      .plan {
        max-width: 230px;
        margin: 0 auto;
      }
      .side {
        border-left: 0;
        padding-left: 0;
        margin-top: 8px;
      }
      .status {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 6px 12px;
      }
    }
  `];

  override getCardSize(): number {
    return 11;
  }

  protected override plateTitle(vehicle: Vehicle): string {
    return vehicle.name;
  }

  protected override plateNote(): string {
    return "Vehicle";
  }

  private body_style(vehicle: Vehicle): BodyStyle {
    const chosen = this.config.body as BodyStyle | undefined;
    return chosen ?? guessBody(vehicle.model);
  }

  private planState(vehicle: Vehicle): PlanState {
    const doors: PlanState["doors"] = {};
    const windows: PlanState["windows"] = {};
    for (const p of POSITIONS) {
      doors[p] = isOn(vehicle.get(`binary_sensor.${p}_door`));
      windows[p] = isOn(vehicle.get(`binary_sensor.${p}_window`));
    }
    const sunroof = vehicle.get("cover.sunroof");
    return {
      doors, windows,
      boot: isOn(vehicle.get("binary_sensor.hatch_open")) ?? (vehicle.get("cover.tailgate")?.state === "open"),
      bonnet: isOn(vehicle.get("binary_sensor.hood_open")),
      sunroof: sunroof ? (known(sunroof) ? sunroof.state === "open" : false) : undefined,
      lights: {
        headlights: isOn(vehicle.get("binary_sensor.headlights")),
        highBeam: isOn(vehicle.get("binary_sensor.high_beam")),
        rearFog: isOn(vehicle.get("binary_sensor.rear_fog_light")),
        indicators: isOn(vehicle.get("binary_sensor.turn_signal")),
      },
    };
  }

  private openItems(vehicle: Vehicle, state: PlanState): TemplateResult {
    const items: TemplateResult[] = [];
    const lock = vehicle.get("lock.doors");
    const unlocked = isOn(vehicle.get("binary_sensor.locked"));
    const locked = lock && known(lock) ? lock.state === "locked" : unlocked === undefined ? undefined : !unlocked;
    if (lock?.state === "open") items.push(html`<li>${mark("off")}Not locked</li>`);
    else if (locked !== undefined) {
      items.push(html`<li>${mark(locked ? "ok" : "off")}${locked ? "Locked" : "Unlocked"}</li>`);
    }
    const alarm = isOn(vehicle.get("binary_sensor.anti_theft"));
    if (alarm !== undefined) items.push(html`<li>${mark(alarm ? "ok" : "off")}${alarm ? "Alarm armed" : "Alarm off"}</li>`);
    const doors = POSITIONS.filter((p) => state.doors[p]);
    const windows = POSITIONS.filter((p) => state.windows[p]);
    const open: string[] = [];
    if (doors.length === 4) open.push("All doors open");
    else doors.forEach((p) => open.push(`${PLACE[p]} door open`));
    if (state.boot) open.push("Boot open");
    if (state.bonnet) open.push("Bonnet open");
    if (state.sunroof) open.push("Sunroof open");
    if (windows.length > 1) open.push(`${windows.length} windows open`);
    else windows.forEach((p) => open.push(`${PLACE[p]} window open`));
    open.forEach((text) => items.push(html`<li>${mark("warn")}${text}</li>`));
    if (isOn(vehicle.get("binary_sensor.brake_fluid"))) items.push(html`<li>${mark("fault")}Check brake fluid</li>`);
    const anyKnown = Object.values(state.doors).some((v) => v !== undefined) || state.boot !== undefined;
    if (!open.length && anyKnown) items.push(html`<li>${mark("ok")}All closed</li>`);
    const lights = state.lights ?? {};
    if (lights.indicators) items.push(html`<li>${mark("warn")}Indicators flashing</li>`);
    if (lights.highBeam) items.push(html`<li>${mark("lamp")}High beams on</li>`);
    else if (lights.headlights) items.push(html`<li>${mark("lamp")}Headlights on</li>`);
    if (lights.rearFog) items.push(html`<li>${mark("lamp")}Rear fog light on</li>`);
    return html`<ul class="status" aria-label="Car status">${items}</ul>`;
  }

  /** Pressure and temperature for each tyre the car reports; a tyre with neither is left out. */
  private tyres(vehicle: Vehicle): TemplateResult | typeof nothing {
    const tyres = [1, 2, 3, 4].map((i) => ({
      i, pressure: vehicle.get(`sensor.tyre_${i}_pressure`), temp: vehicle.get(`sensor.tyre_${i}_temp`),
    })).filter((t) => t.pressure || t.temp);
    if (!tyres.length) return nothing;
    const limit = Number(this.config.tyre_warning_kpa) || undefined;
    const toKpa: Record<string, number> = { kPa: 1, psi: 6.894757, bar: 100, Pa: 0.001, hPa: 0.1 };
    const unit = tyres.find((t) => t.pressure)?.pressure?.attributes.unit_of_measurement;
    return html`<div class="sec">
      <div class="head"><span class="lab">Tyres</span>${unit ? html`<span class="lab">${unit}</span>` : nothing}</div>
      <div class="tyres">
        ${tyres.map(({ i, pressure, temp }) => {
          const value = num(pressure);
          const heat = num(temp);
          const factor = toKpa[pressure?.attributes.unit_of_measurement ?? "kPa"] ?? 1;
          const low = limit !== undefined && value !== undefined && value * factor < limit;
          const said = [value !== undefined ? `${value} ${unit ?? ""}` : undefined,
                        heat !== undefined ? `${heat} ${temp?.attributes.unit_of_measurement ?? "°C"}` : undefined]
            .filter(Boolean).join(", ");
          return html`<button class="tap" @click=${() => moreInfo(this, (pressure ?? temp)?.entity_id)}
            aria-label="Tyre ${i}: ${said || "no reading"}${low ? ", below your warning level" : ""}">
            <span class="lab">${low ? mark("fault") : nothing}Tyre ${i}</span>
            ${pressure ? html`<span class="num ${low ? "low" : ""}">${value === undefined ? "–"
              : formatNumber(this.hass!, value)}</span>` : nothing}
            ${temp ? html`<span class="heat">${heat === undefined ? "–" : formatNumber(this.hass!, heat)}${
              temp.attributes.unit_of_measurement ?? "°C"}</span>` : nothing}
          </button>`;
        })}
      </div></div>`;
  }

  private actions(vehicle: Vehicle): Action[] {
    const chosen = Array.isArray(this.config.actions) ? this.config.actions as string[] : DEFAULT_ACTIONS;
    const out: Action[] = [];
    for (const key of chosen) {
      const action = this.action(vehicle, key);
      if (action) out.push(action);
      if (out.length === MAX_ACTIONS) break;
    }
    return out;
  }

  private cover(vehicle: Vehicle, key: string, entityKey: string, noun: string, glyph: string,
                prefix: string): Action | undefined {
    const cover = vehicle.get(entityKey);
    if (!cover) return undefined;
    const moving = cover.state === "opening" || cover.state === "closing";
    const open = cover.state === "open";
    return {
      key, icon: glyph, hold: !open,
      label: cover.state === "opening" ? "Opening…" : cover.state === "closing" ? "Closing…"
        : open ? `Close ${noun}` : `Open ${noun}`,
      state: this.actionState(vehicle, [prefix], false, moving),
      run: () => vehicle.call("cover", open ? "close_cover" : "open_cover", entityKey),
    };
  }

  private toggle(vehicle: Vehicle, key: string, entityKey: string, label: string, glyph: string,
                 prefix: string): Action | undefined {
    const entity = vehicle.get(entityKey);
    if (!entity) return undefined;
    const on = entity.state === "on";
    return {
      key, label, icon: glyph, state: known(entity) ? this.actionState(vehicle, [prefix], on) : "unavailable",
      run: () => vehicle.call("switch", on ? "turn_off" : "turn_on", entityKey),
    };
  }

  private press(vehicle: Vehicle, key: string, entityKey: string, label: string, glyph: string,
                prefix: string): Action | undefined {
    if (!vehicle.get(entityKey)) return undefined;
    return { key, label, icon: glyph, state: this.actionState(vehicle, [prefix]),
             run: () => vehicle.call("button", "press", entityKey) };
  }

  /** Sounding the horn takes a hold; for a while after, one tap stops it. */
  private horn(vehicle: Vehicle, key: string): Action | undefined {
    if (!vehicle.get("button.horn")) return undefined;
    const last = vehicle.get("sensor.last_command");
    const at = last?.attributes.requested_at ? new Date(last.attributes.requested_at).getTime() : 0;
    const age = Date.now() - at;
    const sounding = last?.attributes.command === "horn-on" && age < HORN_SECONDS * 1000
      && !["rejected", "failed", "cancelled"].includes(last.state);
    if (sounding) {
      window.clearTimeout(this.hornTimer);
      this.hornTimer = window.setTimeout(() => this.requestUpdate(), HORN_SECONDS * 1000 - age + 100);
      return { key, label: "Stop horn", icon: "horn", state: vehicle.pending(["horn-off"]) ? "pending" : "on",
               run: () => vehicle.action("send_command", { command: "horn-off" }) };
    }
    return { key, label: "Horn", icon: "horn", hold: true, state: this.actionState(vehicle, ["horn"]),
             run: () => vehicle.call("button", "press", "button.horn") };
  }

  private hornTimer?: number;

  override disconnectedCallback(): void {
    super.disconnectedCallback();
    window.clearTimeout(this.hornTimer);
  }

  private action(vehicle: Vehicle, key: string): Action | undefined {
    switch (key) {
      case "lock": {
        const lock = vehicle.get("lock.doors");
        if (!lock) return undefined;
        const allowed = vehicle.get("switch.allow_remote_unlock");
        const moving = lock.state === "locking" || lock.state === "unlocking";
        const locked = lock.state === "locked";
        if (moving) {
          return { key, label: lock.state === "locking" ? "Locking…" : "Unlocking…", icon: "lock",
                   state: "pending", run: () => undefined };
        }
        if (locked && allowed && allowed.state !== "on") {
          return { key, label: "Locked", icon: "lock", state: "unavailable",
                   hint: "Remote unlocking is off. Turn it on in Settings to unlock from here.", run: () => undefined };
        }
        return {
          key, label: locked ? "Unlock" : "Lock", icon: locked ? "unlock" : "lock", hold: locked,
          state: this.actionState(vehicle, ["lock", "unlock"]),
          run: () => vehicle.call("lock", locked ? "unlock" : "lock", "lock.doors"),
        };
      }
      case "climate": return this.toggle(vehicle, key, "switch.climate_power", "A/C", "ac", "aircon");
      case "ventilation": return this.toggle(vehicle, key, "switch.ventilation", "Vent", "vent", "ventilate");
      case "lights": return this.toggle(vehicle, key, "switch.lights", "Lights", "lights", "flash");
      case "boot": return this.cover(vehicle, key, "cover.tailgate", "boot", "boot", "tailgate");
      case "windows": return this.cover(vehicle, key, "cover.windows", "windows", "windows", "window");
      case "sunroof": return this.cover(vehicle, key, "cover.sunroof", "sunroof", "sunroof", "sunroof");
      case "horn": return this.horn(vehicle, key);
      case "refresh": return this.press(vehicle, key, "button.refresh", "Refresh", "refresh", "refresh");
      case "charge_now": return this.press(vehicle, key, "button.charge_now", "Charge now", "bolt", "charge-now");
      default: return undefined;
    }
  }

  protected body(vehicle: Vehicle): TemplateResult {
    const state = this.planState(vehicle);
    const style = this.body_style(vehicle);
    const cabin = vehicle.get("sensor.cabin_temp");
    const outside = vehicle.get("sensor.outside_temp");
    const actions = this.actions(vehicle);
    const image = typeof this.config.image === "string" && this.config.image ? this.config.image : undefined;
    const reading = (label: string, entity: HassEntity | undefined, digits = 0, long = false) => entity ? html`<button
      class="tap ${long ? "long" : ""}"
      @click=${() => moreInfo(this, entity.entity_id)}><span class="lab">${label}</span>
      <span class="num">${num(entity) !== undefined ? formatNumber(this.hass!, num(entity)!, digits) : "–"}<span
        class="unit"> ${entity.attributes.unit_of_measurement ?? ""}</span></span></button>` : undefined;
    // Beside the car: temperatures, then the distance driven and this drive's consumption.
    const readings = [reading("Cabin", cabin), reading("Outside", outside),
                      reading("Odometer", vehicle.get("sensor.odometer"), 0, true),
                      reading("Trip", vehicle.get("sensor.trip_consumption"), 1, true)].filter(Boolean);
    return html`
      ${image ? html`<img class="photo" src=${image} alt="${vehicle.name}">` : nothing}
      ${vehicle.has("sensor.soc") ? html`<div class="sec">${batteryBlock(this, vehicle, this.inner, "veh")}</div>`
        : nothing}
      <div class="sec">
        <div class="car">
          ${plan(style, state, `Plan view of ${vehicle.name}`)}
          <div class="side">
            ${this.openItems(vehicle, state)}
            ${readings.length ? html`<div class="temps">${readings}</div>` : nothing}
          </div>
        </div>
      </div>
      ${this.tyres(vehicle)}
      ${actions.length ? html`<div class="sec actions">
        <div class="grid3">
          ${actions.map((a) => html`<gac-action .label=${a.label} .icon=${a.icon} .state=${a.state}
            .hold=${a.hold ?? false} .hint=${a.hint ?? ""} @activate=${a.run}></gac-action>`)}
        </div>
        ${this.commandNote(vehicle, ["lock", "unlock", "aircon", "ventilate", "tailgate", "window", "sunroof",
                                     "horn", "flash", "charge-now"])}
      </div>` : nothing}
    `;
  }
}
