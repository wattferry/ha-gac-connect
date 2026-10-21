// Readings with length drawn as atlas roads: cased fill, junction dots, distance markers.

import { html, svg, SVGTemplateResult, TemplateResult } from "lit";

/** Blue (mw) marks what can be changed; readings use the neutral road, or a state colour. */
export type Tone = "mw" | "road" | "green" | "yellow" | "red";

const fill = (tone: Tone) => `var(--gac-${tone})`;
const casing = (tone: Tone) => `var(--gac-${tone}-case)`;

function minorRoad(x1: number, x2: number, y: number): SVGTemplateResult {
  return svg`<path d="M${x1} ${y}H${x2}" stroke="var(--gac-minor-case)" stroke-width="7"/>
    <path d="M${x1} ${y}H${x2}" stroke="var(--gac-minor)" stroke-width="5"/>`;
}

function majorRoad(x1: number, x2: number, y: number, tone: Tone): SVGTemplateResult {
  return svg`<path d="M${x1} ${y}H${x2}" stroke=${casing(tone)} stroke-width="14"/>
    <path d="M${x1} ${y}H${x2}" stroke=${fill(tone)} stroke-width="10"/>`;
}

/** Traffic arrows moving along a stretch: the car is charging, energy flows in. */
function flow(x1: number, x2: number, y: number, id: string): SVGTemplateResult {
  const arrows = [];
  for (let x = x1 - 14; x < x2 + 14; x += 14) arrows.push(`M${x} ${y - 3}l3 3-3 3`);
  return svg`<clipPath id=${id}><rect x=${x1} y=${y - 5} width=${Math.max(0, x2 - x1)} height="10"/></clipPath>
    <g clip-path="url(#${id})"><path class="flow" d=${arrows.join("")} fill="none" stroke="var(--gac-minor)"
      stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round" opacity="0.9"/></g>`;
}

export interface GaugeOptions {
  width: number;
  fraction: number | undefined;
  tone: Tone;
  flowing?: boolean;
  marker?: string;
  markerUnit?: string;
  markerLabel?: string;
  id: string;
}

/**
 * A reading drawn as a cased road filled to a fraction, with an atlas distance marker between its
 * two triangles. No junctions or thumb on it: nothing here can be dragged.
 */
export function gauge(o: GaugeOptions): TemplateResult {
  const w = Math.max(160, o.width);
  const x0 = 8;
  const x1 = w - 8;
  const y = 12;
  const f = o.fraction === undefined ? undefined : Math.min(1, Math.max(0, o.fraction));
  const head = f === undefined ? undefined : x0 + f * (x1 - x0);
  const markerY = 36;
  let label: SVGTemplateResult | undefined;
  if (o.marker !== undefined && head !== undefined) {
    const span = head - x0;
    const inside = span > 132;
    const cx = inside ? (x0 + head) / 2 : Math.min(head + 12, x1 - 96);
    const anchor = inside ? "middle" : "start";
    label = svg`
      <path d="M${x0 - 5} ${markerY + 8}L${x0} ${markerY - 4}L${x0 + 5} ${markerY + 8}Z" fill="var(--gac-ink)"/>
      <path d="M${head - 5} ${markerY + 8}L${head} ${markerY - 4}L${head + 5} ${markerY + 8}Z" fill="var(--gac-ink)"/>
      ${inside ? svg`<path d="M${x0 + 9} ${markerY + 3.5}H${cx - 62}M${cx + 62} ${markerY + 3.5}H${head - 9}"
        stroke="var(--gac-ink)" stroke-width="1"/>` : ""}
      <text x=${cx} y=${markerY + 12} text-anchor=${anchor} class="road-text">
        <tspan class="road-lab">${o.markerLabel ?? ""} </tspan><tspan class="road-num">${o.marker}</tspan><tspan
          class="road-unit"> ${o.markerUnit ?? ""}</tspan></text>`;
  }
  return html`<svg class="road" width=${w} height=${o.marker !== undefined ? 56 : 26} viewBox="0 0 ${w} ${
    o.marker !== undefined ? 56 : 26}" aria-hidden="true">
    ${minorRoad(x0, x1, y)}
    ${head !== undefined && head > x0 ? majorRoad(x0, head, y, o.tone) : ""}
    ${head !== undefined && o.flowing ? flow(x0, head - 6, y, `${o.id}-flow`) : ""}
    ${label ?? ""}
  </svg>`;
}

export interface DayRoadOptions {
  width: number;
  /** Minutes after midnight. Equal start and stop means the whole day. */
  start?: number;
  stop?: number;
  tone: Tone;
  now?: number;
  dashed?: boolean;
}

/** A 24-hour road with the charging window drawn as a motorway stretch; overnight windows wrap. */
export function dayRoad(o: DayRoadOptions): TemplateResult {
  const w = Math.max(200, o.width);
  const x0 = 10;
  const x1 = w - 10;
  const y = 16;
  const at = (minutes: number) => x0 + (minutes / 1440) * (x1 - x0);
  const spans: [number, number][] = [];
  if (o.start !== undefined && o.stop !== undefined) {
    if (o.start === o.stop) spans.push([0, 1440]);
    else if (o.start < o.stop) spans.push([o.start, o.stop]);
    else spans.push([o.start, 1440], [0, o.stop]);
  }
  const ticks = Array.from({ length: 9 }, (_, i) => i * 180);
  return html`<svg class="road" width=${w} height="50" viewBox="0 0 ${w} 50" aria-hidden="true">
    ${minorRoad(x0, x1, y)}
    ${spans.map(([a, b]) => o.dashed
      ? svg`<path d="M${at(a)} ${y}H${at(b)}" stroke=${casing(o.tone)} stroke-width="12" stroke-dasharray="6 4"/>
        <path d="M${at(a)} ${y}H${at(b)}" stroke=${fill(o.tone)} stroke-width="8" opacity="0.55"/>`
      : majorRoad(at(a), at(b), y, o.tone))}
    ${ticks.map((m) => svg`<path d="M${at(m)} ${y + 10}v${m % 360 === 0 ? 7 : 4}" stroke="var(--gac-ink)"/>`)}
    ${[0, 360, 720, 1080, 1440].map((m) => svg`<text x=${at(m)} y="45" text-anchor="middle"
      class="road-tick">${String(m / 60).padStart(2, "0")}</text>`)}
    ${o.now !== undefined ? svg`<path d="M${at(o.now) - 4} 0L${at(o.now) + 4} 0L${at(o.now)} 6Z"
      fill="var(--gac-ink)"/>` : ""}
  </svg>`;
}

export interface TempRoadOptions {
  width: number;
  min: number;
  max: number;
  cabin?: number;
  target?: number;
  outside?: number;
  running: boolean;
}

/**
 * The temperature scale as a road, with an arrow from the cabin's temperature to the target: the
 * stretch the A/C will drive, solid while it runs. A reading, so no thumbs; the stepper sets it.
 */
export function tempRoad(o: TempRoadOptions): TemplateResult {
  const w = Math.max(200, o.width);
  const x0 = 12;
  const x1 = w - 12;
  const y = 14;
  const at = (t: number) => x0 + (Math.min(o.max, Math.max(o.min, t)) - o.min) / (o.max - o.min) * (x1 - x0);
  const from = o.cabin !== undefined ? at(o.cabin) : undefined;
  const to = o.target !== undefined ? at(o.target) : undefined;
  const outsideX = o.outside !== undefined ? at(o.outside) : undefined;
  const labelX = outsideX === undefined ? undefined : Math.min(x1 - 36, Math.max(x0 + 36, outsideX));
  const clear = (x: number) => labelX === undefined || Math.abs(labelX - x) > 64;
  let arrow: SVGTemplateResult | string = "";
  if (from !== undefined && to !== undefined && Math.abs(to - from) > 12) {
    const dir = Math.sign(to - from);
    const shaft = to - dir * 9;
    arrow = o.running
      ? svg`<path d="M${from} ${y}H${shaft}" stroke="var(--gac-road-case)" stroke-width="12"/>
          <path d="M${from} ${y}H${shaft}" stroke="var(--gac-road)" stroke-width="8"/>
          <path d="M${to} ${y}L${to - dir * 12} ${y - 9}V${y + 9}Z" fill="var(--gac-road)" stroke="var(--gac-road-case)"
            stroke-width="1.5" stroke-linejoin="round"/>`
      : svg`<path d="M${from} ${y}H${shaft}" stroke="var(--gac-road)" stroke-width="2" stroke-dasharray="5 4"/>
          <path d="M${to} ${y}L${to - dir * 11} ${y - 7}V${y + 7}Z" fill="none" stroke="var(--gac-road)" stroke-width="2"
            stroke-linejoin="round"/>`;
    arrow = svg`${arrow}<path d="M${from} ${y - 7}V${y + 7}" stroke="var(--gac-ink)" stroke-width="2.5"/>`;
  } else if (to !== undefined) {
    arrow = svg`<path d="M${to} ${y - 8}V${y + 8}" stroke="var(--gac-ink)" stroke-width="2.5"/>`;
  }
  return html`<svg class="road" width=${w} height="52" viewBox="0 0 ${w} 52" aria-hidden="true">
    ${minorRoad(x0, x1, y)}
    ${arrow}
    ${outsideX !== undefined ? svg`<path d="M${outsideX - 5} 36L${outsideX} 25L${outsideX + 5} 36Z"
      fill="var(--gac-ink)"/><text x=${labelX} y="49" text-anchor="middle"
      class="road-tick">OUTSIDE ${Math.round(o.outside!)}°</text>` : ""}
    ${clear(x0) ? svg`<text x=${x0} y="49" class="road-tick">${o.min}°</text>` : ""}
    ${clear(x1) ? svg`<text x=${x1} y="49" text-anchor="end" class="road-tick">${o.max}°</text>` : ""}
  </svg>`;
}

export const roadStyles = `
  .road { display: block; overflow: visible; }
  .road-text { font-family: var(--gac-label); fill: var(--gac-ink); }
  .road-lab { font-size: 12px; font-weight: 600; letter-spacing: 0.1em; fill: var(--gac-muted); }
  .road-num { font-size: 26px; font-weight: 600; font-variant-numeric: tabular-nums; }
  .road-unit { font-size: 15px; font-weight: 500; fill: var(--gac-muted); }
  .road-tick { font: 600 12px var(--gac-label); fill: var(--gac-muted); letter-spacing: 0.06em; }
  .plan-label { font: 600 12px var(--gac-label); fill: var(--gac-ink); letter-spacing: 0.06em; }
  .flow { animation: gac-flow 1.6s linear infinite; }
  .blink { animation: gac-blink 1s steps(1, end) infinite; }
  @keyframes gac-blink { 50% { opacity: 0.12; } }
  .lamp-high { filter: drop-shadow(0 0 2.5px rgba(255, 255, 255, 0.95)); }
  @keyframes gac-flow { to { transform: translateX(14px); } }
  @media (prefers-reduced-motion: reduce) { .flow, .blink { animation: none; } }
`;
