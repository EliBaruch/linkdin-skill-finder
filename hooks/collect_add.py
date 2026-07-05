"""Append collected skill entries to the personal catalog.

Reads a JSON array of entry objects from stdin, dedupes against the existing
catalog (by post_url), writes new ones, and prints how many were added.

Usage:
    python collect_add.py < entries.json
"""
import sys
import os
import json

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import catalog_lib  # noqa: E402


def main():
    raw = sys.stdin.read()
    try:
        entries = json.loads(raw) if raw.strip() else []
    except ValueError as e:
        print(f"error: input was not valid JSON ({e})")
        return 1
    if not isinstance(entries, list):
        print("error: expected a JSON array of entry objects")
        return 1
    added = catalog_lib.add_entries(entries)
    print(f"added {added} new skill(s); catalog now has "
          f"{len(catalog_lib.load_catalog())} total")
    return 0


if __name__ == "__main__":
    sys.exit(main())
