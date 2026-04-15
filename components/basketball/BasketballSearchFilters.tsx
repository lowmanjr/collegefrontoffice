"use client";

import { useRouter, usePathname, useSearchParams } from "next/navigation";
import { useCallback, useRef } from "react";

const POSITIONS = ["All", "PG", "SG", "SF", "PF", "C", "G", "F"];

interface Props {
  initialQuery: string;
  initialPosition: string;
}

export default function BasketballSearchFilters({ initialQuery, initialPosition }: Props) {
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

  function handlePositionClick(position: string) {
    router.replace(buildUrl({ pos: position }), { scroll: false });
  }

  const currentPos = searchParams.get("pos") ?? "All";

  return (
    <div className="mb-4 flex flex-col sm:flex-row gap-3">
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
          placeholder="Search players..."
          defaultValue={initialQuery}
          onChange={handleNameChange}
          className="w-full rounded-lg border border-gray-300 bg-white py-2.5 pl-9 pr-4 text-sm text-slate-900 placeholder-slate-400 focus:border-emerald-500 focus:ring-1 focus:ring-emerald-500 outline-none transition-colors"
        />
      </div>

      {/* Position filter pills */}
      <div className="flex gap-1.5 flex-wrap">
        {POSITIONS.map((p) => {
          const active = currentPos === p;
          return (
            <button
              key={p}
              onClick={() => handlePositionClick(p)}
              className={`px-3 py-2 rounded-lg text-xs font-semibold transition-colors ${
                active
                  ? "bg-emerald-500 text-white"
                  : "bg-white text-slate-600 border border-gray-200 hover:border-slate-300"
              }`}
            >
              {p}
            </button>
          );
        })}
      </div>
    </div>
  );
}
