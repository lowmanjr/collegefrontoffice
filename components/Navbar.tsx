"use client";

import Link from "next/link";
import GlobalSearch from "@/components/GlobalSearch";
import CfoLogo from "@/components/CfoLogo";
import SportSwitcher from "@/components/SportSwitcher";

export default function Navbar() {
  return (
    <header className="bg-slate-900 text-white border-b border-slate-800">
      <div className="mx-auto max-w-6xl px-4 sm:px-6 h-14 flex items-center justify-between gap-4">
        {/* Logo — clicks to home */}
        <Link href="/" className="group shrink-0">
          <span className="hidden sm:inline">
            <CfoLogo
              height={32}
              showWordmark
              className="group-hover:[&_span]:text-white group-hover:[&_span]:transition-colors"
            />
          </span>
          <span className="sm:hidden">
            <CfoLogo height={28} />
          </span>
        </Link>

        {/* Right side: sport switcher + search */}
        <div className="flex items-center gap-3 sm:gap-4 min-w-0">
          <SportSwitcher />
          <GlobalSearch />
        </div>
      </div>
    </header>
  );
}
