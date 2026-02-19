#!/usr/bin/env python3
"""Query helper for data/logs/logs.db

Provides a few example queries and an export option.
"""
import argparse
import csv
import sqlite3
import sys
from typing import List, Tuple

DB = "data/db/logs.db"

PRETTY_COLS = [
    "id",
    "category",
    "type",
    "user_id",
    "moderator_id",
    "channel_id",
    "message",
    "extra",
    "timestamp",
]


def run_query(query: str, params: Tuple = ()) -> List[Tuple]:
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    cur.execute(query, params)
    rows = cur.fetchall()
    cols = [c[0] for c in cur.description] if cur.description else []
    conn.close()
    return cols, rows


def print_table(cols: List[str], rows: List[Tuple], limit: int = 0) -> None:
    if limit:
        rows = rows[:limit]
    if not rows:
        print("(no rows)")
        return
    widths = [max(len(str(r[i])) for r in rows + [cols]) for i in range(len(cols))]
    fmt = " | ".join(f"{{:{w}}}" for w in widths)
    print(fmt.format(*cols))
    print("-" * (sum(widths) + 3 * (len(cols) - 1)))
    for r in rows:
        print(fmt.format(*[str(x)[:200] for x in r]))


def export_csv(cols: List[str], rows: List[Tuple], path: str) -> None:
    with open(path, "w", newline='', encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(cols)
        for r in rows:
            writer.writerow(r)
    print(f"Exported {len(rows)} rows to {path}")


def cmd_recent(args):
    q = "SELECT * FROM logs ORDER BY id DESC LIMIT ?"
    cols, rows = run_query(q, (args.limit,))
    print_table(cols, rows)


def cmd_by_category(args):
    q = "SELECT * FROM logs WHERE category = ? ORDER BY id DESC LIMIT ?"
    cols, rows = run_query(q, (args.category, args.limit))
    print_table(cols, rows)


def cmd_by_user(args):
    q = "SELECT * FROM logs WHERE user_id = ? ORDER BY id DESC LIMIT ?"
    cols, rows = run_query(q, (args.user_id, args.limit))
    print_table(cols, rows)


def cmd_count_by_type(args):
    q = "SELECT type, COUNT(*) as cnt FROM logs GROUP BY type ORDER BY cnt DESC"
    cols, rows = run_query(q)
    print_table(cols, rows)


def cmd_search_message(args):
    q = "SELECT * FROM logs WHERE message LIKE ? ORDER BY id DESC LIMIT ?"
    pattern = f"%{args.term}%"
    cols, rows = run_query(q, (pattern, args.limit))
    print_table(cols, rows)


def cmd_raw(args):
    cols, rows = run_query(args.query, tuple(args.params or []))
    if args.export:
        export_csv(cols, rows, args.export)
    else:
        print_table(cols, rows)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Query logs.db with example queries")
    sub = parser.add_subparsers(dest="cmd")

    p = sub.add_parser("recent", help="Show recent log entries")
    p.add_argument("-n", "--limit", type=int, default=20)
    p.set_defaults(func=cmd_recent)

    p = sub.add_parser("by-category", help="Filter by category")
    p.add_argument("category", help="Category name (chat, server, mod, member, voice)")
    p.add_argument("-n", "--limit", type=int, default=50)
    p.set_defaults(func=cmd_by_category)

    p = sub.add_parser("by-user", help="Filter by user id")
    p.add_argument("user_id", type=int)
    p.add_argument("-n", "--limit", type=int, default=50)
    p.set_defaults(func=cmd_by_user)

    p = sub.add_parser("count-by-type", help="Count events grouped by type")
    p.set_defaults(func=cmd_count_by_type)

    p = sub.add_parser("search", help="Search message contents")
    p.add_argument("term", help="Search term")
    p.add_argument("-n", "--limit", type=int, default=50)
    p.set_defaults(func=cmd_search_message)

    p = sub.add_parser("raw", help="Run a raw SQL query")
    p.add_argument("query", help="SQL query")
    p.add_argument("params", nargs="*", help="Optional parameters")
    p.add_argument("--export", help="CSV path to export results")
    p.set_defaults(func=cmd_raw)

    args = parser.parse_args(argv)
    if not hasattr(args, "func"):
        parser.print_help()
        return 1
    args.func(args)
    return 0


if __name__ == "__main__":
    sys.exit(main())
