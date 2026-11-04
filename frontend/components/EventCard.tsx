import Link from "next/link";
import { IntelEvent } from "@/lib/api";

const LABEL_KINDS: Record<string, string> = {
  fact_summary: "Fact summary",
  technical_delta: "Technical delta",
  offensive_significance: "Offensive significance",
  defensive_significance: "Defensive significance",
  enterprise_significance: "Enterprise significance",
  watch_items: "Watch items",
};

export function EventCard({ event }: { event: IntelEvent }) {
  return (
    <Link
      href={`/events/${event.id}`}
      className="block rounded-lg border border-white/10 bg-white/[0.04] p-4 hover:border-white/25"
    >
      <h3 className="font-medium text-neutral-100 leading-snug">{event.title}</h3>
      {event.tldr && (
        <p className="mt-2 text-sm text-neutral-400 leading-relaxed">{event.tldr}</p>
      )}
      <div className="mt-2 flex flex-wrap gap-1.5">
        {event.taxonomy.slice(0, 5).map((t) => (
          <span key={t} className="rounded bg-white/5 px-1.5 py-0.5 text-[11px] text-neutral-400">
            {t}
          </span>
        ))}
        {event.version > 1 && (
          <span className="rounded bg-sky-900/60 px-1.5 py-0.5 text-[11px] text-sky-300">
            updated · version {event.version}
          </span>
        )}
      </div>
      <div className="mt-2 text-xs text-neutral-500">
        {event.source ?? event.source_type}
        {event.published_at && ` · ${new Date(event.published_at).toLocaleString("en-GB")}`}
      </div>
    </Link>
  );
}

export function AnalysisBlock({ kind, content, confidence, model }: {
  kind: string;
  content: string;
  confidence: string;
  model: string;
}) {
  return (
    <div className="rounded-lg border border-white/10 bg-white/[0.04] p-4">
      <div className="flex items-center justify-between">
        <h4 className="text-sm font-semibold text-neutral-200">
          {LABEL_KINDS[kind] ?? kind}
        </h4>
        <span className="text-xs text-neutral-500">
          {confidence} · {model}
        </span>
      </div>
      <p className="mt-2 whitespace-pre-wrap text-sm text-neutral-300">{content}</p>
    </div>
  );
}
