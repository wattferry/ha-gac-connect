// GAC Connect dashboard cards. The integration serves this file and adds it to every dashboard.

import { defineControls } from "./controls";
import { GacCardEditor } from "./editor";
import { loadFonts } from "./theme";
import { GacActivityCard } from "./cards/activity-card";
import { GacChargingCard } from "./cards/charging-card";
import { GacClimateCard } from "./cards/climate-card";
import { GacLocationCard } from "./cards/location-card";
import { GacSettingsCard } from "./cards/settings-card";
import { GacVehicleCard } from "./cards/vehicle-card";

const CARDS: [string, CustomElementConstructor, string, string][] = [
  ["gac-vehicle-card", GacVehicleCard, "GAC Vehicle", "Battery, range, what is open on the car, and quick actions."],
  ["gac-climate-card", GacClimateCard, "GAC Climate", "Cabin temperature, A/C, fan, seats and comfort features."],
  ["gac-charging-card", GacChargingCard, "GAC Charging", "Charging state, Charge now and the charging window."],
  ["gac-location-card", GacLocationCard, "GAC Location", "Where the car is, and location tracking."],
  ["gac-activity-card", GacActivityCard, "GAC Activity", "Connection, commands and alerts over the last two days."],
  ["gac-settings-card", GacSettingsCard, "GAC Settings", "Permissions, tracking, polling and entity choices."],
];

loadFonts(import.meta.url);
defineControls();
if (!customElements.get("gac-card-editor")) customElements.define("gac-card-editor", GacCardEditor);

const registry = ((window as unknown as { customCards?: unknown[] }).customCards ??= []);
for (const [type, element, name, description] of CARDS) {
  if (customElements.get(type)) continue;
  customElements.define(type, element);
  registry.push({ type, name, description, preview: true,
                  documentationURL: "https://github.com/wattferry/ha-gac-connect#dashboard-cards" });
}
