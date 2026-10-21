// The atlas: land-tint ground, road classes as the only colours, condensed caps for labels.

import { css } from "lit";

const FONTS: [string, number][] = [
  ["Barlow Condensed", 500], ["Barlow Condensed", 600], ["Barlow Condensed", 700],
  ["Barlow", 400], ["Barlow", 500],
];
const RANGES = {
  latin: "U+0000-00FF,U+0131,U+0152-0153,U+02BB-02BC,U+02C6,U+02DA,U+02DC,U+0304,U+0308,U+0329,U+2000-206F,"
    + "U+20AC,U+2122,U+2191,U+2193,U+2212,U+2215,U+FEFF,U+FFFD",
  "latin-ext": "U+0100-02BA,U+02BD-02C5,U+02C7-02CC,U+02CE-02D7,U+02DD-02FF,U+0304,U+0308,U+0329,U+1D00-1DBF,"
    + "U+1E00-1E9F,U+1EF2-1EFF,U+2020,U+20A0-20AB,U+20AD-20C0,U+2113,U+2C60-2C7F,U+A720-A7FF",
};

/** Shadow roots cannot declare fonts, so the faces shipped beside the bundle go in the document once. */
export function loadFonts(base: string): void {
  // A page that already loads Barlow (the published demo) keeps its own faces.
  if (document.getElementById("gac-connect-fonts") || document.querySelector('link[href*="family=Barlow"]')) return;
  const rules = FONTS.flatMap(([family, weight]) => Object.entries(RANGES).map(([subset, range]) => {
    const file = `${family.toLowerCase().replace(" ", "-")}-${subset}-${weight}-normal.woff2`;
    return `@font-face{font-family:"${family}";font-style:normal;font-weight:${weight};font-display:swap;`
      + `src:url(${new URL(`fonts/${file}`, base).href}) format("woff2");unicode-range:${range}}`;
  }));
  const style = document.createElement("style");
  style.id = "gac-connect-fonts";
  style.textContent = rules.join("\n");
  document.head.append(style);
}

export const tokens = css`
  :host {
    --gac-land: #eaf0e2;
    --gac-paper: #f8faf4;
    --gac-water: #dce6ec;
    --gac-ink: #1e2421;
    --gac-muted: #535b56;
    --gac-hair: rgba(30, 36, 33, 0.2);
    --gac-edge: rgba(30, 36, 33, 0.34);
    --gac-mw: #2e6db4;
    --gac-mw-case: #1b3f6b;
    --gac-mw-ink: #ffffff;
    --gac-green: #1f8a4c;
    --gac-green-case: #145c33;
    --gac-red: #d2352b;
    --gac-red-case: #8e1f18;
    --gac-red-ink: #b02a21;
    --gac-yellow: #f2c230;
    --gac-yellow-case: #8a6a0a;
    --gac-minor: #ffffff;
    --gac-minor-case: #a9b4a3;
    --gac-road: #56625b;
    --gac-road-case: #2f3833;
    --gac-lamp: #f4f6f0;
    --gac-lamp-high: #ffffff;
    --gac-body: #f8faf4;
    --gac-glass: #dce6ec;
    --gac-label: "Barlow Condensed", "Arial Narrow", "Roboto Condensed", sans-serif;
    --gac-text: "Barlow", system-ui, -apple-system, "Segoe UI", Roboto, sans-serif;
    color-scheme: light;
  }
  :host([dark]) {
    --gac-land: #17201b;
    --gac-paper: #1f2a24;
    --gac-water: #1a2a35;
    --gac-ink: #e4ebe2;
    --gac-muted: #a4aea7;
    --gac-hair: rgba(228, 235, 226, 0.16);
    --gac-edge: rgba(228, 235, 226, 0.3);
    --gac-mw: #3f86d4;
    --gac-mw-case: #9cc4ef;
    --gac-mw-ink: #0c1a2b;
    --gac-green: #34a866;
    --gac-green-case: #9ad9b2;
    --gac-red: #e0493e;
    --gac-red-case: #f3a49d;
    --gac-red-ink: #f08a80;
    --gac-yellow: #f2c230;
    --gac-yellow-case: #f7dd8a;
    --gac-minor: #2b3731;
    --gac-minor-case: #4b5852;
    --gac-road: #aeb9b1;
    --gac-road-case: #dfe6dd;
    --gac-lamp: #d9ded6;
    --gac-lamp-high: #ffffff;
    --gac-body: #26322c;
    --gac-glass: #1f3442;
    color-scheme: dark;
  }
`;

export const base = css`
  :host {
    display: block;
  }
  * {
    box-sizing: border-box;
  }
  ha-card {
    display: block;
    background: var(--gac-land);
    color: var(--gac-ink);
    border: 1px solid var(--gac-hair);
    border-radius: 4px;
    box-shadow: none;
    overflow: hidden;
    font: 400 15px/1.35 var(--gac-text);
    container-type: inline-size;
    -webkit-font-smoothing: antialiased;
  }
  ::selection {
    background: var(--gac-mw);
    color: var(--gac-mw-ink);
  }
  .plate {
    height: 44px;
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 0 16px;
    border-bottom: 1px solid var(--gac-hair);
  }
  .ref {
    width: 24px;
    height: 24px;
    flex: none;
    border: 1px solid var(--gac-ink);
    display: grid;
    place-items: center;
  }
  .ref svg {
    width: 16px;
    height: 16px;
  }
  .name {
    font: 700 22px/1 var(--gac-label);
    letter-spacing: 0.05em;
    text-transform: uppercase;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    min-width: 0;
  }
  .plate .lab {
    margin-left: auto;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    max-width: 45%;
  }
  .lab {
    font: 600 12px/16px var(--gac-label);
    letter-spacing: 0.1em;
    text-transform: uppercase;
    color: var(--gac-muted);
  }
  .sec {
    padding: 12px 16px;
  }
  .sec + .sec {
    border-top: 1px solid var(--gac-hair);
  }
  .fig {
    font: 600 40px/1 var(--gac-label);
    font-variant-numeric: tabular-nums lining-nums;
    letter-spacing: 0.01em;
  }
  .fig small,
  .unit {
    font-size: 18px;
    font-weight: 500;
    color: var(--gac-muted);
    letter-spacing: 0.02em;
  }
  .num {
    font-family: var(--gac-label);
    font-variant-numeric: tabular-nums lining-nums;
  }
  .muted {
    color: var(--gac-muted);
  }
  .sr {
    position: absolute;
    width: 1px;
    height: 1px;
    overflow: hidden;
    clip: rect(0 0 0 0);
    white-space: nowrap;
  }
  .fresh {
    min-height: 36px;
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 0 6px 0 16px;
    border-top: 1px solid var(--gac-hair);
  }
  .fresh-info {
    flex: 1;
    min-width: 0;
    min-height: 36px;
    display: flex;
    align-items: center;
    gap: 6px;
    font: 400 13px/1.3 var(--gac-text);
    color: var(--gac-muted);
    text-align: left;
    cursor: pointer;
  }
  .refresh {
    flex: none;
    width: 36px;
    height: 36px;
    display: grid;
    place-items: center;
    padding: 0;
    color: var(--gac-muted);
    background: none;
    border: 0;
    border-radius: 2px;
    cursor: pointer;
  }
  .refresh:hover {
    color: var(--gac-ink);
    background: color-mix(in srgb, var(--gac-land) 85%, var(--gac-ink));
  }
  .refresh svg {
    width: 18px;
    height: 18px;
  }
  .refresh.reading svg {
    animation: gac-spin 1s linear infinite;
  }
  @keyframes gac-spin {
    to {
      transform: rotate(360deg);
    }
  }
  @media (prefers-reduced-motion: reduce) {
    .refresh.reading svg {
      animation: none;
    }
  }
  .refresh:focus-visible,
  .tap:focus-visible {
    outline: 2px solid var(--gac-mw);
    outline-offset: -2px;
  }
  .tap {
    cursor: pointer;
    background: none;
    border: 0;
    padding: 0;
    color: inherit;
    font: inherit;
    text-align: inherit;
  }
  .mark {
    width: 12px;
    height: 12px;
    flex: none;
    display: inline-block;
    vertical-align: -1px;
  }
  .note {
    display: flex;
    align-items: flex-start;
    gap: 8px;
    font-size: 14px;
    line-height: 1.4;
    margin: 0;
  }
  .note .mark {
    margin-top: 3px;
  }
  .note.refused {
    color: var(--gac-red-ink);
  }
  .duo {
    display: grid;
    grid-template-columns: 1fr 1fr;
  }
  .duo > * + * {
    border-left: 1px solid var(--gac-hair);
    padding-left: 16px;
  }
  .row {
    display: flex;
    align-items: center;
    gap: 12px;
    min-height: 48px;
  }
  .row + .row {
    border-top: 1px solid var(--gac-hair);
  }
  .row .what {
    flex: 1;
    min-width: 0;
  }
  .row .title {
    font-size: 15px;
    font-weight: 500;
  }
  .row .desc {
    font-size: 13px;
    color: var(--gac-muted);
    line-height: 1.35;
  }
  .head {
    display: flex;
    align-items: baseline;
    justify-content: space-between;
    gap: 8px;
    margin-bottom: 4px;
  }
  .grid3 {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 8px;
  }
  .grid2 {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 8px;
  }
  .empty {
    padding: 16px;
    font-size: 14px;
    color: var(--gac-muted);
  }
  .empty strong {
    display: block;
    color: var(--gac-ink);
    font: 600 18px/1.2 var(--gac-label);
    letter-spacing: 0.04em;
    text-transform: uppercase;
    margin-bottom: 4px;
  }
  @container (max-width: 330px) {
    .sec,
    .plate {
      padding-left: 12px;
      padding-right: 12px;
    }
    .fresh {
      padding-left: 12px;
    }
    .fig {
      font-size: 34px;
    }
    .grid3 {
      grid-template-columns: repeat(2, 1fr);
    }
  }
`;
