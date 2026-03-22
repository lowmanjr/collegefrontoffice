import CapSpaceBoard from "@/components/CapSpaceBoard";
import PlayerTable from "@/components/PlayerTable";

export default function Home() {
  return (
    <>
      {/* ── Hero ─────────────────────────────────────────────────────────── */}
      <section className="bg-slate-900 py-16 px-4">
        <div className="mx-auto max-w-6xl">

          {/* Sport badge */}
          <span className="inline-block mb-5 rounded-full bg-slate-700 px-3 py-1 text-xs font-semibold uppercase tracking-widest text-green-400">
            CFB 2026 Projections
          </span>

          {/* Headline */}
          <h1
            className="text-5xl sm:text-6xl font-bold text-white leading-tight max-w-3xl"
            style={{ fontFamily: "var(--font-oswald), sans-serif" }}
          >
            Mapping the College Sports Economy.
          </h1>

          {/* Sub-headline */}
          <p className="mt-5 text-lg text-slate-300 max-w-2xl leading-relaxed">
            We combine market data, positional scarcity, and algorithmic modeling to estimate
            player valuations and team cap space. Open assumptions. Real discussions.
          </p>

        </div>
      </section>

      {/* ── Data Boards ──────────────────────────────────────────────────── */}
      <div className="bg-gray-100">
        <div className="mx-auto max-w-6xl px-4 py-12 space-y-12">

          {/* Transparency banner */}
          <div className="bg-blue-50 border-l-4 border-blue-600 rounded-r-lg p-4">
            <p className="text-sm text-blue-900 leading-relaxed">
              <span className="font-semibold">Note:</span> The NIL market is inherently private.
              These figures are proprietary estimates intended as a resource for fans and players
              to better understand market dynamics, not official financial disclosures.
            </p>
          </div>

          {/* Cap Space section */}
          <section>
            <h2
              className="mb-1 text-2xl font-bold text-slate-900 uppercase tracking-wide"
              style={{ fontFamily: "var(--font-oswald), sans-serif" }}
            >
              Team Cap Space Projections
            </h2>
            <p className="mb-6 text-sm text-gray-500">
              Estimated NIL budget utilization across top programs.
            </p>
            <CapSpaceBoard />
          </section>

          {/* Player Valuations section */}
          <section>
            <h2
              className="mb-1 text-2xl font-bold text-slate-900 uppercase tracking-wide"
              style={{ fontFamily: "var(--font-oswald), sans-serif" }}
            >
              Top Valuations
            </h2>
            <p className="mb-6 text-sm text-gray-500">
              C.F.O. algorithmic valuations ranked by estimated market value.
            </p>
            <PlayerTable />
          </section>

        </div>
      </div>
    </>
  );
}
