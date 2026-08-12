import { describe, expect, it } from "vitest";

import {
  agentHitRadius,
  cellLayerInvalidation,
  compareAgentHits,
} from "./rendering";

describe("renderer presentation helpers", () => {
  it("keeps the agent target usable across zoom levels", () => {
    expect(agentHitRadius(1)).toBe(6);
    expect(agentHitRadius(0.5)).toBe(12);
    expect(agentHitRadius(0.02)).toBe(300);
    expect(agentHitRadius(2)).toBe(3.5);
  });

  it("handles invalid scales without division by zero", () => {
    expect(agentHitRadius(0)).toBe(6);
    expect(agentHitRadius(Number.NaN)).toBe(6);
  });

  it("uses locale-independent agent IDs only to break equal-distance ties", () => {
    const hits = [
      { distance: 2, agent: { id: "ä-agent" } },
      { distance: 1, agent: { id: "é-agent" } },
      { distance: 2, agent: { id: "z-agent" } },
    ];
    expect(hits.sort(compareAgentHits).map((hit) => hit.agent.id)).toEqual([
      "é-agent",
      "z-agent",
      "ä-agent",
    ]);
  });

  it("does not redraw cell layers for agents-mode snapshot updates", () => {
    const state = { width: 64, height: 64, mode: "agents" as const };
    expect(cellLayerInvalidation(state, state, true)).toEqual({
      staticLayer: false,
      overlayLayer: false,
    });
  });

  it("invalidates only the dynamic overlay for overlay data or mode changes", () => {
    const agents = { width: 64, height: 64, mode: "agents" as const };
    const food = { width: 64, height: 64, mode: "food" as const };
    expect(cellLayerInvalidation(food, food, true)).toEqual({
      staticLayer: false,
      overlayLayer: true,
    });
    expect(cellLayerInvalidation(agents, food, false)).toEqual({
      staticLayer: false,
      overlayLayer: true,
    });
  });

  it("invalidates both cell layers when world dimensions change", () => {
    expect(cellLayerInvalidation(
      { width: 64, height: 64, mode: "agents" },
      { width: 32, height: 16, mode: "agents" },
      true,
    )).toEqual({ staticLayer: true, overlayLayer: true });
  });
});
