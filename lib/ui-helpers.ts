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
