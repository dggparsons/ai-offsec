import Link from "next/link";
import { api } from "@/lib/api";
import { EventCard } from "@/components/EventCard";

export const dynamic = "force-dynamic";

const SECTION_ORDER: [string, string][] = [
  ["mcp", "MCP & agent plumbing"],
  ["models", "Models & inference"],
  ["research", "Research & papers"],
  ["exploitation", "Exploitation"],
  ["enterprise", "Enterprise adoption"],
];

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
    <div className="space-y-8">
      <section className="rounded-lg border border-neutral-800 bg-neutral-900 p-5">
        <div className="flex items-baseline justify-between">
          <h2 className="text-lg font-semibold text-neutral-100">
            Daily brief{" "}
            <span className="text-sm font-normal text-neutral-500">
              generated {new Date(digest.generated_at).toLocaleString()}
            </span>
          </h2>
          <Link href="/archive" className="text-sm text-sky-400 hover:underline">
            Archive →
          </Link>
        </div>
        <p className="mt-1 text-sm text-neutral-400">
          <span className="text-red-300 font-medium">
            {digest.items_requiring_action} items require action
          </span>
          {" · "}{digest.material_developments} material developments
          {" · "}{digest.suppressed_low_priority} low-priority updates suppressed
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

      {SECTION_ORDER.map(([key, title]) => {
        const events = (digest.sections?.[key] ?? []).slice(0, key === "exploitation" ? 8 : 6);
        if (events.length === 0) return null;
        return (
          <section key={key}>
            <h2 className="mb-3 text-lg font-semibold text-neutral-100">{title}</h2>
            <div className="grid gap-3">
              {events.map((e) => (
                <EventCard key={e.id} event={e} />
              ))}
            </div>
          </section>
        );
      })}
    </div>
  );
}
