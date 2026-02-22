import { useEffect, useState } from "react";
import { useArgusApi } from "../hooks/useArgusApi";

interface SettingsPanelProps {
  config: Record<string, unknown>;
}

type Tab = "hardware" | "vision" | "ascom" | "safety" | "web";

export function SettingsPanel({ config }: SettingsPanelProps) {
  const [tab, setTab] = useState<Tab>("hardware");
  const [draft, setDraft] = useState<Record<string, unknown>>(config);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const api = useArgusApi();

  useEffect(() => {
    setDraft(config);
  }, [config]);

  const tabs: { id: Tab; label: string }[] = [
    { id: "hardware", label: "Hardware" },
    { id: "vision", label: "Vision" },
    { id: "ascom", label: "ASCOM" },
    { id: "safety", label: "Safety" },
    { id: "web", label: "Web Server" },
  ];

  function setNested(section: string, key: string, value: unknown) {
    setDraft((prev) => ({
      ...prev,
      [section]: {
        ...(prev[section] as Record<string, unknown>),
        [key]: value,
      },
    }));
  }

  async function handleSave() {
    setSaving(true);
    try {
      await api.updateConfig(draft);
      setSaved(true);
      setTimeout(() => setSaved(false), 2000);
    } catch (err) {
      console.error(err);
    } finally {
      setSaving(false);
    }
  }

  const hw = (draft["hardware"] as Record<string, unknown>) ?? {};
  const vis = (draft["vision"] as Record<string, unknown>) ?? {};
  const ascom = (draft["ascom"] as Record<string, unknown>) ?? {};
  const safety = (draft["safety"] as Record<string, unknown>) ?? {};
  const web = (draft["web"] as Record<string, unknown>) ?? {};

  return (
    <div className="bg-card rounded-xl p-4 space-y-4">
      <div className="flex gap-1 flex-wrap">
        {tabs.map((t) => (
          <button
            key={t.id}
            onClick={() => setTab(t.id)}
            className={`px-3 py-1 rounded text-xs font-semibold transition-colors ${
              tab === t.id
                ? "bg-accent text-bg"
                : "bg-gray-700 text-gray-300 hover:bg-gray-600"
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      <div className="space-y-3 text-sm">
        {tab === "hardware" && (
          <>
            <Field
              label="Serial Port"
              value={String(hw["serial_port"] ?? "COM3")}
              onChange={(v) => setNested("hardware", "serial_port", v)}
            />
            <Field
              label="Baud Rate"
              value={String(hw["baud_rate"] ?? 9600)}
              onChange={(v) => setNested("hardware", "baud_rate", Number(v))}
              type="number"
            />
            <Field
              label="Motor Type"
              value={String(hw["motor_type"] ?? "stepper")}
              onChange={(v) => setNested("hardware", "motor_type", v)}
            />
          </>
        )}

        {tab === "vision" && (
          <>
            <Field
              label="Camera Index"
              value={String(vis["camera_index"] ?? 0)}
              onChange={(v) => setNested("vision", "camera_index", Number(v))}
              type="number"
            />
          </>
        )}

        {tab === "ascom" && (
          <>
            <Field
              label="Telescope ProgID"
              value={String(ascom["telescope_prog_id"] ?? "")}
              onChange={(v) => setNested("ascom", "telescope_prog_id", v)}
            />
            <Field
              label="Poll Interval (s)"
              value={String(ascom["poll_interval"] ?? 1.0)}
              onChange={(v) => setNested("ascom", "poll_interval", Number(v))}
              type="number"
            />
          </>
        )}

        {tab === "safety" && (
          <>
            <BoolField
              label="Telescope Protrudes"
              value={Boolean(safety["telescope_protrudes"])}
              onChange={(v) => setNested("safety", "telescope_protrudes", v)}
            />
            <Field
              label="Safe Altitude (°)"
              value={String(safety["safe_altitude"] ?? 90.0)}
              onChange={(v) => setNested("safety", "safe_altitude", Number(v))}
              type="number"
            />
            <Field
              label="Max Nudge While Protruding (°)"
              value={String(safety["max_nudge_while_protruding"] ?? 2.0)}
              onChange={(v) =>
                setNested("safety", "max_nudge_while_protruding", Number(v))
              }
              type="number"
            />
          </>
        )}

        {tab === "web" && (
          <>
            <Field
              label="Host"
              value={String(web["host"] ?? "0.0.0.0")}
              onChange={(v) => setNested("web", "host", v)}
            />
            <Field
              label="Port"
              value={String(web["port"] ?? 7373)}
              onChange={(v) => setNested("web", "port", Number(v))}
              type="number"
            />
            <Field
              label="API Token"
              value={String(web["token"] ?? "")}
              onChange={(v) => setNested("web", "token", v)}
            />
          </>
        )}
      </div>

      <div className="flex items-center gap-3">
        <button
          onClick={handleSave}
          disabled={saving}
          className="px-4 py-2 bg-accent text-bg rounded-lg text-sm font-semibold hover:bg-cyan-400 disabled:opacity-50 transition-colors"
        >
          {saving ? "Saving…" : saved ? "✓ Saved" : "Save"}
        </button>
        <span className="text-xs text-gray-500">
          Hardware changes require restart
        </span>
      </div>
    </div>
  );
}

function Field({
  label,
  value,
  onChange,
  type = "text",
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  type?: string;
}) {
  return (
    <div className="flex items-center gap-3">
      <label className="w-44 text-gray-400 text-xs shrink-0">{label}</label>
      <input
        type={type}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="flex-1 bg-bg border border-gray-700 rounded px-2 py-1 text-xs text-gray-100 focus:outline-none focus:border-accent"
      />
    </div>
  );
}

function BoolField({
  label,
  value,
  onChange,
}: {
  label: string;
  value: boolean;
  onChange: (v: boolean) => void;
}) {
  return (
    <div className="flex items-center gap-3">
      <label className="w-44 text-gray-400 text-xs shrink-0">{label}</label>
      <input
        type="checkbox"
        checked={value}
        onChange={(e) => onChange(e.target.checked)}
        className="accent-accent"
      />
    </div>
  );
}
