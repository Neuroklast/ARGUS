import { cn } from "../lib/utils";

interface AzimuthGaugeProps {
  domeAz: number;
  mountAz: number;
}

function fmt(v: number): string {
  return v.toFixed(1) + "°";
}

export function AzimuthGauge({ domeAz, mountAz }: AzimuthGaugeProps) {
  let diff = mountAz - domeAz;
  if (diff > 180) diff -= 360;
  if (diff < -180) diff += 360;
  const absDiff = Math.abs(diff);

  const diffColor =
    absDiff > 5
      ? "text-danger"
      : absDiff > 2
        ? "text-warning"
        : "text-success";

  return (
    <div className="grid grid-cols-3 gap-2 text-center">
      <div className="bg-card rounded-lg p-3">
        <div className="text-xs text-gray-400 mb-1">Dome</div>
        <div className="text-accent text-2xl font-mono font-bold">{fmt(domeAz)}</div>
      </div>
      <div className="bg-card rounded-lg p-3">
        <div className="text-xs text-gray-400 mb-1">Δ Error</div>
        <div className={cn("text-2xl font-mono font-bold", diffColor)}>
          {fmt(diff)}
        </div>
      </div>
      <div className="bg-card rounded-lg p-3">
        <div className="text-xs text-gray-400 mb-1">Mount</div>
        <div className="text-red-400 text-2xl font-mono font-bold">{fmt(mountAz)}</div>
      </div>
    </div>
  );
}
