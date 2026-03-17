# CollegeFrontOffice.com - Master Architecture Document

## 1. Project Overview
College Front Office is a data dashboard and valuation tool for the modern college sports economy. It aggregates player data, calculates a proprietary "C.F.O. Valuation" based on positional scarcity and experience, and tracks estimated university salary cap space.

## 2. Tech Stack
* **Frontend Framework:** Next.js (App Router)
* **Styling:** Tailwind CSS
* **UI Components:** shadcn/ui and Tremor (for charts, data tables, and metrics)
* **Database:** Supabase (PostgreSQL)
* **Hosting:** Vercel
* **Data Pipeline:** Python (pandas, BeautifulSoup) -> Excel Sandbox -> Supabase API

## 3. Data Architecture (Phase 1 MVP)
The database will initially rely on two primary tables:

### Table A: `players`
* `id` (UUID, primary key)
* `name` (String)
* `high_school` (String)
* `position` (String)
* `star_rating` (Integer: 3, 4, or 5)
* `experience_level` (String: "High School", "Active Roster", "Portal")
* `composite_score` (Float)
* `cfo_valuation` (Integer - calculated)
* `last_updated` (Timestamp)

### Table B: `teams`
* `id` (UUID, primary key)
* `university_name` (String)
* `conference` (String)
* `estimated_cap_space` (Integer - defaults to $20,500,000)
* `active_payroll` (Integer - sum of roster cfo_valuations)

## 4. The C.F.O. Valuation Algorithm (V1.0 Logic)
The Python backend will calculate the `cfo_valuation` using this base formula:
Total Value = (Base Rate) * (Positional Multiplier) * (Experience Multiplier)

* **Base Rates:** 5-Star ($100k), 4-Star ($50k), 3-Star ($25k)
* **Positional Multipliers:** QB (2.5x), LT/EDGE (1.5x), WR/CB/DT (1.2x), Others (1.0x)
* **Experience Multipliers:** Portal Starter (3.0x), Active Starter (2.0x), High School (1.0x)

## 5. Coding Guidelines for Claude
* Always use TypeScript for Next.js components.
* Default to server components unless interactivity (useState, onClick) is required.
* Do not invent data; rely on the schema provided.
* Keep components modular (e.g., separate the `PlayerTable` from the `CapSpaceBar`).