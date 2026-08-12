export const PROTOCOL_VERSION = 1 as const;

export type ProtocolVersion = typeof PROTOCOL_VERSION;
export type VisualSpeed = "1x" | "5x" | "20x" | "max";

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
  water_stock: number;
}

export interface VisualMetrics {
  alive_agents: number;
  mean_health_alive: number | null;
  total_world_food: number;
  total_world_water: number;
}

export interface VisualSnapshot {
  tick: number;
  world_state_hash: string;
  world: { width: number; height: number };
  agents: AgentSnapshot[];
  cells: CellSnapshot[];
  metrics: VisualMetrics;
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
    ["tick", "world_state_hash", "world", "agents", "cells", "metrics"],
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
  requireFields(cell, ["x", "y", "food_stock", "water_stock"], path);
  const x = requireNonnegativeInteger(cell.x, `${path}.x`);
  const y = requireNonnegativeInteger(cell.y, `${path}.y`);
  if (x >= width || y >= height) {
    throw new ProtocolParseError(`${path} is outside world bounds.`);
  }
  return {
    x,
    y,
    food_stock: requireNumber(cell.food_stock, `${path}.food_stock`),
    water_stock: requireNumber(cell.water_stock, `${path}.water_stock`),
  };
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
