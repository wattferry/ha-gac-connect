import { css, html, nothing, PropertyValues, TemplateResult } from "lit";
import { GacCard } from "../base";
import { HassEntity, isOn, known, moreInfo } from "../ha";
import { mark } from "../icons";
import { Vehicle } from "../vehicle";

interface CardElement extends HTMLElement {
  hass?: unknown;
}

function coordinate(value: number, positive: string, negative: string): string {
  return `${Math.abs(value).toFixed(5)}° ${value >= 0 ? positive : negative}`;
}

export class GacLocationCard extends GacCard {
  protected readonly cardTitle = "Location";
  protected readonly glyph = "pin";
  private map?: CardElement;
  private mapFor?: string;
  private mapDark?: boolean;
  private loading = false;

  static override styles = [...GacCard.styles, css`
    .map {
      position: relative;
      border-bottom: 1px solid var(--gac-hair);
      --ha-card-border-radius: 0;
      --ha-card-border-width: 0;
      --ha-card-box-shadow: none;
      /* One car on the map needs no name bubble: the marker is just the car, in the theme's text
         colour (light on a dark theme, dark on a light one), with a shadow to lift it off the map. */
      --ha-marker-background: transparent;
      --ha-marker-border-width: 0;
      --ha-marker-color: transparent;
      --ha-marker-size: 40px;
      --ha-cluster-shadow: drop-shadow(0 0 2px var(--gac-land)) drop-shadow(0 1px 3px rgba(0, 0, 0, 0.35));
      min-height: 220px;
      background: var(--gac-water);
    }
    .map > * {
      display: block;
    }
    .place {
      font: 700 28px/1.05 var(--gac-label);
      letter-spacing: 0.03em;
      text-transform: uppercase;
    }
    .coords {
      margin-top: 6px;
      font: 500 16px/1.2 var(--gac-label);
      font-variant-numeric: tabular-nums;
      letter-spacing: 0.04em;
      color: var(--gac-muted);
    }
    .demo-tag {
      position: absolute;
      left: 10px;
      bottom: 8px;
      font: 600 12px/1 var(--gac-label);
      letter-spacing: 0.1em;
      text-transform: uppercase;
      color: var(--gac-muted);
      background: var(--gac-land);
      padding: 3px 6px;
    }
    .off-map {
      display: block;
      width: 100%;
      height: 180px;
    }
    .row gac-switch {
      margin-right: -6px;
    }
  `];

  override getCardSize(): number {
    return 9;
  }

  private coordinates(tracker: HassEntity | undefined): [number, number] | undefined {
    if (!known(tracker)) return undefined;
    const lat = Number(tracker.attributes.latitude);
    const lon = Number(tracker.attributes.longitude);
    return Number.isFinite(lat) && Number.isFinite(lon) && tracker.attributes.latitude !== null ? [lat, lon]
      : undefined;
  }

  protected override updated(changed: PropertyValues): void {
    super.updated(changed);
    const vehicle = this.vehicle;
    const trackerId = vehicle?.id("device_tracker.location");
    const shown = trackerId && this.coordinates(vehicle?.get("device_tracker.location"));
    if (!shown || !trackerId) return;
    const dark = this.hass?.themes?.darkMode === true;
    if (this.map && this.mapFor === trackerId && this.mapDark === dark) {
      this.map.hass = this.hass;
      void this.sizeCar(this.map);
      return;
    }
    void this.loadMap(trackerId, dark);
  }

  private async loadMap(trackerId: string, dark: boolean): Promise<void> {
    if (this.loading) return;
    const loader = (window as unknown as { loadCardHelpers?: () => Promise<any> }).loadCardHelpers;
    if (!loader) return;
    this.loading = true;
    try {
      const helpers = await loader();
      const card: CardElement = await helpers.createCardElement({
        type: "map", entities: [{ entity: trackerId, label_mode: "icon" }], default_zoom: 15, aspect_ratio: "16:11",
        theme_mode: dark ? "dark" : "light", hours_to_show: 0,
      });
      card.hass = this.hass;
      this.map = card;
      void this.sizeCar(card);
      this.mapFor = trackerId;
      this.mapDark = dark;
      this.requestUpdate();
    } finally {
      this.loading = false;
    }
  }

  /**
   * The car is drawn larger than Home Assistant's 24 px icons. Icon size is inherited, so it is set
   * on the map card's own map, which holds the marker, and not on the card, which also holds the
   * re-centre button. If the map is not found, the car simply keeps the standard size.
   */
  private async sizeCar(card: CardElement): Promise<void> {
    await (card as CardElement & { updateComplete?: Promise<unknown> }).updateComplete;
    (card.shadowRoot?.querySelector("ha-map") as HTMLElement | null)?.style.setProperty("--mdc-icon-size", "30px");
  }

  /** A blank atlas tile for when the position is hidden. */
  private blankTile(): TemplateResult {
    return html`<svg class="off-map" viewBox="0 0 320 180" preserveAspectRatio="xMidYMid slice" aria-hidden="true">
      <rect width="320" height="180" fill="var(--gac-land)"/>
      <path d="M0 0H320M0 60H320M0 120H320M80 0V180M160 0V180M240 0V180" stroke="var(--gac-hair)"/>
      <path d="M-10 132C60 120 110 70 180 74S280 40 330 30" fill="none" stroke="var(--gac-minor-case)"
        stroke-width="9"/>
      <path d="M-10 132C60 120 110 70 180 74S280 40 330 30" fill="none" stroke="var(--gac-minor)" stroke-width="6"/>
      <circle cx="160" cy="90" r="22" fill="none" stroke="var(--gac-ink)" stroke-width="1.5" stroke-dasharray="4 4"/>
      <path d="M154 90h12M160 84v12" stroke="var(--gac-ink)" stroke-width="1.5"/>
    </svg>`;
  }

  private trackingRows(vehicle: Vehicle): TemplateResult | typeof nothing {
    const rows = ([["switch.track_parked", "When parked", "Shows where the car is while it is switched off."],
                   ["switch.track_moving", "When switched on", "Follows the car while it is switched on."]] as const)
      .filter(([key]) => vehicle.has(key));
    if (!rows.length) return nothing;
    return html`<div class="sec"><div class="head"><span class="lab">Track location</span></div>
      ${rows.map(([key, title, desc]) => {
        const on = vehicle.get(key)?.state === "on";
        return html`<div class="row"><div class="what"><div class="title">${title}</div>
          <div class="desc">${desc}</div></div>
          <gac-switch label="Track location ${title.toLowerCase()}" .checked=${on}
            @change=${() => vehicle.call("switch", on ? "turn_off" : "turn_on", key)}></gac-switch></div>`;
      })}</div>`;
  }

  protected body(vehicle: Vehicle): TemplateResult {
    const tracker = vehicle.get("device_tracker.location");
    const position = this.coordinates(tracker);
    const power = isOn(vehicle.get("binary_sensor.vehicle_power"));
    const parked = vehicle.get("switch.track_parked")?.state === "on";
    const moving = vehicle.get("switch.track_moving")?.state === "on";
    if (!position) {
      const hiddenNow = (power === false && !parked && moving) || (power === true && !moving && parked);
      return html`<div class="map">${this.blankTile()}</div>
        <div class="empty"><strong>${hiddenNow ? "Hidden for now" : "Location is off"}</strong>
          ${hiddenNow
            ? power ? "Tracking is on only while the car is parked." : "Tracking is on only while the car is switched on."
            : tracker ? "Turn on tracking below to see the car on the map. Positions already recorded stay in "
              + "Home Assistant's history." : "This car has no location entity. Turn on tracking below."}
        </div>
        ${this.trackingRows(vehicle)}`;
    }
    const state = tracker!.state;
    const place = state === "home" ? "Home" : state === "not_home" ? "Away from home" : state;
    const demo = !(window as unknown as { loadCardHelpers?: unknown }).loadCardHelpers;
    return html`
      <div class="map">${this.map ?? (demo ? this.demoMap() : nothing)}</div>
      <div class="sec">
        <button class="tap" @click=${() => moreInfo(this, tracker!.entity_id)}>
          <div class="place">${place}</div>
          <div class="coords">${coordinate(position[0], "N", "S")} · ${coordinate(position[1], "E", "W")}</div>
        </button>
        <p class="note" style="margin-top:10px">${mark(power ? "info" : "ok")}<span>${power
          ? "Switched on" : "Parked"}${tracker!.attributes.gps_accuracy ? ` · within ${
            Math.round(tracker!.attributes.gps_accuracy)} m` : ""}</span></p>
      </div>
      ${this.trackingRows(vehicle)}`;
  }

  /** Outside Home Assistant (the demo page) there is no map card; draw an atlas tile instead. */
  private demoMap(): TemplateResult {
    return html`<svg class="off-map" style="height:220px" viewBox="0 0 320 220" preserveAspectRatio="xMidYMid slice"
      role="img" aria-label="Demo map">
      <rect width="320" height="220" fill="var(--gac-land)"/>
      <path d="M250 0C230 50 262 90 236 140S250 200 240 220H320V0Z" fill="var(--gac-water)"/>
      <path d="M0 150C70 140 120 120 170 120S260 96 330 60" fill="none" stroke="var(--gac-mw-case)" stroke-width="12"/>
      <path d="M0 150C70 140 120 120 170 120S260 96 330 60" fill="none" stroke="var(--gac-mw)" stroke-width="8"/>
      <path d="M96 -10C104 60 118 120 136 230" fill="none" stroke="var(--gac-red-case)" stroke-width="9"/>
      <path d="M96 -10C104 60 118 120 136 230" fill="none" stroke="var(--gac-red)" stroke-width="6"/>
      <path d="M-10 60H200M30 -10V230M190 40V230" fill="none" stroke="var(--gac-minor-case)" stroke-width="6"/>
      <path d="M-10 60H200M30 -10V230M190 40V230" fill="none" stroke="var(--gac-minor)" stroke-width="4"/>
      <g transform="translate(136 72) scale(1.15)" fill="var(--gac-ink)">
        <path d="M5,11L6.5,6.5H17.5L19,11M17.5,16A1.5,1.5 0 0,1 16,14.5A1.5,1.5 0 0,1 17.5,13A1.5,1.5 0 0,1 19,14.5A1.5,1.5 0 0,1 17.5,16M6.5,16A1.5,1.5 0 0,1 5,14.5A1.5,1.5 0 0,1 6.5,13A1.5,1.5 0 0,1 8,14.5A1.5,1.5 0 0,1 6.5,16M18.92,6C18.72,5.42 18.16,5 17.5,5H6.5C5.84,5 5.28,5.42 5.08,6L3,12V20A1,1 0 0,0 4,21H5A1,1 0 0,0 6,20V19H18V20A1,1 0 0,0 19,21H20A1,1 0 0,0 21,20V12L18.92,6Z"/>
      </g>
    </svg><span class="demo-tag">Demo map</span>`;
  }
}
