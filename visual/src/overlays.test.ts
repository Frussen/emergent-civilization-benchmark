import { describe, expect, it } from "vitest";

import {
  densityPresentation,
  findSelectedAgent,
  healthPresentation,
  resourcePresentation,
  resolveInspectionSelection,
  safeRatio,
} from "./overlays";
import type { AgentSnapshot, CellSnapshot, VisualSnapshot } from "./protocol";

const cells: CellSnapshot[] = [
  {
    x: 0,
    y: 0,
    food_stock: 5,
    food_capacity: 10,
    water_stock: 9,
    water_capacity: 12,
  },
  {
    x: 1,
    y: 0,
    food_stock: 0,
    food_capacity: 0,
    water_stock: 0,
    water_capacity: 0,
  },
];

function agent(id: string, x: number, health: number, alive = true): AgentSnapshot {
  return {
    id,
    x,
    y: 0,
    alive,
    health,
    food_inventory: 1,
    water_inventory: 1,
  };
}

function snapshot(agents: AgentSnapshot[]): VisualSnapshot {
  return {
    tick: 1,
    world_state_hash: "hash",
    health_reference: 80,
    world: { width: 2, height: 1 },
    agents,
    cells,
    metrics: {
      alive_agents: agents.filter((item) => item.alive).length,
      mean_health_alive: null,
      total_world_food: 5,
      total_world_water: 9,
    },
    recent_events: [],
  };
}

describe("overlay presentation", () => {
  it("normalizes food and water by each actual capacity", () => {
    expect(resourcePresentation(cells, "food")[0]?.value).toBe(0.5);
    expect(resourcePresentation(cells, "water")[0]?.value).toBe(0.75);
  });

  it("handles zero capacities deterministically", () => {
    expect(safeRatio(0, 0)).toBe(0);
    expect(resourcePresentation(cells, "food")[1]?.value).toBe(0);
  });

  it("uses mean living health and excludes dead agents", () => {
    const result = healthPresentation(
      snapshot([agent("a", 0, 40), agent("b", 0, 80), agent("dead", 0, 0, false)]),
    );
    expect(result[0]).toMatchObject({ rawValue: 60, value: 0.75, reference: 80 });
    expect(result[1]?.value).toBeNull();
  });

  it("derives density from living occupancy and the current displayed high", () => {
    const result = densityPresentation(
      snapshot([agent("a", 0, 80), agent("b", 0, 80), agent("dead", 1, 0, false)]),
    );
    expect(result[0]).toMatchObject({ rawValue: 2, value: 1, reference: 2 });
    expect(result[1]).toMatchObject({ rawValue: 0, value: null, reference: 2 });
  });

  it("finds a selected agent by stable ID after movement", () => {
    const before = [agent("chosen", 0, 80)];
    const after = [agent("chosen", 1, 70)];
    expect(findSelectedAgent(before, "chosen")?.x).toBe(0);
    expect(findSelectedAgent(after, "chosen")).toMatchObject({ x: 1, health: 70 });
  });

  it("resolves a followed agent's cell from its current authoritative position", () => {
    const before = snapshot([agent("chosen", 0, 80)]);
    const after = snapshot([agent("chosen", 1, 70)]);
    const afterDeath = snapshot([agent("chosen", 1, 0, false)]);
    expect(resolveInspectionSelection(before, "chosen", { x: 0, y: 0 })).toMatchObject({
      agent: { x: 0 },
      cell: { x: 0, food_stock: 5 },
    });
    expect(resolveInspectionSelection(after, "chosen", { x: 0, y: 0 })).toMatchObject({
      agent: { x: 1, health: 70 },
      cell: { x: 1, food_stock: 0 },
    });
    expect(resolveInspectionSelection(afterDeath, "chosen", { x: 0, y: 0 })).toMatchObject({
      agent: { x: 1, alive: false },
      cell: { x: 1, food_stock: 0 },
    });
  });

  it("retains an independently selected cell when no agent is selected", () => {
    expect(resolveInspectionSelection(snapshot([]), null, { x: 1, y: 0 })).toMatchObject({
      agent: null,
      cell: { x: 1, y: 0 },
    });
  });
});
