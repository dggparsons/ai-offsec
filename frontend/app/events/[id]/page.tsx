import { notFound } from "next/navigation";
import { api } from "@/lib/api";
import { AnalysisBlock } from "@/components/EventCard";
import { FeedbackButtons } from "@/components/FeedbackButtons";

export const dynamic = "force-dynamic";

export default async function EventDetail({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const event = await api.event(id).catch(() => null);
  if (!event) notFound();

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-semibold text-neutral-100 leading-snug">{event.title}</h1>
        <div className="mt-2 text-sm text-neutral-500">
          {event.source} · v{event.version}
          {event.published_at && ` · published ${new Date(event.published_at).toLocaleString("en-GB")}`}
          {event.modified_at && ` · modified ${new Date(event.modified_at).toLocaleString("en-GB")}`}
          {" · TLP:"}{event.tlp}
        </div>
        <div className="mt-2 flex flex-wrap gap-1.5">
          {event.taxonomy.map((t) => (
            <span key={t} className="rounded bg-neutral-800 px-1.5 py-0.5 text-[11px] text-neutral-400">
              {t}
            </span>
          ))}
        </div>
        <a
          href={event.source_url}
          target="_blank"
          rel="noreferrer"
          className="mt-3 inline-block text-sm text-sky-400 hover:underline"
        >
          Source evidence ↗
        </a>
      </div>

      {event.entities.length > 0 && (
        <section>
          <h2 className="mb-2 text-sm font-semibold uppercase tracking-wide text-neutral-500">Entities</h2>
          <div className="flex flex-wrap gap-2">
            {event.entities.map((e) => (
              <span key={`${e.type}-${e.name}`} className="rounded border border-neutral-700 px-2 py-1 text-xs text-neutral-300">
                <span className="text-neutral-500">{e.type}:</span> {e.name}
              </span>
            ))}
          </div>
        </section>
      )}

      {event.analyses.length > 0 && (
        <section className="space-y-3">
          <h2 className="text-sm font-semibold uppercase tracking-wide text-neutral-500">Assessment</h2>
          {event.analyses.map((a, i) => (
            <AnalysisBlock key={i} kind={a.kind} content={a.content} confidence={a.confidence} model={a.model} />
          ))}
        </section>
      )}

      {event.body_text && (
        <section>
          <h2 className="mb-2 text-sm font-semibold uppercase tracking-wide text-neutral-500">Extracted text</h2>
          <pre className="max-h-96 overflow-auto whitespace-pre-wrap rounded-lg border border-white/10 bg-white/[0.04] p-4 text-xs text-neutral-400">
            {event.body_text}
          </pre>
        </section>
      )}

      <FeedbackButtons eventId={event.id} />
    </div>
  );
}
