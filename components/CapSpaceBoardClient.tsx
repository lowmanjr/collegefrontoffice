"use client";

import { Card, ProgressBar } from "@tremor/react";

export interface Team {
  id: string;
  university_name: string;
  conference: string;
  estimated_cap_space: number;
  active_payroll: number;
  logo_url?: string;
}

interface Props {
  initialTeams: Team[];
}

function formatCurrency(value: number): string {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 0,
  }).format(value);
}

function capColor(pct: number): "red" | "yellow" | "green" {
  if (pct >= 90) return "red";
  if (pct >= 75) return "yellow";
  return "green";
}

export default function CapSpaceBoardClient({ initialTeams }: Props) {
  return (
    <div className="grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-3">
      {initialTeams.map((team) => {
        const pct       = Math.round((team.active_payroll / team.estimated_cap_space) * 100);
        const remaining = team.estimated_cap_space - team.active_payroll;
        const color     = capColor(pct);

        return (
          <Card key={team.id} className="bg-white shadow-md border border-gray-100">
            {/* Header */}
            <div className="mb-1 flex items-start justify-between">
              <div className="flex items-center gap-3">
                {team.logo_url && (
                  <img
                    src={team.logo_url}
                    alt={`${team.university_name} logo`}
                    width={40}
                    height={40}
                    className="h-10 w-10 object-contain"
                  />
                )}
                <div>
                  <p className="text-lg font-semibold text-gray-900">
                    {team.university_name}
                  </p>
                  <p className="text-xs text-gray-500">{team.conference}</p>
                </div>
              </div>
              <span
                className={`rounded-full px-2.5 py-0.5 text-xs font-semibold ${
                  color === "red"
                    ? "bg-red-100 text-red-700"
                    : color === "yellow"
                      ? "bg-yellow-100 text-yellow-700"
                      : "bg-green-100 text-green-700"
                }`}
              >
                {pct}% used
              </span>
            </div>

            {/* Payroll metric — Oswald font for that heavy sports-ticker look */}
            <p
              className="mt-3 text-3xl font-bold text-gray-900"
              style={{ fontFamily: "var(--font-oswald), sans-serif" }}
            >
              {formatCurrency(team.active_payroll)}
            </p>
            <p
              className="mb-3 text-xs text-gray-500"
              style={{ fontFamily: "var(--font-oswald), sans-serif" }}
            >
              of {formatCurrency(team.estimated_cap_space)} cap
            </p>

            {/* Progress bar */}
            <ProgressBar value={pct} color={color} showAnimation />

            {/* Remaining cap */}
            <p className="mt-2 text-xs text-gray-500">
              <span
                className="font-medium text-gray-700"
                style={{ fontFamily: "var(--font-oswald), sans-serif" }}
              >
                {formatCurrency(remaining)}
              </span>{" "}
              remaining
            </p>
          </Card>
        );
      })}
    </div>
  );
}
