// Real-time client for Squared. Authenticates over the socket (first message),
// subscribes to a group, and invokes a callback on balances.updated so the UI
// can refetch. Auto-reconnects and re-subscribes (DESIGN.md §7).

export type SquaredEvent = { type: string; group_id?: number; [k: string]: unknown };

export interface GroupSocket {
  close(): void;
}

function defaultWsUrl(): string {
  // Dev: same-origin, proxied by Vite. Prod: derive from VITE_API_BASE.
  const base = (import.meta.env.VITE_API_BASE ?? "").replace(/\/$/, "");
  if (base) return base.replace(/^http/, "ws") + "/ws";
  const proto = location.protocol === "https:" ? "wss" : "ws";
  return `${proto}://${location.host}/ws`;
}

export function connectGroup(
  token: string,
  groupId: number,
  onEvent: (e: SquaredEvent) => void,
  wsUrl = defaultWsUrl(),
): GroupSocket {
  let ws: WebSocket | null = null;
  let closed = false;
  let retry = 0;

  const open = () => {
    ws = new WebSocket(wsUrl);
    ws.onopen = () => {
      ws!.send(JSON.stringify({ type: "auth", token }));
    };
    ws.onmessage = (msg) => {
      const data = JSON.parse(msg.data) as SquaredEvent;
      if (data.type === "auth_ok") {
        ws!.send(JSON.stringify({ type: "subscribe", group_id: groupId }));
      }
      onEvent(data);
    };
    ws.onclose = () => {
      if (closed) return;
      // Reconnect with backoff; the caller should refetch state on reconnect
      // so any events missed while offline can't leave a stale cache.
      retry = Math.min(retry + 1, 6);
      setTimeout(open, 500 * 2 ** (retry - 1));
    };
  };

  open();
  return {
    close() {
      closed = true;
      ws?.close();
    },
  };
}
