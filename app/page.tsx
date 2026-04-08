import Link from "next/link";
import HeroSearch from "@/components/HeroSearch";

export default function Home() {
  return (
    <>
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{
          __html: JSON.stringify({
            "@context": "https://schema.org",
            "@type": "WebSite",
            name: "College Front Office",
            url: "https://collegefrontoffice.com",
            description: "Proprietary NIL valuations for Power 4 college football programs.",
            potentialAction: {
              "@type": "SearchAction",
              target: "https://collegefrontoffice.com/players?q={search_term_string}",
              "query-input": "required name=search_term_string",
            },
          }),
        }}
      />

      {/* ── Hero ─────────────────────────────────────────────────────────── */}
      <section className="bg-slate-900 py-14 pb-16 px-4">
        <div className="mx-auto max-w-4xl text-center">
          <h1
            className="text-4xl sm:text-5xl font-bold text-white leading-tight"
            style={{ fontFamily: "var(--font-oswald), sans-serif" }}
          >
            College NIL Valuations
          </h1>

          <p className="mt-3 text-lg text-slate-400">
            The most comprehensive NIL valuation database in college sports.
          </p>

          <div className="mt-6">
            <HeroSearch />
          </div>

          {/* ── Route Cards ──────────────────────────────────────────────── */}
          <div className="mt-12 grid grid-cols-1 sm:grid-cols-3 gap-4">
            <Link href="/teams" className="group flex items-center justify-center bg-slate-800/50 border border-slate-700 rounded-xl px-5 py-4 hover:border-slate-500 hover:bg-slate-800 transition-all">
              <h3 className="text-base font-bold text-white uppercase tracking-wide group-hover:text-emerald-400 transition-colors"
                style={{ fontFamily: "var(--font-oswald), sans-serif" }}>
                Teams <span className="text-slate-600 group-hover:text-emerald-400 transition-colors">&rarr;</span>
              </h3>
            </Link>

            <Link href="/players" className="group flex items-center justify-center bg-slate-800/50 border border-slate-700 rounded-xl px-5 py-4 hover:border-slate-500 hover:bg-slate-800 transition-all">
              <h3 className="text-base font-bold text-white uppercase tracking-wide group-hover:text-emerald-400 transition-colors"
                style={{ fontFamily: "var(--font-oswald), sans-serif" }}>
                Players <span className="text-slate-600 group-hover:text-emerald-400 transition-colors">&rarr;</span>
              </h3>
            </Link>

            <Link href="/recruits" className="group flex items-center justify-center bg-slate-800/50 border border-slate-700 rounded-xl px-5 py-4 hover:border-slate-500 hover:bg-slate-800 transition-all">
              <h3 className="text-base font-bold text-white uppercase tracking-wide group-hover:text-emerald-400 transition-colors"
                style={{ fontFamily: "var(--font-oswald), sans-serif" }}>
                Recruits <span className="text-slate-600 group-hover:text-emerald-400 transition-colors">&rarr;</span>
              </h3>
            </Link>
          </div>
        </div>
      </section>
    </>
  );
}
