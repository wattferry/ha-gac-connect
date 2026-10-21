// Plan views drawn for the project, one per body style, front at the top. Open items are
// drawn open (doors swung or slid, lids lifted) and marked, so the state reads without colour.

import { html, svg, SVGTemplateResult, TemplateResult } from "lit";

export type BodyStyle = "hatch" | "saloon" | "suv" | "coupe_suv" | "mpv";

export const BODY_STYLES: { value: BodyStyle; label: string }[] = [
  { value: "hatch", label: "Hatchback" },
  { value: "saloon", label: "Saloon" },
  { value: "suv", label: "SUV" },
  { value: "coupe_suv", label: "Coupé SUV" },
  { value: "mpv", label: "MPV (sliding doors)" },
];

const GUESSES: [RegExp, BodyStyle][] = [
  [/\b(M6|M8|GN6|GN8|E8|E9|MPV)\b/i, "mpv"],
  [/\bHT\b|\bSSR\b|coup/i, "coupe_suv"],
  [/\bAION\s*E?S\b|\bGA[468]\b|\bEMPOW\b|\bHYPTEC\s*GT\b|saloon|sedan/i, "saloon"],
  [/\bUT\b|\bAION\s*Y\b|hatch/i, "hatch"],
];

/** A guess from the device's model name; the card editor can override it. */
export function guessBody(model: string): BodyStyle {
  return GUESSES.find(([pattern]) => pattern.test(model))?.[1] ?? "suv";
}

interface Shape {
  hwFront: number;
  hwRear: number;
  top: number;
  bottom: number;
  rFront: number;
  rRear: number;
  screen: [number, number];
  rear: [number, number];
  deck?: boolean;
  sliding?: boolean;
  rails?: boolean;
}

const SHAPES: Record<BodyStyle, Shape> = {
  hatch: { hwFront: 40, hwRear: 40, top: 30, bottom: 206, rFront: 22, rRear: 14, screen: [62, 84], rear: [164, 180] },
  saloon: { hwFront: 39, hwRear: 39, top: 22, bottom: 218, rFront: 22, rRear: 16, screen: [70, 92],
            rear: [150, 170], deck: true },
  suv: { hwFront: 43, hwRear: 43, top: 24, bottom: 214, rFront: 18, rRear: 10, screen: [64, 84], rear: [184, 200],
         rails: true },
  coupe_suv: { hwFront: 43, hwRear: 37, top: 22, bottom: 216, rFront: 22, rRear: 16, screen: [64, 86],
               rear: [150, 190] },
  mpv: { hwFront: 45, hwRear: 45, top: 16, bottom: 222, rFront: 16, rRear: 8, screen: [50, 72], rear: [200, 214],
         sliding: true },
};

export interface PlanState {
  doors: Partial<Record<Position, boolean>>;
  windows: Partial<Record<Position, boolean>>;
  boot?: boolean;
  bonnet?: boolean;
  sunroof?: boolean | null;
  lights?: Lights;
}

/** Lamps the car reports. It reports either indicator and the hazard lights as one light. */
export interface Lights {
  headlights?: boolean;
  highBeam?: boolean;
  rearFog?: boolean;
  indicators?: boolean;
}

export type Position = "front_left" | "front_right" | "rear_left" | "rear_right";

const CX = 110;
/** The car is drawn at this scale about its middle; callouts are placed in the scaled space around it. */
const K = 1.12;
const CY = 118;
const at = (x: number, y: number): [number, number] => [CX + (x - CX) * K, CY + (y - CY) * K];

function outline(s: Shape): string {
  const { hwFront: f, hwRear: r, top: t, bottom: b, rFront: rf, rRear: rr } = s;
  return `M${CX - f + rf} ${t}Q${CX} ${t - 5} ${CX + f - rf} ${t}Q${CX + f} ${t} ${CX + f} ${t + rf}`
    + `L${CX + r} ${b - rr}Q${CX + r} ${b} ${CX + r - rr} ${b}Q${CX} ${b + 3} ${CX - r + rr} ${b}`
    + `Q${CX - r} ${b} ${CX - r} ${b - rr}L${CX - f} ${t + rf}Q${CX - f} ${t} ${CX - f + rf} ${t}Z`;
}

/** Half-width of the body at a given y, for placing side details on tapered bodies. */
function halfWidth(s: Shape, y: number): number {
  const k = (y - s.top) / (s.bottom - s.top);
  return s.hwFront + (s.hwRear - s.hwFront) * Math.min(1, Math.max(0, k));
}

const warn = "var(--gac-yellow)";

function marker(x: number, y: number): SVGTemplateResult {
  return svg`<path d="M${x - 5} ${y + 4.5}L${x} ${y - 5}L${x + 5} ${y + 4.5}Z" fill=${warn}
    stroke="var(--gac-ink)" stroke-linejoin="round"/>`;
}

export function plan(style: BodyStyle, state: PlanState, title: string): TemplateResult {
  const s = SHAPES[style];
  const [screenTop, screenBottom] = s.screen;
  const [rearTop, rearBottom] = s.rear;
  const mid = Math.round((screenBottom + rearTop) / 2);
  const doorSpans: Record<"front" | "rear", [number, number]> = {
    front: [screenBottom - 6, mid],
    rear: [mid, Math.min(rearTop + 6, mid + (mid - screenBottom) + 6)],
  };
  const axleFront = s.top + (s.bottom - s.top) * 0.2;
  const axleRear = s.bottom - (s.bottom - s.top) * 0.19;
  const wheel = (y: number, side: -1 | 1) => {
    const hw = halfWidth(s, y);
    return svg`<rect x=${CX + side * (hw + 1) - 5} y=${y - 14} width="10" height="28" rx="2.5" fill="var(--gac-ink)"/>`;
  };

  // Each open item is named on the plan; the card lists them again in words below it.
  const labels: SVGTemplateResult[] = [];
  const label = (x: number, y: number, text: string, anchor: "start" | "middle" | "end") => {
    const [lx, ly] = at(x, y);
    labels.push(svg`<text class="plan-label" x=${lx} y=${ly} text-anchor=${anchor}>${text}</text>`);
  };
  const callout = (x: number, y: number) => labels.push(marker(...at(x, y)));

  const sideWindow = (pos: Position) => {
    const [row, side] = pos.split("_") as ["front" | "rear", "left" | "right"];
    const [y1, y2] = row === "front" ? [screenBottom + 2, mid - 2] : [mid + 2, rearTop - 2];
    const dir = side === "left" ? -1 : 1;
    const hw = halfWidth(s, (y1 + y2) / 2);
    const x = dir < 0 ? CX - hw + 4 : CX + hw - 11;
    const open = state.windows[pos] === true;
    if (open && state.doors[pos] !== true) {
      const y = (y1 + y2) / 2;
      callout(CX + dir * (hw + 7), y);
      label(CX + dir * (hw + 14), y + 4, "WINDOW", dir < 0 ? "end" : "start");
    }
    return svg`<rect x=${x} y=${y1} width="7" height=${Math.max(4, y2 - y1)} fill=${open ? warn : "var(--gac-glass)"}
      stroke="var(--gac-ink)" stroke-width="1"/>`;
  };

  const door = (pos: Position) => {
    const [row, side] = pos.split("_") as ["front" | "rear", "left" | "right"];
    const [y1, y2] = doorSpans[row];
    const dir = side === "left" ? -1 : 1;
    const hw = halfWidth(s, y1);
    const edge = CX + dir * hw;
    if (state.doors[pos] !== true) {
      return svg`<path d="M${edge} ${y2}h${-dir * 12}" stroke="var(--gac-ink)" stroke-width="1"/>`;
    }
    const len = y2 - y1;
    if (s.sliding && row === "rear") {
      // Slid back along the side, stopping at the rear corner.
      const end = s.bottom - s.rRear - 6;
      const start = Math.min(y1 + len * 0.45, end - len * 0.8);
      const y = (start + end) / 2;
      callout(edge + dir * 16, y);
      label(edge + dir * 24, y + 4, "DOOR", dir < 0 ? "end" : "start");
      return svg`<rect x=${dir < 0 ? edge - 9 : edge + 3} y=${start} width="6" height=${end - start}
        fill=${warn} stroke="var(--gac-ink)" stroke-width="1.2"/>`;
    }
    const angle = 38 * Math.PI / 180;
    const ex = edge + dir * Math.sin(angle) * len;
    const ey = y1 + Math.cos(angle) * len;
    label(ex + dir * 6, ey + 22, "DOOR", "middle");
    return svg`<g><path d="M${edge} ${y1}L${ex} ${ey}" stroke="var(--gac-ink)" stroke-width="6.5"
      stroke-linecap="round"/><path d="M${edge} ${y1}L${ex} ${ey}" stroke=${warn} stroke-width="4"
      stroke-linecap="round"/>${marker(ex + dir * 6, ey + 6)}</g>`;
  };

  const lidWidth = (y: number) => (halfWidth(s, y) - 12) * 2;
  const lid = (y: number, text: string) => {
    const half = lidWidth(y) / 2;
    callout(CX + half + 9, y + 7);
    label(CX + half + 16, y + 11, text, "start");
    return svg`<rect x=${CX - half} y=${y} width=${half * 2} height="16" rx="2" fill=${warn}
      stroke="var(--gac-ink)" stroke-width="1.5"/>`;
  };
  const bootLid = state.boot ? lid(s.bottom - 1, "BOOT") : "";
  const bonnetLid = state.bonnet ? lid(s.top - 15, "BONNET") : "";
  // Lamps: indicators blink yellow at the four outer corners; headlights (larger and brighter on
  // high beam) sit inward at the front and the rear fog light at the back, so all can show at once.
  const lamp = (x: number, y: number, size: number, up: boolean, fill: string, cls = "") => {
    const tip = up ? y - size : y + size;
    return svg`<path class=${cls} d="M${x - size * 0.62} ${y}L${x} ${tip}L${x + size * 0.62} ${y}Z" fill=${fill}
      stroke="var(--gac-ink)" stroke-width="1" stroke-linejoin="round"/>`;
  };
  const lights = state.lights ?? {};
  const front = s.top - 3;
  const rear = s.bottom + 3;
  const fogY = state.boot ? s.bottom + 19 : rear;
  const beams = svg`
    ${lights.headlights || lights.highBeam ? [-1, 1].map((side) => lights.highBeam
      ? lamp(CX + side * (s.hwFront - 14), front - 1, 15, true, "var(--gac-lamp-high)", "lamp-high")
      : lamp(CX + side * (s.hwFront - 14), front, 10, true, "var(--gac-lamp)")) : ""}
    ${lights.rearFog ? lamp(CX - s.hwRear * 0.4, fogY, 10, false, "var(--gac-lamp-high)") : ""}
    ${lights.indicators ? [-1, 1].flatMap((side) => [
      lamp(CX + side * (s.hwFront + 1), s.top + 9, 9, true, "var(--gac-yellow)", "blink"),
      lamp(CX + side * (s.hwRear + 1), s.bottom - 9, 9, false, "var(--gac-yellow)", "blink"),
    ]) : ""}`;

  const roofLeft = CX - halfWidth(s, mid) + 12;
  const roofRight = CX + halfWidth(s, mid) - 12;
  const roofHeight = Math.min(42, (rearTop - screenBottom) / 2.2);
  if (state.sunroof) {
    const y = at(0, screenBottom + 8 + roofHeight / 2 + 4)[1];
    labels.push(svg`<text class="plan-label" x="218" y=${y} text-anchor="end">SUNROOF</text>`);
  }
  const sunroof = state.sunroof === undefined ? "" : svg`<rect x=${roofLeft + 6} y=${screenBottom + 8}
    width=${roofRight - roofLeft - 12} height=${roofHeight}
    fill=${state.sunroof ? warn : "var(--gac-glass)"} stroke="var(--gac-ink)" stroke-width="1"/>`;
  const hwScreen = halfWidth(s, screenBottom);
  const hwRear = halfWidth(s, rearTop);
  const mirror = (side: -1 | 1) => svg`<rect x=${CX + side * (hwScreen + 4) - 4} y=${screenTop + 2} width="8"
    height="6" rx="1" fill="var(--gac-body)" stroke="var(--gac-ink)"/>`;

  const windows = (["front_left", "rear_left", "front_right", "rear_right"] as Position[]).map(sideWindow);
  const doors = (["front_left", "rear_left", "front_right", "rear_right"] as Position[]).map(door);
  return html`<svg class="plan" viewBox="0 -28 220 296" role="img" aria-label=${title}>
    <g transform="translate(${CX} ${CY}) scale(${K}) translate(${-CX} ${-CY})">
    ${wheel(axleFront, -1)}${wheel(axleFront, 1)}${wheel(axleRear, -1)}${wheel(axleRear, 1)}
    ${bootLid}${bonnetLid}
    <path d=${outline(s)} fill="var(--gac-body)" stroke="var(--gac-ink)" stroke-width="4.5"/>
    <path d=${outline(s)} fill="none" stroke="var(--gac-body)" stroke-width="1.6"/>
    ${mirror(-1)}${mirror(1)}
    <g stroke="var(--gac-ink)" stroke-width="1">
      <path d="M${CX - hwScreen + 10} ${screenTop + 4}Q${CX} ${screenTop - 4} ${CX + hwScreen - 10} ${screenTop + 4}
        L${CX + hwScreen - 6} ${screenBottom}H${CX - hwScreen + 6}Z" fill="var(--gac-glass)"/>
      <path d="M${CX - hwRear + 7} ${rearTop}H${CX + hwRear - 7}L${CX + hwRear - 11} ${rearBottom}Q${CX} ${
        rearBottom + 4} ${CX - hwRear + 11} ${rearBottom}Z" fill="var(--gac-glass)"/>
      <path d="M${roofLeft} ${screenBottom}V${rearTop}M${roofRight} ${screenBottom}V${rearTop}" fill="none"/>
      ${s.deck ? svg`<path d="M${CX - hwRear + 10} ${rearBottom + 14}H${CX + hwRear - 10}" fill="none"/>` : ""}
      ${s.rails ? svg`<path d="M${roofLeft + 3} ${screenBottom + 6}V${rearTop - 6}M${roofRight - 3} ${
        screenBottom + 6}V${rearTop - 6}" stroke-width="2" stroke-linecap="round" fill="none"/>` : ""}
      ${s.sliding ? svg`<path d="M${CX - halfWidth(s, mid) + 2} ${mid + 4}V${rearTop + 4}M${
        CX + halfWidth(s, mid) - 2} ${mid + 4}V${rearTop + 4}" stroke-dasharray="3 2" fill="none"/>` : ""}
    </g>
    ${sunroof}
    ${windows}
    ${doors}
    ${beams}
    </g>
    ${labels}
  </svg>`;
}
