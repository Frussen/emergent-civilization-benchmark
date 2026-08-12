import type { OverlayMode } from "./overlays";

const AGENT_HIT_RADIUS_SCREEN = 6;
const AGENT_MARKER_HIT_RADIUS_LOCAL = 3.5;

export interface CellLayerState {
  width: number;
  height: number;
  mode: OverlayMode;
}

export interface CellLayerInvalidation {
  staticLayer: boolean;
  overlayLayer: boolean;
}

export interface AgentHitCandidate {
  distance: number;
  agent: { id: string };
}

export function agentHitRadius(worldScale: number): number {
  const usableScale = Number.isFinite(worldScale) && worldScale > 0
    ? worldScale
    : 1;
  return Math.max(
    AGENT_MARKER_HIT_RADIUS_LOCAL,
    AGENT_HIT_RADIUS_SCREEN / usableScale,
  );
}

export function compareAgentHits(
  left: AgentHitCandidate,
  right: AgentHitCandidate,
): number {
  const distanceOrder = left.distance - right.distance;
  if (distanceOrder !== 0) return distanceOrder;
  return left.agent.id < right.agent.id
    ? -1
    : left.agent.id > right.agent.id
      ? 1
      : 0;
}

export function cellLayerInvalidation(
  previous: CellLayerState | null,
  next: CellLayerState,
  snapshotChanged: boolean,
): CellLayerInvalidation {
  const dimensionsChanged =
    previous === null ||
    previous.width !== next.width ||
    previous.height !== next.height;
  const modeChanged = previous === null || previous.mode !== next.mode;
  return {
    staticLayer: dimensionsChanged,
    overlayLayer:
      dimensionsChanged ||
      modeChanged ||
      (snapshotChanged && next.mode !== "agents"),
  };
}
