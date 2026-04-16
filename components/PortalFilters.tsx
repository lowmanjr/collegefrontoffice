"use client";

import { useRouter, usePathname, useSearchParams } from "next/navigation";
import { useCallback, useRef } from "react";

const POSITIONS = ["All", "PG", "SG", "SF", "PF", "C"];
const STATUSES = ["All", "Committed", "Evaluating"];
const CONFERENCES = [
  { label: "All Conferences", value: "" },
  { label: "SEC", value: "SEC" },
  { label: "ACC", value: "ACC" },
  { label: "Big Ten", value: "Big Ten" },
  { label: "Big 12", value: "Big 12" },
  { label: "Big East", value: "Big East" },
  { label: "Mountain West", value: "Mountain West" },
];

interface PortalFiltersProps {
  view: string;
  totalPlayers: number;
  totalTeams: number;
}

export default function PortalFilters({
  view,
  totalPlayers,
  totalTeams,
}: PortalFiltersProps) {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const debounceTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const buildUrl = useCallback(
    (overrides: Record<string, string>) => {
      const params = new URLSearchParams(searchParams.toString());
      for (const [key, value] of Object.entries(overrides)) {
        if (value === "" || value === "All") {
          params.delete(key);
        } else {
          params.set(key, value);
        }
      }
      const qs = params.toString();
      return qs ? `${pathname}?${qs}` : pathname;
    },
    [pathname, searchParams],
  );

  function handleViewChange(v: string) {
    // Reset filters when switching views
    const params = new URLSearchParams();
    if (v !== "player") params.set("view", v);
    const qs = params.toString();
    router.replace(qs ? `${pathname}?${qs}` : pathname, { scroll: false });
  }

  function handleSearch(e: React.ChangeEvent<HTMLInputElement>) {
    const value = e.target.value;
    if (debounceTimer.current) clearTimeout(debounceTimer.current);
    debounceTimer.current = setTimeout(() => {
      router.replace(buildUrl({ q: value }), { scroll: false });
    }, 350);
  }

  function handleSelect(key: string, value: string) {
    router.replace(buildUrl({ [key]: value }), { scroll: false });
  }

  const currentQ = searchParams.get("q") ?? "";
  const currentPos = searchParams.get("pos") ?? "All";
  const currentStatus = searchParams.get("status") ?? "All";
  const currentConf = searchParams.get("conf") ?? "";

  const pillBase = "px-4 py-2 rounded-full text-sm font-semibold transition-colors";
  const pillActive = `${pillBase} bg-emerald-500 text-white`;
  const pillInactive = `${pillBase} bg-white text-slate-600 border border-slate-200 hover:border-slate-300`;

  return (
    <div className="space-y-3 py-4">
      {/* Row 1: Toggle + Search */}
      <div className="flex flex-col sm:flex-row gap-3">
        {/* Toggle */}
        <div className="flex gap-2 shrink-0">
          <button
            onClick={() => handleViewChange("player")}
            className={view === "player" ? pillActive : pillInactive}
          >
            By Player
          </button>
          <button
            onClick={() => handleViewChange("team")}
            className={view === "team" ? pillActive : pillInactive}
          >
            By Team
          </button>
        </div>

        {/* Search — By Player view only */}
        {view === "player" && (
          <div className="relative flex-1">
            <svg
              className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400"
              viewBox="0 0 20 20"
              fill="currentColor"
              aria-hidden="true"
            >
              <path
                fillRule="evenodd"
                clipRule="evenodd"
                d="M9 3.5a5.5 5.5 0 100 11 5.5 5.5 0 000-11zM2 9a7 7 0 1112.452 4.391l3.328 3.329a.75.75 0 11-1.06 1.06l-3.329-3.328A7 7 0 012 9z"
              />
            </svg>
            <input
              type="text"
              placeholder="Search players..."
              defaultValue={currentQ}
              onChange={handleSearch}
              className="w-full rounded-lg border border-gray-200 bg-white py-2.5 pl-9 pr-4 text-sm text-slate-900 placeholder-slate-400 shadow-sm focus:border-emerald-500 focus:outline-none focus:ring-1 focus:ring-emerald-500 transition-colors"
            />
          </div>
        )}
      </div>

      {/* Row 2: Dropdowns — By Player view only */}
      {view === "player" && (
        <div className="flex flex-wrap gap-2">
          {/* Position */}
          <div className="relative">
            <select
              value={currentPos}
              onChange={(e) => handleSelect("pos", e.target.value)}
              className="appearance-none rounded-lg border border-gray-200 bg-white py-2 pl-3 pr-8 text-sm text-slate-900 shadow-sm focus:border-emerald-500 focus:outline-none focus:ring-1 focus:ring-emerald-500 cursor-pointer"
            >
              {POSITIONS.map((p) => (
                <option key={p} value={p}>
                  {p === "All" ? "All Positions" : p}
                </option>
              ))}
            </select>
            <svg className="pointer-events-none absolute right-2.5 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
              <path fillRule="evenodd" clipRule="evenodd" d="M5.22 8.22a.75.75 0 011.06 0L10 11.94l3.72-3.72a.75.75 0 111.06 1.06l-4.25 4.25a.75.75 0 01-1.06 0L5.22 9.28a.75.75 0 010-1.06z" />
            </svg>
          </div>

          {/* Status */}
          <div className="relative">
            <select
              value={currentStatus}
              onChange={(e) => handleSelect("status", e.target.value)}
              className="appearance-none rounded-lg border border-gray-200 bg-white py-2 pl-3 pr-8 text-sm text-slate-900 shadow-sm focus:border-emerald-500 focus:outline-none focus:ring-1 focus:ring-emerald-500 cursor-pointer"
            >
              {STATUSES.map((s) => (
                <option key={s} value={s}>
                  {s === "All" ? "All Statuses" : s}
                </option>
              ))}
            </select>
            <svg className="pointer-events-none absolute right-2.5 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
              <path fillRule="evenodd" clipRule="evenodd" d="M5.22 8.22a.75.75 0 011.06 0L10 11.94l3.72-3.72a.75.75 0 111.06 1.06l-4.25 4.25a.75.75 0 01-1.06 0L5.22 9.28a.75.75 0 010-1.06z" />
            </svg>
          </div>

          {/* Conference */}
          <div className="relative">
            <select
              value={currentConf}
              onChange={(e) => handleSelect("conf", e.target.value)}
              className="appearance-none rounded-lg border border-gray-200 bg-white py-2 pl-3 pr-8 text-sm text-slate-900 shadow-sm focus:border-emerald-500 focus:outline-none focus:ring-1 focus:ring-emerald-500 cursor-pointer"
            >
              {CONFERENCES.map((c) => (
                <option key={c.value} value={c.value}>
                  {c.label}
                </option>
              ))}
            </select>
            <svg className="pointer-events-none absolute right-2.5 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
              <path fillRule="evenodd" clipRule="evenodd" d="M5.22 8.22a.75.75 0 011.06 0L10 11.94l3.72-3.72a.75.75 0 111.06 1.06l-4.25 4.25a.75.75 0 01-1.06 0L5.22 9.28a.75.75 0 010-1.06z" />
            </svg>
          </div>
        </div>
      )}

      {/* Row 2 for By Team: Conference filter only */}
      {view === "team" && (
        <div className="flex flex-wrap gap-2">
          {CONFERENCES.map((c) => {
            const isActive = currentConf === c.value;
            return (
              <button
                key={c.value}
                onClick={() => handleSelect("conf", c.value)}
                className={isActive ? pillActive : pillInactive}
              >
                {c.label}
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
}
