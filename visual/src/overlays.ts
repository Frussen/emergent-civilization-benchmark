import type { AgentSnapshot, CellSnapshot, VisualSnapshot } from "./protocol";

export type OverlayMode = "agents" | "food" | "water" | "health" | "density";

export interface CellPresentation {
  x: number;
  y: number;
  value: number | null;
  rawValue: number | null;
  reference: number;
}

export interface InspectionSelection {
  agent: AgentSnapshot | null;
  cell: CellSnapshot | null;
}

export function safeRatio(value: number, capacity: number): number {
  if (capacity <= 0) return 0;
  return clamp01(value / capacity);
}

export function resourcePresentation(
  cells: CellSnapshot[],
  resource: "food" | "water",
): CellPresentation[] {
  return cells.map((cell) => {
    const stock = resource === "food" ? cell.food_stock : cell.water_stock;
    const capacity =
      resource === "food" ? cell.food_capacity : cell.water_capacity;
    return {
      x: cell.x,
      y: cell.y,
      value: safeRatio(stock, capacity),
      rawValue: stock,
      reference: capacity,
    };
  });
}

export function healthPresentation(snapshot: VisualSnapshot): CellPresentation[] {
  const healthByCell = livingValuesByCell(snapshot.agents, (agent) => agent.health);
  return snapshot.cells.map((cell) => {
    const health = healthByCell.get(cellKey(cell.x, cell.y));
    const mean = health ? health.reduce((sum, value) => sum + value, 0) / health.length : null;
    return {
      x: cell.x,
      y: cell.y,
      value: mean === null ? null : safeRatio(mean, snapshot.health_reference),
      rawValue: mean,
      reference: snapshot.health_reference,
    };
  });
}

export function densityPresentation(snapshot: VisualSnapshot): CellPresentation[] {
  const counts = new Map<string, number>();
  for (const agent of snapshot.agents) {
    if (!agent.alive) continue;
    const key = cellKey(agent.x, agent.y);
    counts.set(key, (counts.get(key) ?? 0) + 1);
  }
  const displayedHigh = Math.max(1, ...counts.values());
  return snapshot.cells.map((cell) => {
    const count = counts.get(cellKey(cell.x, cell.y)) ?? 0;
    return {
      x: cell.x,
      y: cell.y,
      value: count === 0 ? null : count / displayedHigh,
      rawValue: count,
      reference: displayedHigh,
    };
  });
}

export function findSelectedAgent(
  agents: AgentSnapshot[],
  selectedId: string | null,
): AgentSnapshot | null {
  if (selectedId === null) return null;
  return agents.find((agent) => agent.id === selectedId) ?? null;
}

export function resolveInspectionSelection(
  snapshot: VisualSnapshot,
  selectedAgentId: string | null,
  selectedCell: { x: number; y: number } | null,
): InspectionSelection {
  const agent = findSelectedAgent(snapshot.agents, selectedAgentId);
  const coordinates = agent
    ? { x: agent.x, y: agent.y }
    : selectedAgentId === null
      ? selectedCell
      : null;
  const cell = coordinates
    ? snapshot.cells.find(
        (item) => item.x === coordinates.x && item.y === coordinates.y,
      ) ?? null
    : null;
  return { agent, cell };
}

export function livingOccupancy(agents: AgentSnapshot[], x: number, y: number): number {
  return agents.filter((agent) => agent.alive && agent.x === x && agent.y === y).length;
}

function livingValuesByCell(
  agents: AgentSnapshot[],
  value: (agent: AgentSnapshot) => number,
): Map<string, number[]> {
  const values = new Map<string, number[]>();
  for (const agent of agents) {
    if (!agent.alive) continue;
    const key = cellKey(agent.x, agent.y);
    const group = values.get(key);
    if (group) group.push(value(agent));
    else values.set(key, [value(agent)]);
  }
  return values;
}

function cellKey(x: number, y: number): string {
  return `${x},${y}`;
}

function clamp01(value: number): number {
  return Math.max(0, Math.min(1, value));
}
