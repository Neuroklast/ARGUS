interface DomeRadarProps {
  domeAz: number;
  mountAz: number;
}

function azToXY(az: number, r: number): { x: number; y: number } {
  const rad = ((az - 90) * Math.PI) / 180;
  return { x: 100 + r * Math.cos(rad), y: 100 + r * Math.sin(rad) };
}

export function DomeRadar({ domeAz, mountAz }: DomeRadarProps) {
  const domePos = azToXY(domeAz, 75);
  const mountPos = azToXY(mountAz, 75);

  return (
    <svg
      viewBox="0 0 200 200"
      className="w-full max-w-[240px] mx-auto"
      aria-label="Dome radar"
    >
      {/* Background */}
      <circle cx="100" cy="100" r="95" fill="#0B0E11" stroke="#1E293B" strokeWidth="1" />

      {/* Concentric rings */}
      {[25, 50, 75].map((r) => (
        <circle
          key={r}
          cx="100"
          cy="100"
          r={r}
          fill="none"
          stroke="#1E293B"
          strokeWidth="0.5"
        />
      ))}

      {/* Cardinal labels */}
      <text x="100" y="14" textAnchor="middle" fill="#6B7280" fontSize="10">N</text>
      <text x="186" y="104" textAnchor="middle" fill="#6B7280" fontSize="10">E</text>
      <text x="100" y="194" textAnchor="middle" fill="#6B7280" fontSize="10">S</text>
      <text x="14" y="104" textAnchor="middle" fill="#6B7280" fontSize="10">W</text>

      {/* Crosshairs */}
      <line x1="100" y1="8" x2="100" y2="192" stroke="#1E293B" strokeWidth="0.5" />
      <line x1="8" y1="100" x2="192" y2="100" stroke="#1E293B" strokeWidth="0.5" />

      {/* Mount pointer (red) */}
      <line
        x1="100"
        y1="100"
        x2={mountPos.x}
        y2={mountPos.y}
        stroke="#FF3333"
        strokeWidth="2"
        strokeLinecap="round"
        style={{ transition: "all 0.3s ease" }}
      />
      <circle cx={mountPos.x} cy={mountPos.y} r="4" fill="#FF3333" />

      {/* Dome pointer (cyan) */}
      <line
        x1="100"
        y1="100"
        x2={domePos.x}
        y2={domePos.y}
        stroke="#00B4D8"
        strokeWidth="2.5"
        strokeLinecap="round"
        style={{ transition: "all 0.3s ease" }}
      />
      <circle cx={domePos.x} cy={domePos.y} r="5" fill="#00B4D8" />

      {/* Center dot */}
      <circle cx="100" cy="100" r="3" fill="#6B7280" />

      {/* Legend */}
      <circle cx="16" cy="176" r="4" fill="#00B4D8" />
      <text x="24" y="180" fill="#9CA3AF" fontSize="8">Dome</text>
      <circle cx="16" cy="188" r="4" fill="#FF3333" />
      <text x="24" y="192" fill="#9CA3AF" fontSize="8">Mount</text>
    </svg>
  );
}
