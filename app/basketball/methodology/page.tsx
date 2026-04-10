import type { Metadata } from "next";
import Link from "next/link";
import { BASE_URL } from "@/lib/constants";

export const revalidate = false;

export const metadata: Metadata = {
  title: "Basketball Methodology | CollegeFrontOffice",
  description:
    "How CFO calculates NIL valuations for college basketball players — formula components, data sources, and calibration.",
  alternates: { canonical: `${BASE_URL}/basketball/methodology` },
};

export default function BasketballMethodologyPage() {
  return (
    <main className="min-h-screen bg-gray-100">
      {/* ── Hero ─────────────────────────────────────────────────────────── */}
      <section className="bg-slate-900 text-white px-6 py-8">
        <div className="mx-auto max-w-3xl">
          <h1
            className="text-4xl sm:text-5xl font-bold uppercase tracking-tight leading-none"
            style={{ fontFamily: "var(--font-oswald), sans-serif" }}
          >
            How We Value College Basketball Players
          </h1>
          <p className="mt-4 text-slate-400 text-base leading-relaxed max-w-2xl">
            College Front Office uses a multiplicative formula to estimate every basketball
            player&apos;s annualized NIL market value. With only 13 scholarships and 5 starters,
            basketball economics are driven by minutes share and role — not depth chart position.
            Players with no college minutes yet are valued on their recruiting profile and draft
            projection.
          </p>
        </div>
      </section>

      {/* ── Body ─────────────────────────────────────────────────────────── */}
      <div className="mx-auto max-w-3xl px-6 py-12 space-y-8">
        {/* ── Section 1: The Formula ───────────────────────────────────── */}
        <section className="bg-white rounded-xl shadow-md p-8">
          <h2
            className="text-xl font-bold text-slate-900 uppercase tracking-wide mb-4"
            style={{ fontFamily: "var(--font-oswald), sans-serif" }}
          >
            The Formula
          </h2>

          <div className="space-y-4">
            <div>
              <p className="text-xs uppercase tracking-widest text-slate-400 mb-2">
                Returning players (with stats)
              </p>
              <div className="bg-slate-50 rounded-lg border border-slate-200 p-4 font-mono text-sm text-slate-700 leading-relaxed">
                NIL Value = Position Base &times; NBA Draft Premium &times; Role Tier<br />
                &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&times; Talent (PER) &times; Market &times; Experience<br />
                &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;+ Social Premium
              </div>
            </div>

            <div>
              <p className="text-xs uppercase tracking-widest text-slate-400 mb-2">
                Incoming players (no college minutes)
              </p>
              <div className="bg-slate-50 rounded-lg border border-slate-200 p-4 font-mono text-sm text-slate-700 leading-relaxed">
                NIL Value = Position Base &times; NBA Draft Premium &times; 0.60<br />
                &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&times; Talent (Composite) &times; Market &times; Experience<br />
                &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;+ Social Premium
              </div>
            </div>
          </div>

          <p className="mt-4 text-sm text-slate-500 leading-relaxed">
            Every component is independently calibrated. The multiplicative structure means each
            factor compounds — a franchise player at a blue-blood program with a lottery projection
            receives the full benefit of all three multipliers stacking.
          </p>
        </section>

        {/* ── Section 2: Position Base ─────────────────────────────────── */}
        <section className="bg-white rounded-xl shadow-md p-8">
          <h2
            className="text-xl font-bold text-slate-900 uppercase tracking-wide mb-4"
            style={{ fontFamily: "var(--font-oswald), sans-serif" }}
          >
            Position Base
          </h2>
          <p className="text-sm text-slate-600 leading-relaxed mb-4">
            Sets the economic floor by position. Basketball position bases are intentionally flat —
            a center and a point guard are within 55% of each other. Role tier and draft premium
            create the real spread, not position.
          </p>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-slate-200 text-left">
                  <th className="py-2 pr-4 font-semibold text-slate-700">Position</th>
                  <th className="py-2 text-right font-semibold text-slate-700">Base Value</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {[
                  ["PG — Point Guard", "$350,000"],
                  ["SG — Shooting Guard", "$300,000"],
                  ["SF — Small Forward", "$275,000"],
                  ["PF — Power Forward", "$250,000"],
                  ["C — Center", "$225,000"],
                ].map(([pos, val]) => (
                  <tr key={pos}>
                    <td className="py-2 pr-4 text-slate-600">{pos}</td>
                    <td className="py-2 text-right font-semibold text-slate-900 tabular-nums">{val}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>

        {/* ── Section 3: NBA Draft Premium ─────────────────────────────── */}
        <section className="bg-white rounded-xl shadow-md p-8">
          <h2
            className="text-xl font-bold text-slate-900 uppercase tracking-wide mb-4"
            style={{ fontFamily: "var(--font-oswald), sans-serif" }}
          >
            NBA Draft Premium
          </h2>
          <p className="text-sm text-slate-600 leading-relaxed mb-4">
            Players with NBA draft projections receive a premium that reflects the massive
            gap between lottery contracts and the undrafted market. The curve is steeper than
            the NFL equivalent because NBA lottery picks sign 4-year guaranteed deals worth
            $10M+ per year.
          </p>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-slate-200 text-left">
                  <th className="py-2 pr-4 font-semibold text-slate-700">Projected Pick</th>
                  <th className="py-2 pr-4 font-semibold text-slate-700">Tier</th>
                  <th className="py-2 text-right font-semibold text-slate-700">Premium</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {[
                  ["1–5", "Consensus lottery", "3.50×"],
                  ["6–14", "Lottery", "2.60×"],
                  ["15–30", "Late first round", "1.80×"],
                  ["31–60", "Second round", "1.25×"],
                  ["Not projected", "Baseline", "1.00×"],
                ].map(([pick, tier, premium]) => (
                  <tr key={pick}>
                    <td className="py-2 pr-4 text-slate-600">{pick}</td>
                    <td className="py-2 pr-4 text-slate-500">{tier}</td>
                    <td className="py-2 text-right font-semibold text-slate-900 tabular-nums">{premium}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>

        {/* ── Section 4: Role Tier ─────────────────────────────────────── */}
        <section className="bg-white rounded-xl shadow-md p-8">
          <h2
            className="text-xl font-bold text-slate-900 uppercase tracking-wide mb-4"
            style={{ fontFamily: "var(--font-oswald), sans-serif" }}
          >
            Role Tier
          </h2>
          <p className="text-sm text-slate-600 leading-relaxed mb-4">
            The single biggest spread driver for players without a draft projection. Role tier
            is derived from minutes per game — a transparent, auditable proxy that coaches and
            fans already use to describe player roles.
          </p>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-slate-200 text-left">
                  <th className="py-2 pr-4 font-semibold text-slate-700">MPG</th>
                  <th className="py-2 pr-4 font-semibold text-slate-700">Role</th>
                  <th className="py-2 text-right font-semibold text-slate-700">Multiplier</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {[
                  ["30+", "Franchise", "2.20×"],
                  ["24–29", "Star", "1.65×"],
                  ["16–23", "Starter", "1.20×"],
                  ["8–15", "Rotation", "0.75×"],
                  ["< 8", "Bench", "0.30×"],
                  ["No stats", "Incoming", "0.60×"],
                ].map(([mpg, role, mult]) => (
                  <tr key={mpg}>
                    <td className="py-2 pr-4 text-slate-600">{mpg}</td>
                    <td className="py-2 pr-4 text-slate-500">{role}</td>
                    <td className="py-2 text-right font-semibold text-slate-900 tabular-nums">{mult}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="mt-4 rounded-lg bg-slate-50 border border-slate-200 p-4">
            <p className="text-sm text-slate-600 leading-relaxed">
              <span className="font-semibold text-slate-800">Sixth man handling:</span>{" "}
              A player logging 20+ minutes off the bench slots into Starter tier — we
              don&apos;t penalize rotation status, only minutes. The &ldquo;incoming&rdquo;
              multiplier (0.60&times;) sits between rotation and bench, so a 5-star freshman
              arriving with a lottery draft projection is valued well above a low-minutes
              veteran.
            </p>
          </div>
        </section>

        {/* ── Section 5: Talent Modifier ───────────────────────────────── */}
        <section className="bg-white rounded-xl shadow-md p-8">
          <h2
            className="text-xl font-bold text-slate-900 uppercase tracking-wide mb-4"
            style={{ fontFamily: "var(--font-oswald), sans-serif" }}
          >
            Talent Modifier
          </h2>
          <p className="text-sm text-slate-600 leading-relaxed mb-4">
            Measures individual talent above or below the college average. The signal source
            depends on whether a player has college game data.
          </p>

          <div className="space-y-6">
            <div className="border-l-4 border-blue-500 pl-5">
              <h3
                className="text-lg font-bold text-slate-900 mb-2"
                style={{ fontFamily: "var(--font-oswald), sans-serif" }}
              >
                Returning Players: PER
              </h3>
              <p className="text-sm text-slate-600 leading-relaxed mb-3">
                Player Efficiency Rating (PER) is the primary talent signal. NCAA average is
                roughly 15.0 — the tiers are calibrated around that baseline.
              </p>
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-slate-200 text-left">
                    <th className="py-2 pr-4 font-semibold text-slate-700">PER</th>
                    <th className="py-2 text-right font-semibold text-slate-700">Modifier</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {[["25+", "1.30×"], ["20–24", "1.20×"], ["15–19", "1.10×"], ["10–14", "1.00×"], ["< 10", "0.90×"]].map(([per, mod]) => (
                    <tr key={per}>
                      <td className="py-2 pr-4 text-slate-600">{per}</td>
                      <td className="py-2 text-right font-semibold text-slate-900 tabular-nums">{mod}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            <div className="border-l-4 border-purple-500 pl-5">
              <h3
                className="text-lg font-bold text-slate-900 mb-2"
                style={{ fontFamily: "var(--font-oswald), sans-serif" }}
              >
                Incoming Players: Composite Score
              </h3>
              <p className="text-sm text-slate-600 leading-relaxed mb-3">
                Players without college stats are evaluated on their 247Sports composite
                recruiting score — the best available pre-college talent signal.
              </p>
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-slate-200 text-left">
                    <th className="py-2 pr-4 font-semibold text-slate-700">Composite</th>
                    <th className="py-2 pr-4 font-semibold text-slate-700">Stars</th>
                    <th className="py-2 text-right font-semibold text-slate-700">Modifier</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {[
                    ["0.9900+", "5-star", "1.30×"],
                    ["0.8900–0.9899", "4-star", "1.15×"],
                    ["0.7900–0.8899", "3-star", "1.00×"],
                    ["< 0.7900", "Unranked", "0.85×"],
                  ].map(([comp, stars, mod]) => (
                    <tr key={comp}>
                      <td className="py-2 pr-4 text-slate-600 font-mono text-xs">{comp}</td>
                      <td className="py-2 pr-4 text-slate-500">{stars}</td>
                      <td className="py-2 text-right font-semibold text-slate-900 tabular-nums">{mod}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </section>

        {/* ── Section 6: Market Multiplier ─────────────────────────────── */}
        <section className="bg-white rounded-xl shadow-md p-8">
          <h2
            className="text-xl font-bold text-slate-900 uppercase tracking-wide mb-4"
            style={{ fontFamily: "var(--font-oswald), sans-serif" }}
          >
            Program &amp; Market
          </h2>
          <p className="text-sm text-slate-600 leading-relaxed mb-4">
            Where a player plays matters. Programs with larger fanbases, stronger NIL
            collectives, and more media exposure generate more NIL opportunity. Basketball
            market multipliers are calibrated independently from football — Duke basketball
            is a top-tier brand even though Duke football is mid-market.
          </p>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-slate-200 text-left">
                  <th className="py-2 pr-4 font-semibold text-slate-700">Multiplier</th>
                  <th className="py-2 pr-4 font-semibold text-slate-700">Program Tier</th>
                  <th className="py-2 font-semibold text-slate-700">Examples</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {[
                  ["1.25–1.30", "Blue bloods", "Duke, Kentucky, Kansas, UNC"],
                  ["1.15–1.24", "Elite programs", "Gonzaga, Houston, UConn"],
                  ["1.05–1.14", "Strong P4", "BYU (1.08), Iowa State, Baylor"],
                  ["0.95–1.04", "Mid conference", "TCU, UCF, Saint Mary's"],
                  ["0.80–0.94", "Lower visibility", "Smaller conference programs"],
                ].map(([mult, tier, examples]) => (
                  <tr key={mult}>
                    <td className="py-2 pr-4 text-slate-600 font-mono text-xs">{mult}</td>
                    <td className="py-2 pr-4 font-semibold text-slate-700">{tier}</td>
                    <td className="py-2 text-slate-500 text-xs">{examples}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>

        {/* ── Section 7: Experience Multiplier ─────────────────────────── */}
        <section className="bg-white rounded-xl shadow-md p-8">
          <h2
            className="text-xl font-bold text-slate-900 uppercase tracking-wide mb-4"
            style={{ fontFamily: "var(--font-oswald), sans-serif" }}
          >
            Experience
          </h2>
          <p className="text-sm text-slate-600 leading-relaxed mb-4">
            NIL earning power increases over a college career as players build name recognition,
            marketing history, and on-court track record.
          </p>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-slate-200 text-left">
                  <th className="py-2 pr-4 font-semibold text-slate-700">Class Year</th>
                  <th className="py-2 text-right font-semibold text-slate-700">Multiplier</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {[
                  ["Freshman", "0.85×"],
                  ["Sophomore", "0.95×"],
                  ["Junior", "1.05×"],
                  ["Senior", "1.10×"],
                  ["Graduate", "1.15×"],
                ].map(([year, mult]) => (
                  <tr key={year}>
                    <td className="py-2 pr-4 text-slate-600">{year}</td>
                    <td className="py-2 text-right font-semibold text-slate-900 tabular-nums">{mult}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>

        {/* ── Section 8: Social Premium ────────────────────────────────── */}
        <section className="bg-white rounded-xl shadow-md p-8">
          <h2
            className="text-xl font-bold text-slate-900 uppercase tracking-wide mb-4"
            style={{ fontFamily: "var(--font-oswald), sans-serif" }}
          >
            Social &amp; Brand Reach
          </h2>
          <p className="text-sm text-slate-600 leading-relaxed mb-4">
            A flat dollar bonus added after the multiplicative formula. Social followers are
            weighted by platform: TikTok at 1.2&times; Instagram&apos;s weight and Twitter/X at
            0.7&times; — basketball players skew younger and TikTok reach converts to NIL deals
            at a higher rate.
          </p>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-slate-200 text-left">
                  <th className="py-2 pr-4 font-semibold text-slate-700">Weighted Followers</th>
                  <th className="py-2 text-right font-semibold text-slate-700">Premium</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {[
                  ["1,000,000+", "$150,000"],
                  ["500,000+", "$75,000"],
                  ["100,000+", "$25,000"],
                  ["50,000+", "$10,000"],
                  ["10,000+", "$3,000"],
                  ["< 10,000", "$0"],
                ].map(([followers, premium]) => (
                  <tr key={followers}>
                    <td className="py-2 pr-4 text-slate-600">{followers}</td>
                    <td className="py-2 text-right font-semibold text-slate-900 tabular-nums">{premium}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>

        {/* ── Section 9: Data Sources ──────────────────────────────────── */}
        <section className="bg-white rounded-xl shadow-md p-8">
          <h2
            className="text-xl font-bold text-slate-900 uppercase tracking-wide mb-4"
            style={{ fontFamily: "var(--font-oswald), sans-serif" }}
          >
            Data Sources
          </h2>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-slate-200 text-left">
                  <th className="py-2 pr-4 font-semibold text-slate-700">Data</th>
                  <th className="py-2 font-semibold text-slate-700">Source</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {[
                  ["Rosters", "ESPN API"],
                  ["Season stats (MPG, PPG, RPG, APG, PER)", "ESPN Core Stats API"],
                  ["Recruiting composite scores", "247Sports"],
                  ["NBA draft projections", "CFO editorial (updated manually)"],
                  ["Social followers", "On3 NIL database"],
                  ["Transfer portal movements", "On3 transfer portal"],
                  ["Reported NIL deals", "Public reporting + CFO estimates"],
                ].map(([data, source]) => (
                  <tr key={data}>
                    <td className="py-2 pr-4 text-slate-600">{data}</td>
                    <td className="py-2 text-slate-500">{source}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>

        {/* ── Section 11: Limitations ──────────────────────────────────── */}
        <section className="bg-slate-900 text-white rounded-xl shadow-md p-6">
          <h2
            className="text-xl font-bold text-white uppercase tracking-wide mb-4"
            style={{ fontFamily: "var(--font-oswald), sans-serif" }}
          >
            Transparency &amp; Limitations
          </h2>
          <ul className="space-y-3">
            {[
              "Usage rate is minutes-based, not true possession-level usage. MPG is a transparent proxy that correlates tightly with actual role.",
              "Social data coverage varies by player. On3 does not track every athlete — players not in their database show $0 social premium.",
              "ESPN provides generic positions (G/F/C) for some players. Granular positions are corrected where recruiting data is available.",
            ].map((text) => (
              <li key={text} className="flex gap-3">
                <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-slate-500" />
                <p className="text-sm text-slate-300 leading-relaxed">{text}</p>
              </li>
            ))}
          </ul>
          <p className="mt-4 text-sm text-slate-400 leading-relaxed">
            We&apos;re transparent about our approach because we believe the NIL market works
            better when everyone has access to credible, independent valuations. These are
            estimates, not guarantees of what a player will or should earn.
          </p>
        </section>

        {/* ── Version / CTA ───────────────────────────────────────────── */}
        <div className="text-center pt-4">
          <p className="text-xs text-slate-400 mb-6">
            Basketball Valuation Engine V1.0 — launched 2025. Formula and calibration
            updated as new data becomes available.
          </p>
          <Link
            href="/basketball/players"
            className="inline-flex items-center gap-2 rounded-lg bg-emerald-500 hover:bg-emerald-600 text-white font-semibold px-6 py-3 transition-colors"
          >
            View Basketball Valuations
            <svg className="h-4 w-4" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
              <path fillRule="evenodd" d="M3 10a.75.75 0 01.75-.75h10.638L10.23 5.29a.75.75 0 111.04-1.08l5.5 5.25a.75.75 0 010 1.08l-5.5 5.25a.75.75 0 11-1.04-1.08l4.158-3.96H3.75A.75.75 0 013 10z" clipRule="evenodd" />
            </svg>
          </Link>
        </div>
      </div>
    </main>
  );
}
