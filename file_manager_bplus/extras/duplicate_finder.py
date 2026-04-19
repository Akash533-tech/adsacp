"""
Duplicate File Detector (Module 5C)
=====================================
Finds groups of potentially-duplicate files using:
  1. Exact size match (same size_bytes)
  2. Same extension + similar size
  3. Similar filename (Levenshtein edit distance ≤ 2)

The Levenshtein implementation uses a classic O(m×n) DP table.
"""

from __future__ import annotations

import html as _html_mod
from dataclasses import dataclass, field
from typing import List, Dict, Tuple, TYPE_CHECKING

if TYPE_CHECKING:
    from bplus.bplus_tree import BPlusTree


@dataclass
class DuplicateGroup:
    files: List[str]               # filenames in this group
    reason: str                    # "same_size" | "similar_name" | "same_ext_size"
    size_bytes: int                # representative size
    recoverable_bytes: int         # size_bytes * (len - 1)


class DuplicateFinder:
    """
    Detects duplicate or near-duplicate files in a BPlusTree virtual filesystem.
    """

    def find_duplicates(self, tree: "BPlusTree") -> List[DuplicateGroup]:
        """
        Scan all files and group by:
          1. Exact same size_bytes → "same_size"
          2. Same extension + within 5% size → "same_ext_size"
          3. Filename Levenshtein distance ≤ 2 → "similar_name"
        """
        all_files = tree.get_all_sorted()
        groups: List[DuplicateGroup] = []

        # ── 1. Exact size duplicates ──────────────────────────────────────
        size_map: Dict[int, List[str]] = {}
        for meta in all_files:
            size_map.setdefault(meta.size_bytes, []).append(meta.filename)

        for size, names in size_map.items():
            if len(names) > 1:
                groups.append(DuplicateGroup(
                    files=names,
                    reason="same_size",
                    size_bytes=size,
                    recoverable_bytes=size * (len(names) - 1),
                ))

        # ── 2. Same extension + size within 5% ───────────────────────────
        checked_pairs = set()
        for i, ma in enumerate(all_files):
            for j in range(i + 1, len(all_files)):
                mb = all_files[j]
                pair = tuple(sorted([ma.filename, mb.filename]))
                if pair in checked_pairs:
                    continue
                if ma.extension and ma.extension == mb.extension:
                    larger = max(ma.size_bytes, mb.size_bytes)
                    smaller = min(ma.size_bytes, mb.size_bytes)
                    if larger > 0 and (larger - smaller) / larger < 0.05:
                        # Only add if not already in a same_size group
                        already = any(
                            set([ma.filename, mb.filename]) <= set(g.files)
                            for g in groups if g.reason == "same_size"
                        )
                        if not already:
                            groups.append(DuplicateGroup(
                                files=[ma.filename, mb.filename],
                                reason="same_ext_size",
                                size_bytes=ma.size_bytes,
                                recoverable_bytes=min(ma.size_bytes, mb.size_bytes),
                            ))
                            checked_pairs.add(pair)

        # ── 3. Similar filename (edit distance ≤ 2) ───────────────────────
        for i, ma in enumerate(all_files):
            for j in range(i + 1, len(all_files)):
                mb = all_files[j]
                pair = tuple(sorted([ma.filename, mb.filename]))
                if pair in checked_pairs:
                    continue
                # Strip extension for comparison
                base_a = ma.filename.rsplit(".", 1)[0] if "." in ma.filename else ma.filename
                base_b = mb.filename.rsplit(".", 1)[0] if "." in mb.filename else mb.filename
                if self.levenshtein(base_a.lower(), base_b.lower()) <= 2:
                    groups.append(DuplicateGroup(
                        files=[ma.filename, mb.filename],
                        reason="similar_name",
                        size_bytes=ma.size_bytes,
                        recoverable_bytes=min(ma.size_bytes, mb.size_bytes),
                    ))
                    checked_pairs.add(pair)

        return groups

    # ── Levenshtein DP (from scratch) ────────────────────────────────────────

    def levenshtein(self, s1: str, s2: str) -> int:
        """
        Classic O(m×n) dynamic programming Levenshtein distance.
        dp[i][j] = min edit distance between s1[:i] and s2[:j].
        Operations: insert, delete, substitute (each cost 1).
        """
        m, n = len(s1), len(s2)
        # dp is (m+1) × (n+1)
        dp = [[0] * (n + 1) for _ in range(m + 1)]

        # Base cases: transform empty string
        for i in range(m + 1):
            dp[i][0] = i      # i deletions
        for j in range(n + 1):
            dp[0][j] = j      # j insertions

        for i in range(1, m + 1):
            for j in range(1, n + 1):
                if s1[i - 1] == s2[j - 1]:
                    dp[i][j] = dp[i - 1][j - 1]          # no cost
                else:
                    dp[i][j] = 1 + min(
                        dp[i - 1][j],      # delete from s1
                        dp[i][j - 1],      # insert into s1
                        dp[i - 1][j - 1],  # substitute
                    )

        return dp[m][n]

    def get_dp_table(self, s1: str, s2: str) -> List[List[int]]:
        """Return the full (m+1)×(n+1) DP table for visualisation."""
        m, n = len(s1), len(s2)
        dp = [[0] * (n + 1) for _ in range(m + 1)]
        for i in range(m + 1):
            dp[i][0] = i
        for j in range(n + 1):
            dp[0][j] = j
        for i in range(1, m + 1):
            for j in range(1, n + 1):
                if s1[i - 1] == s2[j - 1]:
                    dp[i][j] = dp[i - 1][j - 1]
                else:
                    dp[i][j] = 1 + min(dp[i-1][j], dp[i][j-1], dp[i-1][j-1])
        return dp

    def render_dp_table(self, s1: str, s2: str) -> str:
        """
        Return HTML table showing the full DP matrix.
        Diagonal cells (the optimal path) are highlighted in gold.
        The final cell dp[m][n] is highlighted in green.
        """
        s1 = s1[:20]   # cap for readability
        s2 = s2[:20]
        dp = self.get_dp_table(s1, s2)
        m, n = len(s1), len(s2)

        # Find the shortest path via traceback (greedy diagonal preference)
        path: set = set()
        i, j = m, n
        path.add((i, j))
        while i > 0 or j > 0:
            if i == 0:
                j -= 1
            elif j == 0:
                i -= 1
            else:
                candidates = [(dp[i-1][j-1], i-1, j-1),
                              (dp[i-1][j],   i-1, j),
                              (dp[i][j-1],   i,   j-1)]
                candidates.sort()
                _, ni, nj = candidates[0]
                i, j = ni, nj
            path.add((i, j))

        # Header row
        header_cells = '<th style="padding:6px;background:#1a1f2e;color:#4a90d9;border:1px solid #2a3550;min-width:32px"></th>'
        header_cells += '<th style="padding:6px;background:#1a1f2e;color:#4a90d9;border:1px solid #2a3550">ε</th>'
        for ch in s2:
            header_cells += f'<th style="padding:6px;background:#1a1f2e;color:#f59e0b;border:1px solid #2a3550">{_esc(ch)}</th>'

        rows_html = f"<tr>{header_cells}</tr>"

        for i in range(m + 1):
            row_label = "ε" if i == 0 else _esc(s1[i - 1])
            row_html = f'<td style="padding:6px;background:#1a1f2e;color:#ef4444;border:1px solid #2a3550;font-weight:bold">{row_label}</td>'
            for j in range(n + 1):
                val = dp[i][j]
                is_final = (i == m and j == n)
                in_path  = (i, j) in path
                if is_final:
                    bg = "#153d15"; color = "#22c55e"; fw = "bold"
                elif in_path:
                    bg = "#2d2a00"; color = "#f5c518"; fw = "bold"
                else:
                    bg = "#0f1117"; color = "#e8f0fe"; fw = "normal"
                row_html += (
                    f'<td style="padding:6px;background:{bg};color:{color};'
                    f'border:1px solid #2a3550;text-align:center;font-weight:{fw}">'
                    f'{val}</td>'
                )
            rows_html += f"<tr>{row_html}</tr>"

        return f"""
<div style="overflow-x:auto;">
<p style="color:#7a9bc4;font-size:12px;">
  Levenshtein DP table: <b style="color:#ef4444">"{_esc(s1)}"</b> vs 
  <b style="color:#f59e0b">"{_esc(s2)}"</b> — 
  edit distance = <b style="color:#22c55e">{dp[m][n]}</b>
  &nbsp;|&nbsp; <span style="color:#f5c518">■</span> = optimal path
</p>
<table style="border-collapse:collapse;font-family:monospace;font-size:12px;">
  {rows_html}
</table>
</div>
"""

    def get_space_recoverable(self, groups: List[DuplicateGroup]) -> int:
        """Total bytes recoverable by deleting all-but-first in each group."""
        return sum(g.recoverable_bytes for g in groups)


def _esc(s: str) -> str:
    return _html_mod.escape(str(s), quote=False)
