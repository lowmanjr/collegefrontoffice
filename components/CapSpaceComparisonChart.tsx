"use client";

import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from "recharts";

interface TeamCapData {
  name: string;
  payroll: number;
  cap: number;
  pct: number;
}

interface Props {
  data: TeamCapData[];
}

function formatShortCurrency(value: number): string {
  if (value >= 1_000_000) return `$${(value / 1_000_000).toFixed(1)}M`;
  if (value >= 1_000) return `$${(value / 1_000).toFixed(0)}K`;
  return `$${value}`;
}

function barColor(pct: number): string {
  if (pct >= 90) return "#ef4444";
  if (pct >= 75) return "#eab308";
  return "#22c55e";
}

function CustomTooltip({ active, payload }: { active?: boolean; payload?: Array<{ payload: TeamCapData }> }) {
  if (!active || !payload?.length) return null;
  const d = payload[0].payload;
  return (
    <div className="bg-slate-900 text-white rounded-lg px-3 py-2 shadow-lg text-xs">
      <p className="font-semibold mb-1">{d.name}</p>
      <p>Payroll: <span className="text-emerald-400 font-bold">{formatShortCurrency(d.payroll)}</span></p>
      <p>Cap: <span className="text-slate-300">{formatShortCurrency(d.cap)}</span></p>
      <p>Used: <span className="font-bold">{d.pct}%</span></p>
    </div>
  );
}

export default function CapSpaceComparisonChart({ data }: Props) {
  if (data.length === 0) return null;

  return (
    <div style={{ height: data.length * 36 + 40, minHeight: 200 }}>
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} layout="vertical" margin={{ top: 4, right: 20, left: 0, bottom: 4 }}>
          <XAxis
            type="number"
            tickFormatter={formatShortCurrency}
            tick={{ fill: "#94a3b8", fontSize: 10 }}
            axisLine={false}
            tickLine={false}
          />
          <YAxis
            type="category"
            dataKey="name"
            tick={{ fill: "#94a3b8", fontSize: 11, fontWeight: 500 }}
            axisLine={false}
            tickLine={false}
            width={100}
          />
          <Tooltip content={<CustomTooltip />} cursor={{ fill: "rgba(148, 163, 184, 0.08)" }} />
          <Bar dataKey="payroll" radius={[0, 4, 4, 0]} barSize={20}>
            {data.map((entry, i) => (
              <Cell key={i} fill={barColor(entry.pct)} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
