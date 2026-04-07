"use client";

import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";

export interface TrajectoryPoint {
  year: string;
  value: number | null;
  projection: number | null;
}

interface Props {
  data: TrajectoryPoint[];
  isOverride: boolean;
}

function formatShort(value: number): string {
  if (value >= 1_000_000) return `$${(value / 1_000_000).toFixed(2)}M`;
  if (value >= 1_000) return `$${(value / 1_000).toFixed(0)}K`;
  return `$${value}`;
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
function CustomTooltip({ active, payload, label, isOverride }: any) {
  if (!active || !payload?.length) return null;

  return (
    <div className="rounded-lg border border-slate-700 bg-slate-900 px-4 py-3 shadow-xl text-xs">
      <p className="text-slate-400 uppercase tracking-widest mb-2">{label}</p>
      {payload.map(
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        (entry: any) =>
          entry.value != null && (
            <p key={entry.dataKey} style={{ color: entry.color }} className="font-semibold">
              {entry.dataKey === "value"
                ? isOverride
                  ? "Contracted AAV"
                  : "Current Value"
                : "Projected Value"}
              : {formatShort(entry.value)}
            </p>
          )
      )}
    </div>
  );
}

export default function ValuationTrajectoryChart({ data, isOverride }: Props) {
  return (
    <ResponsiveContainer width="100%" height={280}>
      <LineChart data={data} margin={{ top: 8, right: 16, left: 8, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
        <XAxis
          dataKey="year"
          tick={{ fontSize: 12, fill: "#94a3b8" }}
          axisLine={{ stroke: "#e2e8f0" }}
          tickLine={false}
        />
        <YAxis
          tickFormatter={formatShort}
          tick={{ fontSize: 11, fill: "#94a3b8" }}
          axisLine={false}
          tickLine={false}
          width={68}
        />
        <Tooltip content={<CustomTooltip isOverride={isOverride} />} />

        {/* Solid line — contracted AAV (override) or current year anchor */}
        <Line
          type="monotone"
          dataKey="value"
          stroke="#10b981"
          strokeWidth={2.5}
          dot={{ fill: "#10b981", r: 5, strokeWidth: 0 }}
          activeDot={{ r: 7, stroke: "#10b981", strokeWidth: 2, fill: "#fff" }}
          connectNulls={false}
        />

        {/* Dashed line — algorithmic projection (hidden for override charts) */}
        {!isOverride && (
          <Line
            type="monotone"
            dataKey="projection"
            stroke="#818cf8"
            strokeWidth={2}
            strokeDasharray="6 4"
            dot={{ fill: "#818cf8", r: 4, strokeWidth: 0 }}
            activeDot={{ r: 6, stroke: "#818cf8", strokeWidth: 2, fill: "#fff" }}
            connectNulls={false}
          />
        )}
      </LineChart>
    </ResponsiveContainer>
  );
}
