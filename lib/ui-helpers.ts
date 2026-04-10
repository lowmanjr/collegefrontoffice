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

export function roleTierBadgeClass(tier: string | null): string {
  switch (tier) {
    case "franchise": return "bg-yellow-100 text-yellow-800";
    case "star":      return "bg-purple-100 text-purple-800";
    case "starter":   return "bg-green-100 text-green-800";
    case "rotation":  return "bg-blue-100 text-blue-800";
    case "bench":     return "bg-gray-100 text-gray-600";
    case "incoming":  return "bg-orange-100 text-orange-800";
    default:          return "bg-gray-100 text-gray-600";
  }
}
