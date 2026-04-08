"use client";

import { useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import GlobalSearch from "@/components/GlobalSearch";
import CfoLogo from "@/components/CfoLogo";

const NAV_LINKS = [
  { label: "Home", href: "/" },
  { label: "Players", href: "/players" },
  { label: "Recruits", href: "/recruits" },
  { label: "Teams", href: "/teams" },
  { label: "Methodology", href: "/methodology" },
];

export default function Navbar() {
  const [isOpen, setIsOpen] = useState(false);
  const pathname = usePathname();

  function isActive(href: string) {
    if (href === "/") return pathname === "/";
    return pathname.startsWith(href);
  }

  return (
    <header className="bg-slate-900 text-white border-b border-slate-800">
      {/* ── Main bar ───────────────────────────────────────────────────── */}
      <div className="mx-auto max-w-6xl px-4 sm:px-6 h-14 flex items-center justify-between">
        {/* Logo */}
        <Link href="/" className="group">
          <span className="hidden sm:inline">
            <CfoLogo height={32} showWordmark className="group-hover:[&_span]:text-white group-hover:[&_span]:transition-colors" />
          </span>
          <span className="sm:hidden">
            <CfoLogo height={28} />
          </span>
        </Link>

        {/* Desktop links + search */}
        <div className="hidden md:flex items-center gap-6">
          <nav className="flex items-center gap-6">
            {NAV_LINKS.map(({ label, href }) => (
              <Link
                key={href}
                href={href}
                className={`relative text-sm font-medium transition-colors py-1 ${
                  isActive(href)
                    ? "text-white"
                    : "text-gray-300 hover:text-white"
                }`}
              >
                {label}
                {isActive(href) && (
                  <span className="absolute -bottom-1 left-0 right-0 h-0.5 rounded-full bg-emerald-400" />
                )}
              </Link>
            ))}
          </nav>
          <GlobalSearch />
        </div>

        {/* Hamburger button — mobile only */}
        <button
          onClick={() => setIsOpen((prev) => !prev)}
          className="md:hidden flex items-center justify-center w-9 h-9 rounded text-gray-300 hover:text-white hover:bg-slate-700 transition-colors"
          aria-label={isOpen ? "Close menu" : "Open menu"}
          aria-expanded={isOpen}
        >
          {isOpen ? (
            /* X icon */
            <svg
              width="18"
              height="18"
              viewBox="0 0 18 18"
              fill="none"
              xmlns="http://www.w3.org/2000/svg"
              aria-hidden="true"
            >
              <line
                x1="1"
                y1="1"
                x2="17"
                y2="17"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
              />
              <line
                x1="17"
                y1="1"
                x2="1"
                y2="17"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
              />
            </svg>
          ) : (
            /* Hamburger icon */
            <svg
              width="18"
              height="14"
              viewBox="0 0 18 14"
              fill="none"
              xmlns="http://www.w3.org/2000/svg"
              aria-hidden="true"
            >
              <line
                x1="0"
                y1="1"
                x2="18"
                y2="1"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
              />
              <line
                x1="0"
                y1="7"
                x2="18"
                y2="7"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
              />
              <line
                x1="0"
                y1="13"
                x2="18"
                y2="13"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
              />
            </svg>
          )}
        </button>
      </div>

      {/* ── Mobile dropdown ─────────────────────────────────────────────── */}
      {isOpen && (
        <nav className="md:hidden bg-slate-800 border-t border-slate-700 py-2 flex flex-col">
          {NAV_LINKS.map(({ label, href }) => (
            <Link
              key={href}
              href={href}
              onClick={() => setIsOpen(false)}
              className={`block px-4 py-2.5 text-sm font-medium transition-colors ${
                isActive(href)
                  ? "text-white bg-slate-700 border-l-2 border-emerald-400"
                  : "text-gray-300 hover:text-white hover:bg-slate-700"
              }`}
            >
              {label}
            </Link>
          ))}
          <div className="px-4 pt-3 pb-1">
            <GlobalSearch />
          </div>
        </nav>
      )}
    </header>
  );
}
