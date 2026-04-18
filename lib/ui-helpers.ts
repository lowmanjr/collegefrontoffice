/**
 * Shared UI helper functions.
 * Import these instead of duplicating across components.
 */

export function positionBadgeClass(pos: string | null): string {
  if (!pos) return "bg-slate-900 text-white";
  const p = pos.toUpperCase();
  if (p === "QB") return "bg-red-700 text-white";
  if (["WR", "RB", "TE"].includes(p)) return "bg-blue-700 text-white";
  if (["OT", "OG", "C", "OL", "IOL"].includes(p)) return "bg-slate-700 text-white";
  if (["EDGE", "DE", "DT", "DL"].includes(p)) return "bg-orange-700 text-white";
  if (["LB"].includes(p)) return "bg-amber-700 text-white";
  if (["CB", "S"].includes(p)) return "bg-purple-700 text-white";
  if (["K", "P", "LS"].includes(p)) return "bg-slate-500 text-white";
  return "bg-slate-900 text-white";
}

export function basketballPositionBadgeClass(position: string | null): string {
  switch (position) {
    case "PG": return "bg-blue-100 text-blue-800";
    case "SG": return "bg-indigo-100 text-indigo-800";
    case "SF": return "bg-teal-100 text-teal-800";
    case "PF": return "bg-amber-100 text-amber-800";
    case "C":  return "bg-slate-100 text-slate-700";
    default:   return "bg-gray-100 text-gray-600";
  }
}

export function roleTierBadgeClass(
  tier: string | null,
  variant: "light" | "dark" = "light",
): string {
  if (variant === "dark") {
    const base = "rounded px-2.5 py-0.5 text-xs font-semibold uppercase tracking-widest";
    switch (tier) {
      case "franchise": return `${base} bg-emerald-500 text-white`;
      case "star":      return `${base} bg-blue-500 text-white`;
      case "starter":   return `${base} bg-slate-200 text-slate-800`;
      case "rotation":  return `${base} bg-slate-600 text-slate-200`;
      case "bench":     return `${base} bg-slate-700 text-slate-300`;
      default:          return `${base} bg-slate-700 text-slate-400`;
    }
  }
  switch (tier) {
    case "franchise":
      return "rounded px-1.5 py-0.5 text-[10px] font-semibold bg-emerald-500 text-white";
    case "star":
      return "rounded px-1.5 py-0.5 text-[10px] font-semibold bg-blue-500 text-white";
    case "starter":
      return "rounded px-1.5 py-0.5 text-[10px] font-semibold bg-white text-slate-700 border border-slate-300";
    case "rotation":
      return "rounded px-1.5 py-0.5 text-[10px] font-semibold bg-slate-100 text-slate-600";
    case "bench":
      return "text-[10px] font-semibold text-slate-500";
    default:
      return "text-[10px] font-semibold text-slate-400";
  }
}

export function roleTierLabel(tier: string | null): string {
  if (!tier) return "";
  return tier.charAt(0).toUpperCase() + tier.slice(1);
}

export function formatDraftProjectionBadge(pick: number | null): string | null {
  if (pick == null || pick <= 0 || pick > 60) return null;
  if (pick <= 10) return "Top 10 Pick";
  if (pick <= 14) return "Lottery";
  if (pick <= 30) return "1st Round";
  return "2nd Round";
}
