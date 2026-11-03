import Link from "next/link";
import { api } from "@/lib/api";
import { EventCard } from "@/components/EventCard";

export const dynamic = "force-dynamic";

export default async function Dashboard() {
  let digest;
  let error: string | null = null;
  try {
    digest = await api.digest();
  } catch (e) {
    error = e instanceof Error ? e.message : "API unreachable";
  }

  if (error || !digest) {
    return (
      <div className="rounded-lg border border-red-900 bg-red-950/40 p-6">
        <h2 className="font-semibold text-red-300">Backend unavailable</h2>
        <p className="mt-1 text-sm text-neutral-400">{error}</p>
      </div>
    );
  }

  // Section title per event id, from the digest's section buckets.
  const sectionTitles: Record<string, string> = {
    mcp: "MCP & agent plumbing",
    safety: "Safety, jailbreaks & evals",
    models: "Models & inference",
    research: "Research & papers",
    exploitation: "Exploitation",
    enterprise: "Enterprise adoption",
  };
  const sectionOf = new Map<string, string>();
  for (const [key, events] of Object.entries(digest.sections)) {
    const title = sectionTitles[key];
    if (title) for (const e of events) sectionOf.set(e.id, title);
  }

  return (
    <div className="space-y-6">
      <section className="rounded-lg border border-neutral-800 bg-neutral-900 p-5">
        <div className="flex items-baseline justify-between">
          <h2 className="text-lg font-semibold text-neutral-100">
            Today&apos;s ten{" "}
            <span className="text-sm font-normal text-neutral-500">
              {new Date(digest.generated_at).toLocaleDateString("en-GB")}
            </span>
          </h2>
          <Link href="/archive" className="text-sm text-sky-400 hover:underline">
            Archive →
          </Link>
        </div>
        <p className="mt-1 text-sm text-neutral-400">
          <span className="text-red-300 font-medium">
            {digest.items_requiring_action} require action
          </span>
          {" · "}{digest.material_developments} material developments
          {" · "}{digest.eligible_not_shown} eligible not shown
          {" · "}{digest.suppressed_low_priority} suppressed below the bar
        </p>
      </section>

      {digest.emerging_themes.length > 0 && (
        <section className="rounded-lg border border-neutral-800 bg-neutral-900 p-4">
          <h2 className="mb-2 text-sm font-semibold uppercase tracking-wide text-neutral-500">
            Emerging themes
          </h2>
          <div className="flex flex-wrap gap-1.5">
            {digest.emerging_themes.map((t) => (
              <span
                key={t.label}
                className="rounded bg-neutral-800 px-2 py-0.5 text-xs text-neutral-300"
              >
                {t.label} <span className="text-neutral-500">×{t.count}</span>
              </span>
            ))}
          </div>
        </section>
      )}

      {digest.top_events.length === 0 ? (
        <p className="text-sm text-neutral-500">Nothing cleared the bar today.</p>
      ) : (
        <div className="grid gap-3">
          {digest.top_events.map((e, i) => (
            <div key={e.id} className="flex gap-3 items-start">
              <span className="mt-4 w-6 shrink-0 text-right font-mono text-lg text-neutral-600">
                {i + 1}
              </span>
              <div className="min-w-0 flex-1">
                {sectionOf.get(e.id) && (
                  <div className="mb-1 text-[11px] uppercase tracking-wide text-neutral-500">
                    {sectionOf.get(e.id)}
                  </div>
                )}
                <EventCard event={e} />
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
