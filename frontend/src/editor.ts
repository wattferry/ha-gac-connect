// One editor for all six cards: pick the car; the Vehicle card adds its drawing and actions.

import { css, html, LitElement, nothing } from "lit";
import { BODY_STYLES } from "./car-plan";
import { CardConfig, fire, HomeAssistant } from "./ha";
import { DOMAIN, vehicles } from "./vehicle";
import { ACTION_CHOICES } from "./cards/vehicle-card";

const LABELS: Record<string, string> = {
  device: "Car",
  body: "Body style for the drawing",
  image: "Photo of your car (optional)",
  tyre_warning_kpa: "Warn below this tyre pressure (optional)",
  actions: "Actions",
};

const HELPERS: Record<string, string> = {
  device: "The car this card shows. For another car, add another card.",
  body: "Automatic follows the car's model name.",
  image: "A picture you supply, for example /local/my-car.jpg. It shows above the drawing.",
  tyre_warning_kpa: "The car reports pressures but no limit; leave empty for no warning.",
  actions: "Shown when the car has them, up to six.",
};

export class GacCardEditor extends LitElement {
  static override properties = { hass: { attribute: false }, config: { state: true } };

  declare hass: HomeAssistant | undefined;
  declare config: CardConfig | undefined;

  static override styles = css`
    select {
      width: 100%;
      height: 48px;
      font: inherit;
    }
    label {
      display: block;
      margin-bottom: 4px;
    }
  `;

  setConfig(config: CardConfig): void {
    this.config = config;
  }

  /** The picker appears only when there is a choice to make. */
  private get onlyCar(): string | undefined {
    const cars = this.hass ? vehicles(this.hass) : [];
    return cars.length === 1 ? cars[0].id : undefined;
  }

  private schema() {
    const fields: Record<string, unknown>[] = this.onlyCar ? [] : [
      { name: "device", required: true, selector: { device: { filter: { integration: DOMAIN } } } },
    ];
    if (this.config?.type === "custom:gac-vehicle-card") {
      fields.push(
        { name: "body", selector: { select: { mode: "dropdown", options: [
          { value: "auto", label: "Automatic" }, ...BODY_STYLES] } } },
        { name: "image", selector: { text: {} } },
        { name: "tyre_warning_kpa", selector: { number: { min: 100, max: 400, step: 5, mode: "box",
                                                          unit_of_measurement: "kPa" } } },
        { name: "actions", selector: { select: { multiple: true, mode: "list", options: ACTION_CHOICES } } },
      );
    }
    return fields;
  }

  private changed(event: CustomEvent): void {
    const value = { ...event.detail.value };
    for (const key of Object.keys(value)) {
      if (value[key] === "" || value[key] === undefined || (key === "body" && value[key] === "auto")) delete value[key];
    }
    const only = this.onlyCar;
    fire(this, "config-changed", { config: { ...value, ...(only ? { device: only } : {}), type: this.config?.type } });
  }

  protected override render() {
    if (!this.hass || !this.config) return nothing;
    if (customElements.get("ha-form")) {
      return html`<ha-form .hass=${this.hass} .data=${{ body: "auto", ...this.config }} .schema=${this.schema()}
        .computeLabel=${(field: { name: string }) => LABELS[field.name] ?? field.name}
        .computeHelper=${(field: { name: string }) => HELPERS[field.name]}
        @value-changed=${this.changed}></ha-form>`;
    }
    const options = vehicles(this.hass);
    if (options.length < 2) return nothing;
    return html`<label for="device">${LABELS.device}</label>
      <select id="device" @change=${(e: Event) => fire(this, "config-changed", {
        config: { ...this.config, device: (e.target as HTMLSelectElement).value } })}>
        ${options.map((o) => html`<option value=${o.id} ?selected=${o.id === this.config?.device}>${o.name}</option>`)}
      </select>`;
  }
}
