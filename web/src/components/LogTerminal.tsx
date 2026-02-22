import { useEffect, useRef } from "react";

interface LogTerminalProps {
  messages: string[];
}

function lineColor(msg: string): string {
  const upper = msg.toUpperCase();
  if (upper.includes("[ERROR]") || upper.includes("ERROR")) return "text-danger";
  if (upper.includes("[WARNING]") || upper.includes("WARNING") || upper.includes("WARN"))
    return "text-warning";
  if (upper.includes("[INFO]")) return "text-green-400";
  return "text-gray-400";
}

export function LogTerminal({ messages }: LogTerminalProps) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  return (
    <div className="bg-[#090C0F] border border-gray-800 rounded-xl p-3 h-48 overflow-y-auto font-mono text-xs">
      {messages.length === 0 ? (
        <span className="text-gray-600">No log messages yet…</span>
      ) : (
        messages.map((msg, i) => (
          <div key={i} className={lineColor(msg)}>
            {msg}
          </div>
        ))
      )}
      <div ref={bottomRef} />
    </div>
  );
}
