import { useState } from "react";
import { cn } from "../lib/utils";
import { useArgusApi } from "../hooks/useArgusApi";

interface ControlPanelProps {
  mode: string;
  isSlaved: boolean;
  isParked: boolean;
  isSlewing: boolean;
}

export function ControlPanel({ mode, isSlaved, isParked, isSlewing }: ControlPanelProps) {
  const [targetAz, setTargetAz] = useState<string>("");
  const [loading, setLoading] = useState<Record<string, boolean>>({});
  const api = useArgusApi();

  async function withLoading(key: string, fn: () => Promise<unknown>) {
    setLoading((prev) => ({ ...prev, [key]: true }));
    try {
      await fn();
    } catch (err) {
      console.error(err);
    } finally {
      setLoading((prev) => ({ ...prev, [key]: false }));
    }
  }

  const handleGoTo = () => {
    const az = parseFloat(targetAz);
    if (isNaN(az)) return;
    withLoading("goto", () => api.moveDome(az));
  };

  const handleStop = () => withLoading("stop", () => api.stopDome());
  const handlePark = () => withLoading("park", () => api.parkDome());
  const handleHome = () => withLoading("home", () => api.homeDome());
  const handleModeToggle = () =>
    withLoading("mode", () =>
      api.setMode(mode === "MANUAL" ? "AUTO-SLAVE" : "MANUAL")
    );
  const handleSlavedToggle = () =>
    withLoading("slaved", () => api.setSlaved(!isSlaved));

  return (
    <div className="bg-card rounded-xl p-4 space-y-4">
      <h2 className="text-sm font-semibold text-gray-300 uppercase tracking-wide">Control</h2>

      {/* GoTo */}
      <div className="flex gap-2">
        <input
          type="number"
          min={0}
          max={360}
          step={0.1}
          value={targetAz}
          onChange={(e) => setTargetAz(e.target.value)}
          placeholder="Azimuth °"
          className="flex-1 bg-bg border border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-100 focus:outline-none focus:border-accent"
        />
        <button
          onClick={handleGoTo}
          disabled={loading["goto"] || isSlewing}
          className={cn(
            "px-4 py-2 rounded-lg text-sm font-semibold transition-colors",
            "bg-accent text-bg hover:bg-cyan-400 disabled:opacity-50"
          )}
        >
          {loading["goto"] ? "…" : "GoTo"}
        </button>
      </div>

      {/* STOP */}
      <button
        onClick={handleStop}
        disabled={loading["stop"]}
        className="w-full py-3 rounded-xl bg-danger text-white text-lg font-bold uppercase tracking-widest hover:bg-red-600 disabled:opacity-50 transition-colors"
      >
        {loading["stop"] ? "Stopping…" : "⬛ STOP"}
      </button>

      {/* Mode + Slaved toggles */}
      <div className="grid grid-cols-2 gap-2">
        <button
          onClick={handleModeToggle}
          disabled={loading["mode"]}
          className={cn(
            "py-2 rounded-lg text-sm font-semibold transition-colors",
            mode === "MANUAL"
              ? "bg-warning text-bg hover:bg-yellow-400"
              : "bg-accent text-bg hover:bg-cyan-400",
            "disabled:opacity-50"
          )}
        >
          {loading["mode"] ? "…" : mode === "MANUAL" ? "MANUAL" : "AUTO-SLAVE"}
        </button>
        <button
          onClick={handleSlavedToggle}
          disabled={loading["slaved"]}
          className={cn(
            "py-2 rounded-lg text-sm font-semibold transition-colors",
            isSlaved
              ? "bg-success text-bg hover:bg-green-400"
              : "bg-gray-700 text-gray-300 hover:bg-gray-600",
            "disabled:opacity-50"
          )}
        >
          {loading["slaved"] ? "…" : isSlaved ? "Slaved ON" : "Slaved OFF"}
        </button>
      </div>

      {/* Park + Home */}
      <div className="grid grid-cols-2 gap-2">
        <button
          onClick={handlePark}
          disabled={loading["park"] || isParked}
          className="py-2 rounded-lg text-sm font-semibold bg-gray-700 text-gray-200 hover:bg-gray-600 disabled:opacity-50 transition-colors"
        >
          {loading["park"] ? "…" : isParked ? "Parked" : "Park"}
        </button>
        <button
          onClick={handleHome}
          disabled={loading["home"]}
          className="py-2 rounded-lg text-sm font-semibold bg-gray-700 text-gray-200 hover:bg-gray-600 disabled:opacity-50 transition-colors"
        >
          {loading["home"] ? "…" : "Home"}
        </button>
      </div>
    </div>
  );
}
