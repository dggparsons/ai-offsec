"use client";

import { useState } from "react";
import Link from "next/link";
import { API_BASE, SearchResult } from "@/lib/api";

export default function SearchPage() {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<SearchResult[] | null>(null);
  const [loading, setLoading] = useState(false);

  async function run(e: React.FormEvent) {
    e.preventDefault();
    if (!query.trim()) return;
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/api/search?q=${encodeURIComponent(query)}`);
      setResults(await res.json());
    } finally {
      setLoading(false);
    }
  }

  return (
    <div>
      <h1 className="mb-4 text-xl font-semibold text-neutral-100">Hybrid search</h1>
      <form onSubmit={run} className="mb-6 flex gap-2">
        <input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="CVE id, model name, technique, product…"
          className="w-full rounded border border-neutral-700 bg-neutral-900 px-3 py-2 text-neutral-200"
        />
        <button className="rounded bg-sky-700 px-4 py-2 text-neutral-50 hover:bg-sky-600">
          {loading ? "…" : "Search"}
        </button>
      </form>

      {results && results.length === 0 && (
        <p className="text-sm text-neutral-500">No matches.</p>
      )}
      <div className="grid gap-3">
        {results?.map((r) => (
          <Link
            key={r.id}
            href={`/events/${r.id}`}
            className="block rounded-lg border border-neutral-800 bg-neutral-900 p-4 hover:border-neutral-600"
          >
            <h3 className="font-medium text-neutral-100">{r.title}</h3>
            <p className="mt-1 line-clamp-2 text-sm text-neutral-400">{r.snippet}</p>
            <div className="mt-2 text-xs text-neutral-500">
              priority {r.priority_score.toFixed(2)} · rrf {r.rrf_score}
              {r.published_at && ` · ${new Date(r.published_at).toLocaleString("en-GB")}`}
            </div>
          </Link>
        ))}
      </div>
    </div>
  );
}
