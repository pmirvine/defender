"""Persistent hall of fame (today's / all-time share one table here)."""
import json
from pathlib import Path

PATH = Path.home() / ".defender_scores.json"

# Defender's factory default table (initials, score).
DEFAULTS = [
    ("DRJ", 21270), ("SAM", 18315), ("LED", 15920), ("PGD", 13250),
    ("CRB", 11050), ("MRS", 8900), ("SSR", 7200), ("TMH", 5410),
]


def load(path=PATH):
    try:
        data = json.loads(Path(path).read_text())
        return [(str(i)[:3], int(s)) for i, s in data][:8]
    except (OSError, ValueError, TypeError):
        return list(DEFAULTS)


def save(table, path=PATH):
    try:
        Path(path).write_text(json.dumps(table))
    except OSError:
        pass


def qualifies(table, score):
    return score > 0 and (len(table) < 8 or score > table[-1][1])


def insert(table, initials, score):
    table = sorted(table + [(initials[:3].upper(), score)], key=lambda t: -t[1])[:8]
    return table
