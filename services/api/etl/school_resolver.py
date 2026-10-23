from __future__ import annotations

import csv
import re
from collections import Counter
from pathlib import Path

from rapidfuzz import fuzz, process
from supabase import AsyncClient

from .common import fetch_all

_PARENS = re.compile(r"\(.*?\)")
_NON_ALNUM = re.compile(r"[^a-z0-9& ]+")
_SPACES = re.compile(r"\s+")
_NOISE_SUFFIXES = (" ed", " ed2", " ea", " rea", " rd", " scs", " coe", " cas", " lsa", " engineering", " honors")

# Too ambiguous to resolve without context; better to drop than to mislabel an outcome.
AMBIGUOUS = {"uw", "miami", "uc", "washington", "columbia college", "wash", "st johns"}


def normalize(name: str) -> str:
    s = _PARENS.sub(" ", name.lower())
    s = _NON_ALNUM.sub(" ", s)
    s = _SPACES.sub(" ", s).strip()
    s = s.removeprefix("the ")
    for suffix in _NOISE_SUFFIXES:          # "cmu scs" → "cmu", "umich lsa" → "umich"
        if s.endswith(suffix) and len(s) > len(suffix) + 1:
            s = s[: -len(suffix)].strip()
    return s


class SchoolResolver:
    def __init__(self, aliases: dict[str, str]):
        self.aliases = aliases
        self.choices = list(aliases)
        self.unresolved: Counter[str] = Counter()

    @classmethod
    async def load(cls, sb: AsyncClient) -> SchoolResolver:
        rows = await fetch_all(sb, "school_aliases", "alias,slug")
        return cls({r["alias"]: r["slug"] for r in rows})

    def resolve(self, raw: str) -> str | None:
        n = normalize(raw)
        if not n or n in AMBIGUOUS:
            self.unresolved[n] += 1
            return None
        if n in self.aliases:
            return self.aliases[n]
        match = process.extractOne(n, self.choices, scorer=fuzz.WRatio, score_cutoff=92)
        if match:
            return self.aliases[match[0]]
        self.unresolved[n] += 1
        return None

    def dump_unresolved(self, path: Path, top: int = 300) -> None:
        """Triage list: add the frequent ones to data/school_aliases.yaml and re-run load."""
        with path.open("w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["normalized_name", "count"])
            w.writerows(self.unresolved.most_common(top))
