export const PROTOCOL_VERSION = 2 as const;

export type ProtocolVersion = typeof PROTOCOL_VERSION;
export type VisualSpeed = "1x" | "5x" | "20x" | "max";
export type Direction =
  | "north"
  | "north-east"
  | "east"
  | "south-east"
  | "south"
  | "south-west"
  | "west"
  | "north-west";

export interface AgentSnapshot {
  id: string;
  x: number;
  y: number;
  alive: boolean;
  health: number;
  food_inventory: number;
  water_inventory: number;
}

export interface CellSnapshot {
  x: number;
  y: number;
  food_stock: number;
  food_capacity: number;
  water_stock: number;
  water_capacity: number;
}

export interface HarvestVisualEvent {
  event_type: "harvest";
  tick: number;
  agent_id: string;
  resource: "food" | "water";
  amount: number;
  x: number;
  y: number;
}

export interface DeathVisualEvent {
  event_type: "death";
  tick: number;
  agent_id: string;
}

export interface InvalidActionVisualEvent {
  event_type: "invalid_action";
  tick: number;
  agent_id: string;
  action_kind: "wait" | "move" | "harvest";
  direction: Direction | null;
  resource: "food" | "water" | null;
  reason: string;
}

export type VisualEvent =
  | HarvestVisualEvent
  | DeathVisualEvent
  | InvalidActionVisualEvent;

export interface VisualMetrics {
  alive_agents: number;
  mean_health_alive: number | null;
  total_world_food: number;
  total_world_water: number;
}

export interface VisualSnapshot {
  tick: number;
  world_state_hash: string;
  health_reference: number;
  world: { width: number; height: number };
  agents: AgentSnapshot[];
  cells: CellSnapshot[];
  metrics: VisualMetrics;
  recent_events: VisualEvent[];
}

export interface SnapshotMessage {
  version: ProtocolVersion;
  type: "snapshot";
  snapshot: VisualSnapshot;
}

export interface StatusMessage {
  version: ProtocolVersion;
  type: "status";
  playing: boolean;
  speed: VisualSpeed;
  extinct: boolean;
  tick: number;
  scheduler_error: string | null;
}

export interface ErrorMessage {
  version: ProtocolVersion;
  type: "error";
  code: string;
  message: string;
}

export type ServerMessage = SnapshotMessage | StatusMessage | ErrorMessage;

export type ClientCommand =
  | { version: ProtocolVersion; type: "play" }
  | { version: ProtocolVersion; type: "pause" }
  | { version: ProtocolVersion; type: "step" }
  | { version: ProtocolVersion; type: "set_speed"; speed: VisualSpeed };

export class ProtocolParseError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "ProtocolParseError";
  }
}

type RecordValue = Record<string, unknown>;

export function command(
  type: "play" | "pause" | "step",
): ClientCommand {
  return { version: PROTOCOL_VERSION, type };
}

export function speedCommand(speed: VisualSpeed): ClientCommand {
  return { version: PROTOCOL_VERSION, type: "set_speed", speed };
}

export function parseServerMessage(text: string): ServerMessage {
  let value: unknown;
  try {
    value = JSON.parse(text) as unknown;
  } catch {
    throw new ProtocolParseError("Server sent invalid JSON.");
  }

  const envelope = requireRecord(value, "message");
  requireExactVersion(envelope.version);
  const type = requireString(envelope.type, "message.type");
  if (type === "snapshot") return parseSnapshotMessage(envelope);
  if (type === "status") return parseStatusMessage(envelope);
  if (type === "error") return parseErrorMessage(envelope);
  throw new ProtocolParseError(`Unknown server message type: ${type}`);
}

function parseSnapshotMessage(value: RecordValue): SnapshotMessage {
  requireFields(value, ["version", "type", "snapshot"], "snapshot message");
  const raw = requireRecord(value.snapshot, "snapshot");
  requireFields(
    raw,
    [
      "tick",
      "world_state_hash",
      "health_reference",
      "world",
      "agents",
      "cells",
      "metrics",
      "recent_events",
    ],
    "snapshot",
  );
  const world = requireRecord(raw.world, "snapshot.world");
  requireFields(world, ["width", "height"], "snapshot.world");
  const width = requirePositiveInteger(world.width, "snapshot.world.width");
  const height = requirePositiveInteger(world.height, "snapshot.world.height");
  const agents = requireArray(raw.agents, "snapshot.agents").map((agent, index) =>
    parseAgent(agent, index, width, height),
  );
  const cells = requireArray(raw.cells, "snapshot.cells").map((cell, index) =>
    parseCell(cell, index, width, height),
  );
  validateSnapshotCollections(agents, cells, width, height);
  const recentEvents = requireArray(raw.recent_events, "snapshot.recent_events").map(
    (event, index) => parseVisualEvent(event, index, width, height),
  );
  if (recentEvents.length > 75) {
    throw new ProtocolParseError("snapshot.recent_events exceeds the tail limit.");
  }
  if (recentEvents.some((event, index) => index > 0 && event.tick < recentEvents[index - 1]!.tick)) {
    throw new ProtocolParseError("snapshot.recent_events must be chronological.");
  }

  const metrics = requireRecord(raw.metrics, "snapshot.metrics");
  requireFields(
    metrics,
    [
      "alive_agents",
      "mean_health_alive",
      "total_world_food",
      "total_world_water",
    ],
    "snapshot.metrics",
  );
  return {
    version: PROTOCOL_VERSION,
    type: "snapshot",
    snapshot: {
      tick: requireNonnegativeInteger(raw.tick, "snapshot.tick"),
      world_state_hash: requireString(
        raw.world_state_hash,
        "snapshot.world_state_hash",
      ),
      health_reference: requireNonnegativeNumber(
        raw.health_reference,
        "snapshot.health_reference",
      ),
      world: { width, height },
      agents,
      cells,
      metrics: {
        alive_agents: requireNonnegativeInteger(
          metrics.alive_agents,
          "snapshot.metrics.alive_agents",
        ),
        mean_health_alive:
          metrics.mean_health_alive === null
            ? null
            : requireNumber(
                metrics.mean_health_alive,
                "snapshot.metrics.mean_health_alive",
              ),
        total_world_food: requireNumber(
          metrics.total_world_food,
          "snapshot.metrics.total_world_food",
        ),
        total_world_water: requireNumber(
          metrics.total_world_water,
          "snapshot.metrics.total_world_water",
        ),
      },
      recent_events: recentEvents,
    },
  };
}

function parseAgent(
  value: unknown,
  index: number,
  width: number,
  height: number,
): AgentSnapshot {
  const path = `snapshot.agents[${index}]`;
  const agent = requireRecord(value, path);
  requireFields(
    agent,
    ["id", "x", "y", "alive", "health", "food_inventory", "water_inventory"],
    path,
  );
  const x = requireNonnegativeInteger(agent.x, `${path}.x`);
  const y = requireNonnegativeInteger(agent.y, `${path}.y`);
  if (x >= width || y >= height) {
    throw new ProtocolParseError(`${path} is outside world bounds.`);
  }
  return {
    id: requireString(agent.id, `${path}.id`),
    x,
    y,
    alive: requireBoolean(agent.alive, `${path}.alive`),
    health: requireNumber(agent.health, `${path}.health`),
    food_inventory: requireNumber(
      agent.food_inventory,
      `${path}.food_inventory`,
    ),
    water_inventory: requireNumber(
      agent.water_inventory,
      `${path}.water_inventory`,
    ),
  };
}

function parseCell(
  value: unknown,
  index: number,
  width: number,
  height: number,
): CellSnapshot {
  const path = `snapshot.cells[${index}]`;
  const cell = requireRecord(value, path);
  requireFields(
    cell,
    ["x", "y", "food_stock", "food_capacity", "water_stock", "water_capacity"],
    path,
  );
  const x = requireNonnegativeInteger(cell.x, `${path}.x`);
  const y = requireNonnegativeInteger(cell.y, `${path}.y`);
  if (x >= width || y >= height) {
    throw new ProtocolParseError(`${path} is outside world bounds.`);
  }
  const result = {
    x,
    y,
    food_stock: requireNonnegativeNumber(cell.food_stock, `${path}.food_stock`),
    food_capacity: requireNonnegativeNumber(
      cell.food_capacity,
      `${path}.food_capacity`,
    ),
    water_stock: requireNonnegativeNumber(cell.water_stock, `${path}.water_stock`),
    water_capacity: requireNonnegativeNumber(
      cell.water_capacity,
      `${path}.water_capacity`,
    ),
  };
  if (result.food_stock > result.food_capacity || result.water_stock > result.water_capacity) {
    throw new ProtocolParseError(`${path} resource stock exceeds capacity.`);
  }
  return result;
}

function parseVisualEvent(
  value: unknown,
  index: number,
  width: number,
  height: number,
): VisualEvent {
  const path = `snapshot.recent_events[${index}]`;
  const event = requireRecord(value, path);
  const eventType = requireString(event.event_type, `${path}.event_type`);
  if (eventType === "harvest") {
    requireFields(event, ["event_type", "tick", "agent_id", "resource", "amount", "x", "y"], path);
    const resource = requireResource(event.resource, `${path}.resource`);
    const x = requireNonnegativeInteger(event.x, `${path}.x`);
    const y = requireNonnegativeInteger(event.y, `${path}.y`);
    if (x >= width || y >= height) {
      throw new ProtocolParseError(`${path} is outside world bounds.`);
    }
    return {
      event_type: "harvest",
      tick: requireNonnegativeInteger(event.tick, `${path}.tick`),
      agent_id: requireString(event.agent_id, `${path}.agent_id`),
      resource,
      amount: requireNonnegativeNumber(event.amount, `${path}.amount`),
      x,
      y,
    };
  }
  if (eventType === "death") {
    requireFields(event, ["event_type", "tick", "agent_id"], path);
    return {
      event_type: "death",
      tick: requireNonnegativeInteger(event.tick, `${path}.tick`),
      agent_id: requireString(event.agent_id, `${path}.agent_id`),
    };
  }
  if (eventType === "invalid_action") {
    requireFields(
      event,
      ["event_type", "tick", "agent_id", "action_kind", "direction", "resource", "reason"],
      path,
    );
    const actionKind = requireString(event.action_kind, `${path}.action_kind`);
    if (actionKind !== "wait" && actionKind !== "move" && actionKind !== "harvest") {
      throw new ProtocolParseError(`${path}.action_kind is unsupported.`);
    }
    const direction =
      event.direction === null
        ? null
        : requireDirection(event.direction, `${path}.direction`);
    const resource =
      event.resource === null
        ? null
        : requireResource(event.resource, `${path}.resource`);
    validateActionShape(actionKind, direction, resource, path);
    return {
      event_type: "invalid_action",
      tick: requireNonnegativeInteger(event.tick, `${path}.tick`),
      agent_id: requireString(event.agent_id, `${path}.agent_id`),
      action_kind: actionKind,
      direction,
      resource,
      reason: requireString(event.reason, `${path}.reason`),
    };
  }
  throw new ProtocolParseError(`${path}.event_type is unsupported.`);
}

function validateActionShape(
  actionKind: "wait" | "move" | "harvest",
  direction: Direction | null,
  resource: "food" | "water" | null,
  path: string,
): void {
  if (actionKind === "move" && direction === null) {
    throw new ProtocolParseError(`${path}: move requires a direction.`);
  }
  if (actionKind === "harvest" && resource === null) {
    throw new ProtocolParseError(`${path}: harvest requires a resource.`);
  }
  if (actionKind !== "move" && direction !== null) {
    throw new ProtocolParseError(`${path}: only move accepts a direction.`);
  }
  if (actionKind !== "harvest" && resource !== null) {
    throw new ProtocolParseError(`${path}: only harvest accepts a resource.`);
  }
}

function parseStatusMessage(value: RecordValue): StatusMessage {
  requireFields(
    value,
    ["version", "type", "playing", "speed", "extinct", "tick", "scheduler_error"],
    "status message",
  );
  const speed = requireString(value.speed, "status.speed");
  if (!isVisualSpeed(speed)) {
    throw new ProtocolParseError(`Unsupported status speed: ${speed}`);
  }
  return {
    version: PROTOCOL_VERSION,
    type: "status",
    playing: requireBoolean(value.playing, "status.playing"),
    speed,
    extinct: requireBoolean(value.extinct, "status.extinct"),
    tick: requireNonnegativeInteger(value.tick, "status.tick"),
    scheduler_error:
      value.scheduler_error === null
        ? null
        : requireString(value.scheduler_error, "status.scheduler_error"),
  };
}

function parseErrorMessage(value: RecordValue): ErrorMessage {
  requireFields(value, ["version", "type", "code", "message"], "error message");
  return {
    version: PROTOCOL_VERSION,
    type: "error",
    code: requireString(value.code, "error.code"),
    message: requireString(value.message, "error.message"),
  };
}

function validateSnapshotCollections(
  agents: AgentSnapshot[],
  cells: CellSnapshot[],
  width: number,
  height: number,
): void {
  if (new Set(agents.map((agent) => agent.id)).size !== agents.length) {
    throw new ProtocolParseError("Snapshot contains duplicate agent IDs.");
  }
  const coordinates = cells.map((cell) => `${cell.x},${cell.y}`);
  if (cells.length !== width * height || new Set(coordinates).size !== cells.length) {
    throw new ProtocolParseError("Snapshot cells must cover the complete world once.");
  }
}

function requireExactVersion(value: unknown): asserts value is ProtocolVersion {
  if (value !== PROTOCOL_VERSION) {
    throw new ProtocolParseError(
      `Unsupported protocol version: ${String(value)}; expected ${PROTOCOL_VERSION}.`,
    );
  }
}

function requireRecord(value: unknown, path: string): RecordValue {
  if (typeof value !== "object" || value === null || Array.isArray(value)) {
    throw new ProtocolParseError(`${path} must be an object.`);
  }
  return value as RecordValue;
}

function requireArray(value: unknown, path: string): unknown[] {
  if (!Array.isArray(value)) throw new ProtocolParseError(`${path} must be an array.`);
  return value;
}

function requireFields(value: RecordValue, fields: string[], path: string): void {
  const actual = Object.keys(value).sort();
  const expected = [...fields].sort();
  if (actual.length !== expected.length || actual.some((field, i) => field !== expected[i])) {
    throw new ProtocolParseError(`${path} has unexpected or missing fields.`);
  }
}

function requireString(value: unknown, path: string): string {
  if (typeof value !== "string") throw new ProtocolParseError(`${path} must be a string.`);
  return value;
}

function requireBoolean(value: unknown, path: string): boolean {
  if (typeof value !== "boolean") throw new ProtocolParseError(`${path} must be a boolean.`);
  return value;
}

function requireNumber(value: unknown, path: string): number {
  if (typeof value !== "number" || !Number.isFinite(value)) {
    throw new ProtocolParseError(`${path} must be a finite number.`);
  }
  return value;
}

function requireNonnegativeNumber(value: unknown, path: string): number {
  const number = requireNumber(value, path);
  if (number < 0) throw new ProtocolParseError(`${path} must be nonnegative.`);
  return number;
}

function requireResource(value: unknown, path: string): "food" | "water" {
  const resource = requireString(value, path);
  if (resource !== "food" && resource !== "water") {
    throw new ProtocolParseError(`${path} must be food or water.`);
  }
  return resource;
}

function requireDirection(value: unknown, path: string): Direction {
  const direction = requireString(value, path);
  const directions: Direction[] = [
    "north",
    "north-east",
    "east",
    "south-east",
    "south",
    "south-west",
    "west",
    "north-west",
  ];
  if (!directions.includes(direction as Direction)) {
    throw new ProtocolParseError(`${path} is unsupported.`);
  }
  return direction as Direction;
}

function requireNonnegativeInteger(value: unknown, path: string): number {
  const number = requireNumber(value, path);
  if (!Number.isInteger(number) || number < 0) {
    throw new ProtocolParseError(`${path} must be a nonnegative integer.`);
  }
  return number;
}

function requirePositiveInteger(value: unknown, path: string): number {
  const number = requireNonnegativeInteger(value, path);
  if (number === 0) throw new ProtocolParseError(`${path} must be positive.`);
  return number;
}

function isVisualSpeed(value: string): value is VisualSpeed {
  return value === "1x" || value === "5x" || value === "20x" || value === "max";
}
