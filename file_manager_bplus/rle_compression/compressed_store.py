"""
Compressed File Store — Module 4 of RLE Compression
====================================================
Manages compressed file entries independent of the B+ Tree.
The B+ Tree holds file *metadata*; this store holds the actual
compressed *content* keyed by filename.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, TYPE_CHECKING

import pandas as pd

if TYPE_CHECKING:
    from rle_compression.rle_codec import RLEPair, RLEResult


@dataclass
class CompressedEntry:
    """One compressed file record."""
    original_filename: str
    compressed_filename: str          # original + ".rle"
    original_content: str             # simulated content before compression
    encoded_content: str              # RLE-encoded string
    pairs: List["RLEPair"]            # structured pairs
    stats: "RLEResult"                # full compression result
    compressed_at: datetime
    content_type: str                 # "bitmap" | "log" | "text" | "binary" etc.


class CompressedStore:
    """
    Manages compressed versions of files.
    Separate from the B+ Tree — the tree holds metadata,
    this store holds the compressed content blobs.
    """

    def __init__(self) -> None:
        self.entries: Dict[str, CompressedEntry] = {}  # filename → entry

    # ── CRUD ─────────────────────────────────────────────────────────────────

    def store(self, entry: CompressedEntry) -> None:
        """Add or overwrite a compressed entry."""
        self.entries[entry.original_filename] = entry

    def get(self, filename: str) -> Optional[CompressedEntry]:
        """Retrieve a compressed entry by original filename."""
        return self.entries.get(filename)

    def remove(self, filename: str) -> bool:
        """Remove a compressed entry. Returns True if it existed."""
        if filename in self.entries:
            del self.entries[filename]
            return True
        return False

    def all_entries(self) -> List[CompressedEntry]:
        """Return all entries, sorted by filename."""
        return sorted(self.entries.values(), key=lambda e: e.original_filename)

    def is_compressed(self, filename: str) -> bool:
        """Return True if a compressed version of this file exists."""
        return filename in self.entries

    # ── Aggregates ────────────────────────────────────────────────────────────

    def get_total_saved_bytes(self) -> int:
        """
        Total bytes saved (or lost) across all compressed files.
        Negative means RLE expanded more than it saved on average.
        """
        return sum(
            e.stats.original_bytes - e.stats.encoded_bytes
            for e in self.entries.values()
        )

    def get_total_original_bytes(self) -> int:
        """Sum of original sizes of all compressed files."""
        return sum(e.stats.original_bytes for e in self.entries.values())

    def get_best_compressed(self) -> Optional[CompressedEntry]:
        """Return the entry with the highest compression ratio."""
        if not self.entries:
            return None
        return max(self.entries.values(), key=lambda e: e.stats.ratio)

    def get_worst_compressed(self) -> Optional[CompressedEntry]:
        """Return the entry with the lowest compression ratio (worst = most expanded)."""
        if not self.entries:
            return None
        return min(self.entries.values(), key=lambda e: e.stats.ratio)

    # ── Summary DataFrame ──────────────────────────────────────────────────────

    def get_summary_df(self) -> pd.DataFrame:
        """
        Return a DataFrame for the compression dashboard.
        Columns: File | Type | Original | Encoded | Ratio | Saved% | Suitable?
        """
        rows = []
        for e in self.all_entries():
            rows.append({
                'File':         e.original_filename,
                'Type':         e.content_type,
                'Original (B)': e.stats.original_bytes,
                'Encoded (B)':  e.stats.encoded_bytes,
                'Ratio':        e.stats.ratio,
                'Saved%':       e.stats.space_saved_pct,
                'Suitable?':    e.stats.is_beneficial,
            })
        return pd.DataFrame(rows)
