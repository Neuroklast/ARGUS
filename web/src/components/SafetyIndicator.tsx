interface SafetyIndicatorProps {
  telescopeProtrudes: boolean;
  safetyWarning: string | null;
  domeAzMin: number;
  domeAzMax: number;
  domeAz: number;
}

export function SafetyIndicator({
  telescopeProtrudes,
  safetyWarning,
  domeAzMin,
  domeAzMax,
  domeAz,
}: SafetyIndicatorProps) {
  const nearMin = domeAzMin > 0 && domeAz - domeAzMin < 5;
  const nearMax = domeAzMax < 360 && domeAzMax - domeAz < 5;

  if (!telescopeProtrudes && !safetyWarning && !nearMin && !nearMax) return null;

  return (
    <div className="space-y-1">
      {safetyWarning && (
        <div className="flex items-center gap-2 px-3 py-2 bg-red-900/30 border border-danger rounded-lg text-xs text-danger">
          ⚠ {safetyWarning}
        </div>
      )}
      {telescopeProtrudes && (
        <div className="flex items-center gap-2 px-3 py-2 bg-yellow-900/30 border border-warning rounded-lg text-xs text-warning">
          ⚠ Telescope protrudes – collision risk during dome rotation
        </div>
      )}
      {(nearMin || nearMax) && (
        <div className="flex items-center gap-2 px-3 py-2 bg-yellow-900/30 border border-warning rounded-lg text-xs text-warning">
          ⚠ Near azimuth limit ({nearMin ? `min ${domeAzMin}°` : `max ${domeAzMax}°`}) – cable-wrap protection active
        </div>
      )}
    </div>
  );
}
