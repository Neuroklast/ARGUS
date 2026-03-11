import { cn } from "../lib/utils";

interface StatusBarProps {
  connected: boolean;
  hwConnected: boolean;
  ascomConnected: boolean;
  visionActive: boolean;
  mode: string;
  isParked: boolean;
  safetyWarning: string | null;
}

function Badge({
  label,
  ok,
}: {
  label: string;
  ok: boolean;
}) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium",
        ok ? "bg-green-900/50 text-success" : "bg-red-900/50 text-danger"
      )}
    >
      <span
        className={cn(
          "w-1.5 h-1.5 rounded-full",
          ok ? "bg-success" : "bg-danger"
        )}
      />
      {label}
    </span>
  );
}

export function StatusBar({
  connected,
  hwConnected,
  ascomConnected,
  visionActive,
  mode,
  isParked,
  safetyWarning,
}: StatusBarProps) {
  const modeColor =
    isParked
      ? "bg-gray-700 text-gray-300"
      : mode === "AUTO-SLAVE" || mode === "AUTO"
        ? "bg-cyan-900/50 text-accent"
        : "bg-yellow-900/50 text-warning";

  return (
    <div className="space-y-2">
      <div className="flex flex-wrap items-center gap-2">
        {/* WS indicator */}
        <span className="flex items-center gap-1 text-xs">
          <span
            className={cn(
              "w-2 h-2 rounded-full",
              connected ? "bg-success animate-pulse" : "bg-danger"
            )}
          />
          <span className={connected ? "text-success" : "text-danger"}>
            {connected ? "Live" : "Disconnected"}
          </span>
        </span>

        <Badge label="Serial" ok={hwConnected} />
        <Badge label="ASCOM" ok={ascomConnected} />
        <Badge label="Vision" ok={visionActive} />

        <span
          className={cn(
            "inline-flex px-2 py-0.5 rounded-full text-xs font-semibold",
            modeColor
          )}
        >
          {isParked ? "PARKED" : mode}
        </span>
      </div>

      {safetyWarning && (
        <div className="flex items-center gap-2 px-3 py-2 bg-red-900/40 border border-danger rounded-lg text-sm text-danger">
          <span>⚠</span>
          {safetyWarning}
        </div>
      )}
    </div>
  );
}
