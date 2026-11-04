import Link from "next/link";
import { api } from "@/lib/api";
import { EventCard } from "@/components/EventCard";

export const dynamic = "force-dynamic";

// Display order and reader-facing headings for the digest sections.
const SECTION_ORDER: [string, string][] = [
  ["models", "Models & local LLMs"],
  ["exploitation", "CVEs & exploits in AI software"],
  ["mcp", "MCP & agent plumbing"],
  ["safety", "Jailbreaks, red-teaming & evals"],
  ["research", "Research & papers"],
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

  const nonEmptySections = SECTION_ORDER.filter(
    ([key]) => (digest.sections[key] ?? []).length > 0
  );
  const shown = new Set(
    nonEmptySections.flatMap(([key]) => digest.sections[key].map((e) => e.id))
  );
  const uncategorised = digest.top_events.filter((e) => !shown.has(e.id));

  return (
    <div className="space-y-8">
      <section className="flex items-baseline justify-between">
        <h2 className="text-xl font-semibold text-neutral-100">
          Today&apos;s read{" "}
          <span className="text-sm font-normal text-neutral-400">
            {new Date(digest.generated_at).toLocaleDateString("en-GB", {
              day: "numeric",
              month: "long",
              year: "numeric",
            })}
          </span>
        </h2>
        <Link href="/archive" className="text-sm text-sky-400 hover:underline">
          Archive →
        </Link>
      </section>

      {digest.top_events.length === 0 ? (
        <p className="text-sm text-neutral-400">Nothing cleared the bar today.</p>
      ) : (
        nonEmptySections.map(([key, title]) => (
          <section key={key}>
            <h3 className="mb-3 border-b border-white/10 pb-1.5 text-sm font-semibold uppercase tracking-wide text-neutral-400">
              {title}
            </h3>
            <div className="grid gap-3">
              {digest.sections[key].map((e) => (
                <EventCard key={e.id} event={e} />
              ))}
            </div>
          </section>
        ))
      )}

      {uncategorised.length > 0 && (
        <section>
          <h3 className="mb-3 border-b border-white/10 pb-1.5 text-sm font-semibold uppercase tracking-wide text-neutral-400">
            Also today
          </h3>
          <div className="grid gap-3">
            {uncategorised.map((e) => (
              <EventCard key={e.id} event={e} />
            ))}
          </div>
        </section>
      )}

      {digest.emerging_themes.length > 0 && (
        <section>
          <h3 className="mb-2 text-sm font-semibold uppercase tracking-wide text-neutral-400">
            Being talked about
          </h3>
          <div className="flex flex-wrap gap-1.5">
            {digest.emerging_themes.map((t) => (
              <span
                key={t.label}
                className="rounded bg-white/5 px-2 py-0.5 text-xs text-neutral-300"
              >
                {t.label} <span className="text-neutral-500">×{t.count}</span>
              </span>
            ))}
          </div>
        </section>
      )}
    </div>
  );
}
