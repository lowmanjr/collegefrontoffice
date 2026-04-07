"use client";

import { useState, useEffect, useRef } from "react";
import Link from "next/link";
import Image from "next/image";
import { createClient } from "@supabase/supabase-js";

// Lightweight client-side Supabase instance (uses public anon key — safe)
const supabase = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL!,
  process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!
);

interface PlayerResult {
  id: string;
  name: string;
  position: string;
  star_rating: number;
}

interface TeamResult {
  id: string;
  university_name: string;
  logo_url: string | null;
}

interface Results {
  players: PlayerResult[];
  teams: TeamResult[];
}

export default function GlobalSearch() {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<Results>({ players: [], teams: [] });
  const [isSearching, setIsSearching] = useState(false);
  const [isOpen, setIsOpen] = useState(false);
  const [focusedIndex, setFocusedIndex] = useState(-1);
  const containerRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  // ── Debounced search ────────────────────────────────────────────────────
  useEffect(() => {
    if (query.length <= 1) {
      setResults({ players: [], teams: [] });
      setIsOpen(false);
      return;
    }

    setIsSearching(true);
    const timer = setTimeout(async () => {
      const pattern = `%${query}%`;

      const [{ data: players }, { data: teams }] = await Promise.all([
        supabase
          .from("players")
          .select("id, name, position, star_rating")
          .ilike("name", pattern)
          .limit(5),
        supabase
          .from("teams")
          .select("id, university_name, logo_url")
          .ilike("university_name", pattern)
          .limit(3),
      ]);

      setResults({
        players: players ?? [],
        teams: teams ?? [],
      });
      setFocusedIndex(-1);
      setIsOpen(true);
      setIsSearching(false);
    }, 300);

    return () => clearTimeout(timer);
  }, [query]);

  // ── Close on outside click or Escape ───────────────────────────────────
  useEffect(() => {
    function handleKey(e: KeyboardEvent) {
      if (e.key === "Escape") {
        setIsOpen(false);
        inputRef.current?.blur();
      }
      if ((e.metaKey || e.ctrlKey) && e.key === "k") {
        e.preventDefault();
        inputRef.current?.focus();
      }
    }
    function handleClick(e: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setIsOpen(false);
      }
    }
    document.addEventListener("keydown", handleKey);
    document.addEventListener("mousedown", handleClick);
    return () => {
      document.removeEventListener("keydown", handleKey);
      document.removeEventListener("mousedown", handleClick);
    };
  }, []);

  const hasResults = results.players.length > 0 || results.teams.length > 0;

  const flatResults: { type: "team" | "player"; id: string; href: string }[] = [
    ...results.teams.map((t) => ({ type: "team" as const, id: t.id, href: `/teams/${t.id}` })),
    ...results.players.map((p) => ({ type: "player" as const, id: p.id, href: `/players/${p.id}` })),
  ];

  function close() {
    setIsOpen(false);
    setQuery("");
    setFocusedIndex(-1);
  }

  function handleInputKeyDown(e: React.KeyboardEvent) {
    if (!isOpen || flatResults.length === 0) return;

    if (e.key === "ArrowDown") {
      e.preventDefault();
      setFocusedIndex((prev) => (prev < flatResults.length - 1 ? prev + 1 : 0));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setFocusedIndex((prev) => (prev > 0 ? prev - 1 : flatResults.length - 1));
    } else if (e.key === "Enter" && focusedIndex >= 0) {
      e.preventDefault();
      const item = flatResults[focusedIndex];
      if (item) {
        window.location.href = item.href;
        close();
      }
    }
  }

  return (
    <div ref={containerRef} className="relative">
      {/* ── Input ──────────────────────────────────────────────────────── */}
      <div className="flex items-center gap-2 bg-slate-800 border border-slate-700 rounded-lg px-3 py-1.5 w-full sm:w-64 focus-within:border-slate-500 transition-colors">
        {/* Magnifying glass icon */}
        <svg
          width="14"
          height="14"
          viewBox="0 0 14 14"
          fill="none"
          xmlns="http://www.w3.org/2000/svg"
          className="shrink-0 text-slate-400"
          aria-hidden="true"
        >
          <circle cx="5.5" cy="5.5" r="4.5" stroke="currentColor" strokeWidth="1.5" />
          <line
            x1="9.5"
            y1="9.5"
            x2="13"
            y2="13"
            stroke="currentColor"
            strokeWidth="1.5"
            strokeLinecap="round"
          />
        </svg>

        <input
          ref={inputRef}
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={handleInputKeyDown}
          placeholder="Search players & teams…"
          className="bg-transparent text-sm text-white placeholder-slate-400 outline-none w-full"
          aria-label="Global search"
          aria-expanded={isOpen}
          aria-haspopup="listbox"
        />

        {!query && (
          <kbd className="hidden sm:inline-block ml-auto text-[10px] text-slate-500 bg-slate-700 rounded px-1.5 py-0.5 font-mono pointer-events-none shrink-0">
            ⌘K
          </kbd>
        )}

        {/* Loading spinner */}
        {isSearching && (
          <svg
            className="animate-spin shrink-0 text-slate-400"
            width="12"
            height="12"
            viewBox="0 0 12 12"
            fill="none"
            xmlns="http://www.w3.org/2000/svg"
            aria-hidden="true"
          >
            <circle
              cx="6"
              cy="6"
              r="5"
              stroke="currentColor"
              strokeWidth="2"
              strokeDasharray="8 24"
              strokeLinecap="round"
            />
          </svg>
        )}
      </div>

      {/* ── Dropdown ───────────────────────────────────────────────────── */}
      {isOpen && hasResults && (
        <div
          role="listbox"
          className="absolute right-0 mt-2 w-72 sm:w-80 bg-white rounded-xl shadow-xl border border-gray-100 overflow-hidden z-50"
        >
          {/* Teams section */}
          {results.teams.length > 0 && (
            <div>
              <p className="px-4 pt-3 pb-1 text-[10px] font-bold uppercase tracking-widest text-slate-400">
                Teams
              </p>
              {results.teams.map((team, i) => (
                <Link
                  key={team.id}
                  href={`/teams/${team.id}`}
                  onClick={close}
                  role="option"
                  className={`flex items-center gap-3 px-4 py-2.5 transition-colors ${i === focusedIndex ? "bg-slate-100" : "hover:bg-slate-50"}`}
                >
                  {team.logo_url ? (
                    <Image
                      src={team.logo_url}
                      alt={team.university_name}
                      width={24}
                      height={24}
                      className="h-6 w-6 object-contain shrink-0"
                    />
                  ) : (
                    <div className="h-6 w-6 rounded bg-slate-100 shrink-0" />
                  )}
                  <span className="text-sm font-semibold text-gray-900">
                    {team.university_name}
                  </span>
                </Link>
              ))}
            </div>
          )}

          {/* Divider between sections */}
          {results.teams.length > 0 && results.players.length > 0 && (
            <div className="border-t border-gray-100 mx-4" />
          )}

          {/* Players section */}
          {results.players.length > 0 && (
            <div>
              <p className="px-4 pt-3 pb-1 text-[10px] font-bold uppercase tracking-widest text-slate-400">
                Players
              </p>
              {results.players.map((player, i) => {
                const clamped = Math.min(Math.max(player.star_rating, 0), 5);
                const flatIndex = results.teams.length + i;
                return (
                  <Link
                    key={player.id}
                    href={`/players/${player.id}`}
                    onClick={close}
                    role="option"
                    className={`flex items-center justify-between gap-3 px-4 py-2.5 transition-colors ${flatIndex === focusedIndex ? "bg-slate-100" : "hover:bg-slate-50"}`}
                  >
                    <div className="flex items-center gap-2 min-w-0">
                      <span className="rounded bg-slate-900 text-white px-1.5 py-0.5 text-[10px] font-bold uppercase shrink-0">
                        {player.position}
                      </span>
                      <span className="text-sm font-semibold text-gray-900 truncate">
                        {player.name}
                      </span>
                    </div>
                    <span className="text-xs shrink-0 tracking-tight">
                      <span className="text-yellow-500">{"★".repeat(clamped)}</span>
                      <span className="text-gray-300">{"☆".repeat(5 - clamped)}</span>
                    </span>
                  </Link>
                );
              })}
            </div>
          )}

          {/* Footer hint */}
          <p className="px-4 py-2 text-[10px] text-slate-400 border-t border-gray-100 bg-slate-50">
            <kbd className="rounded bg-slate-200 px-1 py-0.5 font-mono text-slate-600">↑↓</kbd> navigate &middot;{" "}
            <kbd className="rounded bg-slate-200 px-1 py-0.5 font-mono text-slate-600">↵</kbd> select &middot;{" "}
            <kbd className="rounded bg-slate-200 px-1 py-0.5 font-mono text-slate-600">esc</kbd> close
          </p>
        </div>
      )}

      {/* Empty state — query typed but nothing found */}
      {isOpen && !hasResults && !isSearching && query.length > 1 && (
        <div className="absolute right-0 mt-2 w-72 sm:w-80 bg-white rounded-xl shadow-xl border border-gray-100 px-4 py-5 z-50 text-center">
          <p className="text-sm text-slate-400">
            No results for <span className="font-semibold text-slate-600">"{query}"</span>
          </p>
        </div>
      )}
    </div>
  );
}
