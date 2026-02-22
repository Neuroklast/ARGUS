const getToken = (): string =>
  (window as unknown as Record<string, string>).__ARGUS_TOKEN__ ?? "";

function headers(): Record<string, string> {
  const token = getToken();
  const h: Record<string, string> = { "Content-Type": "application/json" };
  if (token) h["X-API-Token"] = token;
  return h;
}

async function apiFetch(path: string, options?: RequestInit): Promise<unknown> {
  const res = await fetch(path, { headers: headers(), ...options });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`API error ${res.status}: ${text}`);
  }
  return res.json();
}

export function useArgusApi() {
  const moveDome = (azimuth: number) =>
    apiFetch("/api/move", {
      method: "POST",
      body: JSON.stringify({ azimuth }),
    });

  const stopDome = () => apiFetch("/api/stop", { method: "POST" });

  const parkDome = () => apiFetch("/api/park", { method: "POST" });

  const homeDome = () => apiFetch("/api/home", { method: "POST" });

  const setMode = (mode: "MANUAL" | "AUTO" | "AUTO-SLAVE") =>
    apiFetch("/api/mode", { method: "POST", body: JSON.stringify({ mode }) });

  const setSlaved = (slaved: boolean) =>
    apiFetch("/api/slaved", {
      method: "POST",
      body: JSON.stringify({ slaved }),
    });

  const updateConfig = (config: object) =>
    apiFetch("/api/config", {
      method: "POST",
      body: JSON.stringify(config),
    });

  return {
    moveDome,
    stopDome,
    parkDome,
    homeDome,
    setMode,
    setSlaved,
    updateConfig,
  };
}
