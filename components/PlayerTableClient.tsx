"use client";

import { useState } from "react";
import Link from "next/link";
import {
  Card,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeaderCell,
  TableRow,
} from "@tremor/react";

export interface Player {
  id: string;
  name: string;
  position: string;
  star_rating: number;
  experience_level: string;
  cfo_valuation: number;
}

interface Props {
  initialPlayers: Player[];
}

const POSITIONS = [
  "All", "QB", "RB", "WR", "TE", "LT", "IOL", "EDGE", "DT", "LB", "CB", "S", "ATH",
];

const EXPERIENCE_BADGE: Record<string, string> = {
  "Active Roster": "bg-blue-100 text-blue-700",
  Portal:          "bg-orange-100 text-orange-700",
  "High School":   "bg-green-100 text-green-700",
};

function formatCurrency(value: number): string {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 0,
  }).format(value);
}

function renderStars(rating: number): string {
  const filled = "★".repeat(Math.min(Math.max(rating, 0), 5));
  const empty  = "☆".repeat(5 - Math.min(Math.max(rating, 0), 5));
  return filled + empty;
}

const ITEMS_PER_PAGE = 50;

export default function PlayerTableClient({ initialPlayers }: Props) {
  const [searchQuery, setSearchQuery]       = useState("");
  const [positionFilter, setPositionFilter] = useState("All");
  const [currentPage, setCurrentPage]       = useState(1);

  const filteredPlayers = initialPlayers.filter((player) => {
    const matchesSearch   = player.name.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesPosition = positionFilter === "All" || player.position === positionFilter;
    return matchesSearch && matchesPosition;
  });

  const totalPages      = Math.ceil(filteredPlayers.length / ITEMS_PER_PAGE);
  const paginatedPlayers = filteredPlayers.slice(
    (currentPage - 1) * ITEMS_PER_PAGE,
    currentPage * ITEMS_PER_PAGE,
  );

  return (
    <Card>
      <div className="mb-4 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 className="text-xl font-semibold text-gray-900">Player Valuations</h2>
          <p className="text-sm text-gray-500">C.F.O. Valuation — V1.0 Algorithm</p>
        </div>

        {/* Controls */}
        <div className="flex flex-col gap-2 sm:flex-row">
          <input
            type="text"
            placeholder="Search by name..."
            value={searchQuery}
            onChange={(e) => { setSearchQuery(e.target.value); setCurrentPage(1); }}
            className="rounded-lg border border-gray-200 bg-white px-3 py-2 text-sm text-gray-900 shadow-sm placeholder:text-gray-400 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
          />
          <select
            value={positionFilter}
            onChange={(e) => { setPositionFilter(e.target.value); setCurrentPage(1); }}
            className="rounded-lg border border-gray-200 bg-white px-3 py-2 text-sm text-gray-900 shadow-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
          >
            {POSITIONS.map((pos) => (
              <option key={pos} value={pos}>
                {pos === "All" ? "All Positions" : pos}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Result count */}
      <p className="mb-3 text-xs text-gray-400">
        Showing {paginatedPlayers.length} of {filteredPlayers.length} players
        {filteredPlayers.length !== initialPlayers.length && ` (${initialPlayers.length} total)`}
      </p>

      {/* ── Desktop table (md+) ─────────────────────────────────────────── */}
      <div className="hidden md:block">
        <Table>
          <TableHead className="bg-slate-900">
            <TableRow>
              <TableHeaderCell className="text-white">Name</TableHeaderCell>
              <TableHeaderCell className="text-white">Position</TableHeaderCell>
              <TableHeaderCell className="text-white">Stars</TableHeaderCell>
              <TableHeaderCell className="text-white">Experience</TableHeaderCell>
              <TableHeaderCell className="text-right text-white">CFO Valuation</TableHeaderCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {filteredPlayers.length === 0 ? (
              <TableRow>
                <TableCell colSpan={5} className="py-8 text-center text-sm text-gray-400">
                  No players match your search.
                </TableCell>
              </TableRow>
            ) : (
              paginatedPlayers.map((player) => (
                <TableRow key={player.id} className="hover:bg-slate-50 transition-colors">
                  <TableCell className="font-medium">
                    <Link
                      href={`/players/${player.id}`}
                      className="text-blue-600 hover:underline hover:text-blue-800"
                    >
                      {player.name}
                    </Link>
                  </TableCell>
                  <TableCell>
                    <span className="rounded bg-gray-100 px-2 py-0.5 text-xs font-semibold text-gray-700">
                      {player.position}
                    </span>
                  </TableCell>
                  <TableCell>
                    <span className="tracking-tight">
                      <span className="text-yellow-500">
                        {"★".repeat(Math.min(Math.max(player.star_rating, 0), 5))}
                      </span>
                      <span className="text-gray-300">
                        {"☆".repeat(5 - Math.min(Math.max(player.star_rating, 0), 5))}
                      </span>
                    </span>
                  </TableCell>
                  <TableCell>
                    <span
                      className={`rounded-full px-2.5 py-0.5 text-xs font-medium ${
                        EXPERIENCE_BADGE[player.experience_level] ?? "bg-gray-100 text-gray-600"
                      }`}
                    >
                      {player.experience_level}
                    </span>
                  </TableCell>
                  <TableCell
                    className="text-right font-semibold text-gray-900"
                    style={{ fontFamily: "var(--font-oswald), sans-serif", fontSize: "1.05rem", letterSpacing: "0.02em" }}
                  >
                    {formatCurrency(player.cfo_valuation)}
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </div>

      {/* ── Mobile trading cards (below md) ─────────────────────────────── */}
      <div className="block md:hidden space-y-4">
        {filteredPlayers.length === 0 ? (
          <p className="py-8 text-center text-sm text-gray-400">
            No players match your search.
          </p>
        ) : (
          paginatedPlayers.map((player) => (
            <div
              key={player.id}
              className="bg-white rounded-lg border border-gray-200 p-4 shadow-sm"
            >
              {/* Top row: name (link) + valuation */}
              <div className="flex items-start justify-between gap-2">
                <Link
                  href={`/players/${player.id}`}
                  className="text-base font-bold text-blue-600 hover:underline hover:text-blue-800 leading-tight"
                >
                  {player.name}
                </Link>
                <span
                  className="text-lg font-bold text-gray-900 shrink-0"
                  style={{ fontFamily: "var(--font-oswald), sans-serif", letterSpacing: "0.02em" }}
                >
                  {formatCurrency(player.cfo_valuation)}
                </span>
              </div>

              {/* Middle row: star rating */}
              <div className="mt-1 tracking-tight">
                <span className="text-yellow-500">
                  {"★".repeat(Math.min(Math.max(player.star_rating, 0), 5))}
                </span>
                <span className="text-gray-300">
                  {"☆".repeat(5 - Math.min(Math.max(player.star_rating, 0), 5))}
                </span>
              </div>

              {/* Bottom row: position + experience badges */}
              <div className="mt-3 flex flex-wrap gap-2">
                <span className="rounded bg-slate-900 text-white px-2.5 py-0.5 text-xs font-semibold uppercase">
                  {player.position}
                </span>
                <span
                  className={`rounded-full px-2.5 py-0.5 text-xs font-medium ${
                    EXPERIENCE_BADGE[player.experience_level] ?? "bg-gray-100 text-gray-600"
                  }`}
                >
                  {player.experience_level}
                </span>
              </div>
            </div>
          ))
        )}
      </div>
      {/* ── Pagination controls ──────────────────────────────────────────── */}
      {totalPages > 1 && (
        <div className="mt-6 flex items-center justify-between gap-4">
          <button
            onClick={() => setCurrentPage((p) => p - 1)}
            disabled={currentPage === 1}
            className="px-4 py-2 text-sm font-medium border border-gray-200 rounded-md hover:bg-slate-50 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
          >
            ← Previous
          </button>

          <span className="text-sm text-gray-500">
            Page <span className="font-semibold text-gray-900">{currentPage}</span> of{" "}
            <span className="font-semibold text-gray-900">{totalPages}</span>
          </span>

          <button
            onClick={() => setCurrentPage((p) => p + 1)}
            disabled={currentPage === totalPages}
            className="px-4 py-2 text-sm font-medium border border-gray-200 rounded-md hover:bg-slate-50 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
          >
            Next →
          </button>
        </div>
      )}
    </Card>
  );
}
