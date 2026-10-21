// Demo page: the six cards on a synthetic car, with commands that answer like the real one.
// Nothing here talks to GAC or Home Assistant; every value is made up.

import "../src/index";
import type { HassEntity, HomeAssistant } from "../src/ha";

type Model = "AION V" | "GAC M8" | "AION UT" | "Hyptec HT" | "AION S";

const now = () => new Date();
const minutesAgo = (m: number) => new Date(Date.now() - m * 60_000).toISOString();
const clock = (offset: number) => {
  const d = new Date(Date.now() + offset * 60_000);
  return `${String(d.getHours()).padStart(2, "0")}:${String(d.getMinutes()).padStart(2, "0")}`;
};

function entity(state: string | number, attributes: Record<string, unknown> = {}): Omit<HassEntity, "entity_id"> {
  const at = now().toISOString();
  return { state: String(state), attributes, last_changed: at, last_updated: at };
}

/** The integration's airflow names (translations/en.json). */
const AIRFLOW: Record<string, string> = {
  cabin: "Cabin", cabin_feet: "Cabin + Feet", feet: "Feet", feet_windscreen: "Feet + Windscreen",
  windscreen: "Windscreen", all: "Cabin + Feet + Windscreen",
};

const ENTITY_LABELS = [
  "sensor:soc|Battery", "sensor:range|Range", "sensor:odometer|Odometer", "sensor:cabin_temp|Cabin temperature",
  "sensor:outside_temp|Outside temperature", "sensor:pm25|Cabin PM2.5", "sensor:aux_voltage|12V battery",
  "sensor:tyre_1_pressure|Tyre 1 pressure", "binary_sensor:rear_fog_light|Rear fog light",
  "binary_sensor:headlights|Headlights", "switch:steering_heat|Steering wheel heat", "cover:sunroof|Sunroof",
  "switch:fridge|Fridge", "select:fridge_mode|Fridge mode", "device_tracker:location|Location",
  "climate:climate|Climate", "lock:doors|Doors", "cover:tailgate|Boot", "button:horn|Sound horn",
];

function states(model: Model): Record<string, Omit<HassEntity, "entity_id">> {
  const windowStart = clock(-60);
  const windowStop = clock(360);
  const s: Record<string, Omit<HassEntity, "entity_id">> = {
    "sensor.soc": entity(78, { unit_of_measurement: "%" }),
    "sensor.range": entity(312, { unit_of_measurement: "km" }),
    "sensor.odometer": entity(18432, { unit_of_measurement: "km" }),
    "sensor.cabin_temp": entity(31, { unit_of_measurement: "°C" }),
    "sensor.outside_temp": entity(34, { unit_of_measurement: "°C" }),
    "sensor.aux_voltage": entity(12.6, { unit_of_measurement: "V" }),
    "sensor.battery_temp": entity(29, { unit_of_measurement: "°C" }),
    "sensor.trip_consumption": entity(14.8, { unit_of_measurement: "kWh/100km" }),
    "sensor.pm25": entity(9, { unit_of_measurement: "µg/m³" }),
    "sensor.charge_power": entity(7.2, { unit_of_measurement: "kW" }),
    "sensor.charge_current": entity(31, { unit_of_measurement: "A" }),
    "sensor.charge_voltage": entity(232, { unit_of_measurement: "V" }),
    "sensor.charge_time": entity(100, { unit_of_measurement: "min" }),
    "sensor.charge_schedule": entity("scheduled", { reported_start: windowStart, reported_stop: windowStop,
                                                    reported_days: "Mon, Tue, Wed, Thu, Fri" }),
    "sensor.last_report": entity(minutesAgo(4)),
    "sensor.data_freshness": entity("recent"),
    "sensor.polling_status": entity("ok"),
    "sensor.last_command": entity("rejected", {
      command: "lock", requested_at: minutesAgo(18), pending_commands: [], reported_causes: ["Boot open"],
      refusal_reason: "Conditions not met",
      recent_commands: [
        { command: "aircon-on", state: "confirmed", requested_at: minutesAgo(41) },
        { command: "tailgate-open", state: "confirmed", requested_at: minutesAgo(20) },
        { command: "lock", state: "rejected", failure_reason: "Vehicle rejected request", requested_at: minutesAgo(18) },
      ],
    }),
    "sensor.last_gac_alert": entity("boot_open", { title: "Boot open", created: minutesAgo(19) }),
    "binary_sensor.anti_theft": entity("on"),
    "binary_sensor.high_beam": entity("off"),
    "binary_sensor.rear_fog_light": entity("off"),
    "binary_sensor.turn_signal": entity("off"),
    "sensor.entity_choices": entity(2, {
      always_show: ["switch:steering_heat"], omit: ["binary_sensor:rear_fog_light"],
      entities: Object.fromEntries(ENTITY_LABELS.map((pair) => {
        const [key, label] = pair.split("|");
        const domain = key.split(":")[0].replace("_", " ").replace(/\b./g, (c) => c.toUpperCase());
        return [key, `${domain} · ${label}`];
      })),
    }),
    "binary_sensor.online": entity("on"),
    "binary_sensor.vehicle_power": entity("off"),
    "binary_sensor.plugged": entity("on"),
    "binary_sensor.charging": entity("on"),
    "binary_sensor.charger_locked": entity("off"),
    "binary_sensor.locked": entity("on"),
    "binary_sensor.hatch_open": entity("on"),
    "binary_sensor.hood_open": entity("off"),
    "binary_sensor.headlights": entity("off"),
    "binary_sensor.brake_fluid": entity("off"),
    "binary_sensor.front_left_door": entity("off"),
    "binary_sensor.front_right_door": entity("off"),
    "binary_sensor.rear_left_door": entity("off"),
    "binary_sensor.rear_right_door": entity("off"),
    "binary_sensor.front_left_window": entity("on"),
    "binary_sensor.front_right_window": entity("off"),
    "binary_sensor.rear_left_window": entity("off"),
    "binary_sensor.rear_right_window": entity("off"),
    "lock.doors": entity("unlocked"),
    "cover.tailgate": entity("open"),
    "cover.windows": entity("open"),
    "cover.sunroof": entity("closed"),
    "switch.climate_power": entity("off"),
    "switch.ventilation": entity("off"),
    "switch.lights": entity("off"),
    "switch.recirculation": entity("off"),
    "switch.precondition_battery": entity("off"),
    "switch.sterilisation": entity("off"),
    "switch.steering_heat": entity("off"),
    "switch.charging": entity("on"),
    "button.horn": entity("unknown"),
    "button.refresh": entity("unknown"),
    "button.charge_now": entity("unknown"),
    "button.charger_unlock": entity("unknown"),
    "button.send_charge_window": entity("unknown"),
    "button.refresh_capabilities": entity("unknown"),
    "climate.climate": entity("off", {
      current_temperature: 31, temperature: 22, min_temp: 16, max_temp: 32, target_temp_step: 0.5,
      hvac_modes: ["off", "heat_cool", "fan_only"], preset_modes: ["heating", "cooling"], preset_mode: null,
      fan_modes: ["auto", "1", "2", "3", "4", "5", "6", "7"], fan_mode: "3",
      swing_modes: Object.keys(AIRFLOW), swing_mode: "cabin",
    }),
    "number.ac_minutes": entity(30, { min: 10, max: 60, step: 5, unit_of_measurement: "min" }),
    "select.seat_1_ventilation": entity("off", { options: ["off", "low", "medium", "high"] }),
    "select.seat_2_ventilation": entity("low", { options: ["off", "low", "medium", "high"] }),
    "time.charge_window_start": entity(`${windowStart}:00`),
    "time.charge_window_stop": entity(`${windowStop}:00`),
    ...Object.fromEntries(["mon", "tue", "wed", "thu", "fri", "sat", "sun"].map((d, i) =>
      [`switch.charge_window_${d}`, entity(i < 5 ? "on" : "off")])),
    "switch.charge_window_until_soc": entity("off"),
    "device_tracker.location": entity("not_home", { latitude: 52.2053, longitude: 0.1218, gps_accuracy: 8 }),
    "switch.track_parked": entity("on"),
    "switch.track_moving": entity("off"),
    "switch.allow_remote_unlock": entity("off"),
    "switch.allow_charger_unlock": entity("on"),
    "switch.allow_vehicle_shutdown": entity("off"),
    "switch.allow_account_alerts": entity("on"),
    "switch.allow_plaintext_push": entity("off"),
    "switch.quiet_hours": entity("on"),
    "time.quiet_hours_start": entity("01:00:00"),
    "time.quiet_hours_end": entity("06:00:00"),
    "number.polling_interval": entity(300, { min: 60, max: 3600, step: 1, unit_of_measurement: "s" }),
    "event.car_alert": entity(minutesAgo(300), { event_type: "window_left_open" }),
    "event.gac_alert": entity(minutesAgo(19), { event_type: "boot_open" }),
    ...Object.fromEntries([245, 248, 243, 221].map((p, i) =>
      [`sensor.tyre_${i + 1}_pressure`, entity(p, { unit_of_measurement: "kPa" })])),
    ...Object.fromEntries([28, 29, 27, 31].map((t, i) =>
      [`sensor.tyre_${i + 1}_temp`, entity(t, { unit_of_measurement: "°C" })])),
  };
  const drop = (...keys: string[]) => keys.forEach((k) => delete s[k]);
  if (model === "GAC M8") {
    s["binary_sensor.high_beam"] = entity("on");
    s["binary_sensor.headlights"] = entity("on");
    s["binary_sensor.rear_fog_light"] = entity("on");
    s["switch.fridge"] = entity("on");
    s["select.fridge_mode"] = entity("refrigerate", { options: ["off", "refrigerate", "heat", "freeze"] });
    s["number.fridge_temperature"] = entity(4, { min: 0, max: 20, step: 1, unit_of_measurement: "°C" });
    s["sensor.fridge_time_left"] = entity(45, { unit_of_measurement: "min" });
    s["binary_sensor.rear_right_door"] = entity("on");
    s["binary_sensor.front_left_window"] = entity("off");
    s["binary_sensor.hatch_open"] = entity("off");
    s["cover.tailgate"] = entity("closed");
  }
  if (model === "AION UT") {
    drop("switch.steering_heat", "cover.sunroof",
         ...[1, 2, 3, 4].flatMap((i) => [`sensor.tyre_${i}_pressure`, `sensor.tyre_${i}_temp`]));
  }
  if (model === "Hyptec HT") {
    s["binary_sensor.turn_signal"] = entity("on");
    s["binary_sensor.front_right_door"] = entity("on");
    s["binary_sensor.hatch_open"] = entity("off");
    s["cover.tailgate"] = entity("closed");
    s["binary_sensor.headlights"] = entity("on");
  }
  if (model === "AION S") {
    drop("cover.sunroof", "select.seat_2_ventilation", "switch.precondition_battery");
    s["binary_sensor.hatch_open"] = entity("off");
    s["cover.tailgate"] = entity("closed");
    s["binary_sensor.charging"] = entity("off");
    s["binary_sensor.plugged"] = entity("off");
    s["sensor.soc"] = entity(16, { unit_of_measurement: "%" });
    s["sensor.range"] = entity(58, { unit_of_measurement: "km" });
  }
  return s;
}

// ?lang=en-US tries a 12-hour clock and a week from Sunday; the default is en-GB.
const DEMO_LOCALE = { language: new URLSearchParams(location.search).get("lang") ?? "en-GB",
                      time_format: "language", first_weekday: "language" };

class DemoCar {
  model: Model = "AION V";
  twoCars = false;
  dark = false;
  /** The car the current request is about. */
  private car = 0;
  private states: Record<string, HassEntity> = {};
  private listeners: ((hass: HomeAssistant) => void)[] = [];
  private history?: (message: unknown) => void;
  hass!: HomeAssistant;

  constructor() {
    this.reset();
  }

  private get models(): Model[] {
    return this.twoCars ? [this.model, this.model === "GAC M8" ? "AION V" : "GAC M8"] : [this.model];
  }

  private id(key: string, car = this.car): string {
    const [domain, name] = key.split(".");
    return `${domain}.c${car}_${name}`;
  }

  reset(): void {
    this.states = {};
    this.models.forEach((model, car) => {
      for (const [key, value] of Object.entries(states(model))) {
        const entityId = this.id(key, car);
        this.states[entityId] = { entity_id: entityId, ...value };
      }
    });
    this.publish(true);
  }

  onChange(listener: (hass: HomeAssistant) => void): void {
    this.listeners.push(listener);
    listener(this.hass);
  }

  private publish(registry = false): void {
    const entities = registry || !this.hass ? Object.fromEntries(Object.keys(this.states).map((entityId) => {
      const [, car, name] = /^\w+\.c(\d+)_(.+)$/.exec(entityId)!;
      return [entityId, { entity_id: entityId, device_id: `demo-car-${car}`, platform: "gac_connect",
                          translation_key: name }];
    })) : this.hass.entities;
    this.hass = {
      states: { ...this.states },
      entities,
      devices: Object.fromEntries(this.models.map((model, car) => [`demo-car-${car}`,
        { id: `demo-car-${car}`, name: model, model, serial_number: `DEMO${car}` }])),
      themes: { darkMode: this.dark },
      locale: DEMO_LOCALE,
      language: DEMO_LOCALE.language,
      callService: (domain, service, data) => this.call(domain, service, data ?? {}),
      // As Home Assistant does, from the integration's translations.
      formatEntityAttributeValue: (_entity, attribute, value) =>
        attribute === "swing_mode" ? AIRFLOW[String(value)] ?? String(value) : String(value),
      connection: {
        subscribeMessage: async (callback: (message: any) => void, message: Record<string, unknown>) => {
          if (message.type === "history/stream") {
            this.history = callback;
            const ids = message.entity_ids as string[];
            window.setTimeout(() => callback({ states: Object.fromEntries(ids.map((id) => [id,
              id.includes("car_alert") ? [
                { s: minutesAgo(300), a: { event_type: "window_left_open", windows: ["front_left"] }, lu: 0 },
                { s: minutesAgo(1500), a: { event_type: "charging_stopped" }, lu: 0 },
              ] : [{ s: minutesAgo(19), a: { event_type: "boot_open" }, lu: 0 }]])) }), 60);
          }
          return async () => { this.history = undefined; };
        },
      },
    } as HomeAssistant;
    this.listeners.forEach((listener) => listener(this.hass));
  }

  private set(key: string, state: string | number, attributes?: Record<string, unknown>): void {
    const entityId = this.id(key);
    const current = this.states[entityId];
    if (!current) return;
    const at = now().toISOString();
    this.states[entityId] = { ...current, state: String(state), attributes: attributes ?? current.attributes,
                              last_changed: at, last_updated: at };
  }

  private get(key: string): HassEntity | undefined {
    return this.states[this.id(key)];
  }

  private record(command: string, state: string, extra: Record<string, unknown> = {}): void {
    const last = this.get("sensor.last_command");
    const recent = [...(last?.attributes.recent_commands ?? [])];
    const requestedAt = state === "sending" ? new Date().toISOString() : last?.attributes.requested_at;
    if (state === "sending") recent.push({ command, state, requested_at: requestedAt });
    else if (recent.length) recent[recent.length - 1] = { ...recent[recent.length - 1], state };
    this.set("sensor.last_command", state, {
      command, requested_at: requestedAt, recent_commands: recent.slice(-5),
      pending_commands: state === "sending" || state === "pending" ? [command] : [],
      reported_causes: [], refusal_reason: null, ...extra,
    });
  }

  /** A command that the car answers after a pause, as GAC's cloud does. */
  private command(command: string, apply: () => void, refuse?: () => string | undefined): void {
    const car = this.car;
    this.record(command, "sending");
    this.publish();
    window.setTimeout(() => { this.car = car; this.record(command, "pending"); this.publish(); }, 500);
    window.setTimeout(() => {
      this.car = car;
      const cause = refuse?.();
      if (cause) this.record(command, "rejected", { reported_causes: [cause], refusal_reason: "Conditions not met" });
      else {
        apply();
        this.record(command, "confirmed");
      }
      this.set("sensor.last_report", new Date().toISOString());
      this.publish();
    }, 2600);
  }

  private async call(domain: string, service: string, data: Record<string, any>): Promise<void> {
    const match = /^(\w+)\.c(\d+)_(.+)$/.exec(String(data.entity_id ?? ""));
    this.car = match ? Number(match[2]) : Number(String(data.vin ?? "DEMO0").replace("DEMO", "")) || 0;
    const key = match ? `${match[1]}.${match[3]}` : "";
    const on = (k: string) => this.get(k)?.state === "on";
    switch (`${domain}.${service}`) {
      case "lock.lock":
        this.set("lock.doors", "locking");
        this.command("lock", () => { this.set("lock.doors", "locked"); this.set("binary_sensor.locked", "off"); },
                     () => { const why = on("binary_sensor.hatch_open") ? "Boot open" : undefined;
                             if (why) this.set("lock.doors", "unlocked"); return why; });
        break;
      case "lock.unlock":
        this.set("lock.doors", "unlocking");
        this.command("unlock", () => { this.set("lock.doors", "unlocked"); this.set("binary_sensor.locked", "on"); });
        break;
      case "cover.open_cover":
      case "cover.close_cover": {
        const open = service === "open_cover";
        const name = key.split(".")[1];
        const prefix = name === "tailgate" ? "tailgate" : name === "windows" ? "window" : "sunroof";
        this.set(key, open ? "opening" : "closing");
        this.command(`${prefix}-${open ? "open" : "close"}`, () => {
          this.set(key, open ? "open" : "closed");
          if (name === "tailgate") this.set("binary_sensor.hatch_open", open ? "on" : "off");
          if (name === "windows") {
            for (const p of ["front_left", "front_right", "rear_left", "rear_right"]) {
              this.set(`binary_sensor.${p}_window`, open ? "on" : "off");
            }
          }
        });
        break;
      }
      case "switch.turn_on":
      case "switch.turn_off": {
        const value = service === "turn_on" ? "on" : "off";
        const name = key.split(".")[1];
        const commands: Record<string, string> = {
          climate_power: "aircon", ventilation: "ventilate", lights: "flash", steering_heat: "steering",
          precondition_battery: "battery-precondition", sterilisation: "antivirus", recirculation: "aircon",
          fridge: "fridge", charging: value === "on" ? "charge-resume" : "charge-now",
        };
        if (commands[name]) {
          this.set(key, value);
          this.command(`${commands[name]}-${value}`, () => {
            if (name === "climate_power") this.set("climate.climate", value === "on" ? "heat_cool" : "off");
            if (name === "lights") window.setTimeout(() => { this.set(key, "off"); this.publish(); }, 3000);
          });
        } else {
          this.set(key, value);
          this.publish();
        }
        break;
      }
      case "button.press": {
        const name = key.split(".")[1];
        const commands: Record<string, string> = {
          horn: "horn-on", refresh: "refresh", charge_now: "charge-now", charger_unlock: "charger-unlock",
          send_charge_window: "charge-window", vehicle_power_off: "vehicle-power-off",
        };
        if (!commands[name]) { this.publish(); break; }
        this.command(commands[name], () => {
          if (name === "charge_now") {
            this.set("binary_sensor.charging", "on");
            this.set("sensor.charge_schedule", "unrestricted", this.get("sensor.charge_schedule")?.attributes);
            this.set("switch.charging", "off");
          }
          if (name === "charger_unlock") {
            this.set("binary_sensor.charging", "off");
            this.set("binary_sensor.charger_locked", "on");
          }
          if (name === "send_charge_window") {
            const start = this.get("time.charge_window_start")?.state.slice(0, 5);
            const stop = this.get("time.charge_window_stop")?.state.slice(0, 5);
            const days = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"].filter((d) => on(`switch.charge_window_${d}`))
              .map((d) => d[0].toUpperCase() + d.slice(1));
            this.set("sensor.charge_schedule", "scheduled", { reported_start: start, reported_stop: stop,
              reported_days: days.length === 7 ? "Every day" : days.length ? days.join(", ") : "One time" });
          }
        });
        break;
      }
      case "climate.set_temperature": {
        const climate = this.get("climate.climate")!;
        this.command("aircon-temperature", () => this.set("climate.climate", climate.state,
          { ...climate.attributes, temperature: data.temperature }));
        break;
      }
      case "climate.set_hvac_mode": {
        const climate = this.get("climate.climate")!;
        this.command(data.hvac_mode === "off" ? "aircon-off" : "aircon-on", () => {
          this.set("climate.climate", data.hvac_mode, climate.attributes);
          this.set("switch.climate_power", data.hvac_mode === "off" ? "off" : "on");
        });
        break;
      }
      case "climate.set_fan_mode":
      case "climate.set_swing_mode":
      case "climate.set_preset_mode": {
        const climate = this.get("climate.climate")!;
        const field = service.replace("set_", "");
        this.command("aircon-on", () => {
          this.set("climate.climate", climate.state === "off" ? "heat_cool" : climate.state,
                   { ...climate.attributes, [field]: data[field] });
          this.set("switch.climate_power", "on");
        });
        break;
      }
      case "select.select_option": {
        const name = key.split(".")[1];
        const seat = /seat_(\d)/.exec(name)?.[1];
        const current = this.get(key)!;
        if (seat) {
          this.command(`seat-${seat}-ventilation-${data.option === "off" ? "off" : "on"}`,
                       () => this.set(key, data.option, current.attributes));
        } else {
          this.command("fridge-on", () => this.set(key, data.option, current.attributes));
        }
        break;
      }
      case "number.set_value":
      case "time.set_value": {
        const current = this.get(key)!;
        this.set(key, data.value ?? data.time, current.attributes);
        this.publish();
        break;
      }
      case "gac_connect.send_command":
        this.command(String(data.command), () => undefined);
        break;
      case "gac_connect.set_entity_visibility": {
        const choices = this.get("sensor.entity_choices")!;
        const always = new Set<string>(choices.attributes.always_show);
        const omit = new Set<string>(choices.attributes.omit);
        always.delete(data.entity);
        omit.delete(data.entity);
        if (data.visibility === "always") always.add(data.entity);
        if (data.visibility === "omit") omit.add(data.entity);
        this.set("sensor.entity_choices", always.size + omit.size,
                 { ...choices.attributes, always_show: [...always], omit: [...omit] });
        this.publish();
        break;
      }
      default:
        this.publish();
    }
    void this.history;
  }

  setModel(model: Model): void {
    this.model = model;
    this.reset();
  }

  setTwoCars(two: boolean): void {
    this.twoCars = two;
    this.reset();
  }

  setDark(dark: boolean): void {
    this.dark = dark;
    document.documentElement.dataset.theme = dark ? "dark" : "light";
    this.publish();
  }
}

const car = new DemoCar();
const types = ["vehicle", "climate", "charging", "location", "activity", "settings"];
type Card = HTMLElement & { setConfig(config: unknown): void; hass: HomeAssistant };
let cards: Card[] = [];

/** Each card shows one car, so every car gets its own six cards under its name. */
function layout(hass: HomeAssistant): void {
  const garage = document.querySelector<HTMLElement>("#cars")!;
  garage.replaceChildren();
  cards = [];
  for (const device of Object.values(hass.devices)) {
    const section = document.createElement("section");
    section.className = "car";
    const heading = document.createElement("h2");
    heading.textContent = device.name ?? "Car";
    const grid = document.createElement("div");
    grid.className = "columns";
    const columns = [0, 1, 2].map(() => grid.appendChild(document.createElement("div")));
    types.forEach((type, i) => {
      const card = document.createElement(`gac-${type}-card`) as Card;
      card.setConfig({ type: `custom:gac-${type}-card`, device: device.id,
                       ...(type === "vehicle" ? { tyre_warning_kpa: 230 } : {}) });
      columns[i % 3].append(card);
      cards.push(card);
    });
    section.append(heading, grid);
    garage.append(section);
  }
}

let shown = "";
car.onChange((hass) => {
  const garage = Object.keys(hass.devices).join(",") + Object.values(hass.devices).map((d) => d.name).join(",");
  if (garage !== shown) {
    shown = garage;
    layout(hass);
  }
  cards.forEach((card) => (card.hass = hass));
});

document.querySelector<HTMLSelectElement>("#model")!.addEventListener("change", (e) =>
  car.setModel((e.target as HTMLSelectElement).value as Model));
document.querySelector<HTMLInputElement>("#two")!.addEventListener("change", (e) =>
  car.setTwoCars((e.target as HTMLInputElement).checked));
document.querySelector<HTMLInputElement>("#dark")!.addEventListener("change", (e) =>
  car.setDark((e.target as HTMLInputElement).checked));
const params = new URLSearchParams(location.search);
if (params.get("width")) {
  document.documentElement.style.setProperty("--col-min", `${params.get("width")}px`);
  document.documentElement.style.setProperty("--col-max", `${params.get("width")}px`);
}
const preset = document.documentElement.dataset.theme;
const startDark = params.has("dark") ? params.get("dark") === "1"
  : preset ? preset === "dark" : window.matchMedia("(prefers-color-scheme: dark)").matches;
document.querySelector<HTMLInputElement>("#dark")!.checked = startDark;
car.setDark(startDark);
if (params.get("two") === "1") {
  document.querySelector<HTMLInputElement>("#two")!.checked = true;
  car.setTwoCars(true);
}
if (params.get("model")) {
  document.querySelector<HTMLSelectElement>("#model")!.value = params.get("model")!;
  car.setModel(params.get("model") as Model);
}
if (params.get("act") === "lock") {
  window.setTimeout(() => void car.hass.callService("lock", "lock", { entity_id: "lock.c0_doors" }), 200);
}
