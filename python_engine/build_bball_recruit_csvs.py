"""
Builds basketball_recruits_2026/2027/2028.csv from recruiting data.

High school recruits don't have ESPN athlete IDs until enrollment.
We use a deterministic placeholder ID format: hs{year}_{slug}
where slug is a normalized version of the player name.

Update the recruit lists below when new commits are announced
or rankings change, then re-run to regenerate the CSVs.

Usage:
    python build_bball_recruit_csvs.py
    python build_bball_recruit_csvs.py --year 2026
    python build_bball_recruit_csvs.py --dry-run
"""

import csv
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8")

POSITION_MAP = {
    "PG": "PG", "SG": "SG", "SF": "SF", "PF": "PF", "C": "C",
    "CG": "SG", "GF": "SF", "FC": "PF", "G": "SG", "F": "SF",
}


def composite_to_stars(composite: float) -> int:
    if composite >= 0.9900: return 5
    if composite >= 0.8900: return 4
    if composite >= 0.7900: return 3
    return 2


def make_espn_id(year: int, name: str) -> str:
    slug = re.sub(r"[^a-z0-9]", "_", name.lower().strip())
    slug = re.sub(r"_+", "_", slug).strip("_")
    return f"hs{year}_{slug}"


def normalize_position(pos: str) -> str:
    return POSITION_MAP.get(pos.upper(), "SF")


# ── 2026 RECRUITS ──────────────────────────────────────────────────────────────
RECRUITS_2026 = [
    ("Tyran Stokes",          "SF", 1.0000, "kansas"),
    ("Cameron Williams",      "PF", 0.9992, "duke"),
    ("Bruce Branch III",      "SF", 0.9974, "byu"),
    ("Caleb Gaskins",         "PF", 0.9953, "miami"),
    ("Brandon McCoy Jr.",     "SG", 0.9950, "michigan"),
    ("Taylen Kinney",         "PG", 0.9939, "kansas"),
    ("Colben Landrew",        "SF", 0.9913, "uconn"),
    ("Quinn Costello",        "PF", 0.9879, "michigan"),
    ("Tajh Ariza",            "SF", 0.9865, "oregon"),
    ("Lincoln Cosby",         "SF", 0.9860, "michigan"),
    ("Junior County",         "SG", 0.9836, "uconn"),
    ("Davion Adkins",         "C",  0.9798, "kansas"),
    ("Dean Rueckert",         "SF", 0.9772, "byu"),
    ("Joseph Hartman",        "SG", 0.9707, "michigan"),
    ("Trent Perry",           "SF", 0.9641, "kansas"),
    ("Mason Williams",        "PG", 0.9408, "kentucky"),
    ("Luke Barnett",          "SG", 0.9383, "kansas"),
]


# ── 2027 RECRUITS ──────────────────────────────────────────────────────────────
RECRUITS_2027 = [
    ("CJ Rosser",                 "PF", 0.9995, ""),
    ("Obinna Ekezie Jr.",         "C",  0.9988, ""),
    ("Ryan Hampton",              "SF", 0.9987, ""),
    ("Marcus Spears Jr.",         "PF", 0.9987, ""),
    ("Paul Osaruyi",              "C",  0.9979, ""),
    ("Moussa Kamissoko",          "SF", 0.9975, ""),
    ("Nasir Anderson",            "PG", 0.9970, ""),
    ("Beckham Black",             "PG", 0.9969, ""),
    ("Jordan Page",               "SG", 0.9969, ""),
    ("King Gibson",               "SG", 0.9961, ""),
    ("Dawson Battie",             "PF", 0.9954, ""),
    ("Malachi Jordan",            "SF", 0.9951, ""),
    ("Isaiah Hill",               "C",  0.9939, ""),
    ("Reese Alston",              "PG", 0.9938, ""),
    ("Demarcus Henry",            "SF", 0.9937, ""),
    ("Cayden Daughtry",           "PG", 0.9930, ""),
    ("Gabe Nesmith",              "SF", 0.9930, ""),
    ("Darius Wabbington",         "C",  0.9927, ""),
    ("Jalen Davis",               "SG", 0.9922, ""),
    ("Josh Leonard",              "SF", 0.9922, ""),
    ("Javon Bardwell",            "SF", 0.9915, "kansas"),
    ("Zion Green",                "PF", 0.9911, ""),
    ("NaVorro Bowman Jr.",        "SG", 0.9907, ""),
    ("Davion Thompson",           "PG", 0.9907, ""),
    ("Jeremy Jenkins",            "PF", 0.9905, ""),
    ("Dooney Johnson",            "SF", 0.9902, ""),
    ("Anderson Diaz",             "PG", 0.9889, ""),
    ("RJ Moore",                  "SG", 0.9888, ""),
    ("Ahmad Hudson",              "PF", 0.9888, ""),
    ("Devin Cleveland",           "PG", 0.9886, ""),
    ("Donovan Davis",             "PF", 0.9884, ""),
    ("Tyran Frazier",             "C",  0.9882, ""),
    ("LJ Smith",                  "SG", 0.9879, ""),
    ("Jason Gardner Jr.",         "SG", 0.9873, ""),
    ("Jarvis Hayes Jr.",          "SG", 0.9872, ""),
    ("Gene Roebuck",              "SF", 0.9865, ""),
    ("Munir Greig",               "SF", 0.9862, ""),
    ("Chase Branham",             "PG", 0.9862, ""),
    ("Scottie Adkinson",          "SG", 0.9860, ""),
    ("Jaylan Mitchell",           "PF", 0.9859, ""),
    ("Micah Gordon",              "PG", 0.9850, ""),
    ("Theo Edema",                "C",  0.9843, ""),
    ("Tyrone Jamison",            "PG", 0.9842, ""),
    ("Henry Robinson",            "SF", 0.9839, ""),
    ("Oneal Delancy",             "SG", 0.9839, ""),
    ("Cherif Millogo",            "C",  0.9837, ""),
    ("Ahmed Nur",                 "PF", 0.9837, ""),
    ("Howard Williams",           "SF", 0.9835, ""),
    ("Kevin Savage",              "PG", 0.9829, ""),
    ("Josiah Harrington",         "SF", 0.9829, ""),
    ("Jaxson Davis",              "PG", 0.9825, ""),
    ("Carson Crawford",           "SF", 0.9821, ""),
    ("Brandon Woodard",           "PF", 0.9817, ""),
    ("Antonio Pemberton",         "PG", 0.9807, ""),
    ("Dylan Jones",               "SF", 0.9800, ""),
    ("Chase Lumpkin",             "SG", 0.9797, ""),
    ("Mahamadou Diop",            "C",  0.9797, ""),
    ("Jomar Bernard",             "SF", 0.9796, ""),
    ("J'Lon Lyons",               "PG", 0.9795, ""),
    ("Patrick Otey",              "SG", 0.9794, ""),
    ("Baboucarr Ann",             "SF", 0.9782, ""),
    ("Jack Kohnen",               "SF", 0.9782, ""),
    ("Jahari Miller",             "SG", 0.9765, ""),
    ("Asa Montgomery",            "SF", 0.9756, ""),
    ("Mekhi Robertson",           "SG", 0.9743, ""),
    ("Aaron Britt Jr.",           "PG", 0.9735, ""),
    ("Nicolas Mitrovic",          "C",  0.9735, ""),
    ("Clyde Walters",             "SF", 0.9724, ""),
    ("Kamsi Awaka",               "C",  0.9722, ""),
    ("Darrell Davis",             "PG", 0.9721, ""),
    ("Jalen Brown",               "SG", 0.9721, ""),
    ("Chase Richardson",          "PG", 0.9721, ""),
    ("Jeremiah Profit",           "SF", 0.9705, ""),
    ("Caleb Ourigou",             "C",  0.9705, ""),
    ("Joshua Rivera",             "SG", 0.9704, ""),
    ("Cameron Barnes",            "PF", 0.9695, ""),
    ("Joshua Tyson",              "SG", 0.9689, ""),
    ("Payton Jones",              "PG", 0.9684, ""),
    ("Kager Knueppel",            "PF", 0.9680, ""),
    ("Keaundre Morris",           "PG", 0.9674, ""),
    ("Miguel Orbe",               "SG", 0.9673, ""),
    ("Derek Daniels",             "C",  0.9665, ""),
    ("Andrew Kretkowski",         "SF", 0.9662, ""),
    ("Lyris Robinson",            "SG", 0.9655, ""),
    ("Quincy Douby Jr.",          "SG", 0.9650, ""),
    ("Crew Fotheringham",         "SF", 0.9650, ""),
    ("Jalen White",               "SF", 0.9645, ""),
    ("Godson Okokoh",             "PF", 0.9644, ""),
    ("Tre Keith",                 "SG", 0.9642, ""),
    ("Isaiah Santos",             "SF", 0.9642, ""),
    ("Brian Mitchell Jr.",        "SF", 0.9640, ""),
    ("Chris Brown",               "C",  0.9639, ""),
    ("Ferlandes Wright",          "PF", 0.9636, "louisville"),
    ("Jaydn Jenkins",             "C",  0.9635, ""),
    ("Lewis Uvwo",                "C",  0.9627, ""),
    ("Marri Wesley",              "SF", 0.9619, ""),
    ("Justin Wise",               "SG", 0.9613, ""),
    ("Myles Fuentes",             "PG", 0.9610, ""),
    ("Thomas Vickery",            "SF", 0.9602, ""),
    ("Josiah Nance",              "SG", 0.9592, ""),
    ("Jacques Mitchell",          "SG", 0.9586, ""),
    ("Ty Schlagel",               "SF", 0.9586, ""),
    ("London Dada",               "SF", 0.9572, ""),
    ("Malcolm Price",             "SG", 0.9570, ""),
    ("Deuce McDuffie",            "SF", 0.9565, ""),
    ("Markus Kerr",               "SG", 0.9560, ""),
    ("Charles Pur",               "C",  0.9558, ""),
    ("Bryce Curry",               "SG", 0.9557, ""),
    ("Jacob Canton",              "PG", 0.9555, ""),
    ("Jacoby Briscoe",            "SF", 0.9555, ""),
    ("Kameron Cooper",            "SF", 0.9537, ""),
    ("Jordan Hunter",             "SG", 0.9534, ""),
    ("Marlon Martinez",           "SG", 0.9533, ""),
    ("Kellen Brewer",             "SG", 0.9526, ""),
    ("Frashad Tisby",             "SF", 0.9523, ""),
    ("Deshawn Dillon",            "SG", 0.9515, ""),
    ("Declan Griffiths",          "SF", 0.9511, ""),
    ("Mustafa Mohamed",           "PF", 0.9510, ""),
    ("Joaquim Boumtje Boumtje",   "C",  0.9500, ""),
    ("LJ Diamond",                "SG", 0.9495, ""),
    ("Lucai Anderson",            "SG", 0.9486, ""),
    ("Nick Welch Jr.",            "C",  0.9475, ""),
    ("Will Davis",                "SF", 0.9456, ""),
    ("Sekou Cisse",               "C",  0.9455, ""),
    ("David Conerly",             "SF", 0.9446, ""),
    ("Kamari Whyte",              "SG", 0.9442, ""),
    ("DJ Hawkins",                "SF", 0.9441, ""),
    ("Jimmie Haywood",            "SG", 0.9427, ""),
    ("Zaahir Muhammad-Gray",      "PF", 0.9414, ""),
    ("Griffin Starks",            "PF", 0.9412, ""),
    ("Josiah Adamson",            "SG", 0.9410, ""),
    ("Gassim Toure",              "PG", 0.9408, ""),
    ("Dylan Cowell",              "PF", 0.9402, ""),
    ("Eden Vinyard",              "PF", 0.9395, ""),
    ("Archie Weatherspoon",       "PG", 0.9391, ""),
    ("Luke Howery",               "SG", 0.9390, ""),
    ("Ty Cobb",                   "SG", 0.9382, ""),
    ("Templeton Fountaine V",     "SG", 0.9382, ""),
    ("Trevor Dickson",            "SG", 0.9373, ""),
    ("Steven McLeod",             "PF", 0.9373, ""),
    ("Andrew Ross",               "SG", 0.9365, ""),
    ("Zain Majeed",               "PF", 0.9357, ""),
    ("Braxton Keathley",          "PG", 0.9355, ""),
]


# ── 2028 RECRUITS ──────────────────────────────────────────────────────────────
RECRUITS_2028 = [
    ("AJ Williams",              "SF", 0.9999, ""),
    ("Bamba Touray",             "C",  0.9994, ""),
    ("Colton Hiller",            "SF", 0.9992, ""),
    ("Isaiah Hamilton",          "SF", 0.9986, ""),
    ("Erick Dampier Jr.",        "C",  0.9986, ""),
    ("Bentley Lusakueno",        "C",  0.9982, ""),
    ("Adan Diggs",               "SG", 0.9979, ""),
    ("Shalen Sheppard",          "PF", 0.9973, ""),
    ("Mason Collins",            "SF", 0.9973, ""),
    ("Dylan Betts",              "C",  0.9964, ""),
    ("Kameron Mercer",           "SG", 0.9961, ""),
    ("DJ Okoth",                 "SF", 0.9959, ""),
    ("Josh Lowery",              "SG", 0.9957, ""),
    ("Myles Hayes",              "SG", 0.9944, ""),
    ("Brady Pettigrew",          "SG", 0.9940, ""),
    ("Logan Chwastyk",           "C",  0.9935, ""),
    ("Michai White",             "PG", 0.9930, ""),
    ("Xavier Young",             "C",  0.9926, ""),
    ("Jakyi Miles",              "SG", 0.9924, ""),
    ("Joshua Lindsay",           "SG", 0.9923, ""),
    ("Quinton Wilson",           "SG", 0.9920, ""),
    ("Antoine Caughman Jr.",     "SF", 0.9917, ""),
    ("Malik Moore",              "PG", 0.9916, ""),
    ("Blaze Johnson",            "PG", 0.9916, ""),
    ("Kevin Wheatley Jr.",       "SG", 0.9915, ""),
    ("Isaiah Carter",            "SF", 0.9912, ""),
    ("Tai Bell",                 "PG", 0.9910, ""),
    ("Xavier Skipworth",         "SF", 0.9906, ""),
    ("Evan Willis",              "SF", 0.9896, ""),
    ("Liam Mitakaro",            "SG", 0.9888, ""),
    ("Josiah Rose",              "SG", 0.9880, ""),
    ("Will Brunson",             "SF", 0.9879, ""),
    ("Braxton Bogard",           "PF", 0.9877, ""),
    ("Boogie Cook",              "SF", 0.9875, ""),
    ("CJ Moore",                 "SF", 0.9873, ""),
    ("Nash Avery",               "PF", 0.9872, ""),
    ("Boss Mhoon",               "SF", 0.9872, ""),
    ("Rowan Phillips",           "SG", 0.9870, ""),
    ("Anthony Spratt Jr.",       "SF", 0.9868, ""),
    ("Devaughn Dorrough",        "SF", 0.9863, ""),
    ("Peter Julius",             "C",  0.9858, ""),
    ("Cole Kelly",               "SF", 0.9854, ""),
    ("Will Nelson",              "SF", 0.9853, ""),
    ("Emmanuel Nwabuoku",        "C",  0.9852, ""),
    ("Landon Lampley",           "SF", 0.9850, ""),
    ("Trey Edwards",             "SG", 0.9847, ""),
    ("Kelvin Anderson",          "SG", 0.9847, ""),
    ("Kmajay Jenkins",           "SF", 0.9843, ""),
    ("Isaac Smith",              "SF", 0.9828, ""),
    ("Brielen Craft",            "PG", 0.9827, ""),
    ("Darren Ford",              "SG", 0.9823, ""),
    ("Tyler Sutton",             "SG", 0.9818, ""),
    ("Noah Washington",          "SG", 0.9813, ""),
    ("Kaharri Coleman",          "PG", 0.9810, ""),
    ("Benjamin Berrouet",        "PF", 0.9807, ""),
    ("Jordan Mize",              "SG", 0.9807, ""),
    ("Rezon Harris Jr.",         "SF", 0.9803, ""),
    ("Mateen Cleaves Jr.",       "SG", 0.9799, ""),
    ("Stra Zelic",               "C",  0.9793, ""),
    ("Chase Smith",              "PF", 0.9791, ""),
    ("Nijaun Harris",            "SG", 0.9775, ""),
    ("Joshua Huggins",           "SF", 0.9771, ""),
    ("Kareem Smith-Bey",         "SG", 0.9771, ""),
    ("Keaton Murry",             "SG", 0.9763, ""),
    ("Billy Stanfield III",      "SF", 0.9755, ""),
    ("Derek Swartz",             "SG", 0.9751, ""),
    ("Keonte Smith",             "SF", 0.9744, ""),
    ("Jaden McCullough",         "PG", 0.9731, ""),
    ("Carter Smith",             "SG", 0.9727, ""),
    ("Aidan Carter",             "PG", 0.9723, ""),
    ("Trey McKinney",            "SF", 0.9443, ""),
    ("Xavier Hall",              "C",  0.9403, ""),
    ("Ian Archbold",             "SG", 0.9375, ""),
    ("Toussaint Malukila",       "C",  0.9358, ""),
]


def build_csv(year: int, recruits: list, dry_run: bool = False) -> int:
    rows = []
    for name, pos_247, composite, school_slug in recruits:
        espn_id = make_espn_id(year, name)
        position = normalize_position(pos_247)
        stars = composite_to_stars(composite)
        rows.append({
            "espn_athlete_id": espn_id,
            "player_name": name,
            "star_rating": stars,
            "composite_score": round(composite, 4),
            "position_247": position,
            "committed_school_slug": school_slug,
            "hs_grad_year": year,
        })

    if dry_run:
        print(f"\n  Class of {year}: {len(rows)} recruits")
        committed = [r for r in rows if r["committed_school_slug"]]
        print(f"  Committed to our schools: {len(committed)}")
        for r in committed:
            print(
                f"    {r['player_name']:30s} | {r['position_247']:4s} | "
                f"{r['star_rating']}* | {r['composite_score']} -> {r['committed_school_slug']}"
            )
        return len(rows)

    path = os.path.join(os.path.dirname(__file__), "data", f"basketball_recruits_{year}.csv")
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "espn_athlete_id", "player_name", "star_rating",
                "composite_score", "position_247",
                "committed_school_slug", "hs_grad_year",
            ],
        )
        writer.writeheader()
        writer.writerows(rows)

    print(f"  Wrote {len(rows)} recruits -> {path}")
    return len(rows)


def main(dry_run: bool = False, year: int | None = None) -> None:
    years = {2026: RECRUITS_2026, 2027: RECRUITS_2027, 2028: RECRUITS_2028}
    if year:
        years = {year: years[year]}

    print("Building basketball recruit CSVs...")
    total = 0
    for y, recruits in sorted(years.items()):
        total += build_csv(y, recruits, dry_run)

    print(f"\nTotal: {total} recruits across {len(years)} class years")
    if not dry_run:
        print("\nNext steps:")
        print("  python ingest_bball_recruits.py")
        print("  python calculate_bball_valuations.py")
        print("  python generate_bball_slugs.py")


if __name__ == "__main__":
    dry_run = "--dry-run" in sys.argv
    year_arg = None
    for i, arg in enumerate(sys.argv):
        if arg == "--year" and i + 1 < len(sys.argv):
            year_arg = int(sys.argv[i + 1])
    main(dry_run=dry_run, year=year_arg)
