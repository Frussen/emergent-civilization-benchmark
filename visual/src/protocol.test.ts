import { describe, expect, it } from "vitest";

import { parseServerMessage, ProtocolParseError } from "./protocol";

const snapshot = {
  version: 1,
  type: "snapshot",
  snapshot: {
    tick: 3,
    world_state_hash: "abc",
    world: { width: 2, height: 1 },
    agents: [
      {
        id: "agent-1",
        x: 1,
        y: 0,
        alive: true,
        health: 99,
        food_inventory: 4,
        water_inventory: 5,
      },
    ],
    cells: [
      { x: 0, y: 0, food_stock: 20, water_stock: 19 },
      { x: 1, y: 0, food_stock: 18, water_stock: 20 },
    ],
    metrics: {
      alive_agents: 1,
      mean_health_alive: 99,
      total_world_food: 38,
      total_world_water: 39,
    },
  },
};

describe("parseServerMessage", () => {
  it("parses the explicit protocol-v1 snapshot schema", () => {
    const parsed = parseServerMessage(JSON.stringify(snapshot));
    expect(parsed.type).toBe("snapshot");
    if (parsed.type === "snapshot") expect(parsed.snapshot.agents[0]?.x).toBe(1);
  });

  it("rejects unknown message types visibly", () => {
    expect(() =>
      parseServerMessage(JSON.stringify({ version: 1, type: "delta" })),
    ).toThrow(ProtocolParseError);
  });

  it("rejects incomplete cell coverage", () => {
    const incomplete = structuredClone(snapshot);
    incomplete.snapshot.cells.pop();
    expect(() => parseServerMessage(JSON.stringify(incomplete))).toThrow(
      "complete world",
    );
  });
});
