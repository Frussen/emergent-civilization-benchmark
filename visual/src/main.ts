import "./styles.css";

import { VisualConnection } from "./connection";
import { command, speedCommand, type ServerMessage, type VisualSpeed } from "./protocol";
import { WorldRenderer } from "./renderer";
import { VisualUI } from "./ui";

const root = document.querySelector<HTMLElement>("#app");
if (!root) throw new Error("Missing #app root element.");

const websocketUrl =
  import.meta.env.VITE_ECB_WS_URL ??
  `${location.protocol === "https:" ? "wss" : "ws"}://${location.hostname}:8000/ws`;

const renderer = new WorldRenderer();
let connection: VisualConnection;
const send = (message: ReturnType<typeof command> | ReturnType<typeof speedCommand>) => {
  if (!connection.send(message)) ui.showError("Command was not sent: WebSocket is disconnected.");
};
const ui = new VisualUI(
  root,
  {
    play: () => send(command("play")),
    pause: () => send(command("pause")),
    step: () => send(command("step")),
    setSpeed: (speed: VisualSpeed) => send(speedCommand(speed)),
  },
  websocketUrl,
);

await renderer.initialize(ui.viewport);

function handleMessage(message: ServerMessage): void {
  if (message.type === "snapshot") {
    renderer.render(message.snapshot);
    ui.setSnapshot(message.snapshot);
  } else if (message.type === "status") {
    ui.setStatus(message);
  } else {
    const detail = `${message.code}: ${message.message}`;
    console.error(`[ECB visual] Backend error: ${detail}`);
    ui.showError(detail);
  }
}

connection = new VisualConnection(websocketUrl, {
  onState: (state, detail) => ui.setConnection(state, detail),
  onMessage: handleMessage,
  onProtocolFailure: (detail) => ui.showError(`Protocol: ${detail}`),
});
connection.connect();
