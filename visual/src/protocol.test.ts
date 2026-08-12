import { describe, expect, it } from "vitest";

import { parseServerMessage, ProtocolParseError } from "./protocol";

const snapshot = {
  version: 2,
  type: "snapshot",
  snapshot: {
    tick: 3,
    world_state_hash: "abc",
    health_reference: 100,
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
      {
        x: 0,
        y: 0,
        food_stock: 20,
        food_capacity: 20,
        water_stock: 19,
        water_capacity: 20,
      },
      {
        x: 1,
        y: 0,
        food_stock: 18,
        food_capacity: 20,
        water_stock: 20,
        water_capacity: 20,
      },
    ],
    metrics: {
      alive_agents: 1,
      mean_health_alive: 99,
      total_world_food: 38,
      total_world_water: 39,
    },
    recent_events: [
      {
        event_type: "harvest",
        tick: 2,
        agent_id: "agent-1",
        resource: "food",
        amount: 2,
        x: 1,
        y: 0,
      },
      { event_type: "death", tick: 3, agent_id: "agent-2" },
    ],
  },
};

function invalidActionEvent(
  actionKind: string,
  direction: unknown,
  resource: unknown,
): Record<string, unknown> {
  return {
    event_type: "invalid_action",
    tick: 3,
    agent_id: "agent-invalid",
    action_kind: actionKind,
    direction,
    resource,
    reason: "invalid action",
  };
}

function messageWithEvents(events: Array<Record<string, unknown>>): string {
  return JSON.stringify({
    ...snapshot,
    snapshot: { ...snapshot.snapshot, recent_events: events },
  });
}

describe("parseServerMessage", () => {
  it("parses the explicit protocol-v2 snapshot schema", () => {
    const parsed = parseServerMessage(JSON.stringify(snapshot));
    expect(parsed.type).toBe("snapshot");
    if (parsed.type === "snapshot") expect(parsed.snapshot.agents[0]?.x).toBe(1);
  });

  it("rejects unknown message types visibly", () => {
    expect(() =>
      parseServerMessage(JSON.stringify({ version: 2, type: "delta" })),
    ).toThrow(ProtocolParseError);
  });

  it("rejects incomplete cell coverage", () => {
    const incomplete = structuredClone(snapshot);
    incomplete.snapshot.cells.pop();
    expect(() => parseServerMessage(JSON.stringify(incomplete))).toThrow(
      "complete world",
    );
  });

  it("rejects malformed capacities and event fields", () => {
    const badCapacity = structuredClone(snapshot);
    badCapacity.snapshot.cells[0]!.food_capacity = -1;
    expect(() => parseServerMessage(JSON.stringify(badCapacity))).toThrow(
      "nonnegative",
    );

    const badEvent = structuredClone(snapshot);
    badEvent.snapshot.recent_events[0]!.resource = "wood";
    expect(() => parseServerMessage(JSON.stringify(badEvent))).toThrow(
      "food or water",
    );
  });

  it.each([
    ["wait", null, null],
    ["move", "north", null],
    ["move", "north-east", null],
    ["move", "east", null],
    ["move", "south-east", null],
    ["move", "south", null],
    ["move", "south-west", null],
    ["move", "west", null],
    ["move", "north-west", null],
    ["harvest", null, "food"],
    ["harvest", null, "water"],
  ])("accepts the canonical %s action shape", (actionKind, direction, resource) => {
    expect(() =>
      parseServerMessage(
        messageWithEvents([invalidActionEvent(actionKind, direction, resource)]),
      ),
    ).not.toThrow();
  });

  it.each([
    ["wait", "north", null, "only move accepts a direction"],
    ["wait", null, "food", "only harvest accepts a resource"],
    ["move", null, null, "move requires a direction"],
    ["move", "north", "food", "only harvest accepts a resource"],
    ["harvest", "north", "food", "only move accepts a direction"],
    ["harvest", null, null, "harvest requires a resource"],
  ])(
    "rejects the impossible %s action shape (%s, %s)",
    (actionKind, direction, resource, expected) => {
      expect(() =>
        parseServerMessage(
          messageWithEvents([invalidActionEvent(actionKind, direction, resource)]),
        ),
      ).toThrow(expected);
    },
  );
});
