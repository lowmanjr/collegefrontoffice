export default function RosterManagerPage() {
  return (
    <div className="min-h-screen bg-gray-100">
      <section className="bg-slate-900 text-white py-12 px-4">
        <div className="mx-auto max-w-4xl">
          <span className="inline-block mb-4 rounded-full bg-slate-700 px-3 py-1 text-xs font-semibold uppercase tracking-widest text-green-400">
            Admin
          </span>
          <h1
            className="text-4xl sm:text-5xl font-bold text-white"
            style={{ fontFamily: "var(--font-oswald), sans-serif" }}
          >
            Roster Manager
          </h1>
          <p className="mt-3 text-slate-400 text-sm">
            Manage team rosters, player status, and override flags.
          </p>
        </div>
      </section>

      <div className="mx-auto max-w-4xl px-4 py-10">
        <div className="bg-white rounded-xl shadow-md border border-gray-100 p-12 flex flex-col items-center gap-4 text-center">
          <div className="h-12 w-12 rounded-full bg-slate-100 flex items-center justify-center">
            <svg
              width="22"
              height="22"
              viewBox="0 0 22 22"
              fill="none"
              xmlns="http://www.w3.org/2000/svg"
              aria-hidden="true"
            >
              <rect x="3" y="5" width="16" height="13" rx="2" stroke="#94a3b8" strokeWidth="1.8" />
              <path d="M3 9h16" stroke="#94a3b8" strokeWidth="1.8" strokeLinecap="round" />
              <path d="M8 5V3m6 2V3" stroke="#94a3b8" strokeWidth="1.8" strokeLinecap="round" />
            </svg>
          </div>
          <p className="text-base font-semibold text-slate-700">Coming Soon</p>
          <p className="text-sm text-slate-400 max-w-sm">
            The Roster Manager is under development. Use the Supabase dashboard to manage player
            records directly in the meantime.
          </p>
        </div>
      </div>
    </div>
  );
}
