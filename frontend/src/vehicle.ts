// Finds a car's entities by device and translation key, so renamed entities keep working.
// The cards never decide what a car has: the integration creates entities only for the equipment
// it detected (the car's capability list plus the owner's Always show and Omit choices) and
// disables the rest, so a feature is shown exactly when its entity is here.

import { HassEntity, HomeAssistant, known } from "./ha";

export const DOMAIN = "gac_connect";

export interface VehicleOption {
  id: string;
  name: string;
}

export function vehicles(hass: HomeAssistant): VehicleOption[] {
  const ids = new Set<string>();
  for (const entry of Object.values(hass.entities ?? {})) {
    if (entry.platform === DOMAIN && entry.device_id) ids.add(entry.device_id);
  }
  return [...ids].map((id) => {
    const device = hass.devices?.[id];
    return { id, name: device?.name_by_user || device?.name || "GAC vehicle" };
  }).sort((a, b) => a.name.localeCompare(b.name));
}

const indexes = new WeakMap<object, Map<string, Map<string, string>>>();

function index(hass: HomeAssistant, deviceId: string): Map<string, string> {
  let byDevice = indexes.get(hass.entities);
  if (!byDevice) {
    byDevice = new Map();
    indexes.set(hass.entities, byDevice);
  }
  let keys = byDevice.get(deviceId);
  if (!keys) {
    keys = new Map();
    for (const entry of Object.values(hass.entities)) {
      if (entry.platform !== DOMAIN || entry.device_id !== deviceId || !entry.translation_key) continue;
      keys.set(`${entry.entity_id.split(".")[0]}.${entry.translation_key}`, entry.entity_id);
    }
    byDevice.set(deviceId, keys);
  }
  return keys;
}

/** Command names as the integration's Last command sensor lists them, by family. */
const COMMAND_LABELS: [RegExp, string][] = [
  [/^unlock$/, "Unlock"], [/^lock$/, "Lock"],
  [/^aircon|^climate|^ac-/, "A/C"], [/^ventilate/, "Ventilation"],
  [/^tailgate-open/, "Open boot"], [/^tailgate-close/, "Close boot"],
  [/^window-open/, "Open windows"], [/^window-close/, "Close windows"],
  [/^sunroof-open/, "Open sunroof"], [/^sunroof-close/, "Close sunroof"],
  [/^horn/, "Sound horn"], [/^flash/, "Flash lights"], [/^steering/, "Steering wheel heat"],
  [/^seat-1/, "Driver seat"], [/^seat-2/, "Passenger seat"], [/^seat-/, "Rear seat"],
  [/^battery-precondition/, "Smart battery temp"], [/^antivirus/, "Sterilisation"],
  [/^fridge/, "Fridge"], [/^charge-now/, "Charge now"], [/^charge-resume/, "Scheduled charging"],
  [/^charge-window|^charge-schedule/, "Charge window"], [/^charger-unlock/, "Unlock connector"],
  [/^vehicle-power-off/, "Turn vehicle off"],
];

export function commandLabel(command: string | undefined | null): string {
  if (!command) return "Command";
  return COMMAND_LABELS.find(([pattern]) => pattern.test(command))?.[1]
    ?? command.replace(/-/g, " ").replace(/^./, (c) => c.toUpperCase());
}

export const COMMAND_STATES: Record<string, string> = {
  idle: "No command yet", sending: "Sending", pending: "Waiting for the car",
  awaiting_report: "Accepted; waiting for the car's report", confirmed: "Confirmed by the car",
  reported_success: "The car reported success", rejected: "Refused by the car", failed: "Request failed",
  timed_out: "Not confirmed in time", cancelled: "Cancelled", superseded: "Replaced by a newer request",
};

export type Outcome = "pending" | "ok" | "refused" | "unconfirmed" | "quiet";

export function outcome(state: string | undefined): Outcome {
  switch (state) {
    case "sending": case "pending": case "awaiting_report": return "pending";
    case "confirmed": case "reported_success": return "ok";
    case "rejected": case "failed": return "refused";
    case "timed_out": return "unconfirmed";
    default: return "quiet";
  }
}

export class Vehicle {
  readonly name: string;
  readonly model: string;
  readonly vin: string | undefined;
  private readonly keys: Map<string, string>;

  constructor(readonly hass: HomeAssistant, readonly deviceId: string) {
    const device = hass.devices?.[deviceId];
    this.name = device?.name_by_user || device?.name || "GAC vehicle";
    this.model = device?.model || device?.name || "";
    this.vin = device?.serial_number ?? undefined;
    this.keys = index(hass, deviceId);
  }

  get exists(): boolean {
    return this.keys.size > 0;
  }

  id(key: string): string | undefined {
    return this.keys.get(key);
  }

  has(key: string): boolean {
    return this.get(key) !== undefined;
  }

  /**
   * The entity's state, or nothing when this car lacks it. A registry entry the integration no
   * longer provides (an equipment item an older version created) stays as a "restored" state;
   * that is a leftover, not a feature, so it counts as absent too.
   */
  get(key: string): HassEntity | undefined {
    const id = this.keys.get(key);
    const state = id ? this.hass.states[id] : undefined;
    return state?.attributes.restored === true ? undefined : state;
  }

  /** Commands the integration is still waiting on, from the Last command sensor. */
  pending(prefixes: string[]): boolean {
    const last = this.get("sensor.last_command");
    const commands: string[] = last?.attributes.pending_commands ?? [];
    return commands.some((command) => prefixes.some((prefix) => command.startsWith(prefix)));
  }

  /** The latest command's outcome when it concerns one of these command families. */
  lastFor(prefixes: string[]): { state: string; reason?: string; at?: Date } | undefined {
    const last = this.get("sensor.last_command");
    if (!known(last)) return undefined;
    const command: string | undefined = last.attributes.command;
    if (!command || !prefixes.some((prefix) => command.startsWith(prefix))) return undefined;
    return { state: last.state, reason: refusal(last), at: last.attributes.requested_at
      ? new Date(last.attributes.requested_at) : undefined };
  }

  call(domain: string, service: string, key: string, data: Record<string, unknown> = {}): Promise<unknown> {
    const entityId = this.id(key);
    if (!entityId) return Promise.resolve();
    // Home Assistant shows its own toast on failure; the card shows the car's answer.
    return this.hass.callService(domain, service, { entity_id: entityId, ...data }).catch(() => undefined);
  }

  action(service: string, data: Record<string, unknown>): Promise<unknown> {
    const target = this.vin ? { vin: this.vin, ...data } : data;
    return this.hass.callService(DOMAIN, service, target).catch(() => undefined);
  }
}

/** Why the car refused, in its own words where it gave them. */
export function refusal(last: HassEntity | undefined): string | undefined {
  if (!last) return undefined;
  const causes: string[] = last.attributes.reported_causes ?? [];
  if (causes.length) return causes.join(", ");
  return last.attributes.refusal_reason ?? last.attributes.failure_reason ?? undefined;
}
