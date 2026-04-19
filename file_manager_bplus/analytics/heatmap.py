"""
Disk Usage Analytics — Heatmap / Treemap (Module 4)
====================================================
Builds Plotly-compatible treemap data and various breakdowns
from the live B+ Tree without touching the real filesystem.
"""

from __future__ import annotations

from collections import defaultdict
from typing import List, Dict, TYPE_CHECKING

import pandas as pd

if TYPE_CHECKING:
    from bplus.bplus_tree import BPlusTree
    from file_ops.metadata import FileMetadata


class DiskAnalyzer:
    """Analyse virtual filesystem statistics from a BPlusTree."""

    # ── Treemap ───────────────────────────────────────────────────────────────

    def build_treemap_data(self, tree: "BPlusTree") -> dict:
        """
        Build Plotly treemap dict.
        Hierarchy: root → extension → filename
        Rectangle size = size_bytes.
        """
        all_files = tree.get_all_sorted()

        labels: List[str] = ["bplus-fs"]
        parents: List[str] = [""]
        values: List[int] = [0]   # root value is sum of children, Plotly sums it

        # Gather per-extension data
        ext_files: Dict[str, List["FileMetadata"]] = defaultdict(list)
        for meta in all_files:
            ext = meta.extension.lower() if meta.extension else "(none)"
            ext_files[ext].append(meta)

        for ext, files in sorted(ext_files.items()):
            ext_label = ext if ext else "(no ext)"
            labels.append(ext_label)
            parents.append("bplus-fs")
            values.append(sum(f.size_bytes for f in files))

            for meta in files:
                # Ensure unique label in Plotly
                file_label = f"{meta.filename}"
                labels.append(file_label)
                parents.append(ext_label)
                values.append(max(meta.size_bytes, 1))   # Plotly needs > 0

        return {"labels": labels, "parents": parents, "values": values}

    # ── Extension breakdown ───────────────────────────────────────────────────

    def get_extension_breakdown(self, tree: "BPlusTree") -> pd.DataFrame:
        """
        DataFrame: extension | count | total_bytes | avg_bytes | pct_of_total
        """
        all_files = tree.get_all_sorted()
        if not all_files:
            return pd.DataFrame(columns=["extension", "count", "total_bytes", "avg_bytes", "pct_of_total"])

        grand_total = sum(f.size_bytes for f in all_files) or 1

        ext_map: Dict[str, list] = defaultdict(list)
        for meta in all_files:
            ext = meta.extension.lower() if meta.extension else "(none)"
            ext_map[ext].append(meta.size_bytes)

        rows = []
        for ext, sizes in sorted(ext_map.items()):
            total = sum(sizes)
            rows.append({
                "extension":    ext,
                "count":        len(sizes),
                "total_bytes":  total,
                "avg_bytes":    int(total / len(sizes)),
                "pct_of_total": round(total / grand_total * 100, 2),
            })

        df = pd.DataFrame(rows)
        return df.sort_values("total_bytes", ascending=False).reset_index(drop=True)

    # ── Top files ─────────────────────────────────────────────────────────────

    def get_largest_files(self, tree: "BPlusTree", n: int = 10) -> List["FileMetadata"]:
        """Return top-N files by size_bytes, descending."""
        all_files = tree.get_all_sorted()
        return sorted(all_files, key=lambda f: f.size_bytes, reverse=True)[:n]

    def get_recently_modified(self, tree: "BPlusTree", n: int = 10) -> List["FileMetadata"]:
        """Return top-N files by modified_at, most recent first."""
        from datetime import datetime
        all_files = tree.get_all_sorted()
        return sorted(
            all_files,
            key=lambda f: f.modified_at if f.modified_at else datetime.min,
            reverse=True,
        )[:n]

    # ── Directory sizes ───────────────────────────────────────────────────────

    def get_directory_sizes(self, tree: "BPlusTree") -> Dict[str, int]:
        """Aggregate total bytes per virtual directory path."""
        dir_sizes: Dict[str, int] = defaultdict(int)
        for meta in tree.get_all_sorted():
            # Extract directory from path
            if "/" in meta.path:
                d = meta.path.rsplit("/", 1)[0]
            else:
                d = "/"
            dir_sizes[d] += meta.size_bytes
        return dict(sorted(dir_sizes.items()))
