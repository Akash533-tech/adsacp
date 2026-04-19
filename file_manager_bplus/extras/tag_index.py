"""
Smart Tag Index (Module 5D)
============================
Maintains an inverted index: tag → set of filenames.
Supports AND / OR / NOT boolean query syntax.
"""

from __future__ import annotations

import re
from typing import Dict, List, Set, TYPE_CHECKING

if TYPE_CHECKING:
    pass


class TagIndex:
    """
    Inverted tag index for boolean full-text search over file tags.

    Syntax supported:
      'python AND source'    → files that have BOTH tags
      'web OR frontend'      → files that have EITHER tag
      'python NOT test'      → files with 'python' that do NOT have 'test'
      'python'               → simple single-tag search
    """

    def __init__(self) -> None:
        self.index: Dict[str, Set[str]] = {}   # tag → set(filenames)

    # ── Maintenance ──────────────────────────────────────────────────────────

    def add_file(self, filename: str, tags: List[str]) -> None:
        for tag in tags:
            t = tag.lower().strip()
            if t:
                self.index.setdefault(t, set()).add(filename)

    def remove_file(self, filename: str) -> None:
        for tag, filenames in self.index.items():
            filenames.discard(filename)

    def rebuild_from_tree(self, tree) -> None:
        """Rebuild the entire index from a BPlusTree (called on load/reset)."""
        self.index.clear()
        for meta in tree.get_all_sorted():
            self.add_file(meta.filename, meta.tags)

    # ── Query ────────────────────────────────────────────────────────────────

    def search_tags(self, query: str) -> List[str]:
        """
        Evaluate a boolean tag query.
        Supports AND, OR, NOT (case-insensitive operators).
        Returns sorted list of matching filenames.
        """
        query = query.strip()
        if not query:
            return []

        # Detect operator
        if " AND " in query.upper():
            parts = re.split(r"\s+AND\s+", query, flags=re.IGNORECASE)
            result: Set[str] = self._lookup(parts[0].strip())
            for part in parts[1:]:
                result &= self._lookup(part.strip())
            return sorted(result)

        if " OR " in query.upper():
            parts = re.split(r"\s+OR\s+", query, flags=re.IGNORECASE)
            result = set()
            for part in parts:
                result |= self._lookup(part.strip())
            return sorted(result)

        if " NOT " in query.upper():
            parts = re.split(r"\s+NOT\s+", query, flags=re.IGNORECASE)
            include = self._lookup(parts[0].strip())
            exclude: Set[str] = set()
            for part in parts[1:]:
                exclude |= self._lookup(part.strip())
            return sorted(include - exclude)

        # Simple single tag
        return sorted(self._lookup(query))

    def get_all_tags(self) -> List[str]:
        """Return all known tags, sorted alphabetically."""
        return sorted(self.index.keys())

    def get_tag_counts(self) -> Dict[str, int]:
        """Return {tag: number_of_files} sorted by count descending."""
        counts = {tag: len(files) for tag, files in self.index.items() if files}
        return dict(sorted(counts.items(), key=lambda x: -x[1]))

    # ── Internal ─────────────────────────────────────────────────────────────

    def _lookup(self, tag: str) -> Set[str]:
        return set(self.index.get(tag.lower(), set()))
