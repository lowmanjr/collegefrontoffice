"use client";

import { useState } from "react";
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

export default function PlayerTableClient({ initialPlayers }: Props) {
  const [searchQuery, setSearchQuery]     = useState("");
  const [positionFilter, setPositionFilter] = useState("All");

  const filteredPlayers = initialPlayers.filter((player) => {
    const matchesSearch   = player.name.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesPosition = positionFilter === "All" || player.position === positionFilter;
    return matchesSearch && matchesPosition;
  });

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
            onChange={(e) => setSearchQuery(e.target.value)}
            className="rounded-lg border border-gray-200 bg-white px-3 py-2 text-sm text-gray-900 shadow-sm placeholder:text-gray-400 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
          />
          <select
            value={positionFilter}
            onChange={(e) => setPositionFilter(e.target.value)}
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
        Showing {filteredPlayers.length} of {initialPlayers.length} players
      </p>

      <Table>
        <TableHead>
          <TableRow>
            <TableHeaderCell>Name</TableHeaderCell>
            <TableHeaderCell>Position</TableHeaderCell>
            <TableHeaderCell>Stars</TableHeaderCell>
            <TableHeaderCell>Experience</TableHeaderCell>
            <TableHeaderCell className="text-right">CFO Valuation</TableHeaderCell>
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
            filteredPlayers.map((player) => (
              <TableRow key={player.id}>
                <TableCell className="font-medium text-gray-900">
                  {player.name}
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
                <TableCell className="text-right font-semibold text-gray-900">
                  {formatCurrency(player.cfo_valuation)}
                </TableCell>
              </TableRow>
            ))
          )}
        </TableBody>
      </Table>
    </Card>
  );
}
