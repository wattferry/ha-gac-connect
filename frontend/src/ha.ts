// The slice of Home Assistant's frontend API the cards use.

export interface HassEntity {
  entity_id: string;
  state: string;
  attributes: Record<string, any>;
  last_changed: string;
  last_updated: string;
}

export interface EntityRegistryDisplayEntry {
  entity_id: string;
  device_id?: string;
  platform?: string;
  translation_key?: string;
  entity_category?: "config" | "diagnostic";
  hidden?: boolean;
}

export interface DeviceRegistryEntry {
  id: string;
  name: string | null;
  name_by_user?: string | null;
  model?: string | null;
  serial_number?: string | null;
}

export interface HomeAssistant {
  states: Record<string, HassEntity>;
  entities: Record<string, EntityRegistryDisplayEntry>;
  devices: Record<string, DeviceRegistryEntry>;
  themes: { darkMode?: boolean };
  locale?: { language?: string; time_format?: string; first_weekday?: string };
  language?: string;
  callService(domain: string, service: string, data?: Record<string, unknown>,
              target?: Record<string, unknown>): Promise<unknown>;
  /** An attribute value in the integration's own words, in the user's language. */
  formatEntityAttributeValue?(entity: HassEntity, attribute: string, value?: unknown): string;
  connection: {
    subscribeMessage<T>(callback: (message: T) => void, message: Record<string, unknown>): Promise<() => Promise<void>>;
  };
}

export interface CardConfig {
  type: string;
  /** The car's device ID: each card shows one car. */
  device?: string;
  [key: string]: unknown;
}

export const UNKNOWN = new Set(["unknown", "unavailable", ""]);

/** The integration's translated name for an attribute value; the fallback where it has none. */
export function attributeLabel(hass: HomeAssistant, entity: HassEntity, attribute: string, value: string,
                               fallback: string): string {
  const label = hass.formatEntityAttributeValue?.(entity, attribute, value);
  return label && label !== value ? label : fallback;
}

export function known(entity: HassEntity | undefined): entity is HassEntity {
  return entity !== undefined && !UNKNOWN.has(entity.state);
}

export function num(entity: HassEntity | undefined): number | undefined {
  if (!known(entity)) return undefined;
  const value = Number(entity.state);
  return Number.isFinite(value) ? value : undefined;
}

export function isOn(entity: HassEntity | undefined): boolean | undefined {
  if (!known(entity)) return undefined;
  return entity.state === "on";
}

export function fire(node: HTMLElement, type: string, detail?: unknown): void {
  node.dispatchEvent(new CustomEvent(type, { detail, bubbles: true, composed: true }));
}

export function moreInfo(node: HTMLElement, entityId: string | undefined): void {
  if (entityId) fire(node, "hass-more-info", { entityId });
}

export function navigate(node: HTMLElement, path: string): void {
  history.pushState(null, "", path);
  fire(node, "location-changed", { replace: false });
}

export function formatNumber(hass: HomeAssistant, value: number, digits = 0): string {
  return value.toLocaleString(hass.locale?.language ?? hass.language ?? "en-GB",
                              { minimumFractionDigits: digits, maximumFractionDigits: digits });
}

/** Whether times use AM/PM, from Home Assistant's own time format setting. */
export function hourCycle(hass: HomeAssistant): boolean {
  const format = hass.locale?.time_format;
  if (format === "12") return true;
  if (format === "24") return false;
  const language = format === "system" ? undefined : hass.locale?.language ?? hass.language;
  return new Intl.DateTimeFormat(language, { hour: "numeric" }).resolvedOptions().hour12 === true;
}

/** Minutes after midnight as the owner reads a time of day: "23:09" or "11:09 PM". */
export function timeOfDay(hass: HomeAssistant, minutes: number | undefined): string {
  if (minutes === undefined) return "––:––";
  const date = new Date(2024, 0, 1, Math.floor(minutes / 60) % 24, minutes % 60);
  return date.toLocaleTimeString(hass.locale?.language ?? hass.language ?? "en-GB",
                                 { hour: "numeric", minute: "2-digit", hour12: hourCycle(hass) });
}

const WEEKDAYS = ["sunday", "monday", "tuesday", "wednesday", "thursday", "friday", "saturday"];

/** The first day of the week (0 Sunday … 6 Saturday), from Home Assistant's setting or its language. */
export function firstWeekday(hass: HomeAssistant): number {
  const setting = hass.locale?.first_weekday ?? "language";
  if (WEEKDAYS.includes(setting)) return WEEKDAYS.indexOf(setting);
  const language = hass.locale?.language ?? hass.language ?? "en";
  try {
    const locale = new Intl.Locale(language) as Intl.Locale & {
      getWeekInfo?: () => { firstDay: number }; weekInfo?: { firstDay: number } };
    const first = (locale.getWeekInfo?.() ?? locale.weekInfo)?.firstDay;
    if (first) return first % 7;
  } catch {
    // An unknown language falls through to the default below.
  }
  return /^en(-US)?$/i.test(language) ? 0 : 1;
}

/** A weekday's name in the owner's language (0 Sunday … 6 Saturday). */
export function weekdayName(hass: HomeAssistant, day: number, style: "short" | "long"): string {
  return new Date(2024, 0, 7 + day).toLocaleDateString(hass.locale?.language ?? hass.language ?? "en-GB",
                                                       { weekday: style });
}

export function clock(hass: HomeAssistant, date: Date): string {
  return date.toLocaleTimeString(hass.locale?.language ?? "en-GB",
                                 { hour: "2-digit", minute: "2-digit", hour12: hourCycle(hass) });
}

/** "4 min ago", "2 h ago", "yesterday 18:02". */
export function ago(hass: HomeAssistant, when: Date | undefined, now = new Date()): string {
  if (!when || Number.isNaN(when.getTime())) return "time unknown";
  const seconds = Math.round((now.getTime() - when.getTime()) / 1000);
  if (seconds < -60) return `at ${clock(hass, when)}`;
  if (seconds < 60) return "just now";
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes} min ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24 && when.getDate() === now.getDate()) return `${hours} h ago`;
  const yesterday = new Date(now);
  yesterday.setDate(now.getDate() - 1);
  if (when.toDateString() === yesterday.toDateString()) return `yesterday ${clock(hass, when)}`;
  // Older: the date and the time, as "16 Oct, 17:28".
  const date = when.toLocaleDateString(hass.locale?.language ?? hass.language ?? "en-GB",
                                       { day: "numeric", month: "short",
                                         ...(when.getFullYear() !== now.getFullYear() ? { year: "numeric" } : {}) });
  return `${date}, ${clock(hass, when)}`;
}

/** Minutes as "1 h 40 min". */
export function duration(minutes: number): string {
  const whole = Math.max(0, Math.round(minutes));
  const hours = Math.floor(whole / 60);
  const rest = whole % 60;
  if (hours === 0) return `${rest} min`;
  return rest === 0 ? `${hours} h` : `${hours} h ${rest} min`;
}

export function timestamp(entity: HassEntity | undefined): Date | undefined {
  if (!known(entity)) return undefined;
  const date = new Date(entity.state);
  return Number.isNaN(date.getTime()) ? undefined : date;
}
