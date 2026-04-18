import Link from "next/link";
import { Suspense } from "react";
import { supabase } from "@/lib/supabase";
import type { PostgrestError } from "@supabase/supabase-js";
import type { Metadata } from "next";
import { BASE_URL } from "@/lib/constants";
import { formatCurrency, formatCompactCurrency } from "@/lib/utils";
import {
  basketballPositionBadgeClass,
  roleTierBadgeClass,
  roleTierLabel,
  formatDraftProjectionBadge,
} from "@/lib/ui-helpers";
import PortalFilters from "@/components/PortalFilters";

export const revalidate = 300;

export const metadata: Metadata = {
  title: "Basketball Transfer Portal — NIL Valuations | College Front Office",
  description:
    "NIL valuations for college basketball transfer portal players at CFO-tracked programs.",
  openGraph: {
    title: "Basketball Transfer Portal | College Front Office",
    description:
      "NIL valuations for college basketball transfer portal players.",
  },
  alternates: { canonical: `${BASE_URL}/basketball/portal` },
};

function StatusBadge({ status }: { status: string }) {
  if (status === "committed") {
    return (
      <span className="inline-block rounded px-2 py-0.5 text-[10px] font-semibold bg-green-100 text-green-800">
        Committed
      </span>
    );
  }
  return (
    <span className="inline-block rounded px-2 py-0.5 text-[10px] font-semibold bg-amber-100 text-amber-800">
      In Portal
    </span>
  );
}

function Initials({ name, size = 36 }: { name: string; size?: number }) {
  const parts = name.trim().split(/\s+/);
  const initials =
    parts.length >= 2
      ? (parts[0][0] + parts[parts.length - 1][0]).toUpperCase()
      : name.slice(0, 2).toUpperCase();
  return (
    <div
      className="rounded-full bg-slate-200 flex items-center justify-center shrink-0"
      style={{ width: size, height: size }}
    >
      <span className="text-slate-500 font-bold" style={{ fontSize: size * 0.38 }}>
        {initials}
      </span>
    </div>
  );
}

const ESPN_LOGO: Record<string, number> = {
  "Alabama Crimson Tide": 333,
  "Boise State Broncos": 68,
  "California Golden Bears": 25,
  "Creighton Bluejays": 156,
  "Florida Gators": 57,
  "Georgetown Hoyas": 46,
  "Houston Cougars": 248,
  "Illinois Fighting Illini": 356,
  "Indiana Hoosiers": 84,
  "Iowa State Cyclones": 66,
  "Kansas State Wildcats": 2306,
  "Loyola (Chi) Ramblers": 2350,
  "North Carolina Tar Heels": 153,
  "Ohio State Buckeyes": 194,
  "Oklahoma Sooners": 201,
  "Oklahoma State Cowboys": 197,
  "Oregon State Beavers": 204,
  "Pittsburgh Panthers": 221,
  "Tennessee Volunteers": 2633,
  "Texas A&M Aggies": 245,
  "USF Bulls": 58,
  "University of San Francisco Dons": 2539,
  "Villanova Wildcats": 222,
  "Xavier Musketeers": 2752,
};

function schoolLogo(name: string | null): string | null {
  if (!name) return null;
  const id = ESPN_LOGO[name];
  return id ? `https://a.espncdn.com/i/teamlogos/ncaa/500/${id}.png` : null;
}

interface PortalEntry {
  id: string;
  player_name: string;
  position: string | null;
  status: string;
  star_rating: number | null;
  cfo_valuation: number | null;
  on3_nil_value: number | null;
  headshot_url: string | null;
  origin_school: string | null;
  destination_school: string | null;
  origin_team_id: string | null;
  destination_team_id: string | null;
  origin_team: { university_name: string; slug: string | null; logo_url: string | null; conference: string | null } | null;
  destination_team: { university_name: string; slug: string | null; logo_url: string | null; conference: string | null } | null;
}

interface TeamInfo {
  id: string;
  university_name: string;
  slug: string;
  logo_url: string | null;
  conference: string | null;
}

// Portal names that differ from DB names
const NAME_ALIASES: Record<string, string> = {
  "somto cyril": "somtochukwu cyril",
  "rob wright": "robert wright iii",
  "kennard davis": "kennard davis jr.",
  "richard barron": "rich barron",
  "jp estrella": "j.p. estrella",
};

interface PageProps {
  searchParams: Promise<{ view?: string; q?: string; pos?: string; status?: string; conf?: string }>;
}

async function fetchAllPortalEntries(): Promise<{
  data: PortalEntry[];
  error: PostgrestError | null;
}> {
  const PAGE_SIZE = 1000;
  const rows: PortalEntry[] = [];
  let offset = 0;
  while (true) {
    const { data, error } = await supabase
      .from("basketball_portal_entries")
      .select(
        `id, player_name, position, status, star_rating,
         cfo_valuation, on3_nil_value, headshot_url,
         origin_school, destination_school,
         origin_team_id, destination_team_id,
         origin_team:origin_team_id (university_name, slug, logo_url, conference),
         destination_team:destination_team_id (university_name, slug, logo_url, conference)`
      )
      .order("cfo_valuation", { ascending: false })
      .order("id", { ascending: true })
      .range(offset, offset + PAGE_SIZE - 1);
    if (error) return { data: rows, error };
    const batch = (data ?? []) as unknown as PortalEntry[];
    rows.push(...batch);
    if (!data || data.length < PAGE_SIZE) break;
    offset += PAGE_SIZE;
  }
  return { data: rows, error: null };
}

export default async function BasketballPortalPage({ searchParams }: PageProps) {
  const params = await searchParams;
  const view = params.view ?? "player";
  const search = params.q ?? "";
  const position = params.pos ?? "";
  const statusFilter = params.status?.toLowerCase() ?? "";
  const confFilter = params.conf ?? "";

  // Fetch entries (paginated) and teams in parallel
  const [{ data: entries, error }, { data: teams }] = await Promise.all([
    fetchAllPortalEntries(),
    supabase
      .from("basketball_teams")
      .select("id, university_name, slug, logo_url, conference")
      .order("university_name"),
  ]);

  // Paginate basketball_players — widen the SELECT to carry slug + stats in
  // the same round trip. Two maps are built from the same iteration (F3a).
  const PAGE_SIZE = 1000;
  type PlayerRow = {
    name: string;
    slug: string | null;
    role_tier: string | null;
    ppg: number | null;
    nba_draft_projection: number | null;
  };
  const allPlayerRows: PlayerRow[] = [];
  let offset = 0;
  while (true) {
    const { data } = await supabase
      .from("basketball_players")
      .select("name, slug, role_tier, ppg, nba_draft_projection")
      .range(offset, offset + PAGE_SIZE - 1);
    allPlayerRows.push(...((data ?? []) as PlayerRow[]));
    if (!data || data.length < PAGE_SIZE) break;
    offset += PAGE_SIZE;
  }

  if (error) console.error("Portal query error:", error);

  const allRows = (entries ?? []) as unknown as PortalEntry[];
  const allTeams = (teams ?? []) as TeamInfo[];

  // Build slug + stats lookups in one pass.
  type PlayerStats = {
    role_tier: string | null;
    ppg: number | null;
    draft: number | null;
  };
  const slugMap = new Map<string, string>();
  const statsMap = new Map<string, PlayerStats>();
  for (const p of allPlayerRows) {
    const norm = p.name.toLowerCase().trim();
    if (p.slug) slugMap.set(norm, p.slug);
    statsMap.set(norm, {
      role_tier: p.role_tier,
      ppg: p.ppg,
      draft: p.nba_draft_projection,
    });
  }

  function getPlayerSlug(name: string): string | null {
    const norm = name.toLowerCase().trim();
    return slugMap.get(norm) ?? slugMap.get(NAME_ALIASES[norm] ?? "") ?? null;
  }

  function getPlayerStats(name: string): PlayerStats | undefined {
    const norm = name.toLowerCase().trim();
    return statsMap.get(norm) ?? statsMap.get(NAME_ALIASES[norm] ?? "");
  }

  function formatPpg(ppg: number | null | undefined): string | null {
    if (ppg == null || ppg <= 0) return null;
    return ppg.toFixed(1);
  }

  // Conference team IDs for filtering
  const confTeamIds = confFilter
    ? new Set(allTeams.filter((t) => t.conference === confFilter).map((t) => t.id))
    : null;

  // Filter entries for By Player view
  let filtered = allRows;
  if (search) filtered = filtered.filter((e) => e.player_name.toLowerCase().includes(search.toLowerCase()));
  if (position) filtered = filtered.filter((e) => e.position === position);
  if (statusFilter) filtered = filtered.filter((e) => e.status === statusFilter);
  if (confTeamIds) {
    filtered = filtered.filter(
      (e) => (e.origin_team_id && confTeamIds.has(e.origin_team_id)) || (e.destination_team_id && confTeamIds.has(e.destination_team_id)),
    );
  }

  // Sort: committed first, then evaluating
  const committed = filtered.filter((e) => e.status === "committed");
  const evaluating = filtered.filter((e) => e.status === "evaluating");
  const sorted = [...committed, ...evaluating];

  // By Team stats
  const teamStats = allTeams
    .filter((t) => !confFilter || t.conference === confFilter)
    .map((t) => {
      const incoming = allRows.filter((e) => e.destination_team_id === t.id && e.status === "committed");
      const outgoing = allRows.filter((e) => e.origin_team_id === t.id && e.status === "committed" && e.destination_team_id !== t.id);
      const portal = allRows.filter((e) => e.origin_team_id === t.id && e.status === "evaluating");
      const inVal = incoming.reduce((s, e) => s + (e.cfo_valuation ?? 0), 0);
      const outVal = outgoing.reduce((s, e) => s + (e.cfo_valuation ?? 0), 0);
      return {
        ...t,
        inCount: incoming.length,
        outCount: outgoing.length,
        evalCount: portal.length,
        acquiredValue: inVal,
      };
    })
    .sort((a, b) => b.acquiredValue - a.acquiredValue);

  return (
    <main className="min-h-screen bg-gray-100">
      {/* Hero */}
      <div className="bg-slate-900 text-white px-6 py-6">
        <div className="mx-auto max-w-7xl flex items-center justify-between">
          <div>
            <h1
              className="text-4xl sm:text-5xl font-bold uppercase tracking-tight leading-none"
              style={{ fontFamily: "var(--font-oswald), sans-serif" }}
            >
              Basketball Transfer Portal Valuations
            </h1>
          </div>
          <span className="hidden sm:inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-semibold bg-emerald-500/20 text-emerald-400 ring-1 ring-emerald-500/40">
            <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 animate-pulse" />
            Portal Open
          </span>
        </div>
      </div>

      {/* Filters */}
      <div className="mx-auto max-w-7xl px-4">
        <Suspense>
          <PortalFilters
            view={view}
            totalPlayers={allRows.length}
            totalTeams={allTeams.length}
          />
        </Suspense>
      </div>

      {/* Content */}
      <div className="mx-auto max-w-7xl px-4 pb-8">
        {view === "team" ? (
          /* ── By Team View ──────────────────────────────────────────── */
          <div className="bg-white rounded-xl shadow-md overflow-hidden border border-gray-200">
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="sticky top-0 z-10 bg-slate-900 text-slate-300">
                  <tr>
                    <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-widest">Team</th>
                    <th className="px-3 py-3 text-left text-xs font-semibold uppercase tracking-widest w-28">Conference</th>
                    <th className="px-3 py-3 text-center text-xs font-semibold uppercase tracking-widest w-14">In</th>
                    <th className="px-3 py-3 text-center text-xs font-semibold uppercase tracking-widest w-14">Out</th>
                    <th className="px-3 py-3 text-center text-xs font-semibold uppercase tracking-widest w-20">In Portal</th>
                    <th className="px-4 py-3 text-right text-xs font-semibold uppercase tracking-widest">Acquired Value</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {teamStats.map((t) => (
                    <tr key={t.id} className="hover:bg-slate-50 transition-colors">
                      <td className="px-4 py-3">
                        <Link
                          href={`/basketball/teams/${t.slug}`}
                          className="flex items-center gap-3 hover:underline"
                        >
                          {t.logo_url && (
                            // eslint-disable-next-line @next/next/no-img-element
                            <img src={t.logo_url} alt={t.university_name} width={24} height={24} className="h-6 w-6 object-contain shrink-0" />
                          )}
                          <span
                            className="font-semibold text-slate-900 uppercase tracking-tight"
                            style={{ fontFamily: "var(--font-oswald), sans-serif" }}
                          >
                            {t.university_name}
                          </span>
                        </Link>
                      </td>
                      <td className="px-3 py-3 text-xs text-slate-500">{t.conference}</td>
                      <td className="px-3 py-3 text-center">
                        {t.inCount > 0 ? (
                          <span className="font-semibold text-green-700">{t.inCount}</span>
                        ) : (
                          <span className="text-slate-300">0</span>
                        )}
                      </td>
                      <td className="px-3 py-3 text-center">
                        {t.outCount > 0 ? (
                          <span className="font-semibold text-red-600">{t.outCount}</span>
                        ) : (
                          <span className="text-slate-300">0</span>
                        )}
                      </td>
                      <td className="px-3 py-3 text-center">
                        {t.evalCount > 0 ? (
                          <span className="font-semibold text-amber-600">{t.evalCount}</span>
                        ) : (
                          <span className="text-slate-300">0</span>
                        )}
                      </td>
                      <td className="px-4 py-3 text-right">
                        <span
                          className="font-bold tabular-nums text-slate-900"
                          style={{ fontFamily: "var(--font-oswald), sans-serif" }}
                        >
                          {formatCompactCurrency(t.acquiredValue)}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        ) : sorted.length === 0 ? (
          <div className="bg-white rounded-xl shadow-md p-16 text-center">
            <p className="text-slate-400 text-sm">
              No portal entries match your filters.
            </p>
          </div>
        ) : (
          <>
            {/* ── By Player: Mobile cards ────────────────────────────── */}
            <div className="md:hidden space-y-3">
              {sorted.map((entry) => {
                const mobileSlug = getPlayerSlug(entry.player_name);
                const mobileStats = getPlayerStats(entry.player_name);
                const mobilePpg = formatPpg(mobileStats?.ppg);
                return (
                <div
                  key={entry.id}
                  className="bg-white rounded-xl border border-gray-200 p-4 shadow-sm"
                >
                  <div className="flex items-center gap-3">
                    {entry.headshot_url ? (
                      // eslint-disable-next-line @next/next/no-img-element
                      <img
                        src={entry.headshot_url}
                        alt={entry.player_name}
                        width={44}
                        height={44}
                        className="rounded-full object-cover bg-slate-200 shrink-0"
                        style={{ width: 44, height: 44 }}
                      />
                    ) : (
                      <Initials name={entry.player_name} size={44} />
                    )}
                    <div className="flex-1 min-w-0">
                      <div className="flex items-start justify-between gap-2">
                        <div className="min-w-0">
                          {mobileSlug ? (
                            <Link
                              href={`/basketball/players/${mobileSlug}`}
                              className="font-bold text-slate-900 uppercase tracking-tight truncate hover:text-emerald-600 hover:underline transition-colors block"
                              style={{ fontFamily: "var(--font-oswald), sans-serif" }}
                            >
                              {entry.player_name}
                            </Link>
                          ) : (
                            <h3
                              className="font-bold text-slate-900 uppercase tracking-tight truncate"
                              style={{ fontFamily: "var(--font-oswald), sans-serif" }}
                            >
                              {entry.player_name}
                            </h3>
                          )}
                          {(entry.position || mobilePpg) && (
                            <div className="flex items-center gap-1 mt-0.5 flex-wrap">
                              {entry.position && (
                                <span
                                  className={`inline-block rounded px-2 py-0.5 text-xs font-semibold uppercase tracking-wide ${basketballPositionBadgeClass(entry.position)}`}
                                >
                                  {entry.position}
                                </span>
                              )}
                              {mobilePpg && (
                                <span className="text-xs text-slate-500">
                                  · {mobilePpg} PPG
                                </span>
                              )}
                            </div>
                          )}
                        </div>
                        <StatusBadge status={entry.status} />
                      </div>
                      <div className="flex items-center justify-between gap-2 mt-1">
                        <span className="text-xs text-slate-500 truncate flex items-center gap-1">
                          {/* eslint-disable-next-line @next/next/no-img-element */}
                          {(entry.origin_team?.logo_url || schoolLogo(entry.origin_school)) && (
                            <img src={(entry.origin_team?.logo_url || schoolLogo(entry.origin_school))!} alt="" width={14} height={14} className="h-3.5 w-3.5 object-contain shrink-0" />
                          )}
                          {entry.origin_team?.university_name ?? entry.origin_school ?? "?"}
                          <span className="text-slate-400 mx-0.5">&rarr;</span>
                          {entry.status === "committed" && (
                            <>
                              {/* eslint-disable-next-line @next/next/no-img-element */}
                              {(entry.destination_team?.logo_url || schoolLogo(entry.destination_school)) && (
                                <img src={(entry.destination_team?.logo_url || schoolLogo(entry.destination_school))!} alt="" width={14} height={14} className="h-3.5 w-3.5 object-contain shrink-0" />
                              )}
                            </>
                          )}
                          {entry.status === "committed" ? (entry.destination_team?.university_name ?? entry.destination_school ?? "\u2014") : "\u2014"}
                        </span>
                        <div className="shrink-0 flex flex-col items-end gap-1">
                          <span
                            className="font-bold text-emerald-600 tabular-nums"
                            style={{ fontFamily: "var(--font-oswald), sans-serif" }}
                          >
                            {entry.cfo_valuation != null
                              ? formatCurrency(entry.cfo_valuation)
                              : "\u2014"}
                          </span>
                          {mobileStats?.role_tier && (
                            <span className={roleTierBadgeClass(mobileStats.role_tier, "light")}>
                              {roleTierLabel(mobileStats.role_tier)}
                            </span>
                          )}
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              );
              })}
            </div>

            {/* ── By Player: Desktop table ───────────────────────────── */}
            <div className="hidden md:block bg-white rounded-xl shadow-md overflow-hidden border border-gray-200">
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead className="sticky top-0 z-10 bg-slate-900 text-slate-300">
                    <tr>
                      <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-widest">Player</th>
                      <th className="px-3 py-3 text-left text-xs font-semibold uppercase tracking-widest w-14">Pos</th>
                      <th className="hidden lg:table-cell px-3 py-3 text-right text-xs font-semibold uppercase tracking-widest w-16">PPG</th>
                      <th className="hidden lg:table-cell px-3 py-3 text-left text-xs font-semibold uppercase tracking-widest w-24">Role</th>
                      <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-widest">From</th>
                      <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-widest">To</th>
                      <th className="px-3 py-3 text-center text-xs font-semibold uppercase tracking-widest w-24">Status</th>
                      <th className="px-4 py-3 text-right text-xs font-semibold uppercase tracking-widest">Est. NIL Value</th>
                    </tr>
                  </thead>

                  <tbody className="divide-y divide-gray-100">
                    {sorted.map((entry) => {
                      const originTeam = entry.origin_team;
                      const destTeam = entry.destination_team;
                      const playerSlug = getPlayerSlug(entry.player_name);
                      const stats = getPlayerStats(entry.player_name);
                      const ppgDisplay = formatPpg(stats?.ppg);
                      const draftLabel = formatDraftProjectionBadge(stats?.draft ?? null);
                      return (
                        <tr key={entry.id} className="hover:bg-slate-50 transition-colors">
                          <td className="px-4 py-3">
                            <div className="flex items-center gap-3">
                              {entry.headshot_url ? (
                                // eslint-disable-next-line @next/next/no-img-element
                                <img
                                  src={entry.headshot_url}
                                  alt={entry.player_name}
                                  width={36}
                                  height={36}
                                  className="rounded-full object-cover bg-slate-200 shrink-0"
                                  style={{ width: 36, height: 36 }}
                                />
                              ) : (
                                <Initials name={entry.player_name} size={36} />
                              )}
                              {playerSlug ? (
                                <Link
                                  href={`/basketball/players/${playerSlug}`}
                                  className="font-semibold text-slate-900 hover:text-emerald-600 hover:underline transition-colors uppercase tracking-tight"
                                  style={{ fontFamily: "var(--font-oswald), sans-serif" }}
                                >
                                  {entry.player_name}
                                </Link>
                              ) : (
                                <span
                                  className="font-semibold text-slate-900 uppercase tracking-tight"
                                  style={{ fontFamily: "var(--font-oswald), sans-serif" }}
                                >
                                  {entry.player_name}
                                </span>
                              )}
                              {draftLabel && (
                                <span className="inline-block rounded px-1.5 py-0.5 text-[10px] font-semibold bg-purple-500 text-white ml-1.5">
                                  {draftLabel}
                                </span>
                              )}
                            </div>
                          </td>
                          <td className="px-3 py-3">
                            {entry.position ? (
                              <span
                                className={`inline-block rounded px-2 py-0.5 text-xs font-semibold uppercase tracking-wide ${basketballPositionBadgeClass(entry.position)}`}
                              >
                                {entry.position}
                              </span>
                            ) : (
                              <span className="text-slate-400">&mdash;</span>
                            )}
                          </td>
                          <td className="hidden lg:table-cell px-3 py-3 text-right">
                            {ppgDisplay ? (
                              <span
                                className="font-bold text-emerald-600 tabular-nums"
                                style={{ fontFamily: "var(--font-oswald), sans-serif" }}
                              >
                                {ppgDisplay}
                              </span>
                            ) : (
                              <span className="text-slate-400 text-xs">&mdash;</span>
                            )}
                          </td>
                          <td className="hidden lg:table-cell px-3 py-3">
                            {stats?.role_tier ? (
                              <span className={roleTierBadgeClass(stats.role_tier, "light")}>
                                {roleTierLabel(stats.role_tier)}
                              </span>
                            ) : (
                              <span className="text-slate-400 text-xs">&mdash;</span>
                            )}
                          </td>
                          <td className="px-4 py-3 text-xs text-slate-600">
                            {originTeam?.slug ? (
                              <Link
                                href={`/basketball/teams/${originTeam.slug}`}
                                className="flex items-center gap-2 hover:underline transition-colors"
                              >
                                {originTeam.logo_url && (
                                  // eslint-disable-next-line @next/next/no-img-element
                                  <img src={originTeam.logo_url} alt={originTeam.university_name} width={20} height={20} className="h-5 w-5 object-contain shrink-0" />
                                )}
                                <span>{originTeam.university_name}</span>
                              </Link>
                            ) : (
                              <div className="flex items-center gap-2">
                                {schoolLogo(entry.origin_school) && (
                                  // eslint-disable-next-line @next/next/no-img-element
                                  <img src={schoolLogo(entry.origin_school)!} alt={entry.origin_school ?? ""} width={20} height={20} className="h-5 w-5 object-contain shrink-0" />
                                )}
                                <span>{entry.origin_school ?? "\u2014"}</span>
                              </div>
                            )}
                          </td>
                          <td className="px-4 py-3 text-xs text-slate-600">
                            {entry.status === "committed" ? (
                              destTeam?.slug ? (
                                <Link
                                  href={`/basketball/teams/${destTeam.slug}`}
                                  className="flex items-center gap-2 hover:underline transition-colors font-medium text-slate-800"
                                >
                                  {destTeam.logo_url && (
                                    // eslint-disable-next-line @next/next/no-img-element
                                    <img src={destTeam.logo_url} alt={destTeam.university_name} width={20} height={20} className="h-5 w-5 object-contain shrink-0" />
                                  )}
                                  <span>{destTeam.university_name}</span>
                                </Link>
                              ) : (
                                <div className="flex items-center gap-2">
                                  {schoolLogo(entry.destination_school) && (
                                    // eslint-disable-next-line @next/next/no-img-element
                                    <img src={schoolLogo(entry.destination_school)!} alt={entry.destination_school ?? ""} width={20} height={20} className="h-5 w-5 object-contain shrink-0" />
                                  )}
                                  <span>{entry.destination_school ?? "\u2014"}</span>
                                </div>
                              )
                            ) : (
                              <span className="text-slate-400">&mdash;</span>
                            )}
                          </td>
                          <td className="px-3 py-3 text-center">
                            <StatusBadge status={entry.status} />
                          </td>
                          <td className="px-4 py-3 text-right">
                            {entry.cfo_valuation != null ? (
                              <span
                                className="font-bold text-emerald-600 tabular-nums"
                                style={{ fontFamily: "var(--font-oswald), sans-serif" }}
                              >
                                {formatCurrency(entry.cfo_valuation)}
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

              <div className="border-t border-gray-100 bg-slate-50 px-4 py-3 flex items-center justify-between">
                <p className="text-xs text-slate-400">
                  Showing{" "}
                  <span className="font-semibold text-slate-600">{sorted.length}</span>{" "}
                  portal entries
                </p>
                <p className="text-xs text-slate-400">
                  <Link
                    href="/basketball/methodology"
                    className="text-slate-500 hover:text-slate-700 underline transition-colors"
                  >
                    How are these calculated?
                  </Link>
                </p>
              </div>
            </div>
          </>
        )}
      </div>
    </main>
  );
}
