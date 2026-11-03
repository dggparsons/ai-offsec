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

  return (
    <div className="space-y-6">
      <section className="rounded-lg border border-neutral-800 bg-neutral-900 p-5">
        <div className="flex items-baseline justify-between">
          <h2 className="text-lg font-semibold text-neutral-100">
            Today&apos;s ten{" "}
            <span className="text-sm font-normal text-neutral-500">
              {new Date(digest.generated_at).toLocaleDateString()}
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
          {" · "}{digest.suppressed_low_priority} lower-priority updates suppressed
        </p>
      </section>

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
                <EventCard event={e} />
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
