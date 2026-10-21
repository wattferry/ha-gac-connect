import { css, html, nothing, PropertyValues, TemplateResult } from "lit";
import { GacCard } from "../base";
import { ago, clock, formatNumber, HassEntity, isOn, known, moreInfo, num, timestamp } from "../ha";
import { mark, MarkKind } from "../icons";
import { COMMAND_STATES, commandLabel, outcome, refusal, Vehicle } from "../vehicle";

interface Stop {
  at: Date;
  title: string;
  detail?: string;
  kind: MarkKind;
}

interface HistoryMessage {
  states: Record<string, { s: string; a?: Record<string, any>; lu: number }[]>;
}

const CAR_ALERTS: Record<string, [string, MarkKind]> = {
  charging_stopped: ["Charging stopped with the cable in", "warn"],
  left_unlocked: ["Left unlocked", "warn"],
  left_open: ["Left open", "warn"],
  window_left_open: ["Window left open", "warn"],
  sterilisation_finished: ["Sterilisation finished", "ok"],
  battery_temp_finished: ["Smart battery temp finished", "ok"],
};

const HEALTH: Record<string, [string, MarkKind, string?]> = {
  waiting: ["Starting", "wait"], ok: ["Normal", "ok"], quiet_hours: ["Quiet", "off", "Quiet hours"],
  rate_limited: ["Held", "warn", "Waiting for the request limit"], error: ["Failed", "fault"],
  auth_required: ["Sign in", "fault", "Reconfigure to sign in again"],
};

function words(value: string): string {
  return value.replace(/_/g, " ").replace(/^./, (c) => c.toUpperCase());
}

function alertKind(type: string): MarkKind {
  if (/fault|fail|anti_theft|intrusion|stopped|low|left_in/.test(type)) return "fault";
  if (/finished|done|complete/.test(type)) return "ok";
  return "warn";
}

export class GacActivityCard extends GacCard {
  protected readonly cardTitle = "Activity";
  protected readonly glyph = "activity";
  private events: Stop[] = [];
  private unsubscribe?: Promise<() => Promise<void>>;
  private subscribedTo?: string;

  static override styles = [...GacCard.styles, css`
    .health {
      display: grid;
      grid-template-columns: repeat(3, 1fr);
    }
    .health > button {
      display: flex;
      flex-direction: column;
      gap: 4px;
      padding: 0 8px 0 12px;
      border-left: 1px solid var(--gac-hair);
      min-width: 0;
    }
    .health > button:first-child {
      border-left: 0;
      padding-left: 0;
    }
    .health .value {
      display: flex;
      align-items: center;
      gap: 6px;
      font: 600 17px/1.15 var(--gac-label);
      letter-spacing: 0.02em;
    }
    .health .when {
      font-size: 13px;
      color: var(--gac-muted);
    }
    .refresh {
      margin-top: 12px;
    }
    .last .what {
      font: 600 20px/1.2 var(--gac-label);
      letter-spacing: 0.02em;
    }
    .last .note {
      margin-top: 6px;
    }
    ol {
      list-style: none;
      margin: 4px 0 0;
      padding: 0;
    }
    li {
      display: grid;
      grid-template-columns: 64px 22px 1fr;
      gap: 0 10px;
      min-height: 46px;
    }
    li time {
      padding-top: 2px;
      font: 600 14px/1.2 var(--gac-label);
      font-variant-numeric: tabular-nums;
      color: var(--gac-muted);
      text-align: right;
    }
    .route {
      position: relative;
    }
    .route::before {
      content: "";
      position: absolute;
      left: 7px;
      width: 8px;
      top: 0;
      bottom: 0;
      background: var(--gac-minor);
      box-shadow: inset 1px 0 0 var(--gac-minor-case), inset -1px 0 0 var(--gac-minor-case);
    }
    li:first-child .route::before {
      top: 9px;
    }
    li:last-child .route::before {
      bottom: auto;
      height: 10px;
    }
    .route .mark {
      position: absolute;
      left: 3px;
      top: 2px;
      width: 16px;
      height: 16px;
      background: var(--gac-land);
    }
    .stop {
      padding-bottom: 12px;
      min-width: 0;
    }
    .stop .title {
      font-weight: 500;
      line-height: 1.3;
    }
    .stop .detail {
      font-size: 13px;
      color: var(--gac-muted);
      line-height: 1.35;
    }
    .readings {
      display: grid;
      grid-template-columns: 1fr auto;
      gap: 0 12px;
    }
    .readings > button {
      display: contents;
    }
    .readings span {
      padding: 8px 0;
      border-top: 1px solid var(--gac-hair);
    }
    .readings > button:first-child span {
      border-top: 0;
    }
    .readings .num {
      font-size: 18px;
      font-weight: 600;
      text-align: right;
    }
    .readings .alert {
      display: flex;
      flex-direction: column;
      align-items: flex-end;
      gap: 2px;
      text-align: right;
    }
    .readings .alert span {
      padding: 0;
      border: 0;
    }
    .readings .alert .when {
      font-size: 13px;
      color: var(--gac-muted);
    }
    .readings > button:focus-visible span {
      outline: 2px solid var(--gac-mw);
      outline-offset: -2px;
    }
  `];

  override getCardSize(): number {
    return 10;
  }

  override disconnectedCallback(): void {
    super.disconnectedCallback();
    this.stopHistory();
  }

  override connectedCallback(): void {
    super.connectedCallback();
    if (this.subscribedTo) {
      this.subscribedTo = undefined;
      this.requestUpdate();
    }
  }

  private stopHistory(): void {
    this.unsubscribe?.then((stop) => stop()).catch(() => undefined);
    this.unsubscribe = undefined;
  }

  protected override updated(changed: PropertyValues): void {
    super.updated(changed);
    const vehicle = this.vehicle;
    if (!vehicle || !this.hass) return;
    const ids = ["event.car_alert", "event.gac_alert"].map((key) => vehicle.id(key)).filter(Boolean) as string[];
    const key = ids.join(",");
    if (!ids.length || key === this.subscribedTo) return;
    this.stopHistory();
    this.subscribedTo = key;
    this.events = [];
    const start = new Date(Date.now() - 48 * 3600_000).toISOString();
    this.unsubscribe = this.hass.connection.subscribeMessage<HistoryMessage>((message) => this.onHistory(message), {
      type: "history/stream", entity_ids: ids, start_time: start, minimal_response: false, no_attributes: false,
      significant_changes_only: false,
    });
    this.unsubscribe.catch(() => undefined);
  }

  private onHistory(message: HistoryMessage): void {
    const vehicle = this.vehicle;
    if (!vehicle) return;
    const carAlert = vehicle.id("event.car_alert");
    const stops: Stop[] = [];
    for (const [entityId, entries] of Object.entries(message.states ?? {})) {
      for (const entry of entries) {
        const at = new Date(entry.s);
        const type: string | undefined = entry.a?.event_type;
        if (!type || Number.isNaN(at.getTime())) continue;
        if (entityId === carAlert) {
          const [title, kind] = CAR_ALERTS[type] ?? [words(type), "warn"];
          const windows: string[] | undefined = entry.a?.windows;
          stops.push({ at, title, kind, detail: windows?.length ? windows.map(words).join(", ") : "Car alert" });
        } else {
          stops.push({ at, title: words(type), kind: alertKind(type), detail: "GAC alert" });
        }
      }
    }
    // Home Assistant records a restored event again at each restart, with the same event time: one stop each.
    const unique = new Map([...this.events, ...stops].map((s) => [`${s.at.getTime()}|${s.title}`, s]));
    this.events = [...unique.values()].sort((a, b) => b.at.getTime() - a.at.getTime()).slice(0, 20);
    this.requestUpdate();
  }

  private commandStops(last: HassEntity | undefined): Stop[] {
    const recent: { command: string; state: string; failure_reason?: string; requested_at: string }[] =
      last?.attributes.recent_commands ?? [];
    return recent.map((r) => {
      const kinds: Record<string, MarkKind> = { ok: "ok", refused: "fault", unconfirmed: "warn", pending: "wait",
                                                quiet: "off" };
      const isLast = last?.attributes.command === r.command && last?.attributes.requested_at === r.requested_at;
      const why = outcome(r.state) === "refused" ? (isLast ? refusal(last) : r.failure_reason) : undefined;
      return { at: new Date(r.requested_at), title: commandLabel(r.command), kind: kinds[outcome(r.state)],
               detail: `${COMMAND_STATES[r.state] ?? words(r.state)}${why ? `: ${why}` : ""}` };
    });
  }

  private health(vehicle: Vehicle): TemplateResult {
    const online = isOn(vehicle.get("binary_sensor.online"));
    const freshness = vehicle.get("sensor.data_freshness");
    const report = vehicle.get("sensor.last_report");
    const polling = vehicle.get("sensor.polling_status");
    const [pollText, pollKind, pollDetail] = known(polling) ? HEALTH[polling.state] ?? [words(polling.state), "off"]
      : ["Unknown", "off" as MarkKind];
    const pollWhy = polling?.state === "error" ? polling.attributes.last_error_reason : pollDetail;
    const fresh = freshness?.state;
    const reportKind: MarkKind = fresh === "recent" ? "ok" : fresh === "stale" || fresh === "clock_mismatch" ? "warn"
      : "off";
    const reportText = fresh === "recent" ? "Recent" : fresh === "stale" ? "Old" : fresh === "clock_mismatch"
      ? "Clock ahead" : "Unknown";
    return html`<div class="sec">
      <div class="health">
        <button class="tap" @click=${() => moreInfo(this, vehicle.id("binary_sensor.online"))}>
          <span class="lab">Car</span>
          <span class="value">${mark(online === false ? "fault" : online ? "ok" : "off")}${
            online === false ? "Offline" : online ? "Online" : "Unknown"}</span>
        </button>
        <button class="tap" @click=${() => moreInfo(this, vehicle.id("sensor.last_report"))}>
          <span class="lab">Report</span>
          <span class="value">${mark(reportKind)}${reportText}</span>
          <span class="when">${known(report) ? ago(this.hass!, timestamp(report)) : "none yet"}</span>
        </button>
        <button class="tap" @click=${() => moreInfo(this, polling?.entity_id)}>
          <span class="lab">Polling</span>
          <span class="value">${mark(pollKind)}${pollText}</span>
          ${pollWhy ? html`<span class="when">${pollWhy}</span>` : nothing}
        </button>
      </div>
    </div>`;
  }

  private lastCommand(last: HassEntity | undefined): TemplateResult | typeof nothing {
    if (!known(last) || last.state === "idle") return nothing;
    const state = outcome(last.state);
    const kinds: Record<string, MarkKind> = { ok: "ok", refused: "fault", unconfirmed: "warn", pending: "wait",
                                              quiet: "off" };
    const why = state === "refused" ? refusal(last) : undefined;
    const at = last.attributes.requested_at ? new Date(last.attributes.requested_at) : undefined;
    return html`<div class="sec last">
      <div class="head"><span class="lab">Last command</span>
        <span class="lab">${at ? ago(this.hass!, at) : ""}</span></div>
      <button class="tap what" @click=${() => moreInfo(this, last.entity_id)}>${commandLabel(last.attributes.command)}
      </button>
      <p class="note ${state}">${mark(kinds[state])}<span>${COMMAND_STATES[last.state] ?? words(last.state)}${
        why ? `: ${why}` : ""}</span></p>
    </div>`;
  }

  private timeline(stops: Stop[]): TemplateResult {
    const hass = this.hass!;
    const today = new Date().toDateString();
    return html`<div class="sec">
      <div class="head"><span class="lab">Last 48 hours</span></div>
      ${stops.length ? html`<ol>${stops.map((stop) => html`<li>
        <time datetime=${stop.at.toISOString()}>${stop.at.toDateString() === today ? clock(hass, stop.at)
          : ago(hass, stop.at)}</time>
        <span class="route">${mark(stop.kind)}</span>
        <div class="stop"><div class="title">${stop.title}</div>
          ${stop.detail ? html`<div class="detail">${stop.detail}</div>` : nothing}</div>
      </li>`)}</ol>` : html`<p class="note">${mark("off")}<span>No commands or alerts yet. Car alerts appear here
        when charging stops, or the car is left unlocked or open.</span></p>`}
    </div>`;
  }

  private readings(vehicle: Vehicle): TemplateResult | typeof nothing {
    const rows = ([["sensor.aux_voltage", "12V battery", 1], ["sensor.odometer", "Odometer", 0],
                   ["sensor.trip_consumption", "Trip consumption", 1], ["sensor.pm25", "Cabin PM2.5", 0]] as const)
      .filter(([key]) => vehicle.has(key));
    const alert = vehicle.get("sensor.last_gac_alert");
    if (!rows.length && !alert) return nothing;
    return html`<div class="sec readings">
      ${rows.map(([key, label, digits]) => {
        const entity = vehicle.get(key);
        const value = num(entity);
        return html`<button class="tap" @click=${() => moreInfo(this, entity?.entity_id)}><span>${label}</span>
          <span class="num">${value === undefined ? "–" : formatNumber(this.hass!, value, digits)}<span class="unit">
            ${entity?.attributes.unit_of_measurement ?? ""}</span></span></button>`;
      })}
      ${alert ? html`<button class="tap" @click=${() => moreInfo(this, alert.entity_id)}><span>Last GAC alert</span>
        <span class="alert"><span class="num" style="font-size:15px">${known(alert)
          ? alert.attributes.title || words(alert.state) : "–"}</span>${alert.attributes.created
          ? html`<span class="when">${ago(this.hass!, new Date(alert.attributes.created))}</span>` : nothing}</span>
      </button>` : nothing}
    </div>`;
  }

  protected body(vehicle: Vehicle): TemplateResult {
    const last = vehicle.get("sensor.last_command");
    const stops = [...this.commandStops(last), ...this.events]
      .filter((s) => !Number.isNaN(s.at.getTime()) && Date.now() - s.at.getTime() < 48 * 3600_000)
      .sort((a, b) => b.at.getTime() - a.at.getTime()).slice(0, 8);
    return html`
      ${this.health(vehicle)}
      ${this.lastCommand(last)}
      ${this.timeline(stops)}
      ${this.readings(vehicle)}
    `;
  }
}
