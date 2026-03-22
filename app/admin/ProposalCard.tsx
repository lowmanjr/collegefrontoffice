"use client";

import { useTransition } from "react";
import Link from "next/link";
import { approveProposal, rejectProposal } from "./actions";

interface Proposal {
  id: string;
  player_id: string;
  event_type: string;
  event_date: string;
  proposed_valuation: number;
  current_valuation: number | null;
  reported_deal: number | null;
  description: string | null;
  players: { name: string; cfo_valuation: number } | null;
}

function formatCurrency(value: number): string {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 0,
  }).format(value);
}

export default function ProposalCard({ proposal }: { proposal: Proposal }) {
  const [isPending, startTransition] = useTransition();

  const currentVal  = proposal.current_valuation ?? proposal.players?.cfo_valuation ?? 0;
  const proposedVal = proposal.proposed_valuation;
  const diff        = proposedVal - currentVal;
  const isPositive  = diff >= 0;

  const date = new Date(proposal.event_date).toLocaleDateString("en-US", {
    year: "numeric", month: "long", day: "numeric",
  });

  function handleReject() {
    startTransition(() => rejectProposal(proposal.id));
  }

  function handleApprove() {
    startTransition(() =>
      approveProposal({
        id:                 proposal.id,
        player_id:          proposal.player_id,
        event_type:         proposal.event_type,
        event_date:         proposal.event_date,
        proposed_valuation: proposal.proposed_valuation,
        current_valuation:  currentVal,
        reported_deal:      proposal.reported_deal,
        description:        proposal.description,
      })
    );
  }

  return (
    <div className={`bg-white rounded-xl border border-gray-100 shadow-md p-6 transition-opacity ${isPending ? "opacity-40 pointer-events-none" : ""}`}>

      {/* Header row */}
      <div className="flex flex-wrap items-start justify-between gap-3 mb-4">
        <div>
          <Link
            href={`/players/${proposal.player_id}`}
            className="text-lg font-bold text-gray-900 hover:text-blue-700 transition-colors"
            style={{ fontFamily: "var(--font-oswald), sans-serif" }}
          >
            {proposal.players?.name ?? "Unknown Player"}
          </Link>
          <p className="text-xs text-slate-400 mt-0.5">{date}</p>
        </div>
        <span
          className="rounded bg-slate-900 text-white px-2.5 py-0.5 text-xs font-bold uppercase tracking-widest shrink-0"
          style={{ fontFamily: "var(--font-oswald), sans-serif" }}
        >
          {proposal.event_type}
        </span>
      </div>

      {/* Valuation change */}
      <div className="flex flex-wrap items-center gap-2 mb-3">
        <span
          className="text-xl font-bold text-slate-400 line-through"
          style={{ fontFamily: "var(--font-oswald), sans-serif" }}
        >
          {formatCurrency(currentVal)}
        </span>
        <span className="text-slate-300 font-bold text-lg">→</span>
        <span
          className="text-2xl font-black text-gray-900"
          style={{ fontFamily: "var(--font-oswald), sans-serif" }}
        >
          {formatCurrency(proposedVal)}
        </span>
        <span
          className={`text-sm font-bold ${isPositive ? "text-emerald-600" : "text-red-500"}`}
          style={{ fontFamily: "var(--font-oswald), sans-serif" }}
        >
          ({isPositive ? "+" : ""}{formatCurrency(diff)})
        </span>
      </div>

      {/* Reported deal badge */}
      {proposal.reported_deal != null && (
        <div className="mb-3">
          <span className="rounded-full bg-emerald-100 text-emerald-700 px-3 py-1 text-xs font-bold">
            Reported Deal: {formatCurrency(proposal.reported_deal)}
          </span>
        </div>
      )}

      {/* Description */}
      {proposal.description && (
        <p className="text-sm text-slate-500 leading-relaxed mb-5">
          {proposal.description}
        </p>
      )}

      {/* Action buttons */}
      <div className="flex gap-3 pt-4 border-t border-gray-100">
        <button
          onClick={handleApprove}
          disabled={isPending}
          className="flex-1 rounded-lg bg-emerald-600 hover:bg-emerald-700 text-white text-sm font-semibold py-2 transition-colors disabled:opacity-50"
        >
          {isPending ? "Processing…" : "✓ Approve"}
        </button>
        <button
          onClick={handleReject}
          disabled={isPending}
          className="flex-1 rounded-lg bg-rose-100 hover:bg-rose-200 text-rose-700 text-sm font-semibold py-2 transition-colors disabled:opacity-50"
        >
          ✕ Reject
        </button>
      </div>

    </div>
  );
}
