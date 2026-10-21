// Standard controls in the atlas's vocabulary. A command in flight draws its edge dashed and
// marching, like a road under construction; consequential actions take a held press.

import { css, html, LitElement, nothing, PropertyValues, svg } from "lit";
import { icon } from "./icons";

export type ActionState = "idle" | "on" | "pending" | "refused" | "unavailable";

const HOLD_MS = 700;

const focus = css`
  *,
  *::before,
  *::after {
    box-sizing: border-box;
  }
  :focus-visible {
    outline: 2px solid var(--gac-mw);
    outline-offset: 2px;
  }
`;

const marching = css`
  .pending {
    position: relative;
    border-color: transparent !important;
    background: var(--gac-water) !important;
    color: var(--gac-mw-case) !important;
  }
  .pending::before {
    content: "";
    position: absolute;
    inset: -1px;
    border-radius: inherit;
    pointer-events: none;
    background:
      linear-gradient(90deg, var(--gac-mw-case) 50%, transparent 0) repeat-x top left / 8px 1.5px,
      linear-gradient(90deg, var(--gac-mw-case) 50%, transparent 0) repeat-x bottom left / 8px 1.5px,
      linear-gradient(0deg, var(--gac-mw-case) 50%, transparent 0) repeat-y top left / 1.5px 8px,
      linear-gradient(0deg, var(--gac-mw-case) 50%, transparent 0) repeat-y top right / 1.5px 8px;
    animation: march 0.8s linear infinite;
  }
  @keyframes march {
    to {
      background-position: 8px 0, -8px 100%, 0 -8px, 100% 8px;
    }
  }
  @media (prefers-reduced-motion: reduce) {
    .pending::before {
      animation: none;
    }
  }
`;

export class GacAction extends LitElement {
  static override properties = {
    label: {}, icon: {}, state: { reflect: true }, hold: { type: Boolean }, hint: {},
    _holding: { state: true }, _asked: { state: true },
  };

  declare label: string;
  declare icon: string;
  declare state: ActionState;
  declare hold: boolean;
  declare hint: string;
  declare _holding: boolean;
  declare _asked: boolean;
  private timer?: number;
  private askTimer?: number;

  constructor() {
    super();
    this.state = "idle";
    this.hold = false;
    this._holding = false;
    this._asked = false;
  }

  static override styles = [focus, marching, css`
    :host {
      display: block;
    }
    button {
      position: relative;
      width: 100%;
      height: 48px;
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 8px;
      padding: 0 8px;
      font: 600 16px/1 var(--gac-label);
      letter-spacing: 0.02em;
      color: var(--gac-ink);
      background: var(--gac-paper);
      border: 1px solid var(--gac-edge);
      border-radius: 2px;
      cursor: pointer;
      overflow: hidden;
      transition: background-color 150ms ease-out, color 150ms ease-out, border-color 150ms ease-out;
      -webkit-tap-highlight-color: transparent;
      touch-action: manipulation;
      user-select: none;
    }
    button:hover {
      background: color-mix(in srgb, var(--gac-paper) 88%, var(--gac-ink));
    }
    button:active {
      background: color-mix(in srgb, var(--gac-paper) 80%, var(--gac-ink));
    }
    svg {
      width: 20px;
      height: 20px;
      flex: none;
    }
    span {
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }
    .on {
      background: var(--gac-mw);
      color: var(--gac-mw-ink);
      border-color: var(--gac-mw-case);
    }
    .on:hover {
      background: color-mix(in srgb, var(--gac-mw) 88%, black);
    }
    .refused {
      border-color: var(--gac-red);
      color: var(--gac-red-ink);
      box-shadow: inset 0 0 0 1px var(--gac-red);
    }
    .unavailable {
      color: var(--gac-muted);
      border-style: dotted;
      cursor: not-allowed;
    }
    .unavailable:hover {
      background: var(--gac-paper);
    }
    .hold::after {
      content: "";
      position: absolute;
      left: 6px;
      right: 6px;
      bottom: 5px;
      height: 0;
      border-bottom: 1.5px dashed var(--gac-edge);
    }
    .bar {
      position: absolute;
      left: 0;
      bottom: 0;
      height: 5px;
      width: 0;
      background: var(--gac-mw);
      box-shadow: 0 -1px 0 var(--gac-mw-case);
      transition: width 120ms ease-out;
    }
    .holding .bar {
      width: 100%;
      transition: width ${HOLD_MS}ms linear;
    }
  `];

  private start(event: Event): void {
    if (this.state === "unavailable" || this.state === "pending") return;
    if (!this.hold) return;
    event.preventDefault();
    this._holding = true;
    window.clearTimeout(this.timer);
    this.timer = window.setTimeout(() => {
      this._holding = false;
      navigator.vibrate?.(15);
      this.activate();
    }, HOLD_MS);
  }

  private cancel(): void {
    if (!this._holding) return;
    this._holding = false;
    window.clearTimeout(this.timer);
    this._asked = true;
    window.clearTimeout(this.askTimer);
    this.askTimer = window.setTimeout(() => (this._asked = false), 1800);
  }

  private onClick(): void {
    if (this.hold || this.state === "unavailable" || this.state === "pending") return;
    this.activate();
  }

  private key(event: KeyboardEvent): void {
    if (!this.hold || (event.key !== "Enter" && event.key !== " ")) return;
    event.preventDefault();
    if (event.type === "keydown" && !event.repeat) this.start(event);
    if (event.type === "keyup") this.cancel();
  }

  private activate(): void {
    this.dispatchEvent(new CustomEvent("activate", { bubbles: true, composed: true }));
  }

  override disconnectedCallback(): void {
    super.disconnectedCallback();
    window.clearTimeout(this.timer);
    window.clearTimeout(this.askTimer);
  }

  protected override render() {
    const classes = [this.state, this.hold ? "hold" : "", this._holding ? "holding" : ""].join(" ");
    const text = this._asked ? "Hold to confirm" : this.label;
    return html`<button class=${classes} aria-busy=${this.state === "pending" ? "true" : "false"}
      aria-disabled=${this.state === "unavailable" || this.state === "pending" ? "true" : "false"}
      aria-pressed=${this.state === "on" ? "true" : nothing}
      aria-description=${this.hint || (this.hold ? "Press and hold to confirm" : nothing)}
      title=${this.hint || nothing}
      @click=${this.onClick} @pointerdown=${this.start} @pointerup=${this.cancel} @pointerleave=${this.cancel}
      @pointercancel=${this.cancel} @keydown=${this.key} @keyup=${this.key} @contextmenu=${(e: Event) =>
        this.hold && e.preventDefault()}>
      ${this.icon ? icon(this.icon) : nothing}<span>${text}</span><i class="bar"></i>
    </button>`;
  }
}

/** On/off as a road: a minor road when off, cased motorway when on, a junction for the knob. */
export class GacSwitch extends LitElement {
  static override properties = {
    checked: { type: Boolean }, pending: { type: Boolean }, disabled: { type: Boolean }, label: {},
    holdOn: { type: Boolean, attribute: "hold-on" }, _holding: { state: true },
  };

  declare checked: boolean;
  declare pending: boolean;
  declare disabled: boolean;
  declare label: string;
  declare holdOn: boolean;
  declare _holding: boolean;
  private timer?: number;

  static override styles = [focus, css`
    :host {
      display: inline-block;
      flex: none;
    }
    button {
      width: 60px;
      height: 48px;
      padding: 0;
      background: none;
      border: 0;
      cursor: pointer;
      display: grid;
      place-items: center;
      -webkit-tap-highlight-color: transparent;
      touch-action: manipulation;
    }
    button[aria-disabled="true"] {
      cursor: not-allowed;
      opacity: 0.5;
    }
    .track {
      position: relative;
      display: block;
      /* The original 20 px thumb on a 16 px track, with the track drawn 5 px shorter at each end
         than the thumb's travel, so the thumb covers its square corners at either end. */
      width: 38px;
      height: 16px;
      border-radius: 1px;
      background: var(--gac-minor);
      box-shadow: 0 0 0 1px var(--gac-minor-case), inset 0 0 0 1px var(--gac-minor-case);
      transition: background-color 180ms ease-out, box-shadow 180ms ease-out;
    }
    .on .track {
      background: var(--gac-mw);
      box-shadow: 0 0 0 1px var(--gac-mw-case);
    }
    .knob {
      position: absolute;
      top: 50%;
      left: 0;
      width: 20px;
      height: 20px;
      border-radius: 50%;
      background: var(--gac-minor);
      border: 1.5px solid var(--gac-ink);
      transform: translate(-7px, -50%);
      transition: transform 180ms cubic-bezier(0.2, 0.8, 0.2, 1);
    }
    .on .knob {
      transform: translate(25px, -50%);
    }
    .pending .track {
      background: var(--gac-water);
      box-shadow: none;
      outline: 1.5px dashed var(--gac-mw-case);
      outline-offset: 1px;
    }
    .fill {
      position: absolute;
      inset: 0;
      width: 0;
      background: var(--gac-mw);
      opacity: 0.5;
    }
    .holding .fill {
      width: 100%;
      transition: width ${HOLD_MS}ms linear;
    }
    @media (prefers-reduced-motion: reduce) {
      .knob,
      .track {
        transition: none;
      }
    }
  `];

  constructor() {
    super();
    this.checked = false;
    this.pending = false;
    this.disabled = false;
    this.holdOn = false;
    this._holding = false;
  }

  private needsHold(): boolean {
    return this.holdOn && !this.checked;
  }

  private down(event: Event): void {
    if (!this.needsHold() || this.disabled || this.pending) return;
    event.preventDefault();
    this._holding = true;
    this.timer = window.setTimeout(() => {
      this._holding = false;
      this.toggle();
    }, HOLD_MS);
  }

  private up(): void {
    this._holding = false;
    window.clearTimeout(this.timer);
  }

  private onClick(): void {
    if (this.needsHold() || this.disabled || this.pending) return;
    this.toggle();
  }

  private key(event: KeyboardEvent): void {
    if (!this.needsHold() || (event.key !== "Enter" && event.key !== " ")) return;
    event.preventDefault();
    if (event.type === "keydown" && !event.repeat) this.down(event);
    if (event.type === "keyup") this.up();
  }

  private toggle(): void {
    this.dispatchEvent(new CustomEvent("change", { detail: { checked: !this.checked }, bubbles: true,
                                                   composed: true }));
  }

  protected override render() {
    const classes = [this.checked ? "on" : "", this.pending ? "pending" : "", this._holding ? "holding" : ""];
    return html`<button role="switch" aria-checked=${this.checked ? "true" : "false"} aria-label=${this.label}
      aria-disabled=${this.disabled || this.pending ? "true" : "false"} aria-busy=${this.pending ? "true" : "false"}
      aria-description=${this.needsHold() ? "Press and hold to turn on" : nothing}
      class=${classes.join(" ")} @click=${this.onClick} @pointerdown=${this.down} @pointerup=${this.up}
      @pointerleave=${this.up} @pointercancel=${this.up} @keydown=${this.key} @keyup=${this.key}>
      <span class="track"><i class="fill"></i><i class="knob"></i></span>
    </button>`;
  }
}

export interface Segment {
  value: string;
  label: string;
}

export class GacSegments extends LitElement {
  static override properties = {
    options: { attribute: false }, value: {}, pending: { type: Boolean }, disabled: { type: Boolean }, label: {},
  };

  declare options: Segment[];
  declare value: string | undefined;
  declare pending: boolean;
  declare disabled: boolean;
  declare label: string;

  static override styles = [focus, marching, css`
    :host {
      display: block;
    }
    div {
      display: flex;
      border: 1px solid var(--gac-edge);
      border-radius: 2px;
      background: var(--gac-paper);
    }
    button {
      flex: 1 1 0;
      min-width: 0;
      height: 44px;
      padding: 0 4px;
      font: 600 15px/1 var(--gac-label);
      letter-spacing: 0.03em;
      color: var(--gac-ink);
      background: none;
      border: 0;
      cursor: pointer;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
      -webkit-tap-highlight-color: transparent;
    }
    button + button {
      border-left: 1px solid var(--gac-hair);
    }
    button:hover {
      background: color-mix(in srgb, var(--gac-paper) 88%, var(--gac-ink));
    }
    button[aria-checked="true"] {
      background: var(--gac-mw);
      color: var(--gac-mw-ink);
      box-shadow: inset 0 0 0 1px var(--gac-mw-case);
    }
    div[aria-disabled="true"] button {
      cursor: not-allowed;
      color: var(--gac-muted);
    }
  `];

  constructor() {
    super();
    this.options = [];
    this.pending = false;
    this.disabled = false;
  }

  private pick(value: string): void {
    if (this.disabled || this.pending || value === this.value) return;
    this.dispatchEvent(new CustomEvent("change", { detail: { value }, bubbles: true, composed: true }));
  }

  private key(event: KeyboardEvent): void {
    const index = this.options.findIndex((o) => o.value === this.value);
    const step = event.key === "ArrowRight" ? 1 : event.key === "ArrowLeft" ? -1 : 0;
    if (!step) return;
    event.preventDefault();
    const next = this.options[(index + step + this.options.length) % this.options.length];
    if (next) this.pick(next.value);
  }

  protected override render() {
    return html`<div role="radiogroup" aria-label=${this.label} aria-disabled=${this.disabled ? "true" : "false"}
      aria-busy=${this.pending ? "true" : "false"} class=${this.pending ? "pending" : ""} @keydown=${this.key}>
      ${this.options.map((o) => html`<button role="radio" aria-checked=${o.value === this.value ? "true" : "false"}
        tabindex=${o.value === this.value || (this.value === undefined && o === this.options[0]) ? 0 : -1}
        @click=${() => this.pick(o.value)}>${o.label}</button>`)}
    </div>`;
  }
}

/**
 * Minus and plus around a value. Taps change the shown value at once and send one request
 * after a pause, so a run of taps spends one command from the car's budget.
 */
export class GacStepper extends LitElement {
  static override properties = {
    value: { type: Number }, min: { type: Number }, max: { type: Number }, step: { type: Number }, unit: {},
    digits: { type: Number }, label: {}, pending: { type: Boolean }, disabled: { type: Boolean },
    format: { attribute: false }, _draft: { state: true },
  };

  declare value: number | undefined;
  declare min: number;
  declare max: number;
  declare step: number;
  declare unit: string;
  declare digits: number;
  declare label: string;
  declare pending: boolean;
  declare disabled: boolean;
  declare format: ((value: number) => string) | undefined;
  declare _draft: number | undefined;
  private timer?: number;

  static override styles = [focus, marching, css`
    :host {
      display: block;
    }
    .box {
      display: flex;
      align-items: stretch;
      height: 48px;
      border: 1px solid var(--gac-edge);
      border-radius: 2px;
      background: var(--gac-paper);
    }
    button {
      width: 48px;
      flex: none;
      display: grid;
      place-items: center;
      background: none;
      border: 0;
      color: var(--gac-ink);
      cursor: pointer;
      -webkit-tap-highlight-color: transparent;
      touch-action: manipulation;
    }
    button:hover:not(:disabled) {
      background: color-mix(in srgb, var(--gac-paper) 88%, var(--gac-ink));
    }
    button:disabled {
      color: var(--gac-muted);
      cursor: not-allowed;
      opacity: 0.5;
    }
    svg {
      width: 20px;
      height: 20px;
    }
    output {
      flex: 1;
      min-width: 0;
      display: grid;
      place-items: center;
      border-left: 1px solid var(--gac-hair);
      border-right: 1px solid var(--gac-hair);
      font: 600 22px/1 var(--gac-label);
      font-variant-numeric: tabular-nums;
      white-space: nowrap;
    }
    output small {
      font-size: 15px;
      font-weight: 500;
      color: var(--gac-muted);
    }
    .draft output {
      color: var(--gac-mw-case);
    }
  `];

  constructor() {
    super();
    this.min = 0;
    this.max = 100;
    this.step = 1;
    this.unit = "";
    this.digits = 0;
    this.pending = false;
    this.disabled = false;
  }

  protected override willUpdate(changed: PropertyValues): void {
    if (changed.has("value") && this._draft !== undefined && this.value === this._draft) this._draft = undefined;
  }

  private nudge(direction: 1 | -1): void {
    const current = this._draft ?? this.value ?? this.min;
    const next = Math.min(this.max, Math.max(this.min, Math.round((current + direction * this.step) / this.step)
      * this.step));
    if (next === current) return;
    this._draft = next;
    window.clearTimeout(this.timer);
    this.timer = window.setTimeout(() => {
      this.dispatchEvent(new CustomEvent("change", { detail: { value: next }, bubbles: true, composed: true }));
    }, 1200);
  }

  override disconnectedCallback(): void {
    super.disconnectedCallback();
    window.clearTimeout(this.timer);
  }

  protected override render() {
    const shown = this._draft ?? this.value;
    const text = shown === undefined ? "–" : this.format ? this.format(shown) : shown.toFixed(this.digits);
    const off = this.disabled || this.pending;
    return html`<div class="box ${this.pending ? "pending" : ""} ${this._draft !== undefined ? "draft" : ""}"
      role="group" aria-label=${this.label}>
      <button aria-label="Decrease ${this.label}" ?disabled=${off || (shown ?? this.min) <= this.min}
        @click=${() => this.nudge(-1)}>${icon("minus")}</button>
      <output aria-live="polite"><span>${text}${this.unit ? html`<small>&nbsp;${this.unit}</small>` : nothing}</span></output>
      <button aria-label="Increase ${this.label}" ?disabled=${off || (shown ?? this.max) >= this.max}
        @click=${() => this.nudge(1)}>${icon("plus")}</button>
    </div>`;
  }
}

/** Choices along a road: each stop is a junction; the road is driven up to the chosen one. */
export class GacStops extends LitElement {
  static override properties = {
    options: { attribute: false }, value: {}, pending: { type: Boolean }, label: {}, _draft: { state: true },
  };

  /** The stop under the finger while pressed or dragged; sent once, when it is let go. */
  declare _draft: number | undefined;
  declare options: Segment[];
  declare value: string | undefined;
  declare pending: boolean;
  declare label: string;

  static override styles = [focus, css`
    :host {
      display: block;
    }
    .stops {
      position: relative;
      display: flex;
      touch-action: pan-y;
      user-select: none;
      -webkit-user-select: none;
    }
    .road {
      position: absolute;
      left: 0;
      right: 0;
      top: 13px;
      height: 7px;
      background: var(--gac-minor);
      box-shadow: inset 0 0 0 1px var(--gac-minor-case);
    }
    .driven {
      position: absolute;
      left: 0;
      top: 10px;
      height: 13px;
      background: var(--gac-mw);
      box-shadow: inset 0 0 0 2px var(--gac-mw-case);
      transition: width 200ms ease-out;
    }
    .pending .driven {
      background: var(--gac-water);
      box-shadow: none;
      outline: 1.5px dashed var(--gac-mw-case);
    }
    button {
      position: relative;
      flex: 1 1 0;
      min-width: 0;
      height: 52px;
      padding: 0;
      background: none;
      border: 0;
      cursor: pointer;
      color: var(--gac-muted);
      font: 600 13px/1 var(--gac-label);
      letter-spacing: 0.06em;
      text-transform: uppercase;
      -webkit-tap-highlight-color: transparent;
    }
    button i {
      position: absolute;
      left: 50%;
      top: 9px;
      width: 15px;
      height: 15px;
      margin-left: -7.5px;
      border-radius: 50%;
      background: var(--gac-minor);
      border: 1.5px solid var(--gac-minor-case);
    }
    button.passed i {
      border-color: var(--gac-mw-case);
    }
    button[aria-checked="true"] {
      color: var(--gac-ink);
    }
    button[aria-checked="true"] i {
      width: 19px;
      height: 19px;
      top: 7px;
      margin-left: -9.5px;
      border: 2px solid var(--gac-ink);
    }
    button span {
      position: absolute;
      left: 0;
      right: 0;
      bottom: 4px;
      white-space: nowrap;
      overflow: hidden;
    }
  `];

  constructor() {
    super();
    this.options = [];
    this.pending = false;
  }

  private pick(value: string): void {
    if (this.pending || value === this.value) return;
    this.dispatchEvent(new CustomEvent("change", { detail: { value }, bubbles: true, composed: true }));
  }

  private stopAt(clientX: number): number {
    const box = (this.renderRoot.querySelector(".stops") as HTMLElement).getBoundingClientRect();
    const count = Math.max(1, this.options.length);
    return Math.min(count - 1, Math.max(0, Math.floor(((clientX - box.left) / box.width) * count)));
  }

  private down(event: PointerEvent): void {
    if (this.pending || event.button > 0 || !this.options.length) return;
    (event.currentTarget as HTMLElement).setPointerCapture(event.pointerId);
    this._draft = this.stopAt(event.clientX);
  }

  private move(event: PointerEvent): void {
    if (this._draft !== undefined) this._draft = this.stopAt(event.clientX);
  }

  private up(event: PointerEvent): void {
    if (this._draft === undefined) return;
    const option = event.type === "pointerup" ? this.options[this._draft] : undefined;
    this._draft = undefined;
    // A tap or a drag is sent from here: while the road holds the pointer, the stop's own click
    // may land on the road instead, so that click only serves the keyboard.
    if (option) this.pick(option.value);
  }

  private key(event: KeyboardEvent): void {
    const index = this.options.findIndex((o) => o.value === this.value);
    const step = event.key === "ArrowRight" || event.key === "ArrowUp" ? 1
      : event.key === "ArrowLeft" || event.key === "ArrowDown" ? -1 : 0;
    if (!step) return;
    event.preventDefault();
    const next = this.options[Math.min(this.options.length - 1, Math.max(0, index + step))];
    if (next) {
      this.pick(next.value);
      (this.renderRoot.querySelectorAll("button")[this.options.indexOf(next)] as HTMLElement | undefined)?.focus();
    }
  }

  protected override render() {
    const index = this._draft ?? this.options.findIndex((o) => o.value === this.value);
    const count = Math.max(1, this.options.length);
    const driven = index < 0 ? 0 : ((index + 0.5) / count) * 100;
    return html`<div class="stops ${this.pending ? "pending" : ""}" role="radiogroup" aria-label=${this.label}
      aria-busy=${this.pending ? "true" : "false"} @pointerdown=${this.down} @pointermove=${this.move}
      @pointerup=${this.up} @pointercancel=${this.up} @keydown=${this.key}>
      <i class="road"></i><i class="driven" style="width:${driven}%"></i>
      ${this.options.map((o, i) => html`<button role="radio" aria-checked=${i === index ? "true" : "false"}
        class=${i < index ? "passed" : ""} tabindex=${i === index || (index < 0 && i === 0) ? 0 : -1}
        aria-label=${o.label} @click=${(event: MouseEvent) => { if (event.detail === 0) this.pick(o.value); }}
        ><i></i><span>${o.label}</span></button>`)}
    </div>`;
  }
}

const DAY = 1440;

function clock(minutes: number, twelve = false): string {
  const m = ((Math.round(minutes) % DAY) + DAY) % DAY;
  const hours = Math.floor(m / 60);
  const mins = String(m % 60).padStart(2, "0");
  if (!twelve) return `${String(hours).padStart(2, "0")}:${mins}`;
  return `${hours % 12 || 12}:${mins} ${hours < 12 ? "AM" : "PM"}`;
}

/** Hour labels under the day road: 00 06 12 18 24, or 12a 6a 12p 6p 12a. */
function hourTick(minutes: number, twelve: boolean): string {
  const hours = minutes / 60;
  if (!twelve) return String(hours).padStart(2, "0");
  return `${hours % 12 || 12}${hours % 24 < 12 ? "a" : "p"}`;
}

/**
 * A 24-hour road whose two ends are dragged to set a window, as the charging window or quiet
 * hours. The stretch between them is the motorway; an overnight window wraps. Each end is a
 * slider for the keyboard too. `input` fires while dragging; `change` when an end is let go.
 */
export class GacDayRange extends LitElement {
  static override properties = {
    start: { type: Number }, stop: { type: Number }, openEnded: { type: Boolean, attribute: "open-ended" },
    pending: { type: Boolean }, disabled: { type: Boolean, reflect: true }, now: { type: Number },
    step: { type: Number }, startLabel: { attribute: "start-label" }, stopLabel: { attribute: "stop-label" },
    twelve: { type: Boolean }, _width: { state: true }, _drag: { state: true }, _draft: { state: true },
  };

  declare start: number | undefined;
  declare stop: number | undefined;
  declare openEnded: boolean;
  declare pending: boolean;
  declare disabled: boolean;
  declare now: number | undefined;
  declare step: number;
  declare startLabel: string;
  declare stopLabel: string;
  /** Times read as AM/PM rather than 24-hour. */
  declare twelve: boolean;
  declare _width: number;
  declare _drag: "start" | "stop" | undefined;
  declare _draft: { start?: number; stop?: number } | undefined;
  private resizer?: ResizeObserver;

  static override styles = [focus, css`
    :host {
      display: block;
      user-select: none;
      -webkit-user-select: none;
    }
    svg {
      display: block;
      overflow: visible;
      touch-action: pan-y;
      cursor: pointer;
    }
    :host([disabled]) svg {
      cursor: not-allowed;
      opacity: 0.55;
    }
    .handle {
      cursor: grab;
      outline: none;
    }
    .dragging .handle {
      cursor: grabbing;
    }
    .handle .ring {
      fill: none;
      stroke: transparent;
      stroke-width: 3;
    }
    .handle:focus-visible .ring,
    .handle.active .ring {
      stroke: var(--gac-mw);
    }
    .tick {
      font: 600 12px var(--gac-label);
      fill: var(--gac-muted);
      letter-spacing: 0.06em;
    }
  `];

  constructor() {
    super();
    this.openEnded = false;
    this.pending = false;
    this.disabled = false;
    this.step = 5;
    this.startLabel = "Start";
    this.stopLabel = "Stop";
    this.twelve = false;
    this._width = 300;
  }

  override connectedCallback(): void {
    super.connectedCallback();
    this.resizer = new ResizeObserver((entries) => {
      const width = Math.round(entries[0]?.contentRect.width ?? 0);
      if (width > 0) this._width = width;
    });
    this.resizer.observe(this);
  }

  override disconnectedCallback(): void {
    super.disconnectedCallback();
    this.resizer?.disconnect();
  }

  protected override willUpdate(changed: PropertyValues): void {
    // A draft is dropped once the entity reports what was sent.
    if ((changed.has("start") || changed.has("stop")) && this._draft && !this._drag
        && (this._draft.start === undefined || this._draft.start === this.start)
        && (this._draft.stop === undefined || this._draft.stop === this.stop)) {
      this._draft = undefined;
    }
  }

  private get value(): { start?: number; stop?: number } {
    return { start: this._draft?.start ?? this.start, stop: this._draft?.stop ?? this.stop };
  }

  private geometry() {
    const x0 = 12;
    const x1 = Math.max(200, this._width) - 12;
    return { x0, x1, at: (m: number) => x0 + (m / DAY) * (x1 - x0) };
  }

  private minutesAt(clientX: number): number {
    const svg = this.renderRoot.querySelector("svg");
    if (!svg) return 0;
    const box = svg.getBoundingClientRect();
    const { x0, x1 } = this.geometry();
    const fraction = (clientX - box.left - x0) / (x1 - x0);
    const raw = Math.min(DAY - this.step, Math.max(0, fraction * DAY));
    return Math.round(raw / this.step) * this.step;
  }

  private emit(type: "input" | "change", which: "start" | "stop"): void {
    const { start, stop } = this.value;
    this.dispatchEvent(new CustomEvent(type, { detail: { start, stop, which }, bubbles: true, composed: true }));
  }

  private set(which: "start" | "stop", minutes: number): void {
    if (this.value[which] === minutes) return;
    this._draft = { ...this._draft, [which]: minutes };
    this.emit("input", which);
  }

  private down(event: PointerEvent): void {
    if (this.disabled || event.button > 0) return;
    const target = event.target as Element;
    const minutes = this.minutesAt(event.clientX);
    let which = (target.closest("[data-end]") as HTMLElement | null)?.dataset.end as "start" | "stop" | undefined;
    if (!which) {
      const { start, stop } = this.value;
      const gap = (m?: number) => m === undefined ? Infinity : Math.min(Math.abs(m - minutes), DAY - Math.abs(m - minutes));
      which = this.openEnded || gap(start) <= gap(stop) ? "start" : "stop";
    }
    this._drag = which;
    (event.currentTarget as Element).setPointerCapture(event.pointerId);
    this.set(which, minutes);
    event.preventDefault();
  }

  private move(event: PointerEvent): void {
    if (this._drag) this.set(this._drag, this.minutesAt(event.clientX));
  }

  private up(): void {
    if (!this._drag) return;
    const which = this._drag;
    this._drag = undefined;
    this.emit("change", which);
  }

  private key(which: "start" | "stop", event: KeyboardEvent): void {
    if (this.disabled) return;
    const steps: Record<string, number> = { ArrowRight: this.step, ArrowUp: this.step, ArrowLeft: -this.step,
                                           ArrowDown: -this.step, PageUp: 60, PageDown: -60 };
    const current = this.value[which] ?? 0;
    let next: number | undefined;
    if (event.key in steps) next = (current + steps[event.key] + DAY) % DAY;
    if (event.key === "Home") next = 0;
    if (event.key === "End") next = DAY - this.step;
    if (next === undefined) return;
    event.preventDefault();
    this.set(which, next);
    this.emit("change", which);
  }

  protected override render() {
    const { x0, x1, at } = this.geometry();
    const width = Math.max(200, this._width);
    const y = 18;
    const { start, stop } = this.value;
    const spans: [number, number][] = [];
    if (start !== undefined && (stop !== undefined || this.openEnded)) {
      const end = this.openEnded ? DAY : stop!;
      if (start === end) spans.push([0, DAY]);
      else if (start < end) spans.push([start, end]);
      else spans.push([start, DAY], [0, end]);
    }
    const handle = (which: "start" | "stop", minutes: number | undefined, label: string) => minutes === undefined
      ? nothing
      : svg`<g class="handle ${this._drag === which ? "active" : ""}" data-end=${which} tabindex=${this.disabled ? -1 : 0}
          role="slider" aria-label=${label} aria-valuemin="0" aria-valuemax=${DAY - this.step}
          aria-valuenow=${minutes} aria-valuetext=${clock(minutes, this.twelve)} aria-disabled=${this.disabled ? "true" : "false"}
          @keydown=${(e: KeyboardEvent) => this.key(which, e)}>
          <circle cx=${at(minutes)} cy=${y} r="16" fill="transparent"/>
          <circle class="ring" cx=${at(minutes)} cy=${y} r="11"/>
          <circle cx=${at(minutes)} cy=${y} r="7" fill="var(--gac-minor)" stroke="var(--gac-ink)" stroke-width="2"/>
        </g>`;
    const road = (a: number, b: number) => this.pending
      ? svg`<path d="M${at(a)} ${y}H${at(b)}" stroke="var(--gac-mw-case)" stroke-width="12" stroke-dasharray="6 4"/>
          <path d="M${at(a)} ${y}H${at(b)}" stroke="var(--gac-mw)" stroke-width="8" opacity="0.55"/>`
      : svg`<path d="M${at(a)} ${y}H${at(b)}" stroke="var(--gac-mw-case)" stroke-width="14"/>
          <path d="M${at(a)} ${y}H${at(b)}" stroke="var(--gac-mw)" stroke-width="10"/>`;
    return html`<svg class=${this._drag ? "dragging" : ""} width=${width} height="56" viewBox="0 0 ${width} 56"
      @pointerdown=${this.down} @pointermove=${this.move} @pointerup=${this.up} @pointercancel=${this.up}>
      <path d="M${x0} ${y}H${x1}" stroke="var(--gac-minor-case)" stroke-width="7"/>
      <path d="M${x0} ${y}H${x1}" stroke="var(--gac-minor)" stroke-width="5"/>
      ${spans.map(([a, b]) => road(a, b))}
      ${Array.from({ length: 9 }, (_, i) => i * 180).map((m) => svg`<path d="M${at(m)} ${y + 12}v${m % 360 === 0 ? 7 : 4}"
        stroke="var(--gac-ink)"/>`)}
      ${[0, 360, 720, 1080, 1440].map((m) => svg`<text class="tick" x=${at(m)} y="52" text-anchor="middle">${
        hourTick(m, this.twelve)}</text>`)}
      ${this.now !== undefined ? svg`<path d="M${at(this.now) - 4} 0L${at(this.now) + 4} 0L${at(this.now)} 6Z"
        fill="var(--gac-ink)"/>` : nothing}
      ${handle("start", start, this.startLabel)}
      ${this.openEnded ? nothing : handle("stop", stop, this.stopLabel)}
    </svg>`;
  }
}

/** A choice from a list, opened in place: no native pop-up menu. */
export class GacChoice extends LitElement {
  static override properties = {
    options: { attribute: false }, value: {}, pending: { type: Boolean }, disabled: { type: Boolean }, label: {},
    _open: { state: true },
  };

  declare options: Segment[];
  declare value: string | undefined;
  declare pending: boolean;
  declare disabled: boolean;
  declare label: string;
  declare _open: boolean;

  static override styles = [focus, marching, css`
    :host {
      display: block;
    }
    .current {
      width: 100%;
      height: 44px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 8px;
      padding: 0 12px;
      font: 600 16px/1 var(--gac-label);
      letter-spacing: 0.03em;
      color: var(--gac-ink);
      background: var(--gac-paper);
      border: 1px solid var(--gac-edge);
      border-radius: 2px;
      cursor: pointer;
    }
    .current svg {
      width: 18px;
      height: 18px;
      transition: transform 150ms ease-out;
    }
    .open .current svg {
      transform: rotate(90deg);
    }
    .current:disabled {
      cursor: not-allowed;
      color: var(--gac-muted);
    }
    ul {
      list-style: none;
      margin: 4px 0 0;
      padding: 0;
      border: 1px solid var(--gac-edge);
      border-radius: 2px;
      background: var(--gac-paper);
    }
    li + li {
      border-top: 1px solid var(--gac-hair);
    }
    li button {
      width: 100%;
      min-height: 44px;
      padding: 0 12px;
      text-align: left;
      font: 500 15px/1.2 var(--gac-text);
      color: var(--gac-ink);
      background: none;
      border: 0;
      cursor: pointer;
    }
    li button:hover {
      background: color-mix(in srgb, var(--gac-paper) 88%, var(--gac-ink));
    }
    li button[aria-checked="true"] {
      background: var(--gac-mw);
      color: var(--gac-mw-ink);
      font-weight: 600;
    }
  `];

  constructor() {
    super();
    this.options = [];
    this.pending = false;
    this.disabled = false;
    this._open = false;
  }

  private pick(value: string): void {
    this._open = false;
    if (value !== this.value) {
      this.dispatchEvent(new CustomEvent("change", { detail: { value }, bubbles: true, composed: true }));
    }
    (this.renderRoot.querySelector(".current") as HTMLElement | null)?.focus();
  }

  private key(event: KeyboardEvent): void {
    const buttons = [...this.renderRoot.querySelectorAll<HTMLButtonElement>("li button")];
    const index = buttons.indexOf(event.target as HTMLButtonElement);
    if (event.key === "Escape") {
      this._open = false;
      (this.renderRoot.querySelector(".current") as HTMLElement | null)?.focus();
    } else if (event.key === "ArrowDown" || event.key === "ArrowUp") {
      event.preventDefault();
      buttons[(index + (event.key === "ArrowDown" ? 1 : -1) + buttons.length) % buttons.length]?.focus();
    }
  }

  protected override render() {
    const current = this.options.find((o) => o.value === this.value);
    return html`<div class="${this._open ? "open" : ""} ${this.pending ? "pending" : ""}">
      <button class="current" aria-expanded=${this._open ? "true" : "false"} aria-label="${this.label}: ${
        current?.label ?? "not set"}" ?disabled=${this.disabled || this.pending}
        @click=${() => (this._open = !this._open)}><span>${current?.label ?? "–"}</span>${icon("chevron")}</button>
      ${this._open ? html`<ul role="radiogroup" aria-label=${this.label} @keydown=${this.key}>
        ${this.options.map((o) => html`<li><button role="radio" aria-checked=${o.value === this.value ? "true" : "false"}
          @click=${() => this.pick(o.value)}>${o.label}</button></li>`)}
      </ul>` : nothing}
    </div>`;
  }
}

export function defineControls(): void {
  const define = (name: string, element: CustomElementConstructor) => {
    if (!customElements.get(name)) customElements.define(name, element);
  };
  define("gac-action", GacAction);
  define("gac-switch", GacSwitch);
  define("gac-segments", GacSegments);
  define("gac-stepper", GacStepper);
  define("gac-stops", GacStops);
  define("gac-day-range", GacDayRange);
  define("gac-choice", GacChoice);
}
