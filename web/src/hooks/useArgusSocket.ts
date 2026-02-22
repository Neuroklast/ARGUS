import { useEffect, useRef, useState } from "react";

export interface ArgusState {
  dome_az: number;
  mount_az: number;
  mount_alt: number;
  mount_ra: number;
  mount_dec: number;
  mode: string;
  is_slewing: boolean;
  is_parked: boolean;
  is_slaved: boolean;
  hardware_connected: boolean;
  ascom_connected: boolean;
  vision_active: boolean;
  vision_marker_found: boolean;
  drift_correction: number;
  safety_warning: string | null;
  log_messages: string[];
  timestamp: number;
}

const DEFAULT_STATE: ArgusState = {
  dome_az: 0,
  mount_az: 0,
  mount_alt: 0,
  mount_ra: 0,
  mount_dec: 0,
  mode: "MANUAL",
  is_slewing: false,
  is_parked: false,
  is_slaved: false,
  hardware_connected: false,
  ascom_connected: false,
  vision_active: false,
  vision_marker_found: false,
  drift_correction: 0,
  safety_warning: null,
  log_messages: [],
  timestamp: 0,
};

function getWsUrl(): string {
  const proto = window.location.protocol === "https:" ? "wss" : "ws";
  return `${proto}://${window.location.host}/ws`;
}

export function useArgusSocket() {
  const [state, setState] = useState<ArgusState>(DEFAULT_STATE);
  const [connected, setConnected] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);
  const retryDelayRef = useRef(1000);
  const mountedRef = useRef(true);

  useEffect(() => {
    mountedRef.current = true;

    function connect() {
      if (!mountedRef.current) return;
      const url = getWsUrl();
      const ws = new WebSocket(url);
      wsRef.current = ws;

      ws.onopen = () => {
        if (!mountedRef.current) return;
        setConnected(true);
        retryDelayRef.current = 1000;
      };

      ws.onmessage = (ev) => {
        if (!mountedRef.current) return;
        try {
          const data = JSON.parse(ev.data) as ArgusState;
          setState(data);
        } catch {
          // ignore parse errors
        }
      };

      ws.onclose = () => {
        if (!mountedRef.current) return;
        setConnected(false);
        // Exponential backoff reconnect (max 30 s)
        const delay = Math.min(retryDelayRef.current, 30000);
        retryDelayRef.current = delay * 2;
        setTimeout(connect, delay);
      };

      ws.onerror = () => {
        ws.close();
      };
    }

    connect();

    return () => {
      mountedRef.current = false;
      wsRef.current?.close();
    };
  }, []);

  return { state, connected };
}
