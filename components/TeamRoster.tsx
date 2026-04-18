"use client";

import Link from "next/link";
import { formatCurrency } from "@/lib/utils";
import { positionBadgeClass } from "@/lib/ui-helpers";
import PlayerAvatar from "@/components/PlayerAvatar";
import RosterTabs, { type RosterTab } from "@/components/RosterTabs";

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
}

const TABS: RosterTab<Player>[] = [
  {
    key: "roster",
    label: "Full Roster",
    emptyMessage: "No players currently tracked for this team.",
    predicate: () => true,
  },
  {
    key: "portal",
    label: "Portal",
    emptyMessage: "No portal acquisitions for this team.",
    predicate: (p) => p.acquisition_type === "portal",
  },
  {
    key: "recruits",
    label: "Recruits",
    emptyMessage: "No incoming recruits for this team.",
    predicate: (p) => p.acquisition_type === "recruit",
  },
  {
    key: "retained",
    label: "Retained",
    emptyMessage: "No retained players for this team.",
    predicate: (p) => p.acquisition_type === "retained",
  },
];

export default function TeamRoster({ players }: TeamRosterProps) {
  return (
    <RosterTabs<Player> tabs={TABS} players={players}>
      {(filteredPlayers) => (
        <>
          {/* Mobile cards */}
          <div className="md:hidden space-y-3">
            {filteredPlayers.map((player) => {
              const isPrivate = !player.is_public;
              return (
                <Link
                  key={player.id}
                  href={`/football/players/${player.slug ?? player.id}`}
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
                      Est. NIL Value
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
                              href={`/football/players/${player.slug ?? player.id}`}
                              className="font-semibold text-slate-900 hover:text-emerald-500 hover:underline transition-colors uppercase tracking-tight"
                              style={{ fontFamily: "var(--font-oswald), sans-serif" }}
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
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>
        </>
      )}
    </RosterTabs>
  );
}
