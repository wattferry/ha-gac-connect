import { css, html, nothing, TemplateResult } from "lit";
import { GacCard } from "../base";
import { Segment } from "../controls";
import { attributeLabel, duration, formatNumber, HassEntity, known, moreInfo, num } from "../ha";
import { Vehicle } from "../vehicle";
import { tempRoad } from "../roads";

const HVAC: Record<string, string> = {
  off: "Off", heat_cool: "On", fan_only: "Fan only", heat: "Heat", cool: "Cool", auto: "Auto", dry: "Dry",
};

const PRESETS: Record<string, [string, string]> = {
  heating: ["Max heat", "Starts the A/C in Auto at the highest target."],
  cooling: ["Max cool", "Starts the A/C in Auto at the lowest target."],
};

function words(value: string): string {
  return value.replace(/_/g, " ").replace(/^./, (c) => c.toUpperCase());
}

const EXTRAS: [string, string, string, string][] = [
  ["switch.recirculation", "Recirculation", "On recirculates cabin air; off draws fresh air. Changes while the A/C runs.",
   "aircon"],
  ["switch.sterilisation", "Sterilisation", "Hot-air cabin clean for 30 minutes. Car off, locked, windows shut.",
   "antivirus"],
  ["switch.ventilation", "Ventilation", "Lowers the windows 2–3 cm and runs fresh air.", "ventilate"],
];

export class GacClimateCard extends GacCard {
  protected readonly cardTitle = "Climate";
  protected readonly glyph = "climate";

  static override styles = [...GacCard.styles, css`
    .temps {
      align-items: end;
      margin-bottom: 6px;
    }
    .temps .lab {
      display: block;
      margin-bottom: 6px;
    }
    gac-segments + .presets,
    .stack > * + * {
      margin-top: 8px;
    }
    .presets {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 8px;
    }
    .field + .field {
      margin-top: 12px;
    }
    .field .lab {
      display: block;
      margin-bottom: 6px;
    }
    .row gac-switch {
      margin-right: -6px;
    }
    @container (max-width: 380px) {
      .temps {
        grid-template-columns: 1fr;
        gap: 10px;
      }
      .temps > * + * {
        border-left: 0;
        padding-left: 0;
      }
    }
  `];

  override getCardSize(): number {
    return 12;
  }

  private temperatures(vehicle: Vehicle, climate: HassEntity | undefined): TemplateResult | typeof nothing {
    const cabinEntity = vehicle.get("sensor.cabin_temp");
    if (!cabinEntity && !climate) return nothing;
    const cabin = num(cabinEntity) ?? (climate ? Number(climate.attributes.current_temperature) : undefined);
    const outside = num(vehicle.get("sensor.outside_temp"));
    const target = climate?.attributes.temperature as number | undefined;
    const min = Number(climate?.attributes.min_temp ?? 16);
    const max = Number(climate?.attributes.max_temp ?? 32);
    const step = Number(climate?.attributes.target_temp_step ?? 0.5);
    const running = known(climate) && climate.state !== "off";
    const unit = cabinEntity?.attributes.unit_of_measurement ?? "°C";
    return html`<div class="sec">
      <div class="duo temps">
        <button class="tap" @click=${() => moreInfo(this, cabinEntity?.entity_id ?? climate?.entity_id)}>
          <span class="lab">Cabin</span>
          <span class="fig">${cabin !== undefined && Number.isFinite(cabin) ? formatNumber(this.hass!, cabin, 0)
            : "–"}<small>&nbsp;${unit}</small></span>
        </button>
        ${climate ? html`<div><span class="lab">Target</span>
          <gac-stepper .value=${target} .min=${min} .max=${max} .step=${step} .digits=${step < 1 ? 1 : 0}
            unit=${unit} label="target temperature" .pending=${vehicle.pending(["aircon-temperature"])}
            ?disabled=${!known(climate)}
            @change=${(e: CustomEvent) => vehicle.call("climate", "set_temperature", "climate.climate",
                                                        { temperature: e.detail.value })}></gac-stepper></div>`
          : nothing}
      </div>
      ${climate ? tempRoad({ width: this.inner, min, max, cabin: cabin !== undefined && Number.isFinite(cabin)
        ? cabin : undefined, target, outside, running }) : nothing}
    </div>`;
  }

  private power(vehicle: Vehicle, climate: HassEntity | undefined): TemplateResult | typeof nothing {
    const ac = vehicle.get("switch.climate_power");
    const runTime = vehicle.get("number.ac_minutes");
    if (!climate && !ac) return nothing;
    const pending = vehicle.pending(["aircon"]);
    const modes: string[] = climate?.attributes.hvac_modes ?? [];
    const presets: string[] = climate?.attributes.preset_modes ?? [];
    const minutes = num(runTime);
    return html`<div class="sec stack">
      <div class="head"><span class="lab">A/C</span></div>
      ${climate && modes.length ? html`<gac-segments label="A/C mode" .value=${climate.state} .pending=${pending}
        ?disabled=${!known(climate)} .options=${modes.map((m): Segment => ({ value: m, label: HVAC[m] ?? words(m) }))}
        @change=${(e: CustomEvent) => vehicle.call("climate", "set_hvac_mode", "climate.climate",
                                                    { hvac_mode: e.detail.value })}></gac-segments>`
        : ac ? html`<div class="row"><div class="what"><div class="title">A/C</div></div>
          <gac-switch label="A/C" .checked=${ac.state === "on"} .pending=${pending}
            @change=${() => vehicle.call("switch", ac.state === "on" ? "turn_off" : "turn_on", "switch.climate_power")}>
          </gac-switch></div>` : nothing}
      ${presets.length ? html`<div class="presets">${presets.map((preset) => html`<gac-action
        label=${PRESETS[preset]?.[0] ?? words(preset)} hint=${PRESETS[preset]?.[1] ?? ""}
        icon=${/heat/i.test(preset) ? "sterilise" : "climate"}
        .state=${climate?.attributes.preset_mode === preset ? "on" : pending ? "pending" : "idle"}
        @activate=${() => vehicle.call("climate", "set_preset_mode", "climate.climate", { preset_mode: preset })}>
        </gac-action>`)}</div>` : nothing}
      ${runTime ? html`<div class="field"><span class="lab">Run time per remote start</span>
        <gac-stepper .value=${minutes} .min=${Number(runTime.attributes.min ?? 1)}
          .max=${Number(runTime.attributes.max ?? 60)} .step=${Number(runTime.attributes.step ?? 1)}
          unit=${runTime.attributes.unit_of_measurement ?? "min"} label="run time"
          @change=${(e: CustomEvent) => vehicle.call("number", "set_value", "number.ac_minutes",
                                                      { value: e.detail.value })}></gac-stepper></div>` : nothing}
    </div>`;
  }

  private airflow(vehicle: Vehicle, climate: HassEntity | undefined): TemplateResult | typeof nothing {
    if (!climate) return nothing;
    const fans: string[] = climate.attributes.fan_modes ?? [];
    const swings: string[] = climate.attributes.swing_modes ?? [];
    if (!fans.length && !swings.length) return nothing;
    const pending = vehicle.pending(["aircon"]);
    return html`<div class="sec">
      ${fans.length ? html`<div class="field"><span class="lab">Fan</span>
        <gac-stops label="Fan speed" .value=${climate.attributes.fan_mode} .pending=${pending}
          .options=${fans.map((f): Segment => ({ value: f, label: words(f) }))}
          @change=${(e: CustomEvent) => vehicle.call("climate", "set_fan_mode", "climate.climate",
                                                      { fan_mode: e.detail.value })}></gac-stops></div>` : nothing}
      ${swings.length ? html`<div class="field"><span class="lab">Airflow</span>
        <gac-choice label="Airflow" .value=${climate.attributes.swing_mode} .pending=${pending}
          .options=${swings.map((m): Segment => ({ value: m,
            label: attributeLabel(this.hass!, climate, "swing_mode", m, words(m)) }))}
          @change=${(e: CustomEvent) => vehicle.call("climate", "set_swing_mode", "climate.climate",
                                                      { swing_mode: e.detail.value })}></gac-choice></div>` : nothing}
    </div>`;
  }

  private seats(vehicle: Vehicle): TemplateResult | typeof nothing {
    const seats = ([["select.seat_1_ventilation", "Driver seat", "seat-1"],
                    ["select.seat_2_ventilation", "Passenger seat", "seat-2"]] as const)
      .filter(([key]) => vehicle.has(key));
    const wheel = vehicle.get("switch.steering_heat");
    if (!seats.length && !wheel) return nothing;
    return html`<div class="sec">
      ${seats.map(([key, label, prefix]) => {
        const entity = vehicle.get(key)!;
        return html`<div class="field"><span class="lab">${label} ventilation</span>
          <gac-segments label="${label} ventilation" .value=${entity.state} .pending=${vehicle.pending([prefix])}
            ?disabled=${!known(entity)}
            .options=${(entity.attributes.options as string[] ?? []).map((o): Segment => ({ value: o, label: words(o) }))}
            @change=${(e: CustomEvent) => vehicle.call("select", "select_option", key, { option: e.detail.value })}>
          </gac-segments></div>`;
      })}
      ${wheel ? html`<div class="row" style="margin-top:${seats.length ? 8 : 0}px">
        <div class="what"><div class="title">Steering wheel heat</div></div>
        <gac-switch label="Steering wheel heat" .checked=${wheel.state === "on"} .pending=${vehicle.pending(["steering"])}
          @change=${() => vehicle.call("switch", wheel.state === "on" ? "turn_off" : "turn_on", "switch.steering_heat")}>
        </gac-switch></div>` : nothing}
    </div>`;
  }

  private extras(vehicle: Vehicle): TemplateResult | typeof nothing {
    const shown = EXTRAS.filter(([key]) => vehicle.has(key));
    if (!shown.length) return nothing;
    return html`<div class="sec">${shown.map(([key, title, desc, prefix]) => {
      const entity = vehicle.get(key)!;
      const on = entity.state === "on";
      return html`<div class="row"><div class="what"><div class="title">${title}</div>
        <div class="desc">${desc}</div></div>
        <gac-switch label=${title} .checked=${on} .pending=${vehicle.pending([prefix])} ?disabled=${!known(entity)}
          @change=${() => vehicle.call("switch", on ? "turn_off" : "turn_on", key)}></gac-switch></div>`;
    })}</div>`;
  }

  private fridge(vehicle: Vehicle): TemplateResult | typeof nothing {
    const power = vehicle.get("switch.fridge");
    const mode = vehicle.get("select.fridge_mode");
    const temperature = vehicle.get("number.fridge_temperature");
    if (!power && !mode) return nothing;
    const pending = vehicle.pending(["fridge"]);
    const left = num(vehicle.get("sensor.fridge_time_left"));
    return html`<div class="sec">
      <div class="row"><div class="what"><div class="title">Fridge</div>
        ${left !== undefined ? html`<div class="desc">${duration(left)} left</div>` : nothing}</div>
        ${power ? html`<gac-switch label="Fridge" .checked=${power.state === "on"} .pending=${pending}
          @change=${() => vehicle.call("switch", power.state === "on" ? "turn_off" : "turn_on", "switch.fridge")}>
        </gac-switch>` : nothing}</div>
      ${mode ? html`<gac-segments label="Fridge mode" .value=${mode.state} .pending=${pending}
        .options=${(mode.attributes.options as string[] ?? []).map((o): Segment => ({ value: o, label: words(o) }))}
        @change=${(e: CustomEvent) => vehicle.call("select", "select_option", "select.fridge_mode",
                                                    { option: e.detail.value })}></gac-segments>` : nothing}
      ${temperature ? html`<div class="field" style="margin-top:8px"><gac-stepper .value=${num(temperature)}
        .min=${Number(temperature.attributes.min ?? 0)} .max=${Number(temperature.attributes.max ?? 20)}
        .step=${Number(temperature.attributes.step ?? 1)} unit=${temperature.attributes.unit_of_measurement ?? "°C"}
        label="fridge temperature" .pending=${pending}
        @change=${(e: CustomEvent) => vehicle.call("number", "set_value", "number.fridge_temperature",
                                                    { value: e.detail.value })}></gac-stepper></div>` : nothing}
    </div>`;
  }

  protected body(vehicle: Vehicle): TemplateResult {
    const climate = vehicle.get("climate.climate");
    const note = this.commandNote(vehicle, ["aircon", "seat-", "steering", "antivirus",
                                            "ventilate", "fridge"]);
    const sections = [
      this.temperatures(vehicle, climate), this.power(vehicle, climate), this.airflow(vehicle, climate),
      this.seats(vehicle), this.extras(vehicle), this.fridge(vehicle),
    ].filter((section) => section !== nothing);
    if (!sections.length) {
      return html`<div class="empty"><strong>No climate controls</strong>This car reports no cabin temperature or
        climate controls to Home Assistant.</div>`;
    }
    return html`${sections}${note !== nothing ? html`<div class="sec">${note}</div>` : nothing}`;
  }
}
