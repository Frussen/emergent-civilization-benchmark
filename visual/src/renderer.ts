import { Application, Container, Graphics } from "pixi.js";

import { arrangeMultiOccupancy } from "./layout";
import type { VisualSnapshot } from "./protocol";

const CELL_SIZE = 16;
const MAX_ZOOM = 10;

export class WorldRenderer {
  private readonly app = new Application();
  private readonly world = new Container();
  private readonly cells = new Graphics();
  private readonly agents = new Graphics();
  private snapshot: VisualSnapshot | null = null;
  private fitted = false;
  private dragging = false;
  private dragX = 0;
  private dragY = 0;
  private minimumZoom = 0.05;

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
    this.world.addChild(this.cells, this.agents);
    this.app.stage.addChild(this.world);
    this.installCameraControls();
    new ResizeObserver(() => this.handleResize()).observe(host);
  }

  render(snapshot: VisualSnapshot): void {
    const dimensionsChanged =
      this.snapshot === null ||
      this.snapshot.world.width !== snapshot.world.width ||
      this.snapshot.world.height !== snapshot.world.height;
    this.snapshot = snapshot;
    this.drawCells();
    this.drawAgents();
    if (!this.fitted || dimensionsChanged) this.fitWorld();
    else this.clampCamera();
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

  private drawCells(): void {
    if (!this.snapshot) return;
    this.cells.clear();
    this.cells
      .rect(
        0,
        0,
        this.snapshot.world.width * CELL_SIZE,
        this.snapshot.world.height * CELL_SIZE,
      )
      .fill({ color: 0x111820 });
    for (let x = 0; x <= this.snapshot.world.width; x += 1) {
      this.cells.moveTo(x * CELL_SIZE, 0).lineTo(
        x * CELL_SIZE,
        this.snapshot.world.height * CELL_SIZE,
      );
    }
    for (let y = 0; y <= this.snapshot.world.height; y += 1) {
      this.cells.moveTo(0, y * CELL_SIZE).lineTo(
        this.snapshot.world.width * CELL_SIZE,
        y * CELL_SIZE,
      );
    }
    this.cells.stroke({ color: 0x26323d, width: 0.55, alpha: 0.72 });
  }

  private drawAgents(): void {
    if (!this.snapshot) return;
    this.agents.clear();
    const arranged = arrangeMultiOccupancy(this.snapshot.agents);
    for (const agent of arranged.filter((item) => !item.alive)) {
      this.agents
        .circle(
          (agent.x + 0.5 + agent.offsetX) * CELL_SIZE,
          (agent.y + 0.5 + agent.offsetY) * CELL_SIZE,
          2.2,
        )
        .stroke({ color: 0x77818b, width: 1, alpha: 0.48 });
    }
    for (const agent of arranged.filter((item) => item.alive)) {
      this.agents
        .circle(
          (agent.x + 0.5 + agent.offsetX) * CELL_SIZE,
          (agent.y + 0.5 + agent.offsetY) * CELL_SIZE,
          2.8,
        )
        .fill({ color: 0x67e8c4, alpha: 0.95 });
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
      this.dragging = false;
      canvas.releasePointerCapture(event.pointerId);
      canvas.classList.remove("dragging");
    };
    canvas.addEventListener("pointerup", finishDrag);
    canvas.addEventListener("pointercancel", finishDrag);
    canvas.addEventListener("dblclick", () => this.fitWorld());
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
