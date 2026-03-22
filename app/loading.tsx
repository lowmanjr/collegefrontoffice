export default function Loading() {
  return (
    <div className="animate-pulse">

      {/* ── Hero skeleton ─────────────────────────────────────────────── */}
      <div className="bg-slate-900 py-16 px-4">
        <div className="mx-auto max-w-6xl space-y-4">
          {/* Badge */}
          <div className="h-5 w-36 rounded-full bg-slate-700" />
          {/* Headline */}
          <div className="h-12 w-3/4 rounded-lg bg-slate-700" />
          <div className="h-12 w-1/2 rounded-lg bg-slate-700" />
          {/* Sub-headline */}
          <div className="h-4 w-2/3 rounded bg-slate-800 mt-2" />
          <div className="h-4 w-1/2 rounded bg-slate-800" />
        </div>
      </div>

      {/* ── Data boards skeleton ───────────────────────────────────────── */}
      <div className="bg-gray-100">
        <div className="mx-auto max-w-6xl px-4 py-12 space-y-12">

          {/* Transparency banner skeleton */}
          <div className="h-12 rounded-r-lg bg-blue-100 border-l-4 border-blue-300" />

          {/* Cap Space section */}
          <section className="space-y-4">
            {/* Section header */}
            <div className="h-7 w-64 rounded bg-gray-300" />
            <div className="h-4 w-48 rounded bg-gray-200" />
            {/* 5 team cards */}
            <div className="grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-3 pt-2">
              {Array.from({ length: 5 }).map((_, i) => (
                <div key={i} className="h-32 rounded-xl bg-gray-200" />
              ))}
            </div>
          </section>

          {/* Player Table section */}
          <section className="space-y-3">
            {/* Section header */}
            <div className="h-7 w-44 rounded bg-gray-300" />
            <div className="h-4 w-56 rounded bg-gray-200" />
            {/* Table card shell */}
            <div className="bg-white rounded-xl shadow-sm p-4 pt-5 space-y-2 mt-2">
              {/* Table header row */}
              <div className="h-10 rounded-md bg-slate-800 mb-4" />
              {/* 10 data rows */}
              {Array.from({ length: 10 }).map((_, i) => (
                <div key={i} className="h-12 rounded-md bg-gray-100" />
              ))}
            </div>
          </section>

        </div>
      </div>

    </div>
  );
}
