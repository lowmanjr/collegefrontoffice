"use client";

import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from "recharts";

interface PositionGroup {
  group: string;
  value: number;
  count: number;
}

interface Props {
  data: PositionGroup[];
}

const GROUP_COLORS: Record<string, string> = {
  QB: "#b91c1c",
  WR: "#1d4ed8",
  RB: "#1d4ed8",
  TE: "#1d4ed8",
  OL: "#334155",
  DL: "#c2410c",
  EDGE: "#c2410c",
  LB: "#b45309",
  DB: "#7e22ce",
  SPEC: "#64748b",
};

function formatShortCurrency(value: number): string {
  if (value >= 1_000_000) return `$${(value / 1_000_000).toFixed(1)}M`;
  if (value >= 1_000) return `$${(value / 1_000).toFixed(0)}K`;
  return `$${value}`;
}

function CustomTooltip({ active, payload }: { active?: boolean; payload?: Array<{ payload: PositionGroup }> }) {
  if (!active || !payload?.length) return null;
  const d = payload[0].payload;
  return (
    <div className="bg-slate-900 text-white rounded-lg px-3 py-2 shadow-lg text-xs">
      <p className="font-semibold">{d.group}</p>
      <p className="text-emerald-400 font-bold" style={{ fontFamily: "var(--font-oswald), sans-serif" }}>
        {formatShortCurrency(d.value)}
      </p>
      <p className="text-slate-400">{d.count} player{d.count !== 1 ? "s" : ""}</p>
    </div>
  );
}

export default function PositionValueChart({ data }: Props) {
  if (data.length === 0) return null;

  return (
    <div className="h-64">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} margin={{ top: 8, right: 0, left: 0, bottom: 0 }}>
          <XAxis
            dataKey="group"
            tick={{ fill: "#94a3b8", fontSize: 11, fontWeight: 600 }}
            axisLine={false}
            tickLine={false}
          />
          <YAxis
            tickFormatter={formatShortCurrency}
            tick={{ fill: "#94a3b8", fontSize: 10 }}
            axisLine={false}
            tickLine={false}
            width={50}
          />
          <Tooltip content={<CustomTooltip />} cursor={{ fill: "rgba(148, 163, 184, 0.1)" }} />
          <Bar dataKey="value" radius={[4, 4, 0, 0]}>
            {data.map((entry, i) => (
              <Cell key={i} fill={GROUP_COLORS[entry.group] ?? "#64748b"} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
