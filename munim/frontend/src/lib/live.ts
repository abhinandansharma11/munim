import { useEffect, useRef, useState } from 'react';

export type LiveEvent = { type: string; [k: string]: any };

// Live updates over a WebSocket. If a network blocks WebSockets, the page checks every 2 seconds instead.
export function useLive(onEvent: (e: LiveEvent) => void) {
  const handler = useRef(onEvent);
  handler.current = onEvent;
  const [connected, setConnected] = useState(true);
  useEffect(() => {
    let ws: WebSocket | null = null, alive = true, retry = 0, up = false, timer: number | undefined;
    const open = () => {
      ws = new WebSocket((location.protocol === 'https:' ? 'wss://' : 'ws://') + location.host + '/ws');
      ws.onopen = () => { retry = 0; up = true; setConnected(true); };
      ws.onmessage = (m) => { try { handler.current(JSON.parse(m.data)); } catch (err) { console.error(err); } };
      ws.onclose = () => { up = false; setConnected(false); if (alive) timer = window.setTimeout(open, Math.min(4000, 500 + retry++ * 700)); };
    };
    open();
    const poll = window.setInterval(() => { if (!up) handler.current({ type: 'poll' }); }, 2000);
    return () => { alive = false; clearTimeout(timer); clearInterval(poll); ws?.close(); };
  }, []);
  return connected;
}
