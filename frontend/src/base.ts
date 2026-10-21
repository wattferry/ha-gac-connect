// What every card shares: the car lookup, the name plate, the freshness line, width tracking
// for the road drawings, and the light or dark atlas.

import { html, LitElement, nothing, PropertyValues, TemplateResult, unsafeCSS } from "lit";
import { ago, CardConfig, HomeAssistant, isOn, known, moreInfo, timestamp } from "./ha";
import { icon, mark, MarkKind } from "./icons";
import { roadStyles } from "./roads";
import { base, tokens } from "./theme";
import { ActionState } from "./controls";
import { commandLabel, outcome, refusal, Vehicle, vehicles } from "./vehicle";

export abstract class GacCard extends LitElement {
  static override properties = {
    hass: { attribute: false },
    config: { state: true },
    width: { state: true },
  };

  declare hass: HomeAssistant | undefined;
  declare config: CardConfig;
  declare width: number;
  private resizer?: ResizeObserver;
  private ticker?: number;

  /** Card name on the plate, and its glyph. */
  protected abstract readonly cardTitle: string;
  protected abstract readonly glyph: string;
  protected abstract body(vehicle: Vehicle): TemplateResult | typeof nothing;

  static override styles = [tokens, base, unsafeCSS(roadStyles)];

  constructor() {
    super();
    this.width = 320;
  }

  setConfig(config: CardConfig): void {
    if (!config || typeof config !== "object") throw new Error("Invalid configuration");
    this.config = { ...config };
  }

  static getConfigElement(): HTMLElement {
    return document.createElement("gac-card-editor");
  }

  static getStubConfig(hass: HomeAssistant): Partial<CardConfig> {
    const first = vehicles(hass)[0];
    return first ? { device: first.id } : {};
  }

  getCardSize(): number {
    return 6;
  }

  getGridOptions() {
    return { columns: 12, min_columns: 6, rows: "auto" };
  }

  override connectedCallback(): void {
    super.connectedCallback();
    this.resizer = new ResizeObserver((entries) => {
      const width = Math.round(entries[0]?.contentRect.width ?? 0);
      if (width > 0 && Math.abs(width - this.width) >= 1) this.width = width;
    });
    this.resizer.observe(this);
    this.ticker = window.setInterval(() => this.requestUpdate(), 30_000);
  }

  override disconnectedCallback(): void {
    super.disconnectedCallback();
    this.resizer?.disconnect();
    window.clearInterval(this.ticker);
  }

  protected override willUpdate(changed: PropertyValues): void {
    if (changed.has("hass") && this.hass) this.toggleAttribute("dark", this.hass.themes?.darkMode === true);
  }

  /** Width available to drawings inside a section's padding. */
  protected get inner(): number {
    return Math.max(200, this.width - (this.width <= 330 ? 26 : 34));
  }

  /** The one car this card shows: the one chosen in its editor, or the first GAC car. */
  protected get vehicle(): Vehicle | undefined {
    const hass = this.hass;
    if (!hass) return undefined;
    const chosen = this.config?.device;
    const device = (Array.isArray(chosen) ? chosen[0] : chosen) || vehicles(hass)[0]?.id;
    return device ? new Vehicle(hass, device) : undefined;
  }

  protected override render() {
    if (!this.hass || !this.config) return nothing;
    const vehicle = this.vehicle;
    if (!vehicle || !vehicle.exists) {
      return html`<ha-card>
        ${this.plate(this.cardTitle, "")}
        <div class="empty"><strong>Choose your car</strong>
          No GAC Connect vehicle was found${this.config.device ? " for the chosen car" : ""}. Edit the card and
          pick a car, or add the GAC Connect integration first.</div>
      </ha-card>`;
    }
    return html`<ha-card>
      ${this.plate(this.plateTitle(vehicle), this.plateNote(vehicle))}
      ${this.body(vehicle)}
      ${this.freshness(vehicle)}
    </ha-card>`;
  }

  protected plateTitle(vehicle: Vehicle): string {
    void vehicle;
    return this.cardTitle;
  }

  protected plateNote(vehicle: Vehicle): string {
    return vehicle.name;
  }

  protected plate(title: string, note: string): TemplateResult {
    return html`<div class="plate"><span class="ref">${icon(this.glyph)}</span>
      <span class="name" role="heading" aria-level="2">${title}</span>
      ${note ? html`<span class="lab">${note}</span>` : nothing}</div>`;
  }

  /** The foot of every card: what the car is doing and how old the reading is. */
  protected freshness(vehicle: Vehicle): TemplateResult {
    const hass = this.hass!;
    const report = vehicle.get("sensor.last_report");
    const when = timestamp(report);
    const parts: string[] = [];
    let kind: MarkKind | undefined;
    const online = isOn(vehicle.get("binary_sensor.online"));
    const polling = vehicle.get("sensor.polling_status")?.state;
    const freshness = vehicle.get("sensor.data_freshness")?.state;
    if (online === false) {
      kind = "fault";
      parts.push("Offline");
    } else if (polling === "auth_required") {
      kind = "fault";
      parts.push("Sign in again");
    } else if (polling === "error") {
      kind = "warn";
      parts.push("Refresh failed");
    } else if (polling === "rate_limited") {
      kind = "warn";
      parts.push("Waiting for the request limit");
    } else if (freshness === "stale") {
      kind = "warn";
      parts.push("Old report");
    } else if (freshness === "clock_mismatch") {
      kind = "warn";
      parts.push("Report clock ahead");
    } else if (polling === "quiet_hours") {
      kind = "off";
      parts.push("Quiet hours");
    }
    if (!kind) {
      const charging = isOn(vehicle.get("binary_sensor.charging"));
      const power = isOn(vehicle.get("binary_sensor.vehicle_power"));
      if (charging) parts.push("Charging");
      else if (power === true) parts.push("Switched on");
      else if (power === false) parts.push("Parked");
    }
    parts.push(known(report) ? `Updated ${ago(hass, when)}` : "No report yet");
    const reading = this.readingFrom !== undefined && this.readingFrom === (report?.state ?? "")
      && Date.now() - this.readingSince < 20_000;
    return html`<div class="fresh">
      <button class="tap fresh-info" @click=${() => moreInfo(this, vehicle.id("sensor.last_report"))}>
        ${kind ? mark(kind) : nothing}<span>${parts.join(" · ")}</span></button>
      ${vehicle.has("button.refresh") ? html`<button class="refresh ${reading ? "reading" : ""}"
        aria-label="Read the car now" title="Read the car now" aria-busy=${reading ? "true" : "false"}
        @click=${() => this.readNow(vehicle, report?.state ?? "")}>${icon("refresh")}</button>` : nothing}
    </div>`;
  }

  /** The report the footer's refresh was pressed against; it spins until a newer one arrives. */
  private readingFrom?: string;
  private readingSince = 0;

  private readNow(vehicle: Vehicle, from: string): void {
    this.readingFrom = from;
    this.readingSince = Date.now();
    this.requestUpdate();
    window.setTimeout(() => this.requestUpdate(), 20_100);
    void vehicle.call("button", "press", "button.refresh");
  }

  /** A control's state from the entity and the commands still in flight for it. */
  protected actionState(vehicle: Vehicle, prefixes: string[], on?: boolean, transitioning = false): ActionState {
    if (transitioning || vehicle.pending(prefixes)) return "pending";
    const last = vehicle.lastFor(prefixes);
    if (last && outcome(last.state) === "refused" && last.at && Date.now() - last.at.getTime() < 120_000) {
      return "refused";
    }
    return on ? "on" : "idle";
  }

  /** One line about the latest command when it concerns this card. */
  protected commandNote(vehicle: Vehicle, prefixes: string[]): TemplateResult | typeof nothing {
    const last = vehicle.get("sensor.last_command");
    if (!known(last)) return nothing;
    const command: string | undefined = last.attributes.command;
    if (!command || !prefixes.some((prefix) => command.startsWith(prefix))) return nothing;
    const at = last.attributes.requested_at ? new Date(last.attributes.requested_at) : undefined;
    const state = outcome(last.state);
    if (state !== "pending" && (!at || Date.now() - at.getTime() > 180_000)) return nothing;
    const name = commandLabel(command);
    const lines: Record<string, [MarkKind, string]> = {
      pending: ["wait", last.state === "sending" ? `${name}: sending` : `${name}: waiting for the car`],
      ok: ["ok", `${name}: confirmed by the car`],
      refused: ["fault", `${name} refused${refusal(last) ? `: ${refusal(last)}` : ""}`],
      unconfirmed: ["warn", `${name}: not confirmed in time`],
    };
    const line = lines[state];
    if (!line) return nothing;
    return html`<p class="note ${state}" role="status">${mark(line[0])}<span>${line[1]}</span></p>`;
  }
}
