import { api } from "@/lib/api";
import { EventCard } from "@/components/EventCard";

export const dynamic = "force-dynamic";

export default async function EventsPage({
  searchParams,
}: {
  searchParams: Promise<{ taxonomy?: string; min_priority?: string; order?: string }>;
}) {
  const params = await searchParams;
  const qs = new URLSearchParams();
  if (params.taxonomy) qs.set("taxonomy", params.taxonomy);
  if (params.min_priority) qs.set("min_priority", params.min_priority);
  if (params.order) qs.set("order", params.order);
  qs.set("limit", "50");

  const events = await api.events(`?${qs.toString()}`).catch(() => []);

  return (
    <div>
      <h1 className="mb-4 text-xl font-semibold text-neutral-100">Events</h1>
      <form className="mb-4 flex gap-2 text-sm" action="/events" method="get">
        <input
          name="taxonomy"
          placeholder="taxonomy (e.g. offsec.vulnerability)"
          defaultValue={params.taxonomy ?? ""}
          className="rounded border border-neutral-700 bg-neutral-900 px-3 py-1.5 text-neutral-200 w-72"
        />
        <input
          name="min_priority"
          placeholder="min priority (0-1)"
          defaultValue={params.min_priority ?? ""}
          className="rounded border border-neutral-700 bg-neutral-900 px-3 py-1.5 text-neutral-200 w-40"
        />
        <button className="rounded bg-sky-700 px-3 py-1.5 text-neutral-50 hover:bg-sky-600">
          Filter
        </button>
      </form>
      {events.length === 0 ? (
        <p className="text-sm text-neutral-500">No events yet. The worker ingests due sources every minute.</p>
      ) : (
        <div className="grid gap-3">
          {events.map((e) => <EventCard key={e.id} event={e} />)}
        </div>
      )}
    </div>
  );
}
