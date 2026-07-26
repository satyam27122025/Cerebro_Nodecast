import { useEffect, useRef, useCallback } from "react";
import { useSyncStore } from "../store/useSyncStore";

function getWsUrl(roomCode) {
  if (import.meta.env.VITE_WS_BASE_URL) {
    const base = import.meta.env.VITE_WS_BASE_URL.replace(/\/$/, "");
    return `${base}/ws/sync/${roomCode}/`;
  }
  const apiBase = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";
  const wsProtocol = apiBase.startsWith("https") ? "wss:" : "ws:";
  const wsHost = apiBase.replace(/^https?:\/\//, "").replace(/\/$/, "");
  return `${wsProtocol}//${wsHost}/ws/sync/${roomCode}/`;
}

export function useRealtimeSync(roomCode, role, config = {}) {
  const socketRef = useRef(null);
  const reconnectTimerRef = useRef(null);
  const reconnectCount = useRef(0);
  const onEventRef = useRef(config.onEvent);
  const applySocketEvent = useSyncStore(state => state.applySocketEvent);
  const updateTelemetry = useSyncStore(state => state.updateTelemetry);
  const pushLog = useSyncStore(state => state.pushLog);

  // Keep onEvent ref fresh without triggering reconnects
  useEffect(() => {
    onEventRef.current = config.onEvent;
  });

  const connect = useCallback(() => {
    if (!roomCode) return;

    updateTelemetry({ wsStatus: "connecting" });
    const wsUrl = getWsUrl(roomCode);
    const ws = new WebSocket(wsUrl);
    socketRef.current = ws;

    ws.onopen = () => {
      reconnectCount.current = 0;
      updateTelemetry({ wsStatus: "connected" });
      pushLog("WS CONNECTED");
    };

    ws.onmessage = (event) => {
      try {
        const payload = JSON.parse(event.data);
        const type = payload.type || payload.event;
        const data = payload.data || payload;

        applySocketEvent(type, data);
        if (typeof onEventRef.current === "function") {
          onEventRef.current(payload);
        }
      } catch (err) {
        console.error("Failed to parse WS message", err);
      }
    };

    ws.onclose = () => {
      updateTelemetry({ wsStatus: "disconnected" });
      pushLog("WS DISCONNECTED");

      const timeout = Math.min(1000 * Math.pow(2, reconnectCount.current), 10000);
      reconnectCount.current += 1;
      reconnectTimerRef.current = setTimeout(connect, timeout);
    };

    ws.onerror = () => {
      ws.close();
    };
  // onEvent is intentionally NOT a dependency — we use onEventRef instead
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [roomCode, applySocketEvent, updateTelemetry, pushLog]);

  useEffect(() => {
    connect();
    return () => {
      clearTimeout(reconnectTimerRef.current);
      if (socketRef.current) {
        socketRef.current.onclose = null; // prevent reconnect loop on unmount
        socketRef.current.close();
      }
    };
  }, [connect]);

  const publish = useCallback((type, payload = {}) => {
    if (socketRef.current?.readyState === 1) {
      socketRef.current.send(JSON.stringify({ type, ...payload }));
    }
  }, []);

  return { publish };
}
