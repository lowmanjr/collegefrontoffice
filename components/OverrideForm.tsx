"use client";

import { useState } from "react";

interface Props {
  players: { id: string; name: string; position: string | null; team_name: string | null }[];
}

export default function OverrideForm({ players }: Props) {
  const [selectedPlayerId, setSelectedPlayerId] = useState("");
  const [totalValue, setTotalValue] = useState("");
  const [years, setYears] = useState("");
  const [sourceName, setSourceName] = useState("");
  const [sourceUrl, setSourceUrl] = useState("");
  const [search, setSearch] = useState("");
  const [status, setStatus] = useState<"idle" | "submitting" | "success" | "error">("idle");
  const [errorMsg, setErrorMsg] = useState("");

  const filteredPlayers = search.length > 1
    ? players.filter((p) => p.name.toLowerCase().includes(search.toLowerCase())).slice(0, 8)
    : [];

  const selectedPlayer = players.find((p) => p.id === selectedPlayerId);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!selectedPlayerId || !totalValue || !years || !sourceName) return;

    setStatus("submitting");
    setErrorMsg("");

    try {
      const res = await fetch("/admin/api/overrides", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          player_id: selectedPlayerId,
          total_value: parseInt(totalValue.replace(/[^0-9]/g, "")),
          years: parseFloat(years),
          source_name: sourceName,
          source_url: sourceUrl || null,
        }),
      });

      if (!res.ok) {
        const data = await res.json();
        throw new Error(data.error || "Failed to save override");
      }

      setStatus("success");
      setSelectedPlayerId("");
      setTotalValue("");
      setYears("");
      setSourceName("");
      setSourceUrl("");
      setSearch("");

      setTimeout(() => setStatus("idle"), 3000);
    } catch (err: unknown) {
      setStatus("error");
      setErrorMsg(err instanceof Error ? err.message : "Unknown error");
    }
  }

  return (
    <div className="bg-white rounded-xl shadow-md border border-gray-200 p-6">
      <h2 className="text-lg font-bold text-slate-900 uppercase tracking-wide mb-4"
        style={{ fontFamily: "var(--font-oswald), sans-serif" }}>
        Add Override
      </h2>

      {status === "success" && (
        <div className="mb-4 rounded-lg bg-emerald-50 border border-emerald-200 px-4 py-3 text-sm text-emerald-700 font-medium">
          Override saved successfully. Run the valuation engine to apply.
        </div>
      )}

      {status === "error" && (
        <div className="mb-4 rounded-lg bg-red-50 border border-red-200 px-4 py-3 text-sm text-red-700">
          {errorMsg}
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-4">
        {/* Player search */}
        <div>
          <label className="block text-xs font-semibold text-slate-500 uppercase tracking-wide mb-1">Player</label>
          {selectedPlayer ? (
            <div className="flex items-center justify-between bg-slate-50 rounded-lg px-3 py-2 border border-gray-200">
              <div>
                <span className="font-semibold text-slate-900">{selectedPlayer.name}</span>
                {selectedPlayer.position && (
                  <span className="ml-2 text-xs text-slate-500">{selectedPlayer.position}</span>
                )}
                {selectedPlayer.team_name && (
                  <span className="ml-2 text-xs text-slate-400">&middot; {selectedPlayer.team_name}</span>
                )}
              </div>
              <button type="button" onClick={() => { setSelectedPlayerId(""); setSearch(""); }}
                className="text-xs text-slate-400 hover:text-red-500 transition-colors">
                Clear
              </button>
            </div>
          ) : (
            <div className="relative">
              <input type="text" value={search} onChange={(e) => setSearch(e.target.value)}
                placeholder="Search by name..."
                className="w-full rounded-lg border border-gray-200 bg-white px-3 py-2 text-sm text-slate-900 placeholder-slate-400 focus:border-emerald-500 focus:outline-none focus:ring-1 focus:ring-emerald-500" />
              {filteredPlayers.length > 0 && (
                <div className="absolute z-20 mt-1 w-full bg-white rounded-lg shadow-lg border border-gray-200 overflow-hidden">
                  {filteredPlayers.map((p) => (
                    <button key={p.id} type="button"
                      onClick={() => { setSelectedPlayerId(p.id); setSearch(""); }}
                      className="w-full text-left px-3 py-2 text-sm hover:bg-slate-50 transition-colors flex items-center justify-between">
                      <span className="font-medium text-slate-900">{p.name}</span>
                      <span className="text-xs text-slate-400">{p.position} &middot; {p.team_name ?? "No team"}</span>
                    </button>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>

        {/* Value + Years row */}
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-xs font-semibold text-slate-500 uppercase tracking-wide mb-1">Total Value ($)</label>
            <input type="text" value={totalValue}
              onChange={(e) => setTotalValue(e.target.value)}
              placeholder="e.g. 8000000"
              className="w-full rounded-lg border border-gray-200 bg-white px-3 py-2 text-sm text-slate-900 placeholder-slate-400 focus:border-emerald-500 focus:outline-none focus:ring-1 focus:ring-emerald-500" />
          </div>
          <div>
            <label className="block text-xs font-semibold text-slate-500 uppercase tracking-wide mb-1">Years</label>
            <input type="text" value={years}
              onChange={(e) => setYears(e.target.value)}
              placeholder="e.g. 4"
              className="w-full rounded-lg border border-gray-200 bg-white px-3 py-2 text-sm text-slate-900 placeholder-slate-400 focus:border-emerald-500 focus:outline-none focus:ring-1 focus:ring-emerald-500" />
          </div>
        </div>

        {/* Source */}
        <div>
          <label className="block text-xs font-semibold text-slate-500 uppercase tracking-wide mb-1">Source Name</label>
          <input type="text" value={sourceName}
            onChange={(e) => setSourceName(e.target.value)}
            placeholder='e.g. "The Athletic" or "Market Consensus"'
            className="w-full rounded-lg border border-gray-200 bg-white px-3 py-2 text-sm text-slate-900 placeholder-slate-400 focus:border-emerald-500 focus:outline-none focus:ring-1 focus:ring-emerald-500" />
        </div>

        <div>
          <label className="block text-xs font-semibold text-slate-500 uppercase tracking-wide mb-1">Source URL <span className="text-slate-400 font-normal">(optional)</span></label>
          <input type="url" value={sourceUrl}
            onChange={(e) => setSourceUrl(e.target.value)}
            placeholder="https://..."
            className="w-full rounded-lg border border-gray-200 bg-white px-3 py-2 text-sm text-slate-900 placeholder-slate-400 focus:border-emerald-500 focus:outline-none focus:ring-1 focus:ring-emerald-500" />
        </div>

        {/* Computed preview */}
        {totalValue && years && parseFloat(years) > 0 && (
          <div className="bg-slate-50 rounded-lg px-4 py-3 border border-gray-100">
            <p className="text-xs text-slate-500">Annualized Value</p>
            <p className="text-xl font-bold text-emerald-600" style={{ fontFamily: "var(--font-oswald), sans-serif" }}>
              ${Math.round(parseInt(totalValue.replace(/[^0-9]/g, "")) / parseFloat(years)).toLocaleString()}/yr
            </p>
          </div>
        )}

        <button type="submit" disabled={!selectedPlayerId || !totalValue || !years || !sourceName || status === "submitting"}
          className="w-full rounded-lg bg-emerald-500 hover:bg-emerald-600 disabled:bg-slate-300 disabled:cursor-not-allowed text-white font-semibold py-2.5 text-sm transition-colors">
          {status === "submitting" ? "Saving..." : "Save Override"}
        </button>
      </form>
    </div>
  );
}
