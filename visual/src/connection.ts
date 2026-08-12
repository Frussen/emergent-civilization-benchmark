import {
  parseServerMessage,
  type ClientCommand,
  type ServerMessage,
} from "./protocol";

export type ConnectionState = "connecting" | "connected" | "disconnected" | "error";

export interface ConnectionHandlers {
  onState(state: ConnectionState, detail?: string): void;
  onMessage(message: ServerMessage): void;
  onProtocolFailure(message: string): void;
}

export class VisualConnection {
  private socket: WebSocket | null = null;

  constructor(
    private readonly url: string,
    private readonly handlers: ConnectionHandlers,
  ) {}

  connect(): void {
    this.handlers.onState("connecting");
    const socket = new WebSocket(this.url);
    this.socket = socket;
    socket.addEventListener("open", () => this.handlers.onState("connected"));
    socket.addEventListener("message", (event) => {
      if (typeof event.data !== "string") {
        this.reportProtocolFailure("Server sent a non-text WebSocket message.");
        return;
      }
      try {
        this.handlers.onMessage(parseServerMessage(event.data));
      } catch (error) {
        const detail = error instanceof Error ? error.message : String(error);
        this.reportProtocolFailure(detail);
      }
    });
    socket.addEventListener("error", () => {
      this.handlers.onState("error", `WebSocket error at ${this.url}`);
      console.error(`[ECB visual] WebSocket error at ${this.url}`);
    });
    socket.addEventListener("close", (event) => {
      const suffix = event.reason ? `: ${event.reason}` : "";
      this.handlers.onState("disconnected", `Connection closed (${event.code})${suffix}`);
    });
  }

  send(command: ClientCommand): boolean {
    if (this.socket?.readyState !== WebSocket.OPEN) return false;
    this.socket.send(JSON.stringify(command));
    return true;
  }

  private reportProtocolFailure(detail: string): void {
    console.error(`[ECB visual] Protocol error: ${detail}`);
    this.handlers.onProtocolFailure(detail);
  }
}
