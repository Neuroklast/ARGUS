import { useEffect, useState } from "react";

interface CameraFeedProps {
  visionActive: boolean;
  markerFound: boolean;
}

interface CameraOption {
  index: number;
  name: string;
}

export function CameraFeed({ visionActive, markerFound }: CameraFeedProps) {
  const [cameras, setCameras] = useState<CameraOption[]>([]);
  const [selectedIndex, setSelectedIndex] = useState<number>(0);
  const [imgError, setImgError] = useState(false);

  useEffect(() => {
    fetch("/api/cameras")
      .then((r) => r.json())
      .then((data: CameraOption[]) => {
        setCameras(data);
        if (data.length > 0) setSelectedIndex(data[0].index);
      })
      .catch(() => {});
  }, []);

  return (
    <div className="bg-card rounded-xl overflow-hidden">
      {/* Camera selector */}
      {cameras.length > 1 && (
        <div className="px-3 pt-2">
          <select
            value={selectedIndex}
            onChange={(e) => {
              setSelectedIndex(Number(e.target.value));
              setImgError(false);
            }}
            className="w-full bg-bg border border-gray-700 rounded text-xs text-gray-300 px-2 py-1 focus:outline-none"
          >
            {cameras.map((c) => (
              <option key={c.index} value={c.index}>
                {c.name}
              </option>
            ))}
          </select>
        </div>
      )}

      {/* Feed */}
      <div className="relative">
        {!visionActive || imgError ? (
          <div className="flex items-center justify-center bg-[#090C0F] h-40 text-gray-600 text-sm">
            📷 Camera unavailable
          </div>
        ) : (
          <img
            src={`/api/video_feed?cam=${selectedIndex}`}
            alt="Camera feed"
            className="w-full"
            onError={() => setImgError(true)}
          />
        )}

        {/* Overlay */}
        <div className="absolute top-2 left-2 flex gap-1">
          <span
            className={`px-1.5 py-0.5 rounded text-xs font-mono ${
              markerFound
                ? "bg-green-900/70 text-success"
                : "bg-red-900/70 text-danger"
            }`}
          >
            {markerFound ? "● MARKER" : "○ NO MARKER"}
          </span>
        </div>
      </div>
    </div>
  );
}
