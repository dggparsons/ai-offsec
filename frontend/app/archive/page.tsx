import Link from "next/link";
import { api } from "@/lib/api";
import { EventCard } from "@/components/EventCard";

export const dynamic = "force-dynamic";

export default async function ArchivePage({
  searchParams,
}: {
  searchParams: Promise<{ day?: string }>;
}) {
  const { day } = await searchParams;
  const history = await api.digestHistory().catch(() => []);
  const selected = day ? await api.digestDay(day).catch(() => null) : null;

  return (
    <div className="space-y-6">
      <h1 className="text-xl font-semibold text-neutral-100">Digest archive</h1>
      <p className="text-sm text-neutral-500">
        One snapshot per day (UTC). Today's digest is on the{" "}
        <Link href="/" className="text-sky-400 hover:underline">dashboard</Link>.
      </p>

      {history.length === 0 ? (
        <p className="text-sm text-neutral-500">
          No archived digests yet — the first snapshot is generated on the next daily run.
        </p>
      ) : (
        <div className="flex flex-wrap gap-2">
          {history.map((d) => (
            <Link
              key={d.day}
              href={`/archive?day=${d.day}`}
              className={`rounded border px-3 py-1.5 text-sm ${
                day === d.day
                  ? "border-sky-600 bg-sky-900/40 text-sky-200"
                  : "border-neutral-700 text-neutral-300 hover:border-neutral-500"
              }`}
            >
              {d.day}
            </Link>
          ))}
        </div>
      )}

      {selected?.content && (
        <div className="space-y-4">
          <h2 className="text-lg font-semibold text-neutral-100">
            {selected.day} — {selected.content.items_requiring_action} required action,{" "}
            {selected.content.material_developments} material
          </h2>
          <div className="grid gap-3">
            {selected.content.top_events.map((e) => (
              <EventCard key={e.id} event={e} />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
