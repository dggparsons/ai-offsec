import { api } from "@/lib/api";

export const dynamic = "force-dynamic";

export default async function SourcesPage() {
  const sources = await api.sources().catch(() => []);

  return (
    <div>
      <h1 className="mb-4 text-xl font-semibold text-neutral-100">Source registry</h1>
      <div className="overflow-x-auto rounded-lg border border-neutral-800">
        <table className="w-full text-sm">
          <thead className="bg-neutral-900 text-left text-neutral-400">
            <tr>
              <th className="px-4 py-2">Source</th>
              <th className="px-4 py-2">Priority</th>
              <th className="px-4 py-2">Trust</th>
              <th className="px-4 py-2">Last fetch</th>
              <th className="px-4 py-2">Health</th>
            </tr>
          </thead>
          <tbody>
            {sources.map((s) => (
              <tr key={s.slug} className="border-t border-neutral-800">
                <td className="px-4 py-2">
                  <div className="text-neutral-200">{s.name}</div>
                  <div className="text-xs text-neutral-500">{s.connector} · {s.slug}</div>
                </td>
                <td className="px-4 py-2 font-mono text-neutral-300">{s.priority}</td>
                <td className="px-4 py-2 font-mono text-neutral-300">{s.trust_score.toFixed(2)}</td>
                <td className="px-4 py-2 text-neutral-400">
                  {s.last_fetched_at ? new Date(s.last_fetched_at).toLocaleString() : "never"}
                </td>
                <td className="px-4 py-2">
                  {!s.enabled ? (
                    <span className="text-neutral-500">disabled</span>
                  ) : s.consecutive_failures > 0 ? (
                    <span className="text-red-400">{s.consecutive_failures} failures</span>
                  ) : (
                    <span className="text-emerald-400">ok</span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="mt-3 text-xs text-neutral-600">
        Manage via the API: POST/PATCH /api/sources, force a fetch with POST /api/sources/{"{slug}"}/fetch.
      </p>
    </div>
  );
}
