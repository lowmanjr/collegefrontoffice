"use client";

import { useState } from "react";
import { useRouter, usePathname, useSearchParams } from "next/navigation";
import Link from "next/link";
import Image from "next/image";
import { formatCurrency, formatCompactCurrency } from "@/lib/utils";
import { positionBadgeClass } from "@/lib/ui-helpers";
import PlayerAvatar from "@/components/PlayerAvatar";

// ─── types ──────────────────────────────────────────────────────────────────

interface PortalPlayer {
  id: string;
  slug: string | null;
  name: string;
  position: string | null;
  cfo_valuation: number;
  headshot_url: string | null;
  team_name: string;
  team_slug: string | null;
  team_logo: string | null;
  conference: string | null;
}

interface TeamPortalSummary {
  team_name: string;
  team_slug: string | null;
  team_logo: string | null;
  conference: string | null;
  portal_count: number;
  portal_value: number;
}

interface PortalBoardProps {
  players: PortalPlayer[];
  teamSummaries: TeamPortalSummary[];
  totalCount: number;
  totalValue: number;
}

// ─── constants ──────────────────────────────────────────────────────────────

type ViewKey = "players" | "teams";

const POSITIONS = [
  "All", "QB", "RB", "WR", "TE", "OT", "OL", "DL", "EDGE", "LB", "CB", "S", "K", "P",
];

const POS_ALIASES: Record<string, string[]> = {
  K: ["K", "PK"],
  DL: ["DL", "DT"],
  S: ["S", "DB"],
};

const CONFERENCES = ["All", "SEC", "Big Ten", "Big 12", "ACC", "Independent"];

// ─── component ──────────────────────────────────────────────────────────────

export default function PortalBoard({
  players,
  teamSummaries,
  totalCount,
  totalValue,
}: PortalBoardProps) {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const activeView = (searchParams.get("view") as ViewKey) || "players";

  const [posFilter, setPosFilter] = useState("All");
  const [confFilter, setConfFilter] = useState("All");
  const [nameQuery, setNameQuery] = useState("");
  const [showAll, setShowAll] = useState(false);

  function handleViewChange(view: ViewKey) {
    const params = new URLSearchParams(searchParams.toString());
    if (view === "players") {
      params.delete("view");
    } else {
      params.set("view", view);
    }
    const qs = params.toString();
    router.replace(qs ? `${pathname}?${qs}` : pathname, { scroll: false });
  }

  // ─── Player filtering ─────────────────────────────────────────────────

  const filteredPlayers = players.filter((p) => {
    // Position filter
    if (posFilter !== "All") {
      const aliases = POS_ALIASES[posFilter] ?? [posFilter];
      if (!aliases.includes(p.position ?? "")) return false;
    }
    // Conference filter
    if (confFilter !== "All") {
      if (p.conference !== confFilter) return false;
    }
    // Name search
    if (nameQuery.trim()) {
      if (!p.name.toLowerCase().includes(nameQuery.toLowerCase())) return false;
    }
    return true;
  });

  const displayPlayers = showAll ? filteredPlayers : filteredPlayers.slice(0, 100);

  // ─── Team filtering ───────────────────────────────────────────────────

  const filteredTeams = confFilter !== "All"
    ? teamSummaries.filter((t) => t.conference === confFilter)
    : teamSummaries;

  return (
    <>
      {/* ── View tabs ────────────────────────────────────────────────────── */}
      <div className="flex gap-2 mb-4">
        <button
          onClick={() => handleViewChange("players")}
          className={`rounded-lg px-3 py-1.5 text-sm font-semibold transition-colors ${
            activeView === "players"
              ? "bg-emerald-500 text-white"
              : "bg-white border border-gray-200 text-slate-600 hover:bg-slate-50"
          }`}
        >
          By Player
          <span className="ml-1.5 text-xs opacity-70">({totalCount})</span>
        </button>
        <button
          onClick={() => handleViewChange("teams")}
          className={`rounded-lg px-3 py-1.5 text-sm font-semibold transition-colors ${
            activeView === "teams"
              ? "bg-emerald-500 text-white"
              : "bg-white border border-gray-200 text-slate-600 hover:bg-slate-50"
          }`}
        >
          By Team
          <span className="ml-1.5 text-xs opacity-70">({teamSummaries.length})</span>
        </button>
      </div>

      {/* ── Filters ──────────────────────────────────────────────────────── */}
      <div className="flex flex-col sm:flex-row gap-3 mb-4">
        {activeView === "players" && (
          <div className="relative flex-1">
            <svg
              className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400"
              viewBox="0 0 20 20" fill="currentColor" aria-hidden="true"
            >
              <path fillRule="evenodd" clipRule="evenodd"
                d="M9 3.5a5.5 5.5 0 100 11 5.5 5.5 0 000-11zM2 9a7 7 0 1112.452 4.391l3.328 3.329a.75.75 0 11-1.06 1.06l-3.329-3.328A7 7 0 012 9z"
              />
            </svg>
            <input
              type="text"
              placeholder="Search players..."
              value={nameQuery}
              onChange={(e) => setNameQuery(e.target.value)}
              className="w-full rounded-lg border border-gray-200 bg-white py-2.5 pl-9 pr-4 text-sm text-slate-900 placeholder-slate-400 shadow-sm focus:border-emerald-500 focus:outline-none focus:ring-1 focus:ring-emerald-500 transition-colors"
            />
          </div>
        )}

        {activeView === "players" && (
          <div className="relative sm:w-40">
            <select
              value={posFilter}
              onChange={(e) => setPosFilter(e.target.value)}
              className="w-full appearance-none rounded-lg border border-gray-200 bg-white py-2.5 pl-3 pr-8 text-sm text-slate-900 shadow-sm focus:border-emerald-500 focus:outline-none focus:ring-1 focus:ring-emerald-500 transition-colors cursor-pointer"
            >
              {POSITIONS.map((p) => (
                <option key={p} value={p}>{p === "All" ? "All Positions" : p}</option>
              ))}
            </select>
            <svg className="pointer-events-none absolute right-2.5 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
              <path fillRule="evenodd" clipRule="evenodd" d="M5.22 8.22a.75.75 0 011.06 0L10 11.94l3.72-3.72a.75.75 0 111.06 1.06l-4.25 4.25a.75.75 0 01-1.06 0L5.22 9.28a.75.75 0 010-1.06z" />
            </svg>
          </div>
        )}

        <div className="relative sm:w-40">
          <select
            value={confFilter}
            onChange={(e) => setConfFilter(e.target.value)}
            className="w-full appearance-none rounded-lg border border-gray-200 bg-white py-2.5 pl-3 pr-8 text-sm text-slate-900 shadow-sm focus:border-emerald-500 focus:outline-none focus:ring-1 focus:ring-emerald-500 transition-colors cursor-pointer"
          >
            {CONFERENCES.map((c) => (
              <option key={c} value={c}>{c === "All" ? "All Conferences" : c}</option>
            ))}
          </select>
          <svg className="pointer-events-none absolute right-2.5 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
            <path fillRule="evenodd" clipRule="evenodd" d="M5.22 8.22a.75.75 0 011.06 0L10 11.94l3.72-3.72a.75.75 0 111.06 1.06l-4.25 4.25a.75.75 0 01-1.06 0L5.22 9.28a.75.75 0 010-1.06z" />
          </svg>
        </div>
      </div>

      {/* ── Player View ──────────────────────────────────────────────────── */}
      {activeView === "players" && (
        <>
          {/* Mobile cards */}
          <div className="md:hidden space-y-3">
            {displayPlayers.map((player, i) => (
              <Link
                key={player.id}
                href={`/players/${player.slug ?? player.id}`}
                className="block bg-white rounded-xl border border-gray-200 p-4 hover:border-slate-300 transition-colors shadow-sm"
              >
                <div className="flex items-center gap-3">
                  <span className="text-xs font-bold text-slate-400 w-6 text-right shrink-0">{i + 1}</span>
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
                        <span className={`shrink-0 inline-block rounded px-2 py-0.5 text-xs font-semibold uppercase tracking-wide ${positionBadgeClass(player.position)}`}>
                          {player.position}
                        </span>
                      )}
                    </div>
                    <div className="flex items-center justify-between mt-1">
                      <span className="text-xs text-slate-500 truncate">{player.team_name}</span>
                      <span
                        className="font-bold text-emerald-600 tabular-nums"
                        style={{ fontFamily: "var(--font-oswald), sans-serif" }}
                      >
                        {formatCurrency(player.cfo_valuation)}
                      </span>
                    </div>
                  </div>
                </div>
              </Link>
            ))}
          </div>

          {/* Desktop table */}
          <div className="hidden md:block bg-white rounded-xl shadow-md border border-gray-200 overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="sticky top-0 z-10 bg-slate-900 text-slate-300">
                  <tr>
                    <th className="px-3 py-3 text-left text-xs font-semibold uppercase tracking-widest w-12">#</th>
                    <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-widest">Player</th>
                    <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-widest w-16">Pos</th>
                    <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-widest">Team</th>
                    <th className="px-4 py-3 text-right text-xs font-semibold uppercase tracking-widest">Valuation</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {displayPlayers.map((player, i) => (
                    <tr key={player.id} className="hover:bg-slate-50 transition-colors">
                      <td className="px-3 py-3 text-xs font-bold text-slate-400">{i + 1}</td>
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-3">
                          <PlayerAvatar
                            headshot_url={player.headshot_url}
                            name={player.name}
                            position={player.position}
                            size={36}
                            className="shrink-0"
                          />
                          <Link
                            href={`/players/${player.slug ?? player.id}`}
                            className="font-semibold text-slate-900 hover:text-emerald-500 hover:underline transition-colors uppercase tracking-tight"
                            style={{ fontFamily: "var(--font-oswald), sans-serif" }}
                          >
                            {player.name}
                          </Link>
                        </div>
                      </td>
                      <td className="px-4 py-3">
                        {player.position ? (
                          <span className={`inline-block rounded px-2 py-0.5 text-xs font-semibold uppercase tracking-wide ${positionBadgeClass(player.position)}`}>
                            {player.position}
                          </span>
                        ) : <span className="text-slate-400">&mdash;</span>}
                      </td>
                      <td className="px-4 py-3">
                        <Link
                          href={`/teams/${player.team_slug ?? ""}`}
                          className="flex items-center gap-2 hover:text-emerald-500 transition-colors"
                        >
                          {player.team_logo && (
                            <Image src={player.team_logo} alt="" width={20} height={20} className="h-5 w-5 object-contain" />
                          )}
                          <span className="text-sm text-slate-700">{player.team_name}</span>
                        </Link>
                      </td>
                      <td className="px-4 py-3 text-right">
                        <span
                          className="font-bold text-emerald-600 tabular-nums"
                          style={{ fontFamily: "var(--font-oswald), sans-serif" }}
                        >
                          {formatCurrency(player.cfo_valuation)}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            <div className="border-t border-gray-100 bg-slate-50 px-4 py-3 flex items-center justify-between">
              <p className="text-xs text-slate-400">
                Showing <span className="font-semibold text-slate-600">{displayPlayers.length}</span> of{" "}
                <span className="font-semibold text-slate-600">{filteredPlayers.length}</span> portal transfers
              </p>
              {!showAll && filteredPlayers.length > 100 && (
                <button
                  onClick={() => setShowAll(true)}
                  className="text-xs font-semibold text-emerald-600 hover:text-emerald-700 transition-colors"
                >
                  Show All ({filteredPlayers.length})
                </button>
              )}
            </div>
          </div>
        </>
      )}

      {/* ── Team View ────────────────────────────────────────────────────── */}
      {activeView === "teams" && (
        <>
          {/* Mobile cards */}
          <div className="md:hidden space-y-3">
            {filteredTeams.map((team, i) => (
              <Link
                key={team.team_slug ?? i}
                href={`/teams/${team.team_slug ?? ""}?view=portal`}
                className="block bg-white rounded-xl border border-gray-200 p-4 hover:border-slate-300 transition-colors shadow-sm"
              >
                <div className="flex items-center gap-3">
                  <span className="text-xs font-bold text-slate-400 w-6 text-right shrink-0">{i + 1}</span>
                  {team.team_logo && (
                    <Image src={team.team_logo} alt="" width={36} height={36} className="h-9 w-9 object-contain shrink-0" />
                  )}
                  <div className="flex-1 min-w-0">
                    <h3
                      className="font-bold text-slate-900 uppercase tracking-tight truncate"
                      style={{ fontFamily: "var(--font-oswald), sans-serif" }}
                    >
                      {team.team_name}
                    </h3>
                    <div className="flex items-center justify-between mt-1">
                      <span className="text-xs text-slate-500">{team.conference} &middot; {team.portal_count} transfers</span>
                      <span
                        className="font-bold text-emerald-600 tabular-nums"
                        style={{ fontFamily: "var(--font-oswald), sans-serif" }}
                      >
                        {formatCompactCurrency(team.portal_value)}
                      </span>
                    </div>
                  </div>
                </div>
              </Link>
            ))}
          </div>

          {/* Desktop table */}
          <div className="hidden md:block bg-white rounded-xl shadow-md border border-gray-200 overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="sticky top-0 z-10 bg-slate-900 text-slate-300">
                  <tr>
                    <th className="px-3 py-3 text-left text-xs font-semibold uppercase tracking-widest w-12">#</th>
                    <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-widest">Team</th>
                    <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-widest">Conference</th>
                    <th className="px-4 py-3 text-right text-xs font-semibold uppercase tracking-widest">Portal Additions</th>
                    <th className="px-4 py-3 text-right text-xs font-semibold uppercase tracking-widest">Est. Portal Value</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {filteredTeams.map((team, i) => (
                    <tr key={team.team_slug ?? i} className="hover:bg-slate-50 transition-colors">
                      <td className="px-3 py-3 text-xs font-bold text-slate-400">{i + 1}</td>
                      <td className="px-4 py-3">
                        <Link
                          href={`/teams/${team.team_slug ?? ""}?view=portal`}
                          className="flex items-center gap-3 hover:text-emerald-500 transition-colors"
                        >
                          {team.team_logo && (
                            <Image src={team.team_logo} alt="" width={28} height={28} className="h-7 w-7 object-contain" />
                          )}
                          <span
                            className="font-semibold text-slate-900 uppercase tracking-tight"
                            style={{ fontFamily: "var(--font-oswald), sans-serif" }}
                          >
                            {team.team_name}
                          </span>
                        </Link>
                      </td>
                      <td className="px-4 py-3">
                        <span className="inline-block rounded px-2.5 py-0.5 text-xs font-semibold uppercase tracking-widest bg-slate-100 text-slate-600">
                          {team.conference}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-right font-semibold text-slate-700 tabular-nums">
                        {team.portal_count}
                      </td>
                      <td className="px-4 py-3 text-right">
                        <span
                          className="font-bold text-emerald-600 tabular-nums"
                          style={{ fontFamily: "var(--font-oswald), sans-serif" }}
                        >
                          {formatCompactCurrency(team.portal_value)}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            <div className="border-t border-gray-100 bg-slate-50 px-4 py-3">
              <p className="text-xs text-slate-400">
                <span className="font-semibold text-slate-600">{filteredTeams.length}</span> teams
              </p>
            </div>
          </div>
        </>
      )}
    </>
  );
}
