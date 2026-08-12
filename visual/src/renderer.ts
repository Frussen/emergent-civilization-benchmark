import { Application, Container, Graphics } from "pixi.js";

import { arrangeMultiOccupancy, type PresentedAgent } from "./layout";
import {
  densityPresentation,
  healthPresentation,
  resourcePresentation,
  type CellPresentation,
  type OverlayMode,
} from "./overlays";
import type { VisualSnapshot } from "./protocol";
import {
  agentHitRadius,
  cellLayerInvalidation,
  compareAgentHits,
  type CellLayerState,
} from "./rendering";

const CELL_SIZE = 16;
const MAX_ZOOM = 10;
const CLICK_MOVEMENT_THRESHOLD = 5;

export interface InspectionTarget {
  agentId: string | null;
  cell: { x: number; y: number } | null;
}

export class WorldRenderer {
  private readonly app = new Application();
  private readonly world = new Container();
  private readonly cellBackground = new Graphics();
  private readonly cellOverlay = new Graphics();
  private readonly cellGrid = new Graphics();
  private readonly agents = new Graphics();
  private snapshot: VisualSnapshot | null = null;
  private cellLayerState: CellLayerState | null = null;
  private mode: OverlayMode = "agents";
  private selectedAgentId: string | null = null;
  private fitted = false;
  private dragging = false;
  private dragX = 0;
  private dragY = 0;
  private pointerStartX = 0;
  private pointerStartY = 0;
  private minimumZoom = 0.05;

  constructor(private readonly onInspect: (target: InspectionTarget) => void) {}

  async initialize(host: HTMLElement): Promise<void> {
    await this.app.init({
      background: 0x090d12,
      antialias: true,
      resizeTo: host,
      resolution: Math.min(window.devicePixelRatio, 2),
      autoDensity: true,
    });
    this.app.canvas.setAttribute("aria-label", "ECB authoritative world view");
    host.appendChild(this.app.canvas);
    this.world.addChild(
      this.cellBackground,
      this.cellOverlay,
      this.cellGrid,
      this.agents,
    );
    this.app.stage.addChild(this.world);
    this.installCameraControls();
    new ResizeObserver(() => this.handleResize()).observe(host);
  }

  render(snapshot: VisualSnapshot): void {
    const dimensionsChanged =
      this.snapshot === null ||
      this.snapshot.world.width !== snapshot.world.width ||
      this.snapshot.world.height !== snapshot.world.height;
    const nextLayerState = this.layerState(snapshot, this.mode);
    const invalidation = cellLayerInvalidation(
      this.cellLayerState,
      nextLayerState,
      true,
    );
    this.snapshot = snapshot;
    if (invalidation.staticLayer) this.drawStaticCells();
    if (invalidation.overlayLayer) this.drawCellOverlay();
    this.drawAgents();
    this.cellLayerState = nextLayerState;
    if (!this.fitted || dimensionsChanged) this.fitWorld();
    else this.clampCamera();
  }

  setMode(mode: OverlayMode): void {
    if (mode === this.mode) return;
    this.mode = mode;
    if (!this.snapshot) return;
    const nextLayerState = this.layerState(this.snapshot, mode);
    const invalidation = cellLayerInvalidation(
      this.cellLayerState,
      nextLayerState,
      false,
    );
    if (invalidation.staticLayer) this.drawStaticCells();
    if (invalidation.overlayLayer) this.drawCellOverlay();
    this.cellLayerState = nextLayerState;
  }

  setSelectedAgent(agentId: string | null): void {
    this.selectedAgentId = agentId;
    this.drawAgents();
  }

  fitWorld(): void {
    if (!this.snapshot) return;
    const worldWidth = this.snapshot.world.width * CELL_SIZE;
    const worldHeight = this.snapshot.world.height * CELL_SIZE;
    const padding = 36;
    const scale = Math.min(
      (this.app.screen.width - padding * 2) / worldWidth,
      (this.app.screen.height - padding * 2) / worldHeight,
    );
    this.minimumZoom = Math.max(0.02, Math.min(0.35, scale * 0.5));
    const boundedScale = Math.min(MAX_ZOOM, Math.max(this.minimumZoom, scale));
    this.world.scale.set(boundedScale);
    this.world.position.set(
      (this.app.screen.width - worldWidth * boundedScale) / 2,
      (this.app.screen.height - worldHeight * boundedScale) / 2,
    );
    this.fitted = true;
  }

  private layerState(
    snapshot: VisualSnapshot,
    mode: OverlayMode,
  ): CellLayerState {
    return {
      width: snapshot.world.width,
      height: snapshot.world.height,
      mode,
    };
  }

  private drawStaticCells(): void {
    if (!this.snapshot) return;
    const width = this.snapshot.world.width * CELL_SIZE;
    const height = this.snapshot.world.height * CELL_SIZE;
    this.cellBackground.clear().rect(0, 0, width, height).fill({ color: 0x111820 });
    this.cellGrid.clear();
    for (let x = 0; x <= this.snapshot.world.width; x += 1) {
      this.cellGrid.moveTo(x * CELL_SIZE, 0).lineTo(x * CELL_SIZE, height);
    }
    for (let y = 0; y <= this.snapshot.world.height; y += 1) {
      this.cellGrid.moveTo(0, y * CELL_SIZE).lineTo(width, y * CELL_SIZE);
    }
    this.cellGrid.stroke({ color: 0x26323d, width: 0.55, alpha: 0.72 });
  }

  private drawCellOverlay(): void {
    this.cellOverlay.clear();
    if (!this.snapshot || this.mode === "agents") return;
    const presentation = this.cellPresentation();
    for (const cell of presentation) {
      if (cell.value === null) continue;
      this.cellOverlay
        .rect(cell.x * CELL_SIZE, cell.y * CELL_SIZE, CELL_SIZE, CELL_SIZE)
        .fill({ color: this.cellColor(cell) });
    }
  }

  private cellPresentation(): CellPresentation[] {
    if (!this.snapshot) return [];
    if (this.mode === "food") return resourcePresentation(this.snapshot.cells, "food");
    if (this.mode === "water") return resourcePresentation(this.snapshot.cells, "water");
    if (this.mode === "health") return healthPresentation(this.snapshot);
    if (this.mode === "density") return densityPresentation(this.snapshot);
    return this.snapshot.cells.map((cell) => ({
      x: cell.x,
      y: cell.y,
      value: null,
      rawValue: null,
      reference: 0,
    }));
  }

  private cellColor(cell: CellPresentation): number {
    if (cell.value === null) return 0x111820;
    if (this.mode === "food") return interpolateColor(0x10191a, 0x3f9f62, cell.value);
    if (this.mode === "water") return interpolateColor(0x101820, 0x338dcc, cell.value);
    if (this.mode === "health") return interpolateColor(0xb94a48, 0x48a86b, cell.value);
    return interpolateColor(0x171421, 0x9b6bd3, cell.value);
  }

  private drawAgents(): void {
    this.agents.clear();
    if (!this.snapshot) return;
    const arranged = arrangeMultiOccupancy(this.snapshot.agents);
    for (const agent of arranged.filter((item) => !item.alive)) {
      this.agents
        .circle(agentScreenX(agent), agentScreenY(agent), 2.2)
        .stroke({ color: 0x77818b, width: 1, alpha: 0.58 });
    }
    for (const agent of arranged.filter((item) => item.alive)) {
      this.agents
        .circle(agentScreenX(agent), agentScreenY(agent), 2.8)
        .fill({ color: 0x67e8c4, alpha: 0.96 })
        .stroke({ color: 0x17332c, width: 0.65, alpha: 0.8 });
    }
    const selected = arranged.find((agent) => agent.id === this.selectedAgentId);
    if (selected) {
      this.agents
        .circle(agentScreenX(selected), agentScreenY(selected), 5.1)
        .stroke({ color: 0xffd166, width: 1.4, alpha: 1 });
    }
  }

  private installCameraControls(): void {
    const canvas = this.app.canvas;
    canvas.addEventListener("wheel", (event) => {
      if (!this.snapshot) return;
      event.preventDefault();
      const rect = canvas.getBoundingClientRect();
      const pointerX = event.clientX - rect.left;
      const pointerY = event.clientY - rect.top;
      const previous = this.world.scale.x;
      const next = Math.min(
        MAX_ZOOM,
        Math.max(this.minimumZoom, previous * Math.exp(-event.deltaY * 0.0015)),
      );
      const localX = (pointerX - this.world.x) / previous;
      const localY = (pointerY - this.world.y) / previous;
      this.world.scale.set(next);
      this.world.position.set(pointerX - localX * next, pointerY - localY * next);
      this.clampCamera();
    }, { passive: false });
    canvas.addEventListener("pointerdown", (event) => {
      this.dragging = true;
      this.pointerStartX = event.clientX;
      this.pointerStartY = event.clientY;
      this.dragX = event.clientX - this.world.x;
      this.dragY = event.clientY - this.world.y;
      canvas.setPointerCapture(event.pointerId);
      canvas.classList.add("dragging");
    });
    canvas.addEventListener("pointermove", (event) => {
      if (!this.dragging) return;
      this.world.position.set(event.clientX - this.dragX, event.clientY - this.dragY);
      this.clampCamera();
    });
    const finishDrag = (event: PointerEvent) => {
      const movement = Math.hypot(
        event.clientX - this.pointerStartX,
        event.clientY - this.pointerStartY,
      );
      this.dragging = false;
      if (canvas.hasPointerCapture(event.pointerId)) canvas.releasePointerCapture(event.pointerId);
      canvas.classList.remove("dragging");
      if (event.type === "pointerup" && movement <= CLICK_MOVEMENT_THRESHOLD) {
        this.inspectAt(event.clientX, event.clientY);
      }
    };
    canvas.addEventListener("pointerup", finishDrag);
    canvas.addEventListener("pointercancel", finishDrag);
    canvas.addEventListener("dblclick", () => this.fitWorld());
  }

  private inspectAt(clientX: number, clientY: number): void {
    if (!this.snapshot) return;
    const rect = this.app.canvas.getBoundingClientRect();
    const localX = (clientX - rect.left - this.world.x) / this.world.scale.x;
    const localY = (clientY - rect.top - this.world.y) / this.world.scale.y;
    const cellX = Math.floor(localX / CELL_SIZE);
    const cellY = Math.floor(localY / CELL_SIZE);
    if (
      cellX < 0 ||
      cellY < 0 ||
      cellX >= this.snapshot.world.width ||
      cellY >= this.snapshot.world.height
    ) {
      this.onInspect({ agentId: null, cell: null });
      return;
    }
    const arranged = arrangeMultiOccupancy(this.snapshot.agents);
    const hitRadius = agentHitRadius(this.world.scale.x);
    const hits = arranged
      .map((agent) => ({
        agent,
        distance: Math.hypot(localX - agentScreenX(agent), localY - agentScreenY(agent)),
      }))
      .filter((hit) => hit.distance <= hitRadius)
      .sort(compareAgentHits);
    this.onInspect({
      agentId: hits[0]?.agent.id ?? null,
      cell: { x: cellX, y: cellY },
    });
  }

  private handleResize(): void {
    if (this.snapshot) this.fitWorld();
  }

  private clampCamera(): void {
    if (!this.snapshot) return;
    const width = this.snapshot.world.width * CELL_SIZE * this.world.scale.x;
    const height = this.snapshot.world.height * CELL_SIZE * this.world.scale.y;
    const margin = Math.min(80, this.app.screen.width / 4, this.app.screen.height / 4);
    const minX = Math.min(margin, this.app.screen.width - margin - width);
    const maxX = Math.max(this.app.screen.width - margin - width, margin);
    const minY = Math.min(margin, this.app.screen.height - margin - height);
    const maxY = Math.max(this.app.screen.height - margin - height, margin);
    this.world.x = Math.min(maxX, Math.max(minX, this.world.x));
    this.world.y = Math.min(maxY, Math.max(minY, this.world.y));
  }
}

function agentScreenX(agent: PresentedAgent): number {
  return (agent.x + 0.5 + agent.offsetX) * CELL_SIZE;
}

function agentScreenY(agent: PresentedAgent): number {
  return (agent.y + 0.5 + agent.offsetY) * CELL_SIZE;
}

function interpolateColor(low: number, high: number, value: number): number {
  const ratio = Math.max(0, Math.min(1, value));
  const channel = (shift: number) =>
    Math.round(((low >> shift) & 0xff) + (((high >> shift) & 0xff) - ((low >> shift) & 0xff)) * ratio);
  return (channel(16) << 16) | (channel(8) << 8) | channel(0);
}
