import { useEffect, useRef, useState } from "react";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from "recharts";

interface DataPoint {
  time: string;
  dome: number;
  mount: number;
}

interface AzimuthChartProps {
  domeAz: number;
  mountAz: number;
  timestamp: number;
}

const MAX_POINTS = 60; // 60 s at 1 Hz sampling

export function AzimuthChart({ domeAz, mountAz, timestamp }: AzimuthChartProps) {
  const [data, setData] = useState<DataPoint[]>([]);
  const lastTs = useRef<number>(0);

  useEffect(() => {
    if (timestamp === lastTs.current) return;
    lastTs.current = timestamp;
    const time = new Date(timestamp * 1000).toLocaleTimeString();
    setData((prev) => {
      const next = [...prev, { time, dome: domeAz, mount: mountAz }];
      return next.length > MAX_POINTS ? next.slice(-MAX_POINTS) : next;
    });
  }, [timestamp, domeAz, mountAz]);

  return (
    <div className="bg-card rounded-xl p-3">
      <div className="text-xs text-gray-400 mb-2 uppercase tracking-wide">
        Azimuth History (60 s)
      </div>
      <ResponsiveContainer width="100%" height={160}>
        <LineChart data={data} margin={{ top: 4, right: 4, bottom: 0, left: -20 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#1E293B" />
          <XAxis
            dataKey="time"
            tick={{ fill: "#6B7280", fontSize: 9 }}
            interval="preserveStartEnd"
          />
          <YAxis
            domain={[0, 360]}
            tick={{ fill: "#6B7280", fontSize: 9 }}
            tickCount={5}
          />
          <Tooltip
            contentStyle={{ background: "#141A22", border: "1px solid #1E293B", fontSize: 11 }}
            labelStyle={{ color: "#9CA3AF" }}
          />
          <Legend
            wrapperStyle={{ fontSize: 10, color: "#9CA3AF" }}
            iconType="plainline"
          />
          <Line
            type="monotone"
            dataKey="dome"
            stroke="#00B4D8"
            dot={false}
            strokeWidth={2}
            name="Dome"
            isAnimationActive={false}
          />
          <Line
            type="monotone"
            dataKey="mount"
            stroke="#FF3333"
            dot={false}
            strokeWidth={2}
            name="Mount"
            isAnimationActive={false}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
