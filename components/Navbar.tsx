"use client";

import { useState } from "react";
import Link from "next/link";

const NAV_LINKS = [
  { label: "Home",    href: "/" },
  { label: "Players", href: "/players" },
  { label: "Teams",   href: "/teams" },
];

export default function Navbar() {
  const [isOpen, setIsOpen] = useState(false);

  return (
    <header className="bg-slate-900 text-white">
      {/* ── Main bar ───────────────────────────────────────────────────── */}
      <div className="mx-auto max-w-6xl px-4 sm:px-6 h-14 flex items-center justify-between">

        {/* Logo */}
        <Link href="/" className="flex items-center gap-2.5 group">
          <svg
            width="38"
            height="32"
            viewBox="0 0 38 32"
            fill="none"
            xmlns="http://www.w3.org/2000/svg"
            aria-hidden="true"
          >
            <text
              x="1"
              y="26"
              fontFamily="var(--font-oswald), sans-serif"
              fontStyle="italic"
              fontWeight="700"
              fontSize="26"
              fill="white"
              letterSpacing="-1"
            >
              CFO
            </text>
            <line x1="33" y1="2" x2="27" y2="30" stroke="#4ade80" strokeWidth="2.5" strokeLinecap="round" />
          </svg>
          <span
            className="hidden sm:block text-sm font-semibold text-gray-200 group-hover:text-white transition-colors"
            style={{ fontFamily: "var(--font-oswald), sans-serif", letterSpacing: "0.06em" }}
          >
            CollegeFrontOffice
          </span>
        </Link>

        {/* Desktop links */}
        <nav className="hidden md:flex items-center gap-6">
          {NAV_LINKS.map(({ label, href }) => (
            <Link
              key={href}
              href={href}
              className="text-sm font-medium text-gray-300 hover:text-white transition-colors"
            >
              {label}
            </Link>
          ))}
        </nav>

        {/* Hamburger button — mobile only */}
        <button
          onClick={() => setIsOpen((prev) => !prev)}
          className="md:hidden flex items-center justify-center w-9 h-9 rounded text-gray-300 hover:text-white hover:bg-slate-700 transition-colors"
          aria-label={isOpen ? "Close menu" : "Open menu"}
          aria-expanded={isOpen}
        >
          {isOpen ? (
            /* X icon */
            <svg width="18" height="18" viewBox="0 0 18 18" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
              <line x1="1" y1="1" x2="17" y2="17" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
              <line x1="17" y1="1" x2="1" y2="17" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
            </svg>
          ) : (
            /* Hamburger icon */
            <svg width="18" height="14" viewBox="0 0 18 14" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
              <line x1="0" y1="1"  x2="18" y2="1"  stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
              <line x1="0" y1="7"  x2="18" y2="7"  stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
              <line x1="0" y1="13" x2="18" y2="13" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
            </svg>
          )}
        </button>

      </div>

      {/* ── Mobile dropdown ─────────────────────────────────────────────── */}
      {isOpen && (
        <nav className="md:hidden bg-slate-800 border-t border-slate-700 px-4 py-3 flex flex-col">
          {NAV_LINKS.map(({ label, href }) => (
            <Link
              key={href}
              href={href}
              onClick={() => setIsOpen(false)}
              className="py-3 text-sm font-medium text-gray-300 hover:text-white border-b border-slate-700 last:border-0 transition-colors"
            >
              {label}
            </Link>
          ))}
        </nav>
      )}
    </header>
  );
}
