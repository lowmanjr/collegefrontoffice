"use client";

import { formatCompactCurrency } from "@/lib/utils";

interface Segment {
  label: string;
  shortLabel: string;
  value: number;
  strokeColor: string;
  dotColor: string;
}

interface RosterDonutProps {
  retainedValue: number;
  portalValue: number;
  recruitValue: number;
  totalValuation: number;
}

/**
 * Rounds percentages so they sum to exactly 100.
 * Awards remainder to the largest segment.
 */
function roundPercentages(values: number[], total: number): number[] {
  if (total === 0) return values.map(() => 0);
  const raw = values.map((v) => (v / total) * 100);
  const floored = raw.map(Math.floor);
  let remainder = 100 - floored.reduce((a, b) => a + b, 0);

  // Distribute remainder to segments with largest fractional parts
  const fractions = raw.map((r, i) => ({ i, frac: r - floored[i] }));
  fractions.sort((a, b) => b.frac - a.frac);
  for (let k = 0; k < remainder; k++) {
    floored[fractions[k].i] += 1;
  }
  return floored;
}

export default function RosterDonut({
  retainedValue,
  portalValue,
  recruitValue,
  totalValuation,
}: RosterDonutProps) {
  const allSegments: Segment[] = [
    {
      label: "Est. Retained Value",
      shortLabel: "Retained",
      value: retainedValue,
      strokeColor: "#64748b", // slate-500
      dotColor: "bg-slate-500",
    },
    {
      label: "Est. Portal Value",
      shortLabel: "Portal",
      value: portalValue,
      strokeColor: "#3b82f6", // blue-500
      dotColor: "bg-blue-500",
    },
    {
      label: "Est. Recruiting Class Value",
      shortLabel: "Recruits",
      value: recruitValue,
      strokeColor: "#10b981", // emerald-500
      dotColor: "bg-emerald-500",
    },
  ];

  const segments = allSegments.filter((s) => s.value > 0);
  const values = segments.map((s) => s.value);
  const percentages = roundPercentages(values, totalValuation);

  // SVG donut parameters
  const size = 180;
  const strokeWidth = 28;
  const radius = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;
  const center = size / 2;

  // Build stroke-dasharray segments
  let cumulativeOffset = 0;
  const arcs = segments.map((seg, i) => {
    const pct = percentages[i] / 100;
    const dashLength = pct * circumference;
    const gapLength = circumference - dashLength;
    const offset = -cumulativeOffset + circumference * 0.25; // start at top (12 o'clock)
    cumulativeOffset += dashLength;

    return {
      ...seg,
      pct: percentages[i],
      dasharray: `${dashLength} ${gapLength}`,
      dashoffset: offset,
    };
  });

  if (totalValuation === 0) return null;

  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-5 mb-4">
      <div className="flex flex-col sm:flex-row items-center sm:items-center gap-6 sm:gap-8">
        {/* ── Donut ───────────────────────────────────────────────────── */}
        <div className="relative shrink-0" style={{ width: size, height: size }}>
          <svg
            viewBox={`0 0 ${size} ${size}`}
            className="w-[150px] h-[150px] sm:w-[180px] sm:h-[180px]"
            aria-label={`Roster value breakdown: ${segments.map((s, i) => `${s.shortLabel} ${percentages[i]}%`).join(", ")}`}
          >
            {/* Background ring */}
            <circle
              cx={center}
              cy={center}
              r={radius}
              fill="none"
              stroke="#f1f5f9"
              strokeWidth={strokeWidth}
            />

            {/* Colored arcs */}
            {arcs.map((arc, i) => (
              <circle
                key={arc.shortLabel}
                cx={center}
                cy={center}
                r={radius}
                fill="none"
                stroke={arc.strokeColor}
                strokeWidth={strokeWidth}
                strokeDasharray={arc.dasharray}
                strokeDashoffset={arc.dashoffset}
                strokeLinecap="butt"
                className="transition-all duration-700 ease-out"
                style={{
                  transformOrigin: "center",
                }}
              />
            ))}
          </svg>

          {/* Center text */}
          <div className="absolute inset-0 flex flex-col items-center justify-center">
            <span className="text-[10px] uppercase tracking-widest text-slate-400 leading-tight">
              Est. Roster Value
            </span>
            <span
              className="text-xl sm:text-2xl font-bold text-slate-900 leading-tight mt-0.5"
              style={{ fontFamily: "var(--font-oswald), sans-serif" }}
            >
              {formatCompactCurrency(totalValuation)}
            </span>
          </div>
        </div>

        {/* ── Legend ──────────────────────────────────────────────────── */}
        <div className="flex flex-col gap-3">
          {arcs.map((arc) => (
            <div
              key={arc.shortLabel}
              className="flex items-center gap-3"
              aria-label={arc.label}
            >
              <span className={`inline-block w-3 h-3 rounded-full shrink-0 ${arc.dotColor}`} />
              <div className="flex items-baseline gap-2">
                <span className="text-sm font-semibold text-slate-700 w-16">
                  {arc.shortLabel}
                </span>
                <span className="text-xs text-slate-400 w-8 text-right tabular-nums">
                  {arc.pct}%
                </span>
                <span
                  className="text-sm font-bold text-slate-900 tabular-nums"
                  style={{ fontFamily: "var(--font-oswald), sans-serif" }}
                >
                  {formatCompactCurrency(arc.value)}
                </span>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
