"use client";

import { useState } from "react";
import { API_BASE } from "@/lib/api";

const ACTIONS = [
  { action: "important", label: "Important", cls: "bg-emerald-800 hover:bg-emerald-700" },
  { action: "save", label: "Save", cls: "bg-sky-800 hover:bg-sky-700" },
  { action: "escalate", label: "Escalate", cls: "bg-orange-800 hover:bg-orange-700" },
  { action: "dismiss", label: "Dismiss", cls: "bg-neutral-800 hover:bg-neutral-700" },
];

export function FeedbackButtons({ eventId }: { eventId: string }) {
  const [done, setDone] = useState<string | null>(null);
  const [failed, setFailed] = useState(false);

  // Public read-only deployments (e.g. ai-offsec.com) don't accept writes.
  if (process.env.NEXT_PUBLIC_READ_ONLY === "true") return null;

  async function submit(action: string) {
    setFailed(false);
    const res = await fetch(`${API_BASE}/api/feedback`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ event_id: eventId, action }),
    });
    // Never show a tick for a write the API rejected (e.g. 403 write guard).
    if (!res.ok) {
      setFailed(true);
      return;
    }
    setDone(action);
  }

  return (
    <section>
      <h2 className="mb-2 text-sm font-semibold uppercase tracking-wide text-neutral-500">
        Analyst action
      </h2>
      <div className="flex gap-2">
        {ACTIONS.map(({ action, label, cls }) => (
          <button
            key={action}
            onClick={() => submit(action)}
            disabled={done !== null}
            className={`rounded px-3 py-1.5 text-sm text-neutral-50 disabled:opacity-40 ${cls}`}
          >
            {done === action ? `${label} ✓` : label}
          </button>
        ))}
      </div>
      <p className="mt-2 text-xs text-neutral-600">
        {failed ? (
          <span className="text-red-400">Not recorded — the API rejected the write.</span>
        ) : (
          "Feedback trains the relevance model — it never alters the source record."
        )}
      </p>
    </section>
  );
}
