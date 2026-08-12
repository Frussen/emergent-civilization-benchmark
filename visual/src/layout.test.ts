import { describe, expect, it } from "vitest";

import { arrangeMultiOccupancy } from "./layout";
import type { AgentSnapshot } from "./protocol";

function agent(id: string, x = 10, y = 12): AgentSnapshot {
  return {
    id,
    x,
    y,
    alive: true,
    health: 100,
    food_inventory: 20,
    water_inventory: 20,
  };
}

describe("arrangeMultiOccupancy", () => {
  it("sorts co-located agents by ID and assigns stable distinct offsets", () => {
    const first = arrangeMultiOccupancy([agent("c"), agent("a"), agent("b")]);
    const second = arrangeMultiOccupancy([agent("b"), agent("c"), agent("a")]);

    expect(first).toEqual(second);
    expect(first.map((item) => item.id)).toEqual(["a", "b", "c"]);
    expect(new Set(first.map((item) => `${item.offsetX},${item.offsetY}`)).size).toBe(3);
  });

  it("preserves every scientific coordinate", () => {
    const arranged = arrangeMultiOccupancy([agent("a"), agent("b")]);
    expect(arranged.every((item) => item.x === 10 && item.y === 12)).toBe(true);
  });
});
