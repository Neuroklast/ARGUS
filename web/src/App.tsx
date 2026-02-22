import { useEffect, useState } from "react";
import { useArgusSocket } from "./hooks/useArgusSocket";
import { DomeRadar } from "./components/DomeRadar";
import { AzimuthGauge } from "./components/AzimuthGauge";
import { ControlPanel } from "./components/ControlPanel";
import { StatusBar } from "./components/StatusBar";
import { LogTerminal } from "./components/LogTerminal";
import { CameraFeed } from "./components/CameraFeed";
import { AzimuthChart } from "./components/AzimuthChart";
import { SettingsPanel } from "./components/SettingsPanel";
import { SafetyIndicator } from "./components/SafetyIndicator";

type Tab = "dashboard" | "camera" | "settings" | "log";

export default function App() {
  const { state, connected } = useArgusSocket();
  const [tab, setTab] = useState<Tab>("dashboard");
  const [config, setConfig] = useState<Record<string, unknown>>({});

  useEffect(() => {
    fetch("/api/config")
      .then((r) => r.json())
      .then((data: Record<string, unknown>) => setConfig(data))
      .catch(() => {});
  }, []);

  const safety = (config["safety"] as Record<string, unknown>) ?? {};
  const dome = (config["dome"] as Record<string, unknown>) ?? {};

  const tabs: { id: Tab; label: string }[] = [
    { id: "dashboard", label: "Dashboard" },
    { id: "camera", label: "Kamera" },
    { id: "settings", label: "Einstellungen" },
    { id: "log", label: "Log" },
  ];

  return (
    <div className="min-h-screen bg-bg text-gray-100 flex flex-col">
      {/* Header */}
      <header className="flex items-center justify-between px-6 py-3 border-b border-gray-800 bg-card shrink-0">
        <div className="flex items-center gap-3">
          <span className="text-accent text-xl font-bold font-mono tracking-widest">
            ARGUS
          </span>
          <span className="text-gray-500 text-xs hidden sm:block">
            Advanced Rotation Guidance Using Sensors
          </span>
        </div>
        <div className="flex items-center gap-2">
          <span
            className={`w-2 h-2 rounded-full ${
              connected ? "bg-success animate-pulse" : "bg-danger"
            }`}
          />
          <span className={`text-xs ${connected ? "text-success" : "text-danger"}`}>
            {connected ? "Connected" : "Reconnecting…"}
          </span>
        </div>
      </header>

      {/* Safety banner */}
      {state.safety_warning && (
        <div className="bg-red-900/50 border-b border-danger px-6 py-2 text-danger text-sm flex items-center gap-2">
          <span>⚠</span>
          <span>{state.safety_warning}</span>
        </div>
      )}

      {/* Tab bar */}
      <nav className="flex gap-1 px-6 pt-3 pb-0 border-b border-gray-800">
        {tabs.map((t) => (
          <button
            key={t.id}
            onClick={() => setTab(t.id)}
            className={`px-4 py-2 text-sm font-medium rounded-t-lg transition-colors -mb-px border-b-2 ${
              tab === t.id
                ? "border-accent text-accent bg-card"
                : "border-transparent text-gray-400 hover:text-gray-200"
            }`}
          >
            {t.label}
          </button>
        ))}
      </nav>

      {/* Content */}
      <main className="flex-1 overflow-auto p-4">
        {tab === "dashboard" && (
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
            {/* Left column */}
            <div className="space-y-4">
              <div className="bg-card rounded-xl p-4">
                <div className="text-xs text-gray-400 uppercase tracking-wide mb-2">
                  Dome Radar
                </div>
                <DomeRadar domeAz={state.dome_az} mountAz={state.mount_az} />
              </div>
              <AzimuthGauge domeAz={state.dome_az} mountAz={state.mount_az} />
              <SafetyIndicator
                telescopeProtrudes={Boolean(safety["telescope_protrudes"])}
                safetyWarning={state.safety_warning}
                domeAzMin={Number(dome["az_min"] ?? 0)}
                domeAzMax={Number(dome["az_max"] ?? 360)}
                domeAz={state.dome_az}
              />
            </div>

            {/* Middle column */}
            <div className="space-y-4">
              <StatusBar
                connected={connected}
                hwConnected={state.hardware_connected}
                ascomConnected={state.ascom_connected}
                visionActive={state.vision_active}
                mode={state.mode}
                isParked={state.is_parked}
                safetyWarning={state.safety_warning}
              />
              <ControlPanel
                mode={state.mode}
                isSlaved={state.is_slaved}
                isParked={state.is_parked}
                isSlewing={state.is_slewing}
              />
              <AzimuthChart
                domeAz={state.dome_az}
                mountAz={state.mount_az}
                timestamp={state.timestamp}
              />
            </div>

            {/* Right column */}
            <div className="space-y-4">
              <CameraFeed
                visionActive={state.vision_active}
                markerFound={state.vision_marker_found}
              />
              <div className="bg-card rounded-xl p-3">
                <div className="text-xs text-gray-400 uppercase tracking-wide mb-2">
                  Telemetry
                </div>
                <div className="grid grid-cols-2 gap-2 text-xs font-mono">
                  <TelRow label="RA" value={state.mount_ra.toFixed(4) + " h"} />
                  <TelRow label="Dec" value={state.mount_dec.toFixed(2) + "°"} />
                  <TelRow label="Alt" value={state.mount_alt.toFixed(1) + "°"} />
                  <TelRow label="Drift" value={state.drift_correction.toFixed(2) + "°"} />
                </div>
              </div>
              <LogTerminal messages={state.log_messages} />
            </div>
          </div>
        )}

        {tab === "camera" && (
          <div className="max-w-2xl mx-auto space-y-4">
            <CameraFeed
              visionActive={state.vision_active}
              markerFound={state.vision_marker_found}
            />
          </div>
        )}

        {tab === "settings" && (
          <div className="max-w-2xl mx-auto">
            <SettingsPanel config={config} />
          </div>
        )}

        {tab === "log" && (
          <div className="max-w-4xl mx-auto">
            <div className="bg-[#090C0F] border border-gray-800 rounded-xl p-4 font-mono text-xs space-y-0.5 h-[70vh] overflow-y-auto">
              {state.log_messages.map((msg, i) => {
                const upper = msg.toUpperCase();
                const color = upper.includes("[ERROR]")
                  ? "text-danger"
                  : upper.includes("[WARNING]")
                    ? "text-warning"
                    : upper.includes("[INFO]")
                      ? "text-green-400"
                      : "text-gray-400";
                return (
                  <div key={i} className={color}>
                    {msg}
                  </div>
                );
              })}
            </div>
          </div>
        )}
      </main>
    </div>
  );
}

function TelRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex justify-between">
      <span className="text-gray-500">{label}</span>
      <span className="text-gray-200">{value}</span>
    </div>
  );
}
