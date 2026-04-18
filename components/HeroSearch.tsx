"use client";

import { useState, useEffect, useRef } from "react";
import Link from "next/link";
import Image from "next/image";
import { createClient } from "@supabase/supabase-js";

const supabase = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL!,
  process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!
);

interface PlayerResult {
  id: string;
  name: string;
  position: string;
}

interface TeamResult {
  id: string;
  university_name: string;
  logo_url: string | null;
}

export default function HeroSearch() {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<{ players: PlayerResult[]; teams: TeamResult[] }>({ players: [], teams: [] });
  const [isSearching, setIsSearching] = useState(false);
  const [isOpen, setIsOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

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
        supabase.from("players").select("id, slug, name, position").ilike("name", pattern).limit(5),
        supabase.from("teams").select("id, slug, university_name, logo_url").ilike("university_name", pattern).limit(3),
      ]);
      setResults({ players: players ?? [], teams: teams ?? [] });
      setIsOpen(true);
      setIsSearching(false);
    }, 300);
    return () => clearTimeout(timer);
  }, [query]);

  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) setIsOpen(false);
    }
    function handleKey(e: KeyboardEvent) {
      if (e.key === "Escape") setIsOpen(false);
    }
    document.addEventListener("mousedown", handleClick);
    document.addEventListener("keydown", handleKey);
    return () => {
      document.removeEventListener("mousedown", handleClick);
      document.removeEventListener("keydown", handleKey);
    };
  }, []);

  const hasResults = results.players.length > 0 || results.teams.length > 0;
  function close() { setIsOpen(false); setQuery(""); }

  return (
    <div ref={containerRef} className="relative mx-auto max-w-xl">
      <div className="flex items-center gap-3 bg-slate-800 border border-slate-600 rounded-xl px-5 py-3.5 focus-within:border-slate-400 focus-within:ring-1 focus-within:ring-slate-400 transition-all">
        <svg width="20" height="20" viewBox="0 0 20 20" fill="none" className="shrink-0 text-slate-400" aria-hidden="true">
          <circle cx="8.5" cy="8.5" r="6" stroke="currentColor" strokeWidth="1.8" />
          <line x1="13.5" y1="13.5" x2="18" y2="18" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
        </svg>
        <input
          ref={inputRef}
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Search players, teams, or positions..."
          className="bg-transparent text-base text-white placeholder-slate-500 outline-none w-full"
          aria-label="Search"
        />
        {isSearching && (
          <svg className="animate-spin shrink-0 text-slate-400" width="16" height="16" viewBox="0 0 16 16" fill="none">
            <circle cx="8" cy="8" r="6" stroke="currentColor" strokeWidth="2" strokeDasharray="10 28" strokeLinecap="round" />
          </svg>
        )}
        <kbd className="hidden sm:inline-block text-[10px] text-slate-500 bg-slate-700 rounded px-1.5 py-0.5 font-mono shrink-0">
          ⌘K
        </kbd>
      </div>

      {/* Dropdown */}
      {isOpen && hasResults && (
        <div className="absolute left-0 right-0 mt-2 bg-white rounded-xl shadow-2xl border border-gray-100 overflow-hidden z-50">
          {results.teams.length > 0 && (
            <div>
              <p className="px-4 pt-3 pb-1 text-[10px] font-bold uppercase tracking-widest text-slate-400">Teams</p>
              {results.teams.map((team) => (
                <Link key={team.id} href={`/football/teams/${(team as any).slug ?? team.id}`} onClick={close}
                  className="flex items-center gap-3 px-4 py-2.5 hover:bg-slate-50 transition-colors">
                  {team.logo_url ? (
                    <Image src={team.logo_url} alt={team.university_name} width={24} height={24} className="h-6 w-6 object-contain shrink-0" />
                  ) : <div className="h-6 w-6 rounded bg-slate-100 shrink-0" />}
                  <span className="text-sm font-semibold text-gray-900">{team.university_name}</span>
                </Link>
              ))}
            </div>
          )}
          {results.teams.length > 0 && results.players.length > 0 && <div className="border-t border-gray-100 mx-4" />}
          {results.players.length > 0 && (
            <div>
              <p className="px-4 pt-3 pb-1 text-[10px] font-bold uppercase tracking-widest text-slate-400">Players</p>
              {results.players.map((player) => (
                <Link key={player.id} href={`/football/players/${(player as any).slug ?? player.id}`} onClick={close}
                  className="flex items-center justify-between px-4 py-2.5 hover:bg-slate-50 transition-colors">
                  <span className="text-sm font-semibold text-gray-900">{player.name}</span>
                  <span className="rounded bg-slate-900 text-white px-1.5 py-0.5 text-[10px] font-bold uppercase">{player.position}</span>
                </Link>
              ))}
            </div>
          )}
        </div>
      )}

      {isOpen && !hasResults && !isSearching && query.length > 1 && (
        <div className="absolute left-0 right-0 mt-2 bg-white rounded-xl shadow-2xl border border-gray-100 px-4 py-5 z-50 text-center">
          <p className="text-sm text-slate-400">
            No results for &ldquo;<span className="font-semibold text-slate-600">{query}</span>&rdquo;
          </p>
        </div>
      )}
    </div>
  );
}
