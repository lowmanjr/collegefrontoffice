import { supabase } from "@/lib/supabase";
import ProposalCard from "./ProposalCard";

export default async function AdminPage() {
  const { data: proposals, error } = await supabase
    .from("proposed_events")
    .select("*, players(name, cfo_valuation)")
    .eq("status", "pending")
    .order("event_date", { ascending: false });

  if (error) console.error("Admin fetch error:", error);

  const queue = proposals ?? [];

  return (
    <div className="min-h-screen bg-gray-100">

      {/* ── Hero ───────────────────────────────────────────────────────────── */}
      <section className="bg-slate-900 text-white py-12 px-4">
        <div className="mx-auto max-w-4xl">
          <span className="inline-block mb-4 rounded-full bg-slate-700 px-3 py-1 text-xs font-semibold uppercase tracking-widest text-green-400">
            Admin
          </span>
          <h1
            className="text-4xl sm:text-5xl font-bold text-white"
            style={{ fontFamily: "var(--font-oswald), sans-serif" }}
          >
            Approval Feed
          </h1>
          <p className="mt-3 text-slate-400 text-sm">
            Review and publish proposed valuation updates to the live timeline.
          </p>
        </div>
      </section>

      {/* ── Inbox ──────────────────────────────────────────────────────────── */}
      <div className="mx-auto max-w-4xl px-4 py-10">

        {/* Count badge */}
        <div className="mb-6 flex items-center gap-3">
          <h2
            className="text-xl font-bold text-slate-900 uppercase tracking-wide"
            style={{ fontFamily: "var(--font-oswald), sans-serif" }}
          >
            Pending Proposals
          </h2>
          {queue.length > 0 && (
            <span className="rounded-full bg-blue-600 text-white text-xs font-bold px-2.5 py-0.5">
              {queue.length}
            </span>
          )}
        </div>

        {queue.length === 0 ? (
          <div className="bg-white rounded-xl shadow-md border border-gray-100 p-12 flex flex-col items-center gap-3 text-center">
            {/* Checkmark icon */}
            <div className="h-12 w-12 rounded-full bg-emerald-100 flex items-center justify-center">
              <svg width="22" height="22" viewBox="0 0 22 22" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
                <path d="M4 11.5L9 16.5L18 6" stroke="#059669" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
            </div>
            <p className="text-base font-semibold text-slate-700">Inbox Zero: No pending valuation updates.</p>
            <p className="text-sm text-slate-400">All proposals have been reviewed.</p>
          </div>
        ) : (
          <div className="space-y-5">
            {/* eslint-disable-next-line @typescript-eslint/no-explicit-any */}
            {queue.map((proposal: any) => (
              <ProposalCard key={proposal.id} proposal={proposal} />
            ))}
          </div>
        )}

      </div>
    </div>
  );
}
