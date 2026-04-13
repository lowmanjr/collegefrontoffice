"use client";

import { useRouter, usePathname, useSearchParams } from "next/navigation";
import Link from "next/link";
import { formatCurrency, formatCompactCurrency } from "@/lib/utils";
import { positionBadgeClass } from "@/lib/ui-helpers";
import PlayerAvatar from "@/components/PlayerAvatar";

// ─── types ──────────────────────────────────────────────────────────────────

interface Player {
  id: string;
  slug: string | null;
  name: string;
  position: string | null;
  cfo_valuation: number | null;
  is_public: boolean;
  headshot_url: string | null;
  acquisition_type: string;
}

interface TeamRosterProps {
  players: Player[];
  retainedValue: number;
  portalValue: number;
  recruitValue: number;
  totalValuation: number;
}

// ─── constants ──────────────────────────────────────────────────────────────

type ViewKey = "roster" | "portal" | "recruits" | "retained";

const TABS: { key: ViewKey; label: string }[] = [
  { key: "roster", label: "Full Roster" },
  { key: "portal", label: "Portal" },
  { key: "recruits", label: "Recruits" },
  { key: "retained", label: "Retained" },
];

const EMPTY_MESSAGES: Record<ViewKey, string> = {
  roster: "No players currently tracked for this team.",
  portal: "No portal acquisitions for this team.",
  recruits: "No incoming recruits for this team.",
  retained: "No retained players for this team.",
};

// ─── component ──────────────────────────────────────────────────────────────

export default function TeamRoster({
  players,
  retainedValue,
  portalValue,
  recruitValue,
  totalValuation,
}: TeamRosterProps) {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const activeView = (searchParams.get("view") as ViewKey) || "roster";

  function handleTabClick(view: ViewKey) {
    const params = new URLSearchParams(searchParams.toString());
    if (view === "roster") {
      params.delete("view");
    } else {
      params.set("view", view);
    }
    const qs = params.toString();
    router.replace(qs ? `${pathname}?${qs}` : pathname, { scroll: false });
  }

  // Filter players based on active tab
  const filteredPlayers =
    activeView === "roster"
      ? players
      : players.filter((p) => {
          if (activeView === "portal") return p.acquisition_type === "portal";
          if (activeView === "recruits") return p.acquisition_type === "recruit";
          if (activeView === "retained") return p.acquisition_type === "retained";
          return true;
        });

  // ─── Summary bar segments ─────────────────────────────────────────────────

  const segments = [
    { label: "Est. Retained Value", value: retainedValue, color: "bg-slate-500" },
    { label: "Est. Portal Value", value: portalValue, color: "bg-blue-500" },
    { label: "Est. Recruiting Class Value", value: recruitValue, color: "bg-emerald-500" },
  ].filter((s) => s.value > 0);

  return (
    <>
      {/* ── Summary bar ──────────────────────────────────────────────────── */}
      {totalValuation > 0 && (
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-4 mb-4">
          {/* Proportional bar */}
          <div className="flex rounded-full overflow-hidden h-3 mb-3">
            {segments.map((seg) => (
              <div
                key={seg.label}
                className={`${seg.color} transition-all`}
                style={{ width: `${(seg.value / totalValuation) * 100}%` }}
              />
            ))}
          </div>

          {/* Labels */}
          <div className="flex flex-wrap gap-x-6 gap-y-1">
            {segments.map((seg) => (
              <div key={seg.label} className="flex items-center gap-2">
                <span className={`inline-block w-2.5 h-2.5 rounded-full ${seg.color}`} />
                <span className="text-xs text-slate-500">{seg.label}</span>
                <span
                  className="text-xs font-bold text-slate-700 tabular-nums"
                  style={{ fontFamily: "var(--font-oswald), sans-serif" }}
                >
                  {formatCompactCurrency(seg.value)}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* ── Tabs ─────────────────────────────────────────────────────────── */}
      <div className="flex gap-2 mb-4 overflow-x-auto">
        {TABS.map((tab) => {
          const count =
            tab.key === "roster"
              ? players.length
              : players.filter((p) =>
                  tab.key === "portal"
                    ? p.acquisition_type === "portal"
                    : tab.key === "recruits"
                    ? p.acquisition_type === "recruit"
                    : p.acquisition_type === "retained"
                ).length;

          return (
            <button
              key={tab.key}
              onClick={() => handleTabClick(tab.key)}
              className={`shrink-0 rounded-lg px-3 py-1.5 text-sm font-semibold transition-colors ${
                activeView === tab.key
                  ? "bg-emerald-500 text-white"
                  : "bg-white border border-gray-200 text-slate-600 hover:bg-slate-50"
              }`}
            >
              {tab.label}
              <span className="ml-1.5 text-xs opacity-70">({count})</span>
            </button>
          );
        })}
      </div>

      {/* ── Roster display ───────────────────────────────────────────────── */}
      {filteredPlayers.length === 0 ? (
        <div className="bg-white rounded-xl shadow-md border border-gray-100 p-12 text-center">
          <p className="text-sm font-semibold text-slate-400">
            {EMPTY_MESSAGES[activeView]}
          </p>
        </div>
      ) : (
        <>
          {/* Mobile cards */}
          <div className="md:hidden space-y-3">
            {filteredPlayers.map((player) => {
              const isPrivate = !player.is_public;
              return (
                <Link
                  key={player.id}
                  href={`/players/${player.slug ?? player.id}`}
                  className="block bg-white rounded-xl border border-gray-200 p-4 hover:border-slate-300 transition-colors shadow-sm"
                >
                  <div className="flex items-center gap-3">
                    <PlayerAvatar
                      headshot_url={player.headshot_url}
                      name={player.name}
                      position={player.position}
                      size={44}
                      className="shrink-0"
                    />
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center justify-between gap-2">
                        <h3
                          className="font-bold text-slate-900 uppercase tracking-tight truncate"
                          style={{ fontFamily: "var(--font-oswald), sans-serif" }}
                        >
                          {player.name}
                        </h3>
                        {player.position && (
                          <span
                            className={`shrink-0 inline-block rounded px-2 py-0.5 text-xs font-semibold uppercase tracking-wide ${positionBadgeClass(player.position)}`}
                          >
                            {player.position}
                          </span>
                        )}
                      </div>
                      <div className="flex items-center justify-end mt-1">
                        {isPrivate ? (
                          <span className="text-slate-400 text-xs italic">Private</span>
                        ) : player.cfo_valuation != null ? (
                          <span
                            className="font-bold text-emerald-600 tabular-nums"
                            style={{ fontFamily: "var(--font-oswald), sans-serif" }}
                          >
                            {formatCurrency(player.cfo_valuation)}
                          </span>
                        ) : (
                          <span className="text-slate-400 text-xs">&mdash;</span>
                        )}
                      </div>
                    </div>
                  </div>
                </Link>
              );
            })}
          </div>

          {/* Desktop table */}
          <div className="hidden md:block bg-white rounded-xl shadow-md border border-gray-200 overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="sticky top-0 z-10 bg-slate-900 text-slate-300">
                  <tr>
                    <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-widest">
                      Player
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-widest w-16">
                      Pos
                    </th>
                    <th className="px-4 py-3 text-right text-xs font-semibold uppercase tracking-widest">
                      CFO Valuation
                    </th>
                  </tr>
                </thead>

                <tbody className="divide-y divide-gray-100">
                  {filteredPlayers.map((player) => {
                    const isPrivate = !player.is_public;
                    return (
                      <tr
                        key={player.id}
                        className="hover:bg-slate-50 transition-colors group"
                      >
                        <td className="px-4 py-3.5">
                          <div className="flex items-center gap-3">
                            <PlayerAvatar
                              headshot_url={player.headshot_url}
                              name={player.name}
                              position={player.position}
                              size={40}
                              className="shrink-0"
                            />
                            <Link
                              href={`/players/${player.slug ?? player.id}`}
                              className="font-semibold text-slate-900 hover:text-emerald-500 hover:underline transition-colors uppercase tracking-tight"
                              style={{
                                fontFamily: "var(--font-oswald), sans-serif",
                              }}
                            >
                              {player.name}
                            </Link>
                          </div>
                        </td>

                        <td className="px-4 py-3.5">
                          {player.position ? (
                            <span
                              className={`inline-block rounded px-2 py-0.5 text-xs font-semibold uppercase tracking-wide ${positionBadgeClass(player.position)}`}
                            >
                              {player.position}
                            </span>
                          ) : (
                            <span className="text-slate-400">&mdash;</span>
                          )}
                        </td>

                        <td className="px-4 py-3.5 text-right">
                          {isPrivate ? (
                            <span className="text-slate-400 text-xs italic">
                              Private
                            </span>
                          ) : player.cfo_valuation != null ? (
                            <span
                              className="font-bold text-emerald-600 tabular-nums"
                              style={{
                                fontFamily: "var(--font-oswald), sans-serif",
                              }}
                            >
                              {formatCurrency(player.cfo_valuation)}
                            </span>
                          ) : (
                            <span className="text-slate-400 text-xs">
                              &mdash;
                            </span>
                          )}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>

            <div className="border-t border-gray-100 bg-slate-50 px-4 py-3 flex items-center justify-between">
              <p className="text-xs text-slate-400">
                <span className="font-semibold text-slate-600">
                  {filteredPlayers.length}
                </span>{" "}
                players
              </p>
              <p className="text-xs text-slate-400">
                C.F.O. Valuation Engine V3.6b
              </p>
            </div>
          </div>
        </>
      )}
    </>
  );
}
