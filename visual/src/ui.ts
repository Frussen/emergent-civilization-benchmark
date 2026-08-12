import type { ConnectionState } from "./connection";
import type { StatusMessage, VisualSnapshot, VisualSpeed } from "./protocol";

const SPEEDS: VisualSpeed[] = ["1x", "5x", "20x", "max"];

export interface UIHandlers {
  play(): void;
  pause(): void;
  step(): void;
  setSpeed(speed: VisualSpeed): void;
}

export class VisualUI {
  private connectionState: ConnectionState = "connecting";
  private status: StatusMessage | null = null;
  private snapshot: VisualSnapshot | null = null;
  private readonly connectionLabel: HTMLElement;
  private readonly tick: HTMLElement;
  private readonly alive: HTMLElement;
  private readonly health: HTMLElement;
  private readonly food: HTMLElement;
  private readonly water: HTMLElement;
  private readonly playback: HTMLElement;
  private readonly speed: HTMLElement;
  private readonly error: HTMLElement;
  private readonly buttons: HTMLButtonElement[];
  readonly viewport: HTMLElement;

  constructor(root: HTMLElement, handlers: UIHandlers, websocketUrl: string) {
    root.innerHTML = `
      <main class="shell">
        <header class="topbar">
          <div>
            <p class="eyebrow">Emergent Civilization Benchmark</p>
            <h1>Live world</h1>
          </div>
          <div class="connection"><span class="state-dot"></span><span data-ui="connection">Connecting</span></div>
        </header>
        <section class="workspace">
          <div class="viewport" data-ui="viewport">
            <div class="camera-hint">Drag to pan · Wheel to zoom · Double-click to fit</div>
          </div>
          <aside class="panel">
            <section>
              <h2>Authoritative state</h2>
              <dl class="metrics">
                <div><dt>Tick</dt><dd data-ui="tick">—</dd></div>
                <div><dt>Alive agents</dt><dd data-ui="alive">—</dd></div>
                <div><dt>Mean health alive</dt><dd data-ui="health">—</dd></div>
                <div><dt>Total world food</dt><dd data-ui="food">—</dd></div>
                <div><dt>Total world water</dt><dd data-ui="water">—</dd></div>
              </dl>
            </section>
            <section>
              <h2>Playback</h2>
              <dl class="metrics compact">
                <div><dt>State</dt><dd data-ui="playback">—</dd></div>
                <div><dt>Speed</dt><dd data-ui="speed">—</dd></div>
              </dl>
              <div class="controls">
                <button data-action="play">Play</button>
                <button data-action="pause">Pause</button>
                <button data-action="step">Step</button>
              </div>
              <div class="speed-controls" aria-label="Playback speed">
                ${SPEEDS.map((item) => `<button data-speed="${item}">${item === "max" ? "Max" : item}</button>`).join("")}
              </div>
            </section>
            <section class="technical">
              <h2>Connection</h2>
              <p class="endpoint">${escapeHtml(websocketUrl)}</p>
              <p class="error" data-ui="error" aria-live="polite"></p>
            </section>
          </aside>
        </section>
      </main>`;

    this.viewport = requireElement(root, "[data-ui=viewport]");
    this.connectionLabel = requireElement(root, "[data-ui=connection]");
    this.tick = requireElement(root, "[data-ui=tick]");
    this.alive = requireElement(root, "[data-ui=alive]");
    this.health = requireElement(root, "[data-ui=health]");
    this.food = requireElement(root, "[data-ui=food]");
    this.water = requireElement(root, "[data-ui=water]");
    this.playback = requireElement(root, "[data-ui=playback]");
    this.speed = requireElement(root, "[data-ui=speed]");
    this.error = requireElement(root, "[data-ui=error]");
    this.buttons = [...root.querySelectorAll<HTMLButtonElement>("button")];

    requireButton(root, "[data-action=play]").onclick = handlers.play;
    requireButton(root, "[data-action=pause]").onclick = handlers.pause;
    requireButton(root, "[data-action=step]").onclick = handlers.step;
    for (const speed of SPEEDS) {
      requireButton(root, `[data-speed="${speed}"]`).onclick = () => handlers.setSpeed(speed);
    }
    this.refreshControls();
  }

  setConnection(state: ConnectionState, detail?: string): void {
    this.connectionState = state;
    this.connectionLabel.textContent = state[0]?.toUpperCase() + state.slice(1);
    this.connectionLabel.parentElement?.setAttribute("data-state", state);
    if (detail && state !== "connected") this.showError(detail);
    this.refreshControls();
  }

  setSnapshot(snapshot: VisualSnapshot): void {
    this.snapshot = snapshot;
    this.tick.textContent = snapshot.tick.toLocaleString();
    this.alive.textContent = snapshot.metrics.alive_agents.toLocaleString();
    this.health.textContent = formatMetric(snapshot.metrics.mean_health_alive);
    this.food.textContent = formatMetric(snapshot.metrics.total_world_food);
    this.water.textContent = formatMetric(snapshot.metrics.total_world_water);
  }

  setStatus(status: StatusMessage): void {
    this.status = status;
    this.playback.textContent = status.extinct
      ? "Extinct"
      : status.playing
        ? "Playing"
        : "Paused";
    this.speed.textContent = status.speed === "max" ? "Max" : status.speed;
    if (status.scheduler_error) this.showError(`Scheduler: ${status.scheduler_error}`);
    this.refreshControls();
  }

  showError(message: string): void {
    this.error.textContent = message;
    this.error.classList.add("visible");
  }

  private refreshControls(): void {
    const usable = this.connectionState === "connected" && this.status !== null;
    for (const button of this.buttons) button.disabled = !usable;
    if (!usable || !this.status) return;
    requireButton(document, "[data-action=play]").disabled = this.status.playing || this.status.extinct;
    requireButton(document, "[data-action=pause]").disabled = !this.status.playing;
    for (const speed of SPEEDS) {
      const button = requireButton(document, `[data-speed="${speed}"]`);
      button.classList.toggle("selected", this.status.speed === speed);
      button.setAttribute("aria-pressed", String(this.status.speed === speed));
    }
  }
}

function requireElement(root: ParentNode, selector: string): HTMLElement {
  const element = root.querySelector<HTMLElement>(selector);
  if (!element) throw new Error(`Missing UI element: ${selector}`);
  return element;
}

function requireButton(root: ParentNode, selector: string): HTMLButtonElement {
  const button = root.querySelector<HTMLButtonElement>(selector);
  if (!button) throw new Error(`Missing UI button: ${selector}`);
  return button;
}

function formatMetric(value: number | null): string {
  return value === null
    ? "—"
    : value.toLocaleString(undefined, { maximumFractionDigits: 2 });
}

function escapeHtml(value: string): string {
  const element = document.createElement("span");
  element.textContent = value;
  return element.innerHTML;
}
