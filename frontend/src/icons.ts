// One stroke family: 20 x 20, 1.5 px, round joins. Drawn for the cards, not taken from a library.

import { html, svg, SVGTemplateResult, TemplateResult } from "lit";

const paths: Record<string, SVGTemplateResult> = {
  car: svg`<path d="M4 13V9.5L5.6 5.4A1.5 1.5 0 0 1 7 4.5h6a1.5 1.5 0 0 1 1.4.9L16 9.5V13"/><path d="M3 13h14v2.5H3zM4 9.5h12"/><path d="M5 15.5V17M15 15.5V17"/>`,
  climate: svg`<path d="M10 2.5v15M3.5 6.2l13 7.6M3.5 13.8l13-7.6"/><path d="M8 3.8L10 5.5 12 3.8M8 16.2L10 14.5 12 16.2"/>`,
  plug: svg`<path d="M7 2.5v4M13 2.5v4"/><path d="M5 6.5h10v3a5 5 0 0 1-10 0z"/><path d="M10 14.5v3"/>`,
  pin: svg`<path d="M10 17.5s5.5-5 5.5-9.5a5.5 5.5 0 0 0-11 0c0 4.5 5.5 9.5 5.5 9.5z"/><circle cx="10" cy="8" r="2"/>`,
  activity: svg`<path d="M6 3v14"/><circle cx="6" cy="5" r="1.6"/><circle cx="6" cy="10" r="1.6"/><circle cx="6" cy="15" r="1.6"/><path d="M10 5h7M10 10h5M10 15h6"/>`,
  settings: svg`<path d="M3 5.5h8M15 5.5h2M3 14.5h2M9 14.5h8"/><circle cx="13" cy="5.5" r="2"/><circle cx="7" cy="14.5" r="2"/>`,
  lock: svg`<rect x="4" y="9" width="12" height="8.5" rx="1"/><path d="M6.5 9V6.5a3.5 3.5 0 0 1 7 0V9"/>`,
  unlock: svg`<rect x="4" y="9" width="12" height="8.5" rx="1"/><path d="M6.5 9V6.5a3.5 3.5 0 0 1 6.8-1.2"/>`,
  ac: svg`<path d="M10 3v14M4 6.5l12 7M4 13.5l12-7"/>`,
  vent: svg`<path d="M3 15V8l4-4h10v11z"/><path d="M10 7.5v4.5M8 10l2 2 2-2"/>`,
  boot: svg`<path d="M3 16V9.5L5.5 5h9L17 9.5V16z"/><path d="M3 11.5h14M8 14h4"/>`,
  horn: svg`<path d="M3 8v4h3l6 4V4L6 8z"/><path d="M15 7a4 4 0 0 1 0 6"/>`,
  lights: svg`<path d="M10 4.5C6.5 4.5 4 7 4 10s2.5 5.5 6 5.5z"/><path d="M13 6.5h4M13 10h4M13 13.5h4"/>`,
  windows: svg`<path d="M3.5 16.5V9L8 4h8.5v12.5z"/><path d="M3.5 10.5h13"/>`,
  sunroof: svg`<rect x="3.5" y="3.5" width="13" height="13" rx="1"/><rect x="6.5" y="6.5" width="7" height="5"/>`,
  refresh: svg`<path d="M16 10a6 6 0 1 1-1.8-4.3"/><path d="M16.5 3.5v3.5H13"/>`,
  power: svg`<path d="M10 3v7"/><path d="M6.2 5.8a6 6 0 1 0 7.6 0"/>`,
  bolt: svg`<path d="M11 2.5L5 11h5l-1 6.5L15 9h-5z"/>`,
  seat: svg`<path d="M7 3.5h3l1 8H7.5z"/><path d="M6.5 11.5h7l1.5 3.5H8z"/><path d="M8 15v2.5M14 15v2.5"/>`,
  wheel: svg`<circle cx="10" cy="10" r="6.5"/><circle cx="10" cy="10" r="1.5"/><path d="M4 9.5h4.5M11.5 9.5H16M10 11.5v5"/>`,
  fridge: svg`<rect x="5" y="2.5" width="10" height="15" rx="1"/><path d="M5 8h10M7.5 4.5v2M7.5 10v3"/>`,
  battery: svg`<rect x="2.5" y="6" width="13" height="8" rx="1"/><path d="M17.5 8.5v3"/><path d="M5 8.5h4v3H5z"/>`,
  recirculate: svg`<path d="M15 8a5 5 0 0 0-9.3-1.5M5 12a5 5 0 0 0 9.3 1.5"/><path d="M5 3.5v3.3h3.3M15 16.5v-3.3h-3.3"/>`,
  sterilise: svg`<circle cx="10" cy="10" r="3"/><path d="M10 3v2M10 15v2M3 10h2M15 10h2M5 5l1.4 1.4M13.6 13.6L15 15M5 15l1.4-1.4M13.6 6.4L15 5"/>`,
  minus: svg`<path d="M5 10h10"/>`,
  plus: svg`<path d="M5 10h10M10 5v10"/>`,
  check: svg`<path d="M4.5 10.5l3.5 3.5 7.5-8"/>`,
  map: svg`<path d="M3 5.5l4.5-2 5 2 4.5-2v11l-4.5 2-5-2-4.5 2z"/><path d="M7.5 3.5v11M12.5 5.5v11"/>`,
  chevron: svg`<path d="M7.5 5l5 5-5 5"/>`,
  connector: svg`<circle cx="10" cy="10" r="6.5"/><circle cx="7.5" cy="8.5" r="1"/><circle cx="12.5" cy="8.5" r="1"/><circle cx="10" cy="12.5" r="1"/>`,
};

export function icon(name: keyof typeof paths | string): TemplateResult {
  return html`<svg viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.5"
    stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${paths[name] ?? paths.car}</svg>`;
}

/** State marks that do not rely on colour: square = fine, triangle = attention, ring = waiting. */
export type MarkKind = "ok" | "warn" | "fault" | "wait" | "off" | "info" | "lamp";

export function mark(kind: MarkKind): TemplateResult {
  const shapes = {
    ok: svg`<rect x="1" y="1" width="10" height="10" fill="var(--gac-green)" stroke="var(--gac-green-case)"/>`,
    warn: svg`<path d="M6 1L11.2 10.6H.8z" fill="var(--gac-yellow)" stroke="var(--gac-ink)" stroke-linejoin="round"/>`,
    fault: svg`<path d="M6 1L11.2 10.6H.8z" fill="var(--gac-red)" stroke="var(--gac-ink)" stroke-linejoin="round"/>`,
    wait: svg`<circle cx="6" cy="6" r="4.5" fill="none" stroke="var(--gac-mw)" stroke-width="1.5" stroke-dasharray="2.4 1.6"/>`,
    off: svg`<rect x="1.5" y="1.5" width="9" height="9" fill="none" stroke="var(--gac-muted)"/>`,
    info: svg`<circle cx="6" cy="6" r="4.25" fill="none" stroke="var(--gac-ink)" stroke-width="1.5"/>`,
    lamp: svg`<path d="M6 1L11.2 10.6H.8z" fill="var(--gac-lamp-high)" stroke="var(--gac-ink)" stroke-linejoin="round"/>`,
  };
  return html`<svg class="mark" viewBox="0 0 12 12" aria-hidden="true">${shapes[kind]}</svg>`;
}
