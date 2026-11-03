const API =
  process.env.API_INTERNAL_URL ||
  process.env.NEXT_PUBLIC_API_URL ||
  "http://localhost:8000";

export interface IntelEvent {
  id: string;
  source: string | null;
  source_url: string;
  source_type: string;
  title: string;
  published_at: string | null;
  modified_at: string | null;
  taxonomy: string[];
  identifiers: Record<string, string[]>;
  priority_score: number;
  tldr: string;
  version: number;
  is_novel: boolean;
  tlp: string;
  entities: { type: string; name: string; role: string }[];
  analyses: {
    kind: string;
    content: string;
    confidence: string;
    model: string;
    created_at: string;
  }[];
  body_text?: string;
}

export interface Digest {
  window_hours: number;
  generated_at: string;
  items_requiring_action: number;
  material_developments: number;
  suppressed_low_priority: number;
  top_events: IntelEvent[];
  sections: Record<string, IntelEvent[]>;
  emerging_themes: { label: string; count: number }[];
}

export interface SearchResult {
  id: string;
  title: string;
  source_url: string;
  source_type: string;
  published_at: string | null;
  taxonomy: string[];
  priority_score: number;
  rrf_score: number;
  snippet: string;
}

export interface SourceInfo {
  slug: string;
  name: string;
  connector: string;
  url: string;
  priority: string;
  trust_score: number;
  enabled: boolean;
  last_fetched_at: string | null;
  last_success_at: string | null;
  consecutive_failures: number;
}

async function get<T>(path: string, revalidate = 30): Promise<T> {
  const res = await fetch(`${API}${path}`, { next: { revalidate } });
  if (!res.ok) throw new Error(`API ${path}: ${res.status}`);
  return res.json();
}

export const api = {
  digest: () => get<Digest>("/api/digest/daily"),
  digestHistory: () => get<{ day: string; generated_at: string }[]>("/api/digest/history"),
  digestDay: (day: string) =>
    get<{ day: string; content: Digest | null }>(`/api/digest/day/${day}`),
  events: (params = "") => get<IntelEvent[]>(`/api/events${params}`),
  event: (id: string) => get<IntelEvent>(`/api/events/${id}`, 0),
  search: (q: string) =>
    get<SearchResult[]>(`/api/search?q=${encodeURIComponent(q)}`, 0),
  sources: () => get<SourceInfo[]>("/api/sources"),
};

export const API_BASE = API;
