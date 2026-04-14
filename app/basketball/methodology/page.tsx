import type { Metadata } from "next";
import Link from "next/link";
import { BASE_URL } from "@/lib/constants";

export const revalidate = false;

export const metadata: Metadata = {
  title: "How Basketball NIL Valuations Work — CFO Methodology | College Front Office",
  description:
    "Learn how College Front Office calculates NIL valuations for college basketball players and recruits. Our proprietary multi-factor model explained.",
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
            How CFO Basketball Valuations Work
          </h1>
          <p className="mt-4 text-slate-400 text-base leading-relaxed max-w-2xl">
            College Front Office uses a proprietary multi-factor model to estimate every
            basketball player&apos;s annualized NIL market value. With only 13 scholarships
            and five starters, basketball NIL economics are driven by role, program prestige,
            draft projection, and market reach. These are proprietary estimates, not official
            financial disclosures.
          </p>
        </div>
      </section>

      {/* ── Body ─────────────────────────────────────────────────────────── */}
      <div className="mx-auto max-w-3xl px-6 py-12 space-y-8">
        {/* ── Section 1: What We Measure ─────────────────────────────────── */}
        <section className="bg-white rounded-xl shadow-md p-8">
          <h2
            className="text-xl font-bold text-slate-900 uppercase tracking-wide mb-4"
            style={{ fontFamily: "var(--font-oswald), sans-serif" }}
          >
            What We Measure
          </h2>
          <div className="space-y-6">
            <div className="border-l-4 border-blue-500 pl-5">
              <h3
                className="text-lg font-bold text-slate-900 mb-2"
                style={{ fontFamily: "var(--font-oswald), sans-serif" }}
              >
                Minutes &amp; Role
              </h3>
              <p className="text-sm text-slate-600 leading-relaxed">
                A player&apos;s contribution on the court is the foundation of their value. We
                measure how much a program depends on a player — not just their statistics, but
                how central they are to the team&apos;s rotation. The more a program relies on a
                player, the more that player is worth in the NIL market.
              </p>
            </div>

            <div className="border-l-4 border-emerald-500 pl-5">
              <h3
                className="text-lg font-bold text-slate-900 mb-2"
                style={{ fontFamily: "var(--font-oswald), sans-serif" }}
              >
                Position Value
              </h3>
              <p className="text-sm text-slate-600 leading-relaxed">
                Not all positions command equal NIL earning power. Guards who run offenses and
                create for teammates tend to attract more NIL interest than bigs, reflecting
                broader market dynamics in how programs and brands value different roles on the
                floor. Our position-specific base values are calibrated to the Power 4 market
                using transfer portal deal data and publicly reported NIL figures.
              </p>
            </div>

            <div className="border-l-4 border-blue-500 pl-5">
              <h3
                className="text-lg font-bold text-slate-900 mb-2"
                style={{ fontFamily: "var(--font-oswald), sans-serif" }}
              >
                NBA Draft Projection
              </h3>
              <p className="text-sm text-slate-600 leading-relaxed">
                Players with credible NBA draft stock carry a premium that reflects their scarcity
                and the time-limited window for programs to keep them. The gap between a lottery
                pick and an undrafted player is massive — NBA lottery contracts are four-year
                guaranteed deals worth tens of millions. When a player has meaningful draft
                attention, that projection is weighted heavily in our model.
              </p>
            </div>

            <div className="border-l-4 border-emerald-500 pl-5">
              <h3
                className="text-lg font-bold text-slate-900 mb-2"
                style={{ fontFamily: "var(--font-oswald), sans-serif" }}
              >
                Program &amp; Market
              </h3>
              <p className="text-sm text-slate-600 leading-relaxed">
                Where a player plays matters. The same player is worth more at a blue-blood
                program than at a mid-major, because NIL collectives, alumni networks, and media
                markets differ dramatically by school. Basketball market multipliers are calibrated
                independently from football — Duke basketball is a top-tier brand even though
                Duke football is mid-market.
              </p>
            </div>

            <div className="border-l-4 border-amber-500 pl-5">
              <h3
                className="text-lg font-bold text-slate-900 mb-2"
                style={{ fontFamily: "var(--font-oswald), sans-serif" }}
              >
                Talent Assessment
              </h3>
              <p className="text-sm text-slate-600 leading-relaxed">
                For players with college game tape, we assess efficiency and production relative
                to the average college player. For incoming players without college stats,
                recruiting profile and national ranking serve as the primary talent signal. The
                model uses the best available signal for each player — never guessing when real
                data exists.
              </p>
            </div>

            <div className="border-l-4 border-purple-500 pl-5">
              <h3
                className="text-lg font-bold text-slate-900 mb-2"
                style={{ fontFamily: "var(--font-oswald), sans-serif" }}
              >
                Experience &amp; Eligibility
              </h3>
              <p className="text-sm text-slate-600 leading-relaxed">
                A senior who has built name recognition over four years of college basketball
                commands more NIL earning power than an identical freshman. Our model adjusts
                for class year, recognizing that mid-career players with established tape and
                marketing history often command the strongest position.
              </p>
            </div>

            <div className="border-l-4 border-pink-500 pl-5">
              <h3
                className="text-lg font-bold text-slate-900 mb-2"
                style={{ fontFamily: "var(--font-oswald), sans-serif" }}
              >
                Social &amp; Brand Reach
              </h3>
              <p className="text-sm text-slate-600 leading-relaxed">
                Personal brand matters in NIL. Followers, engagement, and platform presence
                translate directly into deal value. A player with a significant social following
                earns a premium on top of their on-court valuation. Social reach is a meaningful
                bonus but is intentionally capped — College Front Office is a basketball-first
                valuation.
              </p>
            </div>
          </div>
        </section>

        {/* ── Section 2: How We Value Recruits ────────────────────────────── */}
        <section className="bg-white rounded-xl shadow-md p-8">
          <h2
            className="text-xl font-bold text-slate-900 uppercase tracking-wide mb-4"
            style={{ fontFamily: "var(--font-oswald), sans-serif" }}
          >
            How We Value Recruits
          </h2>
          <p className="text-sm text-slate-600 leading-relaxed mb-5">
            College Front Office also values elite high school basketball recruits — the
            four-star and five-star prospects who make up the next generation of college talent.
            Valuing recruits requires a different approach than valuing college athletes, because
            high school players don&apos;t have college production data, minutes logs, or draft
            projections. Instead, we rely on the signals that actually drive the recruiting market.
          </p>
          <div className="space-y-6">
            <div className="border-l-4 border-purple-500 pl-5">
              <h3
                className="text-lg font-bold text-slate-900 mb-2"
                style={{ fontFamily: "var(--font-oswald), sans-serif" }}
              >
                Recruiting Profile
              </h3>
              <p className="text-sm text-slate-600 leading-relaxed">
                For high school players who haven&apos;t taken a college floor yet, national
                recruiting rankings and composite scores serve as our primary talent signal.
                Higher-rated recruits consistently command larger NIL packages, and our model
                reflects that relationship.
              </p>
            </div>

            <div className="border-l-4 border-blue-500 pl-5">
              <h3
                className="text-lg font-bold text-slate-900 mb-2"
                style={{ fontFamily: "var(--font-oswald), sans-serif" }}
              >
                Program Commitment
              </h3>
              <p className="text-sm text-slate-600 leading-relaxed">
                A five-star recruit committed to a powerhouse program with a strong NIL collective
                and large fanbase has a different market than the same player who is uncommitted or
                headed to a smaller program. Our model accounts for the financial ecosystem a recruit
                is entering.
              </p>
            </div>

            <div className="border-l-4 border-emerald-500 pl-5">
              <h3
                className="text-lg font-bold text-slate-900 mb-2"
                style={{ fontFamily: "var(--font-oswald), sans-serif" }}
              >
                Class Year
              </h3>
              <p className="text-sm text-slate-600 leading-relaxed">
                Recruits closer to arriving on campus — signed seniors about to enroll — are
                valued higher than younger prospects whose commitments and development are less
                certain. We currently track the Classes of 2026, 2027, and 2028.
              </p>
            </div>
          </div>

          <div className="mt-6 rounded-lg bg-slate-50 border border-slate-200 p-4">
            <p className="text-sm text-slate-600 leading-relaxed">
              <span className="font-semibold text-slate-800">We only value four-star and five-star recruits.</span>{" "}
              Below that threshold, high school basketball NIL markets are too speculative
              to model responsibly. We believe it&apos;s better to show no number than a
              misleading one.
            </p>
            <p className="text-sm text-slate-500 leading-relaxed mt-3">
              Once a recruit enrolls in college and begins accumulating real playing time, their
              valuation naturally transitions from our recruiting model to our college athlete model
              as production data and draft projections become available.
            </p>
          </div>
        </section>

        {/* ── Section 3: Reported Deals ─────────────────────────────────── */}
        <section className="bg-white rounded-xl shadow-md p-8">
          <h2
            className="text-xl font-bold text-slate-900 uppercase tracking-wide mb-4"
            style={{ fontFamily: "var(--font-oswald), sans-serif" }}
          >
            Reported Deals
          </h2>
          <p className="text-sm text-slate-600 leading-relaxed mb-4">
            When a player has a publicly reported NIL deal from a credible source, we use
            that reported figure as their valuation instead of our algorithmic estimate. We
            believe real market data is always more accurate than any model.
          </p>
          <p className="text-sm text-slate-600 leading-relaxed">
            Reported deal data is sourced from public reporting, NIL collectives, and direct
            submissions. Each source is attributed on the player&apos;s profile when available.
          </p>
        </section>

        {/* ── Section 4: Update Frequency ──────────────────────────────── */}
        <section className="bg-white rounded-xl shadow-md p-8">
          <h2
            className="text-xl font-bold text-slate-900 uppercase tracking-wide mb-4"
            style={{ fontFamily: "var(--font-oswald), sans-serif" }}
          >
            How Often Valuations Update
          </h2>
          <p className="text-sm text-slate-600 leading-relaxed">
            Valuations are recalculated regularly as new data becomes available — including
            updated stats, roster changes, draft projections, and social media growth. During
            active portal windows we update daily. Portal and recruiting pages reflect the most
            current available data.
          </p>
        </section>

        {/* ── Section 5: A Note on Accuracy ────────────────────────────── */}
        <section className="bg-slate-900 text-white rounded-xl shadow-md p-6">
          <h2
            className="text-xl font-bold text-white uppercase tracking-wide mb-4"
            style={{ fontFamily: "var(--font-oswald), sans-serif" }}
          >
            A Note on Accuracy
          </h2>
          <p className="text-sm text-slate-300 leading-relaxed mb-4">
            No model is perfect. NIL is a young, rapidly evolving market with limited public
            data. CFO valuations are estimates — informed by the best available data and a
            rigorous methodology, but not guarantees of what a player will or should earn.
            For most scholarship players at tracked programs, our valuations fall within the
            range that market participants — agents, collectives, and programs — would consider
            reasonable for a player of that profile.
          </p>
          <p className="text-sm text-slate-400 leading-relaxed">
            We&apos;re transparent about our approach because we believe the NIL market works
            better when everyone — players, families, collectives, and programs — has access to
            credible, independent valuations.
          </p>
        </section>

        {/* ── Version / CTA ───────────────────────────────────────────── */}
        <div className="text-center pt-4">
          <p className="text-xs text-slate-400 mb-6">
            Basketball Valuation Engine — methodology updated April 2026.
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
