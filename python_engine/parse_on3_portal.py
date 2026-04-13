"""
parse_on3_portal.py
-------------------
Parses raw On3 transfer portal text dump into a structured CSV.
Only includes COMMITTED transfers (skips "Entered" / uncommitted).

Usage:
    python parse_on3_portal.py

Input:  python_engine/data/on3_portal_raw.txt
Output: python_engine/data/on3_portal_2026.csv
"""

import csv
import re
import sys
import os

sys.stdout.reconfigure(encoding="utf-8")

RAW_FILE = os.path.join(os.path.dirname(__file__), "data", "on3_portal_raw.txt")
CSV_FILE = os.path.join(os.path.dirname(__file__), "data", "on3_portal_2026.csv")

# Map On3 avatar text to school names
AVATAR_MAP = {
    "alabama": "Alabama",
    "arizona": "Arizona",
    "arizona state": "Arizona State",
    "arkansas": "Arkansas",
    "arkansas state": "Arkansas State",
    "auburn": "Auburn",
    "baylor": "Baylor",
    "boise state": "Boise State",
    "boston college": "Boston College",
    "bowling green": "Bowling Green",
    "brigham young": "BYU",
    "byu": "BYU",
    "cal": "Cal",
    "california": "Cal",
    "central florida": "UCF",
    "charlotte": "Charlotte",
    "cincinnati": "Cincinnati",
    "clemson": "Clemson",
    "coastal carolina": "Coastal Carolina",
    "colorado": "Colorado",
    "duke": "Duke",
    "east carolina": "East Carolina",
    "fiu": "FIU",
    "florida": "Florida",
    "florida atlantic": "Florida Atlantic",
    "florida international": "FIU",
    "florida state": "Florida State",
    "fresno state": "Fresno State",
    "georgia": "Georgia",
    "georgia tech": "Georgia Tech",
    "hawaii": "Hawai'i",
    "houston": "Houston",
    "illinois": "Illinois",
    "indiana": "Indiana",
    "iowa": "Iowa",
    "iowa state": "Iowa State",
    "jacksonville state": "Jacksonville State",
    "james madison": "James Madison",
    "kansas": "Kansas",
    "kansas state": "Kansas State",
    "kent state": "Kent State",
    "kentucky": "Kentucky",
    "liberty": "Liberty",
    "louisiana": "Louisiana",
    "louisville": "Louisville",
    "lsu": "LSU",
    "marshall": "Marshall",
    "maryland": "Maryland",
    "memphis": "Memphis",
    "miami": "Miami",
    "michigan": "Michigan",
    "michigan state": "Michigan State",
    "middle tennessee": "Middle Tennessee",
    "minnesota": "Minnesota",
    "mississippi state": "Mississippi State",
    "missouri": "Missouri",
    "nc state": "NC State",
    "nebraska": "Nebraska",
    "nevada": "Nevada",
    "new mexico": "New Mexico",
    "new mexico state": "New Mexico State",
    "north carolina": "North Carolina",
    "north texas": "North Texas",
    "northwestern": "Northwestern",
    "notre dame": "Notre Dame",
    "ohio": "Ohio",
    "ohio state": "Ohio State",
    "oklahoma": "Oklahoma",
    "oklahoma state": "Oklahoma State",
    "old dominion": "Old Dominion",
    "ole miss": "Ole Miss",
    "oregon": "Oregon",
    "oregon state": "Oregon State",
    "penn state": "Penn State",
    "pittsburgh": "Pittsburgh",
    "purdue": "Purdue",
    "rice": "Rice",
    "rutgers": "Rutgers",
    "sam houston": "Sam Houston",
    "san diego state": "San Diego State",
    "san jose state": "San Jose State",
    "smu": "SMU",
    "south carolina": "South Carolina",
    "south florida": "South Florida",
    "stanford": "Stanford",
    "syracuse": "Syracuse",
    "tcu": "TCU",
    "temple": "Temple",
    "tennessee": "Tennessee",
    "texas": "Texas",
    "texas a&m": "Texas A&M",
    "texas state": "Texas State",
    "texas tech": "Texas Tech",
    "toledo": "Toledo",
    "troy": "Troy",
    "tulane": "Tulane",
    "tulsa": "Tulsa",
    "uab": "UAB",
    "ucf": "UCF",
    "ucla": "UCLA",
    "uconn": "UConn",
    "unlv": "UNLV",
    "usc": "USC",
    "usf": "South Florida",
    "ut martin": "UT Martin",
    "utah": "Utah",
    "utah state": "Utah State",
    "utep": "UTEP",
    "utsa": "UTSA",
    "vanderbilt": "Vanderbilt",
    "virginia": "Virginia",
    "virginia tech": "Virginia Tech",
    "wake forest": "Wake Forest",
    "washington": "Washington",
    "washington state": "Washington State",
    "west virginia": "West Virginia",
    "western kentucky": "Western Kentucky",
    "western michigan": "Western Michigan",
    "wisconsin": "Wisconsin",
    "wyoming": "Wyoming",
    # Destination avatar variations (with mascot already stripped or partial)
    "vanderbilt commodores": "Vanderbilt",
    "california golden bears": "Cal",
    "usf bulls": "South Florida",
    "hawaii rainbow warriors": "Hawai'i",
    "tulane green wave": "Tulane",
    "san diego state aztecs": "San Diego State",
    "new mexico lobos": "New Mexico",
    "appalachian state mountaineers": "Appalachian State",
    "connecticut huskies": "UConn",
    "east carolina pirates": "East Carolina",
    "georgia southern eagles": "Georgia Southern",
    "georgia state panthers": "Georgia State",
    "bowling green falcons": "Bowling Green",
    "ball state cardinals": "Ball State",
    "central michigan chippewas": "Central Michigan",
    "colorado state rams": "Colorado State",
    "eastern michigan eagles": "Eastern Michigan",
    "eastern kentucky colonels": "Eastern Kentucky",
    "louisiana tech bulldogs": "Louisiana Tech",
    "louisiana monroe warhawks": "Louisiana Monroe",
    "massachusetts minutemen": "Massachusetts",
    "miami (oh) redhawks": "Miami (OH)",
    "middle tennessee state blue raiders": "Middle Tennessee",
    "south alabama jaguars": "South Alabama",
    "southern miss golden eagles": "Southern Miss",
    "fiu golden panthers": "FIU",
    "kennesaw state owls": "Kennesaw State",
    "north dakota state bison": "North Dakota State",
    "sam houston state bearkats": "Sam Houston",
    "sacramento state hornets": "Sacramento State",
    "montana grizzlies": "Montana",
    "stephen f. austin lumberjacks": "Stephen F. Austin",
    "grambling state tigers": "Grambling State",
    "abilene christian wildcats": "Abilene Christian",
    "alabama a&m bulldogs": "Alabama A&M",
    "central arkansas bears": "Central Arkansas",
    "delaware state hornets": "Delaware State",
    "east tennessee state buccaneers": "East Tennessee State",
    "north carolina central eagles": "North Carolina Central",
    "howard payne yellow jackets": "Howard Payne",
    "marist red foxes": "Marist",
    "unc pembroke braves": "UNC Pembroke",
    "weber state wildcats": "Weber State",
    "uc davis aggies": "UC Davis",
}


def extract_school_from_avatar(line: str) -> str | None:
    """Extract school name from 'School Avatar' or 'School Mascot Avatar' text."""
    line = line.strip()
    if not line.endswith("Avatar"):
        return None
    # Remove " Avatar" suffix
    text = line[:-7].strip()
    # Try matching with common mascot names removed
    mascots = [
        "Wildcats", "Tigers", "Crimson Tide", "Razorbacks", "Bulldogs",
        "Bears", "Eagles", "Golden Bears", "Bearcats", "Buffaloes",
        "Blue Devils", "Gators", "Seminoles", "Yellow Jackets",
        "Cougars", "Fighting Illini", "Hoosiers", "Hawkeyes", "Cyclones",
        "Jayhawks", "Mountaineers", "Cardinals", "Terrapins",
        "Wolverines", "Spartans", "Golden Gophers", "Cornhuskers",
        "Buckeyes", "Ducks", "Nittany Lions", "Boilermakers",
        "Scarlet Knights", "Mustangs", "Gamecocks", "Cardinal",
        "Orange", "Cavaliers", "Hokies", "Demon Deacons",
        "Huskies", "Badgers", "Fighting Irish", "Cowboys",
        "Longhorns", "Aggies", "Red Raiders", "Horned Frogs",
        "Knights", "Utes", "Hurricanes", "Tar Heels", "Wolfpack",
        "Panthers", "Volunteers", "Sooners", "Rebels",
        "Bruins", "Trojans", "Beavers", "Sun Devils",
        "Golden Flashes", "Thundering Herd", "Roadrunners",
        "Bobcats", "Rams", "Miners", "Owls", "Mean Green",
        "Rockets", "Broncos", "Wave", "Green Wave", "Golden Hurricane",
        "Blazers", "Monarchs", "Chanticleers", "Dukes", "Flames",
        "Cajuns", "Penguins", "49ers", "Hilltoppers", "Jaguars",
        "Skyhawks", "Peacocks", "Hawks", "Gaels", "Red Wolves",
        "Paladins", "Catamounts", "Bison", "Leathernecks",
        "Pilots", "Toreros",
    ]
    school = text
    for mascot in mascots:
        if school.endswith(" " + mascot):
            school = school[: -(len(mascot) + 1)].strip()
            break

    # Normalize and look up
    key = school.lower().strip()
    if key in AVATAR_MAP:
        return AVATAR_MAP[key]

    # Try the full text (without Avatar)
    key2 = text.lower().strip()
    if key2 in AVATAR_MAP:
        return AVATAR_MAP[key2]

    return text  # Return raw text if no mapping found


def parse_nil_value(val: str) -> str:
    """Parse On3 NIL value string like '$4M', '$750K', '$2.9M' to a dollar string."""
    val = val.strip()
    if val == "-" or not val:
        return ""
    val = val.replace("$", "").replace(",", "")
    if val.upper().endswith("M"):
        return str(int(float(val[:-1]) * 1_000_000))
    if val.upper().endswith("K"):
        return str(int(float(val[:-1]) * 1_000))
    try:
        return str(int(float(val)))
    except ValueError:
        return ""


VALID_POSITIONS = {
    "QB", "RB", "WR", "TE", "OT", "OL", "OG", "C", "IOL",
    "EDGE", "DL", "DT", "DE", "LB", "CB", "S", "DB",
    "K", "P", "PK", "LS", "ATH", "FB", "APB", "SLOT",
}


def parse_raw_portal(filepath: str) -> list[dict]:
    """Parse On3 raw text dump into structured records."""
    with open(filepath, "r", encoding="utf-8") as f:
        lines = [line.rstrip("\n") for line in f.readlines()]

    # Skip header lines (Rank, Player, Pos, Rating, NIL Value, Status, Last Team, New Team)
    # Find where actual data starts (first line that's just a number = rank)
    start = 0
    for i, line in enumerate(lines):
        if line.strip().isdigit() and i >= 8:
            start = i
            break

    records = []
    i = start
    while i < len(lines):
        line = lines[i].strip()

        # Look for rank line (standalone integer)
        if not line.isdigit():
            i += 1
            continue

        rank = int(line)
        i += 1

        # Next line: secondary number (On3 internal ranking)
        if i < len(lines) and lines[i].strip().isdigit():
            i += 1  # skip secondary rank

        # "Default Avatar" line
        if i < len(lines) and lines[i].strip() == "Default Avatar":
            i += 1

        # Position
        position = ""
        if i < len(lines):
            pos_candidate = lines[i].strip().upper()
            if pos_candidate in VALID_POSITIONS:
                position = pos_candidate
                i += 1

        # Player name
        name = ""
        if i < len(lines):
            name = lines[i].strip()
            i += 1

        # Optional "Claim Profile"
        if i < len(lines) and lines[i].strip() == "Claim Profile":
            i += 1

        # Class (FR, SO, JR, SR, RS-FR, RS-SO, etc.)
        if i < len(lines) and re.match(r"^(RS-)?(FR|SO|JR|SR|GR)", lines[i].strip(), re.IGNORECASE):
            i += 1  # skip class

        # Height (e.g., "6-2", "6-5.5")
        if i < len(lines) and re.match(r"^\d+-\d", lines[i].strip()):
            i += 1

        # Weight (e.g., "195")
        if i < len(lines) and re.match(r"^\d{2,3}$", lines[i].strip()):
            i += 1

        # High school name
        if i < len(lines) and not lines[i].strip().startswith("("):
            i += 1

        # (City, State)
        if i < len(lines) and lines[i].strip().startswith("("):
            i += 1

        # Rating(s) - one or two decimal numbers
        while i < len(lines) and re.match(r"^\d+\.\d+$", lines[i].strip()):
            i += 1

        # NIL Value (e.g., "$4M", "-")
        nil_value = ""
        if i < len(lines):
            val = lines[i].strip()
            if val.startswith("$") or val == "-":
                nil_value = parse_nil_value(val)
                i += 1

        # Status: "Committed" or "Entered"
        status = ""
        if i < len(lines):
            status_line = lines[i].strip()
            if status_line in ("Committed", "Entered"):
                status = status_line
                i += 1

        # If "Entered", skip date line and continue
        if status == "Entered":
            # May have a date line like "1/16/2026"
            if i < len(lines) and re.match(r"^\d{1,2}/\d{2}/\d{4}$", lines[i].strip()):
                i += 1
            # Skip blank lines
            while i < len(lines) and lines[i].strip() == "":
                i += 1
            continue  # Skip uncommitted players

        # Origin school avatar
        origin = ""
        if i < len(lines) and "Avatar" in lines[i]:
            origin = extract_school_from_avatar(lines[i].strip())
            i += 1

        # Destination school avatar
        destination = ""
        if i < len(lines) and "Avatar" in lines[i]:
            destination = extract_school_from_avatar(lines[i].strip())
            i += 1

        if name and status == "Committed":
            records.append({
                "Rank": rank,
                "Player": name,
                "Position": position,
                "Origin": origin or "",
                "Destination": destination or "",
                "On3 Valuation": nil_value,
            })

    return records


def main():
    print("Parsing On3 transfer portal raw data...")
    records = parse_raw_portal(RAW_FILE)
    print(f"  Parsed {len(records)} committed transfers")

    # Write CSV
    with open(CSV_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["Rank", "Player", "Position", "Origin", "Destination", "On3 Valuation"])
        writer.writeheader()
        writer.writerows(records)

    print(f"  Written to {CSV_FILE}")

    # Quick stats
    with_val = sum(1 for r in records if r["On3 Valuation"])
    print(f"  With NIL valuation: {with_val}")
    print(f"  Without NIL valuation: {len(records) - with_val}")

    # Show first 10
    print("\n  Top 10:")
    for r in records[:10]:
        val = f"${int(r['On3 Valuation']):,}" if r["On3 Valuation"] else "-"
        print(f"    {r['Rank']:4d}  {r['Player']:30s} {r['Position']:5s} {r['Origin']:20s} -> {r['Destination']:20s} {val}")

    # Check for unmapped schools
    unmapped_origins = set()
    unmapped_dests = set()
    for r in records:
        if r["Origin"] and r["Origin"] not in AVATAR_MAP.values() and r["Origin"] not in [
            v for v in AVATAR_MAP.values()
        ]:
            unmapped_origins.add(r["Origin"])
        if r["Destination"] and r["Destination"] not in AVATAR_MAP.values():
            unmapped_dests.add(r["Destination"])

    if unmapped_origins or unmapped_dests:
        print(f"\n  Unmapped origins ({len(unmapped_origins)}):")
        for s in sorted(unmapped_origins):
            print(f"    {s}")
        print(f"  Unmapped destinations ({len(unmapped_dests)}):")
        for s in sorted(unmapped_dests):
            print(f"    {s}")


if __name__ == "__main__":
    main()
