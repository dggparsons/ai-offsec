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
        <p className="mt-2 text-sm text-neutral-500">
          Start the stack with <code>docker compose up --build</code>; the first
          ingestion cycle runs automatically once the worker boots.
        </p>
      </div>
    );
  }

  const actionItems = digest.top_events.filter((e) => e.priority_score >= 0.7);
  const material = digest.top_events.filter((e) => e.priority_score < 0.7);

  return (
    <div className="space-y-8">
      <section className="rounded-lg border border-neutral-800 bg-neutral-900 p-5">
        <h2 className="text-lg font-semibold text-neutral-100">
          Daily brief <span className="text-sm font-normal text-neutral-500">(last {digest.window_hours}h)</span>
        </h2>
        <p className="mt-1 text-sm text-neutral-400">
          <span className="text-red-300 font-medium">{digest.items_requiring_action} items require action</span>
          {" · "}{digest.material_developments} material developments
          {" · "}{digest.suppressed_low_priority} lower-priority updates suppressed
        </p>
        {digest.emerging_themes.length > 0 && (
          <div className="mt-3 flex flex-wrap gap-2">
            {digest.emerging_themes.slice(0, 8).map((t) => (
              <span key={t.label} className="rounded bg-neutral-800 px-2 py-1 text-xs text-neutral-300">
                {t.label} <span className="text-neutral-500">×{t.count}</span>
              </span>
            ))}
          </div>
        )}
      </section>

      <section>
        <h2 className="mb-3 text-lg font-semibold text-neutral-100">Priority now</h2>
        {actionItems.length === 0 ? (
          <p className="text-sm text-neutral-500">Nothing above the action threshold in this window.</p>
        ) : (
          <div className="grid gap-3">
            {actionItems.map((e) => <EventCard key={e.id} event={e} />)}
          </div>
        )}
      </section>

      <section>
        <h2 className="mb-3 text-lg font-semibold text-neutral-100">Material developments</h2>
        {material.length === 0 ? (
          <p className="text-sm text-neutral-500">No further material developments.</p>
        ) : (
          <div className="grid gap-3">
            {material.map((e) => <EventCard key={e.id} event={e} />)}
          </div>
        )}
      </section>
    </div>
  );
}
