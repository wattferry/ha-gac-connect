import { css, html, nothing, TemplateResult } from "lit";
import { GacCard } from "../base";
import { hourCycle, known, navigate, num, timeOfDay } from "../ha";
import { icon, mark } from "../icons";
import { Vehicle } from "../vehicle";

type Toggle = [key: string, title: string, desc: string, holdOn?: boolean];

const GROUPS: [string, Toggle[]][] = [
  ["Remote permissions", [
    ["switch.allow_remote_unlock", "Remote unlocking", "Lets the Vehicle card and the Doors lock unlock the car.", true],
    ["switch.allow_charger_unlock", "Release charging cable",
     "Shows Release cable on the Charging card. It stops charging.", true],
    ["switch.allow_vehicle_shutdown", "Remote shutdown", "Shows Turn vehicle off below.", true],
  ]],
  ["Location", [
    ["switch.track_parked", "Track when parked", "Shows the position while the car is switched off."],
    ["switch.track_moving", "Track when switched on", "Follows the car while it is switched on."],
  ]],
  ["Alerts and push", [
    ["switch.allow_account_alerts", "GAC account alerts",
     "Refreshes GAC's alert list every 10 minutes. Signing in with the official app prevents GAC alerts from "
     + "appearing here."],
    ["switch.allow_plaintext_push", "Unencrypted push",
     "Faster command results through GAC's push feed, whose login and topic names travel unencrypted.", true],
  ]],
];

const CHOICES = [
  { value: "automatic", label: "Auto" }, { value: "always", label: "Always" }, { value: "omit", label: "Omit" },
];

function interval(seconds: number): string {
  if (seconds < 60) return `${seconds} s`;
  if (seconds % 60 === 0) return `${seconds / 60} min`;
  return `${Math.floor(seconds / 60)} min ${seconds % 60} s`;
}

export class GacSettingsCard extends GacCard {
  protected readonly cardTitle = "Settings";
  protected readonly glyph = "settings";
  private entitiesOpen = false;
  private quietLive?: { start?: number; stop?: number };
  private filter = "";

  static override styles = [...GacCard.styles, css`
    .row gac-switch {
      margin-right: -6px;
    }
    input {
      height: 44px;
      width: 100%;
      padding: 0 10px;
      color: var(--gac-ink);
      background: var(--gac-paper);
      border: 1px solid var(--gac-edge);
      border-radius: 2px;
    }
    input[type="search"] {
      font: 400 15px/1 var(--gac-text);
      margin-bottom: 8px;
    }
    input:focus-visible,
    summary:focus-visible,
    .link:focus-visible {
      outline: 2px solid var(--gac-mw);
      outline-offset: 1px;
    }
    input:disabled {
      color: var(--gac-muted);
      border-style: dotted;
    }
    .field + .field,
    .grid2 {
      margin-top: 8px;
    }
    .field .lab {
      display: block;
      margin-bottom: 6px;
    }
    summary {
      display: flex;
      align-items: center;
      gap: 8px;
      min-height: 44px;
      cursor: pointer;
      list-style: none;
    }
    summary::-webkit-details-marker {
      display: none;
    }
    summary svg,
    .link svg {
      width: 18px;
      height: 18px;
      margin-left: auto;
      transition: transform 150ms ease-out;
    }
    details[open] summary svg {
      transform: rotate(90deg);
    }
    .entity {
      padding: 8px 0;
      border-top: 1px solid var(--gac-hair);
    }
    .entity .title {
      font-size: 14px;
      margin-bottom: 6px;
    }
    .link {
      display: flex;
      align-items: center;
      gap: 8px;
      width: 100%;
      min-height: 44px;
      padding: 0;
      background: none;
      border: 0;
      color: var(--gac-ink);
      font: 600 15px/1 var(--gac-label);
      letter-spacing: 0.08em;
      text-transform: uppercase;
      cursor: pointer;
    }
  `];

  override getCardSize(): number {
    return 14;
  }

  private toggles(vehicle: Vehicle, title: string, toggles: Toggle[]): TemplateResult | typeof nothing {
    const shown = toggles.filter(([key]) => vehicle.has(key));
    if (!shown.length) return nothing;
    return html`<div class="sec"><div class="head"><span class="lab">${title}</span></div>
      ${shown.map(([key, name, desc, holdOn]) => {
        const entity = vehicle.get(key)!;
        const on = entity.state === "on";
        return html`<div class="row"><div class="what"><div class="title">${name}</div><div class="desc">${desc}</div>
          </div><gac-switch label=${name} .checked=${on} ?hold-on=${holdOn === true} ?disabled=${!known(entity)}
            @change=${() => vehicle.call("switch", on ? "turn_off" : "turn_on", key)}></gac-switch></div>`;
      })}</div>`;
  }

  private polling(vehicle: Vehicle): TemplateResult | typeof nothing {
    const poll = vehicle.get("number.polling_interval");
    const quiet = vehicle.get("switch.quiet_hours");
    const start = vehicle.get("time.quiet_hours_start");
    const end = vehicle.get("time.quiet_hours_end");
    if (!poll && !quiet) return nothing;
    const quietOn = quiet?.state === "on";
    const minutes = (entity = start) => {
      const match = known(entity) ? /^(\d{1,2}):(\d{2})/.exec(entity.state) : null;
      return match ? Number(match[1]) * 60 + Number(match[2]) : undefined;
    };
    const clock = (m?: number) => m === undefined ? "––:––"
      : `${String(Math.floor(m / 60)).padStart(2, "0")}:${String(m % 60).padStart(2, "0")}`;
    const shown = (m?: number) => timeOfDay(this.hass!, m);
    const from = this.quietLive?.start ?? minutes(start);
    const until = this.quietLive?.stop ?? minutes(end);
    return html`<div class="sec"><div class="head"><span class="lab">Polling</span></div>
      ${poll ? html`<div class="field"><div class="title" style="margin-bottom:6px">Read the car every</div>
        <gac-stepper .value=${num(poll)} .min=${Number(poll.attributes.min ?? 60)}
          .max=${Number(poll.attributes.max ?? 3600)} .step=${60} .format=${interval} label="poll interval"
          @change=${(e: CustomEvent) => vehicle.call("number", "set_value", "number.polling_interval",
                                                      { value: e.detail.value })}></gac-stepper></div>` : nothing}
      ${quiet ? html`<div class="row" style="margin-top:4px"><div class="what"><div class="title">Quiet hours</div>
        <div class="desc">No polling ${start && end ? `from ${shown(from)} until ${shown(until)}` : "at night"}.</div>
        </div>
        <gac-switch label="Quiet hours" .checked=${quietOn}
          @change=${() => vehicle.call("switch", quietOn ? "turn_off" : "turn_on", "switch.quiet_hours")}></gac-switch>
      </div>` : nothing}
      ${start && end ? html`<gac-day-range .start=${minutes(start)} .stop=${minutes(end)} ?disabled=${!quietOn}
        ?twelve=${hourCycle(this.hass!)}
        start-label="Quiet hours start" stop-label="Quiet hours end"
        @input=${(e: CustomEvent) => { this.quietLive = { start: e.detail.start, stop: e.detail.stop };
                                       this.requestUpdate(); }}
        @change=${(e: CustomEvent) => {
          this.quietLive = undefined;
          const which = e.detail.which as "start" | "stop";
          vehicle.call("time", "set_value", `time.quiet_hours_${which === "start" ? "start" : "end"}`,
                       { time: `${clock(e.detail[which])}:00` });
        }}></gac-day-range>` : nothing}
    </div>`;
  }

  private vehicleActions(vehicle: Vehicle): TemplateResult | typeof nothing {
    const refresh = vehicle.has("button.refresh_capabilities");
    const off = vehicle.has("button.vehicle_power_off");
    if (!refresh && !off) return nothing;
    return html`<div class="sec"><div class="head"><span class="lab">Vehicle</span></div>
      <div class="grid2">
        ${refresh ? html`<gac-action label="Re-read equipment" icon="refresh"
          hint="Reads the car's capability list again, for example after a software update."
          .state=${this.actionState(vehicle, ["capabilities"])}
          @activate=${() => vehicle.call("button", "press", "button.refresh_capabilities")}></gac-action>` : nothing}
        ${off ? html`<gac-action label="Turn car off" icon="power" hold hint="Switches the car off."
          .state=${this.actionState(vehicle, ["vehicle-power-off"])}
          @activate=${() => vehicle.call("button", "press", "button.vehicle_power_off")}></gac-action>` : nothing}
      </div>
      ${this.commandNote(vehicle, ["vehicle-power-off"])}
    </div>`;
  }

  private entities(vehicle: Vehicle): TemplateResult | typeof nothing {
    const choices = vehicle.get("sensor.entity_choices");
    if (!choices) return nothing;
    const all: Record<string, string> = choices.attributes.entities ?? {};
    const always = new Set<string>(choices.attributes.always_show ?? []);
    const omit = new Set<string>(choices.attributes.omit ?? []);
    const query = this.filter.trim().toLowerCase();
    const rows = Object.entries(all).filter(([key, label]) => !query || label.toLowerCase().includes(query)
      || key.includes(query));
    return html`<div class="sec">
      <details ?open=${this.entitiesOpen} @toggle=${(e: Event) => {
        this.entitiesOpen = (e.target as HTMLDetailsElement).open;
        this.requestUpdate();
      }}>
        <summary><span class="lab">Entity choices</span><span class="muted" style="font-size:14px">${
          known(choices) && Number(choices.state) > 0 ? `${choices.state} set` : "all automatic"}</span>${
          icon("chevron")}</summary>
        ${this.entitiesOpen ? html`
          <p class="note">${mark("info")}<span>Auto follows the car's capability list. Each change reloads GAC
            Connect for a few seconds.</span></p>
          <input type="search" placeholder="Filter entities" aria-label="Filter entities" .value=${this.filter}
            @input=${(e: Event) => { this.filter = (e.target as HTMLInputElement).value; this.requestUpdate(); }}>
          ${rows.map(([key, label]) => html`<div class="entity"><div class="title">${label}</div>
            <gac-segments label=${label} .options=${CHOICES}
              .value=${always.has(key) ? "always" : omit.has(key) ? "omit" : "automatic"}
              @change=${(e: CustomEvent) => vehicle.action("set_entity_visibility",
                                                             { entity: key, visibility: e.detail.value })}>
            </gac-segments></div>`)}` : nothing}
      </details>
    </div>`;
  }

  protected body(vehicle: Vehicle): TemplateResult {
    return html`
      ${GROUPS.map(([title, toggles]) => this.toggles(vehicle, title, toggles))}
      ${this.polling(vehicle)}
      ${this.vehicleActions(vehicle)}
      ${this.entities(vehicle)}
      <div class="sec"><button class="link" @click=${() => navigate(this, `/config/devices/device/${
        vehicle.deviceId}`)}>Device page and diagnostics${icon("chevron")}</button></div>
    `;
  }
}
