import Link from "next/link";
import { supabase } from "@/lib/supabase";
import type { Metadata } from "next";
import { BASE_URL } from "@/lib/constants";
import { formatCurrency } from "@/lib/utils";
import { basketballPositionBadgeClass } from "@/lib/ui-helpers";

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

function StarRating({ stars }: { stars: number | null }) {
  if (!stars) return <span className="text-slate-400">—</span>;
  return (
    <span className="text-amber-500 text-xs tracking-tight">
      {"★".repeat(Math.min(stars, 5))}
      {"☆".repeat(Math.max(0, 5 - stars))}
    </span>
  );
}

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
  origin_team: { university_name: string; slug: string | null; logo_url: string | null } | null;
  destination_team: { university_name: string; slug: string | null; logo_url: string | null } | null;
}

// Portal names that differ from DB names
const NAME_ALIASES: Record<string, string> = {
  "somto cyril": "somtochukwu cyril",
  "rob wright": "robert wright iii",
  "kennard davis": "kennard davis jr.",
  "richard barron": "rich barron",
  "jp estrella": "j.p. estrella",
};

export default async function BasketballPortalPage() {
  const [{ data: entries, error }, { data: playerSlugs }] = await Promise.all([
    supabase
      .from("basketball_portal_entries")
      .select(
        `id, player_name, position, status, star_rating,
         cfo_valuation, on3_nil_value, headshot_url,
         origin_school, destination_school,
         origin_team_id, destination_team_id,
         origin_team:origin_team_id (university_name, slug, logo_url),
         destination_team:destination_team_id (university_name, slug, logo_url)`
      )
      .order("cfo_valuation", { ascending: false }),
    supabase
      .from("basketball_players")
      .select("name, slug")
      .neq("slug", ""),
  ]);

  if (error) console.error("Portal query error:", error);

  // Build slug lookup: normalized name → slug
  const slugMap = new Map(
    (playerSlugs ?? [])
      .filter((p: { slug: string | null }) => p.slug)
      .map((p: { name: string; slug: string }) => [p.name.toLowerCase().trim(), p.slug]),
  );

  function getPlayerSlug(name: string): string | null {
    const norm = name.toLowerCase().trim();
    return slugMap.get(norm) ?? slugMap.get(NAME_ALIASES[norm] ?? "") ?? null;
  }

  const rows = (entries ?? []) as unknown as PortalEntry[];
  const committed = rows.filter((e) => e.status === "committed");
  const evaluating = rows.filter((e) => e.status === "evaluating");
  // Show committed first, then evaluating — each group by valuation desc
  const sorted = [...committed, ...evaluating];

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

      {/* Table */}
      <div className="mx-auto max-w-7xl px-4 pb-8">
        {sorted.length === 0 ? (
          <div className="bg-white rounded-xl shadow-md p-16 text-center">
            <p className="text-slate-400 text-sm">
              No portal entries found. Run sync_bball_portal_display.py to populate.
            </p>
          </div>
        ) : (
          <>
            {/* Mobile cards */}
            <div className="md:hidden space-y-3">
              {sorted.map((entry, i) => {
                const mobileSlug = getPlayerSlug(entry.player_name);
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
                      <div className="flex items-center justify-between gap-2">
                        {mobileSlug ? (
                          <Link
                            href={`/basketball/players/${mobileSlug}`}
                            className="font-bold text-slate-900 uppercase tracking-tight truncate hover:text-emerald-600 hover:underline transition-colors"
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
                        <StatusBadge status={entry.status} />
                      </div>
                      <div className="flex items-center justify-between mt-1">
                        <span className="text-xs text-slate-500 truncate flex items-center gap-1">
                          {/* eslint-disable-next-line @next/next/no-img-element */}
                          {(entry.origin_team?.logo_url || schoolLogo(entry.origin_school)) && (
                            <img src={(entry.origin_team?.logo_url || schoolLogo(entry.origin_school))!} alt="" width={14} height={14} className="h-3.5 w-3.5 object-contain shrink-0" />
                          )}
                          {entry.origin_team?.university_name ?? entry.origin_school ?? "?"}
                          <span className="text-slate-400 mx-0.5">→</span>
                          {entry.status === "committed" && (
                            <>
                              {/* eslint-disable-next-line @next/next/no-img-element */}
                              {(entry.destination_team?.logo_url || schoolLogo(entry.destination_school)) && (
                                <img src={(entry.destination_team?.logo_url || schoolLogo(entry.destination_school))!} alt="" width={14} height={14} className="h-3.5 w-3.5 object-contain shrink-0" />
                              )}
                            </>
                          )}
                          {entry.status === "committed" ? (entry.destination_team?.university_name ?? entry.destination_school ?? "—") : "—"}
                        </span>
                        <span
                          className="font-bold text-emerald-600 tabular-nums shrink-0"
                          style={{ fontFamily: "var(--font-oswald), sans-serif" }}
                        >
                          {entry.cfo_valuation != null
                            ? formatCurrency(entry.cfo_valuation)
                            : "—"}
                        </span>
                      </div>
                    </div>
                  </div>
                </div>
              );
              })}
            </div>

            {/* Desktop table */}
            <div className="hidden md:block bg-white rounded-xl shadow-md overflow-hidden border border-gray-200">
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead className="sticky top-0 z-10 bg-slate-900 text-slate-300">
                    <tr>
                      <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-widest">
                        Player
                      </th>
                      <th className="px-3 py-3 text-left text-xs font-semibold uppercase tracking-widest w-14">
                        Pos
                      </th>
                      <th className="px-3 py-3 text-center text-xs font-semibold uppercase tracking-widest w-20">
                        Stars
                      </th>
                      <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-widest">
                        From
                      </th>
                      <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-widest">
                        To
                      </th>
                      <th className="px-3 py-3 text-center text-xs font-semibold uppercase tracking-widest w-24">
                        Status
                      </th>
                      <th className="px-4 py-3 text-right text-xs font-semibold uppercase tracking-widest">
                        CFO Value
                      </th>
                    </tr>
                  </thead>

                  <tbody className="divide-y divide-gray-100">
                    {sorted.map((entry, i) => {
                      const originTeam = entry.origin_team;
                      const destTeam = entry.destination_team;
                      const playerSlug = getPlayerSlug(entry.player_name);
                      return (
                        <tr
                          key={entry.id}
                          className="hover:bg-slate-50 transition-colors"
                        >
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
                              <span className="text-slate-400">—</span>
                            )}
                          </td>
                          <td className="px-3 py-3 text-center">
                            <StarRating stars={entry.star_rating} />
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
                                <span>{entry.origin_school ?? "—"}</span>
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
                                  <span>{entry.destination_school ?? "—"}</span>
                                </div>
                              )
                            ) : (
                              <span className="text-slate-400">—</span>
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
                              <span className="text-slate-400 text-xs">—</span>
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
                  Showing portal activity for{" "}
                  <span className="font-semibold text-slate-600">
                    CFO-tracked programs
                  </span>{" "}
                  only
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
