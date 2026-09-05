#!/usr/bin/env python3
"""Merge a batch of researched rows into data/resources.csv.

Every addition passes through here rather than being pasted into the CSV, so
three things are true of every row in the directory:

  * it has every column the build expects, spelled the way the build spells it;
  * it is not a duplicate of something already there (matched on name and on
    website, because the same programme gets typed two ways);
  * it carries the date it was verified.

Usage:  python3 merge_rows.py /tmp/add_foo.json [...]
"""
import csv, json, re, sys
from pathlib import Path

CSV = Path(__file__).parent / "data" / "resources.csv"
COLS = ["Resource Name", "Category", "Subcategory", "Description", "Who Can Access",
        "Undocumented-Friendly", "Cost", "Access Type", "Boroughs Served", "Phone",
        "Website", "Address / Location", "Hours", "Languages",
        "Warm-Handoff Partner", "Tags", "Last Verified", "Notes"]


def norm(s):
    return re.sub(r"[^a-z0-9]", "", (s or "").lower())


def host(u):
    m = re.match(r"https?://(?:www\.)?([^/]+)", (u or "").strip())
    return m.group(1).lower() if m else ""


def load():
    with open(CSV, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def main(paths):
    rows = load()
    have_name = {norm(r["Resource Name"]) for r in rows}
    # A host alone is too coarse — nyc.gov hosts forty of these — so the guard
    # is the full path, which is what actually identifies a programme page.
    have_url = {(r["Website"] or "").rstrip("/").lower() for r in rows if r["Website"]}

    added, skipped = [], []
    for path in paths:
        for new in json.load(open(path)):
            missing = [c for c in COLS if c not in new]
            if missing:
                sys.exit(f"{path}: {new.get('Resource Name')!r} is missing {missing}")
            if not new.get("Last Verified"):
                sys.exit(f"{path}: {new['Resource Name']!r} has no Last Verified date")
            if not new.get("Phone") and not new.get("Website"):
                sys.exit(f"{path}: {new['Resource Name']!r} has no phone and no website, "
                         "so there is no way to act on it")
            key, url = norm(new["Resource Name"]), (new["Website"] or "").rstrip("/").lower()
            if key in have_name:
                skipped.append((new["Resource Name"], "same name")); continue
            if url and url in have_url:
                skipped.append((new["Resource Name"], "same website")); continue
            have_name.add(key)
            if url:
                have_url.add(url)
            rows.append({c: new.get(c, "") for c in COLS})
            added.append(new["Resource Name"])

    with open(CSV, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLS, quoting=csv.QUOTE_ALL)
        w.writeheader()
        for r in rows:
            w.writerow({c: r.get(c, "") for c in COLS})

    print(f"added {len(added)}, skipped {len(skipped)}, total {len(rows)}")
    for n, why in skipped:
        print(f"  skipped {n} ({why})")


if __name__ == "__main__":
    main(sys.argv[1:] or sys.exit(__doc__))
