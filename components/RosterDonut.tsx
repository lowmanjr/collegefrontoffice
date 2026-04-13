"use client";

import { formatCompactCurrency } from "@/lib/utils";

interface RosterDonutProps {
  retainedValue: number;
  portalValue: number;
  recruitValue: number;
  totalValuation: number;
  /** "light" for white bg (default), "dark" for slate-900 bg */
  variant?: "light" | "dark";
}

function roundPercentages(values: number[], total: number): number[] {
  if (total === 0) return values.map(() => 0);
  const raw = values.map((v) => (v / total) * 100);
  const floored = raw.map(Math.floor);
  let remainder = 100 - floored.reduce((a, b) => a + b, 0);
  const fractions = raw.map((r, i) => ({ i, frac: r - floored[i] }));
  fractions.sort((a, b) => b.frac - a.frac);
  for (let k = 0; k < remainder; k++) {
    floored[fractions[k].i] += 1;
  }
  return floored;
}

const ALL_SEGMENTS = [
  { label: "Est. Retained Value", shortLabel: "Retained", strokeColor: "#94a3b8", dotClass: "bg-slate-400" },
  { label: "Est. Portal Value", shortLabel: "Portal", strokeColor: "#60a5fa", dotClass: "bg-blue-400" },
  { label: "Est. Recruiting Class Value", shortLabel: "Recruits", strokeColor: "#34d399", dotClass: "bg-emerald-400" },
];

export default function RosterDonut({
  retainedValue,
  portalValue,
  recruitValue,
  totalValuation,
  variant = "light",
}: RosterDonutProps) {
  const dark = variant === "dark";
  const rawValues = [retainedValue, portalValue, recruitValue];
  const activeIndices = rawValues.map((v, i) => (v > 0 ? i : -1)).filter((i) => i >= 0);
  const activeValues = activeIndices.map((i) => rawValues[i]);
  const percentages = roundPercentages(activeValues, totalValuation);

  // SVG donut
  const size = 180;
  const strokeWidth = 26;
  const radius = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;
  const center = size / 2;

  let cumulativeOffset = 0;
  const arcs = activeIndices.map((segIdx, i) => {
    const seg = ALL_SEGMENTS[segIdx];
    const pct = percentages[i] / 100;
    const dashLength = pct * circumference;
    const gapLength = circumference - dashLength;
    const offset = -cumulativeOffset + circumference * 0.25;
    cumulativeOffset += dashLength;
    return {
      ...seg,
      value: rawValues[segIdx],
      pct: percentages[i],
      dasharray: `${dashLength} ${gapLength}`,
      dashoffset: offset,
    };
  });

  if (totalValuation === 0) return null;

  return (
    <div className="flex flex-col md:flex-row items-center md:items-center gap-5 md:gap-8">
      {/* ── Donut ─────────────────────────────────────────────────────── */}
      <div className="relative shrink-0 w-[150px] h-[150px] md:w-[180px] md:h-[180px]">
        <svg
          viewBox={`0 0 ${size} ${size}`}
          className="w-full h-full"
          aria-label={`Roster value breakdown: ${arcs.map((a) => `${a.shortLabel} ${a.pct}%`).join(", ")}`}
        >
          <circle
            cx={center} cy={center} r={radius}
            fill="none"
            stroke={dark ? "#334155" : "#f1f5f9"}
            strokeWidth={strokeWidth}
          />
          {arcs.map((arc) => (
            <circle
              key={arc.shortLabel}
              cx={center} cy={center} r={radius}
              fill="none"
              stroke={arc.strokeColor}
              strokeWidth={strokeWidth}
              strokeDasharray={arc.dasharray}
              strokeDashoffset={arc.dashoffset}
              strokeLinecap="butt"
              className="transition-all duration-700 ease-out"
            />
          ))}
        </svg>
        <div className="absolute inset-0 flex items-center justify-center">
          <span
            className={`text-2xl md:text-3xl font-bold leading-none ${dark ? "text-emerald-400" : "text-slate-900"}`}
            style={{ fontFamily: "var(--font-oswald), sans-serif" }}
          >
            {formatCompactCurrency(totalValuation)}
          </span>
        </div>
      </div>

      {/* ── Legend ────────────────────────────────────────────────────── */}
      <div className="grid gap-2.5">
        {arcs.map((arc) => (
          <div key={arc.shortLabel} className="flex items-center gap-3" aria-label={arc.label}>
            <span className={`inline-block w-2.5 h-2.5 rounded-full shrink-0 ${arc.dotClass}`} />
            <span className={`text-sm font-semibold w-[68px] ${dark ? "text-slate-200" : "text-slate-700"}`}>
              {arc.shortLabel}
            </span>
            <span className={`text-xs w-8 text-right tabular-nums ${dark ? "text-slate-500" : "text-slate-400"}`}>
              {arc.pct}%
            </span>
            <span
              className={`text-sm font-bold tabular-nums text-right w-[72px] ${dark ? "text-white" : "text-slate-900"}`}
              style={{ fontFamily: "var(--font-oswald), sans-serif" }}
            >
              {formatCompactCurrency(arc.value)}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
