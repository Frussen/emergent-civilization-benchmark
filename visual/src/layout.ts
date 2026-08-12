import type { AgentSnapshot } from "./protocol";

export interface PresentedAgent extends AgentSnapshot {
  offsetX: number;
  offsetY: number;
}

/** Deterministic presentation offsets in cell units; scientific x/y are unchanged. */
export function arrangeMultiOccupancy(agents: AgentSnapshot[]): PresentedAgent[] {
  const groups = new Map<string, AgentSnapshot[]>();
  for (const agent of agents) {
    const key = `${agent.x},${agent.y}`;
    const group = groups.get(key);
    if (group) group.push(agent);
    else groups.set(key, [agent]);
  }

  const presented: PresentedAgent[] = [];
  for (const group of groups.values()) {
    group.sort((left, right) =>
      left.id < right.id ? -1 : left.id > right.id ? 1 : 0,
    );
    const offsets = offsetsForCount(group.length);
    group.forEach((agent, index) => {
      const offset = offsets[index];
      if (!offset) throw new Error("Missing deterministic occupancy offset.");
      presented.push({ ...agent, offsetX: offset.x, offsetY: offset.y });
    });
  }
  return presented;
}

function offsetsForCount(count: number): Array<{ x: number; y: number }> {
  if (count === 1) return [{ x: 0, y: 0 }];
  const offsets: Array<{ x: number; y: number }> = [];
  let remaining = count;
  let ring = 1;
  while (remaining > 0) {
    const ringCount = Math.min(remaining, ring * 8);
    const radius = Math.min(0.12 + ring * 0.1, 0.36);
    for (let index = 0; index < ringCount; index += 1) {
      const angle = -Math.PI / 2 + (index * Math.PI * 2) / ringCount;
      offsets.push({ x: Math.cos(angle) * radius, y: Math.sin(angle) * radius });
    }
    remaining -= ringCount;
    ring += 1;
  }
  return offsets;
}
