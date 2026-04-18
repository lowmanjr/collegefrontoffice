"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const SPORTS = [
  { label: "Football", href: "/football/players" },
  { label: "Basketball", href: "/basketball/players" },
];

export default function SportSwitcher() {
  const pathname = usePathname();

  const isBasketball = pathname.startsWith("/basketball");
  const isFootball = pathname.startsWith("/football");

  // Only render on sport-specific pages
  if (!isFootball && !isBasketball) return null;

  return (
    <div className="flex items-center gap-1 bg-slate-800 rounded-lg p-0.5">
      {SPORTS.map(({ label, href }) => {
        const active =
          (label === "Football" && isFootball) ||
          (label === "Basketball" && isBasketball);

        return (
          <Link
            key={label}
            href={href}
            className={`px-3 py-1 rounded-md text-xs font-semibold transition-colors ${
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
  );
}
