import type { Metadata } from "next";
import Link from "next/link";
import { BASE_URL } from "@/lib/constants";

export const revalidate = false;

export const metadata: Metadata = {
  title: "How NIL Valuations Work — CFO Methodology | College Front Office",
  description:
    "Learn how College Front Office calculates NIL valuations for college football players and recruits. Our proprietary multi-factor model explained.",
  alternates: { canonical: `${BASE_URL}/methodology` },
};

export default function MethodologyPage() {
  return (
    <main className="min-h-screen bg-gray-100">
      {/* ── Hero ─────────────────────────────────────────────────────────── */}
      <section className="bg-slate-900 text-white px-6 py-8">
        <div className="mx-auto max-w-3xl">
          <h1
            className="text-4xl sm:text-5xl font-bold uppercase tracking-tight leading-none"
            style={{ fontFamily: "var(--font-oswald), sans-serif" }}
          >
            How CFO Valuations Work
          </h1>
          <p className="mt-4 text-slate-400 text-base leading-relaxed max-w-2xl">
            College Front Office uses a proprietary multi-factor model to estimate every
            player&apos;s annualized NIL market value. These are proprietary estimates, not
            official financial disclosures.
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
                On-Field Projection
              </h3>
              <p className="text-sm text-slate-600 leading-relaxed">
                The foundation of every valuation is football. We assess a player&apos;s projected
                career trajectory using draft modeling, on-field production data, and independent
                talent ratings. Players with stronger professional
                outlooks command higher NIL valuations — because brands, collectives, and programs
                are investing in future visibility.
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
                Not all positions carry equal weight in the NIL marketplace. Quarterbacks
                consistently command the largest deals, followed by premium offensive tackles, edge
                rushers, and skill positions. Our position-specific base values are calibrated
                annually using coaching surveys, GM interviews, and transfer portal deal data.
                Tight ends are valued as a two-starter position, reflecting the modern game&apos;s
                reliance on multi-TE offensive sets.
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
                Where a player plays matters. Programs with larger fanbases, stronger NIL
                collectives, and higher revenue generate more NIL opportunity for their athletes. A
                player&apos;s valuation accounts for the financial ecosystem of their specific
                program.
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
                We use a three-tier talent evaluation system. The primary signal is on-field
                production — season-level statistical performance ranked against all FBS players at
                the same position. When production data isn&apos;t available (common for offensive
                linemen and incoming transfers), we use independent talent ratings as a
                calibrated fallback. For players without either signal, we fall back to their
                recruiting pedigree.
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
                A player&apos;s remaining eligibility and time in college affect their market
                leverage. Our model adjusts for class year, recognizing that mid-career players with
                established tape often command the strongest position.
              </p>
            </div>

            <div className="border-l-4 border-slate-500 pl-5">
              <h3
                className="text-lg font-bold text-slate-900 mb-2"
                style={{ fontFamily: "var(--font-oswald), sans-serif" }}
              >
                Depth Chart Role
              </h3>
              <p className="text-sm text-slate-600 leading-relaxed">
                A player&apos;s role on the team — starter, backup, or reserve — directly affects
                their valuation. Starters command full market value. Backup players at
                single-starter positions (like quarterback) face steeper discounts than backups at
                multi-starter positions. We source
                depth chart data from independent scouting services and update it throughout the
                season.
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
                Personal brand matters in NIL. We incorporate a player&apos;s social media following
                as a measure of their direct marketing value to sponsors. Social reach is a
                meaningful bonus but is intentionally capped — College Front Office is a
                football-first valuation.
              </p>
            </div>
          </div>
        </section>

        {/* ── Section 2: How We Value High School Recruits ──────────────── */}
        <section className="bg-white rounded-xl shadow-md p-8">
          <h2
            className="text-xl font-bold text-slate-900 uppercase tracking-wide mb-4"
            style={{ fontFamily: "var(--font-oswald), sans-serif" }}
          >
            How We Value High School Recruits
          </h2>
          <p className="text-sm text-slate-600 leading-relaxed mb-5">
            College Front Office also values elite high school football recruits — the four-star and
            five-star prospects who make up the next generation of college talent.
          </p>
          <p className="text-sm text-slate-600 leading-relaxed mb-5">
            Valuing recruits requires a different approach than valuing college athletes. High school
            players don&apos;t have college production data, snap counts, or draft projections.
            Instead, we rely on the signals that actually drive the recruiting market:
          </p>
          <div className="space-y-6">
            <div className="border-l-4 border-purple-500 pl-5">
              <h3
                className="text-lg font-bold text-slate-900 mb-2"
                style={{ fontFamily: "var(--font-oswald), sans-serif" }}
              >
                Recruiting Consensus Rankings
              </h3>
              <p className="text-sm text-slate-600 leading-relaxed">
                Composite scores published by major recruiting services are the foundation of every
                recruit valuation. They represent the best available assessment of a prospect&apos;s
                talent and potential. Higher-rated recruits consistently command larger NIL packages,
                and our model reflects that relationship.
              </p>
            </div>

            <div className="border-l-4 border-blue-500 pl-5">
              <h3
                className="text-lg font-bold text-slate-900 mb-2"
                style={{ fontFamily: "var(--font-oswald), sans-serif" }}
              >
                Position Premium
              </h3>
              <p className="text-sm text-slate-600 leading-relaxed">
                Position matters just as much for recruits as it does for college athletes.
                Quarterback and offensive tackle recruits consistently command the largest deals,
                followed by premium skill and defensive positions — mirroring the same positional
                economics that drive the college and professional markets.
              </p>
            </div>

            <div className="border-l-4 border-emerald-500 pl-5">
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

            <div className="border-l-4 border-amber-500 pl-5">
              <h3
                className="text-lg font-bold text-slate-900 mb-2"
                style={{ fontFamily: "var(--font-oswald), sans-serif" }}
              >
                Class Year &amp; Enrollment Proximity
              </h3>
              <p className="text-sm text-slate-600 leading-relaxed">
                Recruits closer to arriving on campus — signed seniors about to enroll — are valued
                higher than younger prospects whose commitments and development are less certain.
              </p>
            </div>
          </div>

          <div className="mt-6 rounded-lg bg-slate-50 border border-slate-200 p-4">
            <p className="text-sm text-slate-600 leading-relaxed">
              <span className="font-semibold text-slate-800">We only value four-star and five-star recruits.</span>{" "}
              Below that threshold, the high school NIL market is too thin and unpredictable to
              model with confidence. We believe it&apos;s better to show no number than a misleading
              one.
            </p>
            <p className="text-sm text-slate-500 leading-relaxed mt-3">
              Once a recruit enrolls in college and begins accumulating real playing time, their
              valuation naturally transitions from our recruiting model to our college athlete model
              as production data, depth chart positioning, and draft projections become available.
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
            updated production metrics, roster changes, draft projections, and social media
            growth.
          </p>
        </section>

        {/* ── Section 6: Accuracy Note ─────────────────────────────────── */}
        <section className="bg-slate-900 text-white rounded-xl shadow-md p-6">
          <h2
            className="text-xl font-bold text-white uppercase tracking-wide mb-4"
            style={{ fontFamily: "var(--font-oswald), sans-serif" }}
          >
            A Note on Accuracy
          </h2>
          <p className="text-sm text-slate-300 leading-relaxed mb-4">
            No model is perfect. NIL is a young, rapidly evolving market with limited public data.
            CFO valuations are estimates — informed by the best available data and a rigorous
            methodology, but not guarantees of what a player will or should earn. Our current
            model produces valuations within 20% of market consensus for most starters, and our
            high school recruit valuations track independent estimates at a median ratio of 1.0×.
          </p>
          <p className="text-sm text-slate-400 leading-relaxed">
            We&apos;re transparent about our approach because we believe the NIL market works better
            when everyone — players, families, collectives, and programs — has access to credible,
            independent valuations.
          </p>
        </section>

        {/* ── CTA ──────────────────────────────────────────────────────── */}
        <div className="text-center pt-4">
          <p className="text-sm text-slate-500 mb-4">
            <strong className="text-slate-700">Questions about our methodology?</strong> Explore
            player profiles to see the model in action.
          </p>
          <Link
            href="/players"
            className="inline-flex items-center gap-2 rounded-lg bg-emerald-500 hover:bg-emerald-600 text-white font-semibold px-6 py-3 transition-colors"
          >
            View Player Valuations
            <svg className="h-4 w-4" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
              <path fillRule="evenodd" d="M3 10a.75.75 0 01.75-.75h10.638L10.23 5.29a.75.75 0 111.04-1.08l5.5 5.25a.75.75 0 010 1.08l-5.5 5.25a.75.75 0 11-1.04-1.08l4.158-3.96H3.75A.75.75 0 013 10z" clipRule="evenodd" />
            </svg>
          </Link>
        </div>
      </div>
    </main>
  );
}
