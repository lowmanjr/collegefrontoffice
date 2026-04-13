"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const LINKS = [
  { label: "Players", href: "/basketball/players" },
  { label: "Teams", href: "/basketball/teams" },
  { label: "Portal", href: "/basketball/portal" },
  { label: "Recruits", href: "/basketball/recruits" },
  { label: "Methodology", href: "/basketball/methodology" },
];

export default function BasketballSubNav() {
  const pathname = usePathname();

  return (
    <nav className="bg-slate-800 border-b border-slate-700">
      <div className="mx-auto max-w-7xl px-4 flex items-center gap-1 h-9 overflow-x-auto">
        {LINKS.map(({ label, href }) => {
          const active = pathname === href || pathname.startsWith(href + "/");
          return (
            <Link
              key={href}
              href={href}
              className={`px-3 py-1 rounded text-xs font-semibold whitespace-nowrap transition-colors ${
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
