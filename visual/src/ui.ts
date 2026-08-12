import type { ConnectionState } from "./connection";
import {
  densityPresentation,
  livingOccupancy,
  resolveInspectionSelection,
  type OverlayMode,
} from "./overlays";
import type { StatusMessage, VisualEvent, VisualSnapshot, VisualSpeed } from "./protocol";

const SPEEDS: VisualSpeed[] = ["1x", "5x", "20x", "max"];
const MODES: OverlayMode[] = ["agents", "food", "water", "health", "density"];

export interface UIHandlers {
  play(): void;
  pause(): void;
  step(): void;
  setSpeed(speed: VisualSpeed): void;
  setMode(mode: OverlayMode): void;
}

export class VisualUI {
  private connectionState: ConnectionState = "connecting";
  private status: StatusMessage | null = null;
  private snapshot: VisualSnapshot | null = null;
  private mode: OverlayMode = "agents";
  private selectedAgentId: string | null = null;
  private selectedCell: { x: number; y: number } | null = null;
  private readonly connectionLabel: HTMLElement;
  private readonly tick: HTMLElement;
  private readonly alive: HTMLElement;
  private readonly health: HTMLElement;
  private readonly food: HTMLElement;
  private readonly water: HTMLElement;
  private readonly playback: HTMLElement;
  private readonly speed: HTMLElement;
  private readonly error: HTMLElement;
  private readonly legend: HTMLElement;
  private readonly inspector: HTMLElement;
  private readonly events: HTMLElement;
  private readonly commandButtons: HTMLButtonElement[];
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
            <div class="mode-bar" aria-label="World overlay">
              ${MODES.map((mode) => `<button data-mode="${mode}">${title(mode)}</button>`).join("")}
            </div>
            <div class="legend" data-ui="legend"></div>
            <div class="camera-hint">Click agent to inspect · Drag to pan · Wheel to zoom · Double-click to fit</div>
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
                <button data-command data-action="play">Play</button>
                <button data-command data-action="pause">Pause</button>
                <button data-command data-action="step">Step</button>
              </div>
              <div class="speed-controls" aria-label="Playback speed">
                ${SPEEDS.map((item) => `<button data-command data-speed="${item}">${item === "max" ? "Max" : item}</button>`).join("")}
              </div>
            </section>
            <section>
              <h2>Inspector</h2>
              <div class="inspector" data-ui="inspector"><p>Click an agent or cell.</p></div>
            </section>
            <section class="event-section">
              <div class="section-heading"><h2>Recent canonical events</h2><span>latest 75</span></div>
              <div class="events" data-ui="events"><p>No events in this snapshot.</p></div>
              <p class="feed-note">Bounded observational tail; Max mode may skip older displayed events. The run log remains canonical.</p>
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
    this.legend = requireElement(root, "[data-ui=legend]");
    this.inspector = requireElement(root, "[data-ui=inspector]");
    this.events = requireElement(root, "[data-ui=events]");
    this.commandButtons = [...root.querySelectorAll<HTMLButtonElement>("[data-command]")];

    requireButton(root, "[data-action=play]").onclick = handlers.play;
    requireButton(root, "[data-action=pause]").onclick = handlers.pause;
    requireButton(root, "[data-action=step]").onclick = handlers.step;
    for (const speed of SPEEDS) {
      requireButton(root, `[data-speed="${speed}"]`).onclick = () => handlers.setSpeed(speed);
    }
    for (const mode of MODES) {
      requireButton(root, `[data-mode="${mode}"]`).onclick = () => {
        this.mode = mode;
        handlers.setMode(mode);
        this.refreshModes();
        this.refreshLegend();
      };
    }
    this.refreshModes();
    this.refreshLegend();
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
    this.refreshLegend();
    this.refreshInspector();
    this.refreshEvents(snapshot.recent_events);
  }

  setInspection(agentId: string | null, cell: { x: number; y: number } | null): void {
    this.selectedAgentId = agentId;
    this.selectedCell = cell;
    this.refreshInspector();
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

  private refreshInspector(): void {
    if (!this.snapshot) return;
    const { agent, cell } = resolveInspectionSelection(
      this.snapshot,
      this.selectedAgentId,
      this.selectedCell,
    );
    if (!agent && !cell) {
      this.inspector.innerHTML = "<p>Click an agent or cell.</p>";
      return;
    }
    const agentHtml = agent
      ? `<h3>${escapeHtml(agent.id)}</h3><dl class="metrics">
          <div><dt>Position</dt><dd>(${agent.x}, ${agent.y})</dd></div>
          <div><dt>State</dt><dd>${agent.alive ? "Alive" : "Dead"}</dd></div>
          <div><dt>Health</dt><dd>${formatMetric(agent.health)}</dd></div>
          <div><dt>Food inventory</dt><dd>${formatMetric(agent.food_inventory)}</dd></div>
          <div><dt>Water inventory</dt><dd>${formatMetric(agent.water_inventory)}</dd></div>
        </dl>`
      : "";
    const cellHtml = cell
      ? `<div class="cell-inspection"><h3>Cell (${cell.x}, ${cell.y})</h3><dl class="metrics">
          <div><dt>Food</dt><dd>${formatMetric(cell.food_stock)} / ${formatMetric(cell.food_capacity)}</dd></div>
          <div><dt>Water</dt><dd>${formatMetric(cell.water_stock)} / ${formatMetric(cell.water_capacity)}</dd></div>
          <div><dt>Living occupancy</dt><dd>${livingOccupancy(this.snapshot.agents, cell.x, cell.y)}</dd></div>
        </dl></div>`
      : "";
    this.inspector.innerHTML = agentHtml + cellHtml;
  }

  private refreshEvents(events: VisualEvent[]): void {
    if (events.length === 0) {
      this.events.innerHTML = "<p>No events in this snapshot.</p>";
      return;
    }
    this.events.innerHTML = events
      .map((event) => `<div class="event event-${event.event_type}">
        <span class="event-tick">t${event.tick}</span>
        <span class="event-kind">${eventLabel(event)}</span>
        <span class="event-agent">${escapeHtml(event.agent_id)}</span>
        <span class="event-detail">${escapeHtml(eventDetail(event))}</span>
      </div>`)
      .join("");
    this.events.scrollTop = this.events.scrollHeight;
  }

  private refreshLegend(): void {
    if (this.mode === "agents") {
      this.legend.innerHTML = '<span class="agent-key living"></span>living <span class="agent-key dead"></span>dead';
      return;
    }
    const maxDensity = this.snapshot
      ? (densityPresentation(this.snapshot)[0]?.reference ?? 1)
      : 1;
    const labels: Record<Exclude<OverlayMode, "agents">, [string, string, string]> = {
      food: ["Food stock ÷ cell capacity", "0", "capacity"],
      water: ["Water stock ÷ cell capacity", "0", "capacity"],
      health: ["Mean living health", "0", this.snapshot ? formatMetric(this.snapshot.health_reference) : "reference"],
      density: ["Living occupancy", "0", String(maxDensity)],
    };
    const [name, low, high] = labels[this.mode];
    this.legend.innerHTML = `<span>${name}</span><div class="legend-scale scale-${this.mode}"></div><div class="legend-labels"><span>${low}</span><span>${high}</span></div>`;
  }

  private refreshModes(): void {
    for (const mode of MODES) {
      const button = requireButton(document, `[data-mode="${mode}"]`);
      button.classList.toggle("selected", this.mode === mode);
      button.setAttribute("aria-pressed", String(this.mode === mode));
    }
  }

  private refreshControls(): void {
    const usable = this.connectionState === "connected" && this.status !== null;
    for (const button of this.commandButtons) button.disabled = !usable;
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

function eventLabel(event: VisualEvent): string {
  if (event.event_type === "harvest") return "HARVEST";
  if (event.event_type === "death") return "DEATH";
  return "INVALID";
}

function eventDetail(event: VisualEvent): string {
  if (event.event_type === "harvest") {
    return `${event.resource} +${formatMetric(event.amount)} at (${event.x}, ${event.y})`;
  }
  if (event.event_type === "invalid_action") return event.reason;
  return "agent died";
}

function title(value: string): string {
  return value[0]?.toUpperCase() + value.slice(1);
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
