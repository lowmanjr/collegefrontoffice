"use client";

import { useState } from "react";
import { formatCurrency } from "@/lib/utils";

interface Override {
  player_id: string;
  player_name: string;
  total_value: number;
  years: number;
  annualized_value: number;
  source_name: string | null;
  source_url: string | null;
}

interface Props {
  initialOverrides: Override[];
}

export default function OverrideList({ initialOverrides }: Props) {
  const [overrides, setOverrides] = useState(initialOverrides);
  const [deletingId, setDeletingId] = useState<string | null>(null);

  async function handleDelete(playerId: string) {
    if (!confirm("Remove this override? The player will revert to algorithmic valuation after the next engine run.")) return;

    setDeletingId(playerId);
    try {
      const res = await fetch(`/admin/api/overrides?player_id=${playerId}`, { method: "DELETE" });
      if (res.ok) {
        setOverrides((prev) => prev.filter((o) => o.player_id !== playerId));
      }
    } catch (err) {
      console.error("Delete failed:", err);
    }
    setDeletingId(null);
  }

  if (overrides.length === 0) {
    return (
      <div className="bg-white rounded-xl shadow-md border border-gray-200 p-8 text-center">
        <p className="text-sm text-slate-400">No active overrides.</p>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-xl shadow-md border border-gray-200 overflow-hidden">
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="bg-slate-900 text-slate-300">
            <tr>
              <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-widest">Player</th>
              <th className="px-4 py-3 text-right text-xs font-semibold uppercase tracking-widest hidden sm:table-cell">Total</th>
              <th className="px-4 py-3 text-center text-xs font-semibold uppercase tracking-widest hidden sm:table-cell">Years</th>
              <th className="px-4 py-3 text-right text-xs font-semibold uppercase tracking-widest">Annual</th>
              <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-widest hidden md:table-cell">Source</th>
              <th className="px-4 py-3 w-16"></th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {overrides.map((ov) => (
              <tr key={`${ov.player_id}-${ov.source_name}`} className="hover:bg-slate-50 transition-colors">
                <td className="px-4 py-3 font-semibold text-slate-900">{ov.player_name}</td>
                <td className="px-4 py-3 text-right text-slate-600 tabular-nums hidden sm:table-cell"
                  style={{ fontFamily: "var(--font-oswald), sans-serif" }}>
                  {formatCurrency(ov.total_value)}
                </td>
                <td className="px-4 py-3 text-center text-slate-600 hidden sm:table-cell">{ov.years}</td>
                <td className="px-4 py-3 text-right font-bold text-emerald-600 tabular-nums"
                  style={{ fontFamily: "var(--font-oswald), sans-serif" }}>
                  {formatCurrency(ov.annualized_value)}
                </td>
                <td className="px-4 py-3 hidden md:table-cell">
                  {ov.source_url ? (
                    <a href={ov.source_url} target="_blank" rel="noopener noreferrer"
                      className="text-xs text-blue-600 hover:underline">{ov.source_name ?? "Link"}</a>
                  ) : (
                    <span className="text-xs text-slate-400">{ov.source_name ?? "—"}</span>
                  )}
                </td>
                <td className="px-4 py-3">
                  <button onClick={() => handleDelete(ov.player_id)}
                    disabled={deletingId === ov.player_id}
                    className="text-xs text-slate-400 hover:text-red-500 disabled:opacity-50 transition-colors">
                    {deletingId === ov.player_id ? "..." : "Remove"}
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="border-t border-gray-100 bg-slate-50 px-4 py-3">
        <p className="text-xs text-slate-400">
          <span className="font-semibold text-slate-600">{overrides.length}</span> active override{overrides.length !== 1 ? "s" : ""}
        </p>
      </div>
    </div>
  );
}
