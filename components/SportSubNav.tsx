"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

type Sport = "football" | "basketball";

const SPORT_LABELS: Record<Sport, string> = {
  football: "Football",
  basketball: "Basketball",
};

const SECTIONS = [
  { label: "Players", path: "players" },
  { label: "Teams", path: "teams" },
  { label: "Portal", path: "portal" },
  { label: "Recruits", path: "recruits" },
  { label: "Methodology", path: "methodology" },
];

interface SportSubNavProps {
  sport: Sport;
}

export default function SportSubNav({ sport }: SportSubNavProps) {
  const pathname = usePathname();
  const sportLabel = SPORT_LABELS[sport];

  return (
    <nav className="bg-slate-800 border-b border-slate-700">
      <div className="mx-auto max-w-6xl px-4 sm:px-6 flex items-center gap-1 h-9 overflow-x-auto">
        {/* Sport label — non-clickable "you are here" signal */}
        <span className="shrink-0 px-2 text-xs font-semibold text-emerald-400 whitespace-nowrap">
          {sportLabel}
        </span>
        <span className="shrink-0 text-slate-600 text-xs" aria-hidden="true">
          ·
        </span>

        {/* Section links */}
        {SECTIONS.map(({ label, path }) => {
          const href = `/${sport}/${path}`;
          const active = pathname === href || pathname.startsWith(href + "/");
          return (
            <Link
              key={path}
              href={href}
              className={`shrink-0 px-3 py-1 rounded text-xs font-semibold whitespace-nowrap transition-colors ${
                active
                  ? "bg-emerald-500 text-white"
                  : "text-slate-400 hover:text-white"
              }`}
            >
              {label}
            </Link>
          );
        })}
      </div>
    </nav>
  );
}
