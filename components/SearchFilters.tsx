"use client";

import { useRouter, usePathname, useSearchParams } from "next/navigation";
import { useCallback, useRef } from "react";

const POSITIONS = [
  "All",
  "QB",
  "RB",
  "WR",
  "TE",
  "OL",
  "DL",
  "EDGE",
  "LB",
  "CB",
  "S",
  "ATH",
  "K",
  "P",
];

export default function SearchFilters() {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();

  const debounceTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Build a new query string from current params + overrides
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
    [pathname, searchParams]
  );

  function handleNameChange(e: React.ChangeEvent<HTMLInputElement>) {
    const value = e.target.value;
    if (debounceTimer.current) clearTimeout(debounceTimer.current);
    debounceTimer.current = setTimeout(() => {
      router.replace(buildUrl({ q: value }), { scroll: false });
    }, 350);
  }

  function handlePositionChange(e: React.ChangeEvent<HTMLSelectElement>) {
    router.replace(buildUrl({ pos: e.target.value }), { scroll: false });
  }

  const currentQ = searchParams.get("q") ?? "";
  const currentPos = searchParams.get("pos") ?? "All";

  return (
    <div className="flex flex-col sm:flex-row gap-3 mb-4">
      {/* Name search */}
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
          placeholder="Search players…"
          defaultValue={currentQ}
          onChange={handleNameChange}
          className="w-full rounded-lg border border-gray-200 bg-white py-2.5 pl-9 pr-4 text-sm text-slate-900 placeholder-slate-400 shadow-sm focus:border-emerald-500 focus:outline-none focus:ring-1 focus:ring-emerald-500 transition-colors"
        />
      </div>

      {/* Position filter */}
      <div className="relative sm:w-40">
        <select
          value={currentPos}
          onChange={handlePositionChange}
          className="w-full appearance-none rounded-lg border border-gray-200 bg-white py-2.5 pl-3 pr-8 text-sm text-slate-900 shadow-sm focus:border-emerald-500 focus:outline-none focus:ring-1 focus:ring-emerald-500 transition-colors cursor-pointer"
        >
          {POSITIONS.map((pos) => (
            <option key={pos} value={pos}>
              {pos === "All" ? "All Positions" : pos}
            </option>
          ))}
        </select>
        {/* Chevron */}
        <svg
          className="pointer-events-none absolute right-2.5 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400"
          viewBox="0 0 20 20"
          fill="currentColor"
          aria-hidden="true"
        >
          <path
            fillRule="evenodd"
            clipRule="evenodd"
            d="M5.22 8.22a.75.75 0 011.06 0L10 11.94l3.72-3.72a.75.75 0 111.06 1.06l-4.25 4.25a.75.75 0 01-1.06 0L5.22 9.28a.75.75 0 010-1.06z"
          />
        </svg>
      </div>
    </div>
  );
}
