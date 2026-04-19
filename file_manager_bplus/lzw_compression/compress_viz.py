"""
Compression visualization helpers for the Streamlit UI.
All functions return HTML strings or DataFrames — no Streamlit calls here
(keeps this module testable and importable without a running app context).
"""

from __future__ import annotations

import html
import pandas as pd
from typing import List, TYPE_CHECKING

if TYPE_CHECKING:
    from lzw_compression.lzw import LZWStep, CompressionStats


# ─────────────────────────────────────────────────────────────────────────────
# Ratio bar
# ─────────────────────────────────────────────────────────────────────────────

def render_compression_ratio_bar(stats: "CompressionStats") -> str:
    """
    Return HTML for a visual compression bar:
      [████████░░░░░░░░░░░░] 42% compressed  (58% saved)
    Green = compressed portion, grey = saved space.
    """
    compressed_pct = max(0.0, min(100.0, 100.0 - stats.space_saved_pct))
    saved_pct = max(0.0, min(100.0, stats.space_saved_pct))

    bar_blocks = 40
    filled = int(bar_blocks * compressed_pct / 100)
    empty = bar_blocks - filled

    bar = "█" * filled + "░" * empty

    return f"""
<div style="font-family:monospace;background:#1a1f2e;padding:14px 18px;
            border-radius:8px;border:1px solid #2a3550;margin:10px 0;">
  <div style="color:#4a90d9;font-size:12px;margin-bottom:6px;">
    📦 Compression Ratio Bar
  </div>
  <div style="font-size:15px;letter-spacing:1px;">
    <span style="color:#22c55e">[{bar[:filled]}</span><span style="color:#4a4a5a">{bar[filled:]}]</span>
  </div>
  <div style="margin-top:8px;font-size:13px;">
    <span style="color:#22c55e;font-weight:600;">{compressed_pct:.1f}% retained</span>
    &nbsp;·&nbsp;
    <span style="color:#f59e0b;font-weight:600;">{saved_pct:.1f}% space saved</span>
    &nbsp;·&nbsp;
    <span style="color:#a0aec0;">{stats.original_bytes} B → {stats.compressed_bytes} B</span>
    &nbsp;·&nbsp;
    <span style="color:#7c3aed;">{stats.ratio:.2f}× ratio</span>
  </div>
</div>
"""


# ─────────────────────────────────────────────────────────────────────────────
# Step table DataFrame
# ─────────────────────────────────────────────────────────────────────────────

def render_step_table(steps: List["LZWStep"]) -> pd.DataFrame:
    """
    Return a DataFrame with columns:
      Step | Buffer | Char | Match | In Dict? | Code Emitted | New Entry | Dict Size
    """
    rows = []
    for s in steps:
        rows.append({
            "Step":         s.step_num,
            "Buffer":       repr(s.buffer),
            "Char":         repr(s.current_char) if s.current_char else "—",
            "Match":        repr(s.match),
            "In Dict?":     "✓ YES" if s.in_dict else "✗ NO",
            "Code Emitted": str(s.code_emitted) if s.code_emitted >= 0 else "—",
            "New Entry":    repr(s.new_entry) if s.new_entry else "—",
            "Dict Size":    len(s.dict_snapshot),
        })
    return pd.DataFrame(rows)
