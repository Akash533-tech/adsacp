"""
RLE Visualization Helpers — Module 3 of RLE Compression
=========================================================
All visualization uses only inline CSS — no external stylesheets,
no class names, no <style> blocks. Safe for Streamlit markdown rendering.
"""

from __future__ import annotations

import html as _html_mod
import math
from typing import List, TYPE_CHECKING

import pandas as pd

if TYPE_CHECKING:
    from rle_compression.rle_codec import RLEStep, RLEResult, RLECodec


def _e(s: str) -> str:
    """HTML escape helper."""
    return _html_mod.escape(str(s), quote=False)


class RLEVisualizer:
    """All RLE visualization methods return HTML strings or DataFrames."""

    # ── Encoding animation ────────────────────────────────────────────────────

    def render_encode_animation_html(
        self,
        text: str,
        steps: List["RLEStep"],
        current_step: int,
    ) -> str:
        """
        Returns HTML showing encoding progress at a given step.

        Layout:
          Input chars: colored spans (gray=done, green=current run, muted=future)
          Below: position indices
          Output: emitted pair pills (blue=done, amber=building)
          Run counter badge
        """
        if not steps or current_step >= len(steps):
            return '<div style="color:#6b7280;font-size:12px">No steps to display.</div>'

        step = steps[current_step]
        current_pos = step.position
        current_run_start = current_pos - (step.run_count - 1)
        current_run_end = current_pos     # inclusive

        # ── Character spans ───────────────────────────────────────────────────
        char_spans = []
        for i, ch in enumerate(text):
            display_ch = _e(ch) if ch != '\n' else '↵'
            if i < current_run_start:
                # Already fully processed
                style = (
                    'display:inline-block;width:22px;text-align:center;padding:3px 0;'
                    'background:#1a2535;color:#4a5568;font-family:monospace;'
                    'font-size:12px;border-radius:3px;margin:1px;border:1px solid #2a3550;'
                )
            elif current_run_start <= i <= current_run_end:
                # Current active run — highlight green
                style = (
                    'display:inline-block;width:22px;text-align:center;padding:3px 0;'
                    'background:#14532d;color:#4ade80;font-family:monospace;'
                    'font-size:13px;font-weight:bold;border-radius:3px;margin:1px;'
                    'border:2px solid #22c55e;'
                )
            else:
                # Not yet reached — muted
                style = (
                    'display:inline-block;width:22px;text-align:center;padding:3px 0;'
                    'background:#0f1117;color:#374151;font-family:monospace;'
                    'font-size:12px;border-radius:3px;margin:1px;border:1px solid #1a1f2e;'
                )
            char_spans.append(f'<span style="{style}">{display_ch}</span>')

        # ── Index row ─────────────────────────────────────────────────────────
        index_spans = []
        for i in range(len(text)):
            col = '#22c55e' if current_run_start <= i <= current_run_end else '#374151'
            index_spans.append(
                f'<span style="display:inline-block;width:24px;text-align:center;'
                f'font-size:9px;color:{col};font-family:monospace;">{i}</span>'
            )

        # ── Emitted pair pills ────────────────────────────────────────────────
        pair_pills = []
        # Collect all pairs emitted so far by scanning previous steps
        emitted_pairs = []
        seen_offsets = set()
        for s in steps[:current_step + 1]:
            if s.run_ended and s.pair_emitted:
                key = (s.position, s.current_char, s.run_count)
                if key not in seen_offsets:
                    emitted_pairs.append(s.pair_emitted)
                    seen_offsets.add(key)

        for pair_str in emitted_pairs:
            pill_style = (
                'display:inline-block;background:#1d3a5e;color:#60a5fa;'
                'border:1px solid #3b82f6;border-radius:12px;padding:3px 10px;'
                'font-family:monospace;font-size:12px;font-weight:600;margin:2px;'
            )
            pair_pills.append(f'<span style="{pill_style}">{_e(pair_str)}</span>')

        # Current building pair (not yet emitted)
        if not step.run_ended:
            building = f'{step.run_count}{"…" if step.run_count > 1 else ""}{_e(step.current_char)}'
            amber_style = (
                'display:inline-block;background:#451a03;color:#fbbf24;'
                'border:1px solid #f59e0b;border-radius:12px;padding:3px 10px;'
                'font-family:monospace;font-size:12px;font-weight:600;margin:2px;'
                'animation:none;'
            )
            pair_pills.append(f'<span style="{amber_style}">{building}</span>')

        pills_html = ''.join(pair_pills) if pair_pills else (
            '<span style="color:#4a5568;font-size:12px">— not yet emitted —</span>'
        )

        # ── Run counter badge ─────────────────────────────────────────────────
        badge_color = '#22c55e' if not step.run_ended else '#3b82f6'
        status_text = (
            f'Building run: {step.run_count}× &apos;{_e(step.current_char)}&apos;'
            if not step.run_ended
            else f'Emitted: &apos;{_e(step.pair_emitted)}&apos;'
        )
        badge_html = (
            f'<span style="background:{badge_color}20;color:{badge_color};'
            f'border:1px solid {badge_color};border-radius:6px;padding:4px 12px;'
            f'font-family:monospace;font-size:13px;font-weight:600;">'
            f'{status_text}</span>'
        )

        # ── Assemble ──────────────────────────────────────────────────────────
        chars_html = ''.join(char_spans)
        indices_html = ''.join(index_spans)

        return f"""
<div style="background:#0f1117;border:1px solid #2a3550;border-radius:8px;padding:16px;">
  <div style="font-size:11px;color:#4a90d9;margin-bottom:6px;font-weight:600;
              text-transform:uppercase;letter-spacing:0.05em;">Input String</div>
  <div style="line-height:2;margin-bottom:2px;flex-wrap:wrap;display:flex;">{chars_html}</div>
  <div style="margin-bottom:12px;">{indices_html}</div>
  <div style="margin-bottom:10px;">{badge_html}</div>
  <div style="font-size:11px;color:#4a90d9;margin-bottom:6px;font-weight:600;
              text-transform:uppercase;letter-spacing:0.05em;">Output So Far</div>
  <div style="flex-wrap:wrap;display:flex;gap:2px;">{pills_html}</div>
  <div style="margin-top:10px;font-family:monospace;font-size:11px;color:#4a5568;">
    Bytes in: {step.bytes_in} &nbsp;|&nbsp; Bytes out: {step.bytes_out}
    &nbsp;|&nbsp; Step {step.step_num + 1} of {len(steps)}
  </div>
</div>
"""

    # ── Comparison bar ────────────────────────────────────────────────────────

    def render_comparison_bar(self, result: "RLEResult") -> str:
        """
        Side-by-side byte comparison bar.
        Green portion = saved. Red = expansion if RLE made it worse.
        """
        orig = result.original_bytes
        enc = result.encoded_bytes

        if orig == 0:
            return '<div style="color:#6b7280">Empty — nothing to display.</div>'

        # Original bar: always full width
        orig_label = f'{orig} bytes (original)'

        if enc <= orig:
            # Compression case — green
            enc_pct = (enc / orig) * 100
            saved_pct = 100 - enc_pct
            enc_blocks = max(1, int(enc_pct / 2))
            saved_blocks = 50 - enc_blocks
            bar_color = '#22c55e'
            label_color = '#22c55e'
            suffix = f'({result.space_saved_pct:.1f}% saved, {result.ratio:.2f}× ratio)'
            enc_label = f'{enc} bytes encoded  {suffix}'
            enc_bar = (
                f'<span style="color:#22c55e">{"█" * enc_blocks}</span>'
                f'<span style="color:#14532d">{"░" * saved_blocks}</span>'
            )
        else:
            # Expansion case — red
            enc_pct = (orig / enc) * 100   # inverse: what fraction of encoded is original
            orig_blocks = max(1, int(enc_pct / 2))
            extra_blocks = 50 - orig_blocks
            bar_color = '#ef4444'
            label_color = '#ef4444'
            expansion_pct = abs(result.space_saved_pct)
            suffix = f'({expansion_pct:.1f}% LARGER — RLE expanded this file!)'
            enc_label = f'{enc} bytes  {suffix}'
            enc_bar = (
                f'<span style="color:#22c55e">{"█" * orig_blocks}</span>'
                f'<span style="color:#ef4444">{"█" * extra_blocks}</span>'
            )

        orig_bar = '<span style="color:#4a90d9">' + '█' * 50 + '</span>'

        warning_html = ''
        if not result.is_beneficial:
            warning_html = (
                '<div style="background:#3d1515;border:1px solid #ef4444;border-radius:6px;'
                'padding:8px 14px;margin-top:8px;color:#ff8080;font-size:12px;">'
                '⚠️ <b>RLE expanded this file</b> — the data has too much variety for RLE to help. '
                'Use RLE only on repetitive data (bitmaps, DNA, log indentation).</div>'
            )

        return f"""
<div style="background:#0f1117;border:1px solid #2a3550;border-radius:8px;
            padding:14px 18px;font-family:monospace;">
  <div style="font-size:11px;color:#4a90d9;font-weight:600;margin-bottom:8px;
              text-transform:uppercase;letter-spacing:0.05em;">Byte Comparison</div>
  <div style="margin-bottom:6px;">
    <span style="color:#6b7280;font-size:11px;display:inline-block;width:90px;">Original</span>
    <span style="font-size:14px;">{orig_bar}</span>
    <span style="color:#4a90d9;font-size:12px;margin-left:8px;">{orig_label}</span>
  </div>
  <div>
    <span style="color:#6b7280;font-size:11px;display:inline-block;width:90px;">Encoded</span>
    <span style="font-size:14px;">{enc_bar}</span>
    <span style="color:{label_color};font-size:12px;margin-left:8px;">{enc_label}</span>
  </div>
  {warning_html}
</div>
"""

    # ── Run breakdown table ───────────────────────────────────────────────────

    def render_run_breakdown_table(self, result: "RLEResult") -> pd.DataFrame:
        """
        DataFrame with one row per run showing byte efficiency.

        Columns: Run # | Character | Run Length | Encoded As | Bytes In | Bytes Out | Efficient?
        """
        rows = []
        for i, pair in enumerate(result.pairs):
            b_in = pair.count        # bytes consumed from original
            b_out = pair.byte_cost() # bytes in encoded output
            if b_out < b_in:
                eff = '✓ YES'
            elif b_out == b_in:
                eff = '≈ neutral'
            else:
                eff = '✗ EXPANDED'

            rows.append({
                'Run #':       i + 1,
                'Character':   repr(pair.character),
                'Run Length':  pair.count,
                'Encoded As':  f'"{str(pair)}"',
                'Bytes In':    b_in,
                'Bytes Out':   b_out,
                'Efficient?':  eff,
            })
        return pd.DataFrame(rows)

    # ── Pixel art compression ─────────────────────────────────────────────────

    def render_pixel_art_compression(
        self,
        rows: List[str],
        codec: "RLECodec",
    ) -> str:
        """
        For bitmap content: render each row as colored pixels + its RLE encoding.
        Highlights the row with the best compression in bright green.
        """
        # Colour map for pixel characters
        pixel_colors = {
            'W': '#ffffff', 'L': '#c0c0c0', 'G': '#808080',
            'D': '#404040', 'B': '#000000',
            '\n': None,
        }

        # Compute ratio for each row to find best
        row_results = []
        for row in rows:
            row_clean = row.replace('\n', '')
            if not row_clean:
                continue
            res = codec.encode(row_clean, track_steps=False)
            row_results.append((row_clean, res))

        if not row_results:
            return '<div style="color:#6b7280;font-size:12px">No rows to display.</div>'

        best_ratio = max(r.ratio for _, r in row_results)
        row_htmls = []

        for row_str, res in row_results:
            is_best = abs(res.ratio - best_ratio) < 0.01
            border_color = '#22c55e' if is_best else '#2a3550'
            bg_color = '#0d1f0d' if is_best else '#0f1117'

            # Pixel cells
            pixel_cells = []
            for ch in row_str[:40]:   # cap display at 40 pixels
                bg = pixel_colors.get(ch, '#444444')
                if bg is None:
                    continue
                pixel_cells.append(
                    f'<span style="display:inline-block;width:10px;height:14px;'
                    f'background:{bg};margin:0;border:1px solid #111;"></span>'
                )

            pixels_html = ''.join(pixel_cells)
            encoded_str = _e(res.encoded[:30]) + ('…' if len(res.encoded) > 30 else '')
            ratio_color = '#22c55e' if res.ratio >= 1.5 else '#f59e0b' if res.ratio >= 1.0 else '#ef4444'
            best_badge = ' 🏆 <b style="color:#22c55e">BEST</b>' if is_best else ''

            row_htmls.append(f"""
<div style="background:{bg_color};border:1px solid {border_color};border-radius:5px;
            padding:6px 10px;margin-bottom:4px;display:flex;align-items:center;gap:12px;">
  <div style="flex:0 0 auto;">{pixels_html}</div>
  <div style="font-family:monospace;font-size:11px;color:#6b7280;">→</div>
  <div style="font-family:monospace;font-size:12px;color:#60a5fa;flex:1;">{encoded_str}</div>
  <div style="font-family:monospace;font-size:12px;font-weight:700;color:{ratio_color};
              white-space:nowrap;">{res.ratio:.2f}×{best_badge}</div>
</div>
""")

        return f"""
<div style="background:#0a0d14;border:1px solid #2a3550;border-radius:8px;padding:12px;">
  <div style="font-size:11px;color:#4a90d9;font-weight:600;margin-bottom:8px;
              text-transform:uppercase;letter-spacing:0.05em;">
    Per-Row Pixel Compression
    <span style="color:#4a5568;font-weight:normal;margin-left:8px;">(W=white L=light G=gray D=dark B=black)</span>
  </div>
  {''.join(row_htmls)}
</div>
"""

    # ── Suitability gauge ──────────────────────────────────────────────────────

    def render_suitability_gauge(self, analysis: dict) -> str:
        """
        ASCII-art gauge showing RLE suitability score.
        Score = repetition_score * 100
        Color: red (0-30%), orange (30-60%), green (60-100%)
        """
        score_raw = analysis.get('repetition_score', 0.0)
        score_pct = min(100, max(0, score_raw * 100))
        recommendation = analysis.get('recommendation', 'Unknown')
        avg_run = analysis.get('avg_run_length', 0.0)
        max_run = analysis.get('max_run_length', 0)
        estimated_ratio = analysis.get('estimated_ratio', 0.0)

        if score_pct < 30:
            bar_color = '#ef4444'
            bg_color = '#3d1515'
            label_color = '#ff8080'
        elif score_pct < 60:
            bar_color = '#f59e0b'
            bg_color = '#451a03'
            label_color = '#fbbf24'
        else:
            bar_color = '#22c55e'
            bg_color = '#14532d'
            label_color = '#4ade80'

        total_blocks = 50
        filled = max(1, int(total_blocks * score_pct / 100))
        empty = total_blocks - filled

        filled_str = f'<span style="color:{bar_color}">{"█" * filled}</span>'
        empty_str = f'<span style="color:#2a3550">{"░" * empty}</span>'

        rec_emoji = {
            'Excellent': '🌟',
            'Good': '✅',
            'Poor': '⚠️',
            'Terrible': '❌',
        }.get(recommendation, '•')

        return f"""
<div style="background:#0f1117;border:1px solid #2a3550;border-radius:8px;
            padding:14px 18px;font-family:monospace;">
  <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:8px;">
    <span style="font-size:11px;color:#4a90d9;font-weight:600;text-transform:uppercase;
                 letter-spacing:0.05em;">RLE Suitability</span>
    <span style="background:{bg_color};color:{label_color};border:1px solid {bar_color};
                 border-radius:12px;padding:2px 12px;font-size:12px;font-weight:700;">
      {rec_emoji} {recommendation}
    </span>
  </div>
  <div style="font-size:15px;letter-spacing:0px;">[{filled_str}{empty_str}]
    <span style="color:{label_color};font-size:13px;margin-left:8px;font-weight:600;">
      {score_pct:.0f}%
    </span>
  </div>
  <div style="margin-top:8px;font-size:11px;color:#6b7280;display:flex;gap:20px;">
    <span>Avg run: <b style="color:#e8f0fe">{avg_run}×</b></span>
    <span>Longest run: <b style="color:#e8f0fe">{max_run}×</b></span>
    <span>Est. ratio: <b style="color:#e8f0fe">{estimated_ratio:.2f}×</b></span>
  </div>
</div>
"""

    # ── Before/after highlight ────────────────────────────────────────────────

    def render_before_after_highlight(self, original: str, encoded: str) -> str:
        """
        Side-by-side view showing how character groups in original
        map to RLE tokens in encoded output.

        Original characters grouped into run brackets with token below.
        """
        if not original or not encoded:
            return '<div style="color:#6b7280;font-size:12px">Nothing to display.</div>'

        # Parse the encoded string to get pairs
        pairs = []
        i = 0
        while i < len(encoded):
            count_str = ''
            while i < len(encoded) and encoded[i].isdigit():
                count_str += encoded[i]
                i += 1
            if i >= len(encoded):
                break
            ch = encoded[i]
            i += 1
            count = int(count_str) if count_str else 1
            pairs.append((count, ch))

        # Build top row (original chars grouped) and bottom row (tokens)
        group_htmls = []
        colors = ['#1d3a5e', '#14532d', '#2d1d5e', '#3d1d1d', '#1d3d2d', '#2a2000']
        max_display = 60   # cap for readability
        chars_used = 0

        for gi, (count, ch) in enumerate(pairs):
            if chars_used >= max_display:
                break
            display_count = min(count, max_display - chars_used)
            bg = colors[gi % len(colors)]
            border = '#4a90d9' if gi % 2 == 0 else '#22c55e'
            char_display = _e(ch) if ch != '\n' else '↵'
            token_str = f'{count}{ch}' if count > 1 else ch

            # Char cells
            cells = ''.join(
                f'<span style="display:inline-block;width:18px;text-align:center;'
                f'background:{bg};border-top:2px solid {border};'
                f'border-left:1px solid {border}20;'
                f'padding:4px 0;font-family:monospace;font-size:12px;color:#e8f0fe;">'
                f'{_e(char_display)}</span>'
                for _ in range(display_count)
            )

            # Token cell (spans all chars)
            token_width = display_count * 20
            token_html = (
                f'<div style="width:{token_width}px;text-align:center;'
                f'background:{bg};border-bottom:2px solid {border};'
                f'border-radius:0 0 4px 4px;padding:3px 2px;'
                f'font-family:monospace;font-size:11px;font-weight:700;color:{border};">'
                f'{_e(token_str)}</div>'
            )

            group_htmls.append(f"""
<div style="display:inline-block;vertical-align:top;margin:1px;">
  <div>{cells}</div>
  {token_html}
</div>
""")
            chars_used += display_count

        more_note = ''
        total_len = len(original)
        if total_len > max_display:
            more_note = (
                f'<span style="color:#4a5568;font-size:11px;margin-left:8px;">'
                f'... {total_len - max_display} more chars</span>'
            )

        return f"""
<div style="background:#0f1117;border:1px solid #2a3550;border-radius:8px;
            padding:12px 16px;overflow-x:auto;">
  <div style="font-size:11px;color:#4a90d9;font-weight:600;margin-bottom:8px;
              text-transform:uppercase;letter-spacing:0.05em;">
    Run Structure — original chars grouped by run, token below
  </div>
  <div style="white-space:nowrap;line-height:1;">
    {''.join(group_htmls)}{more_note}
  </div>
  <div style="margin-top:8px;font-size:11px;color:#4a5568;">
    Encoded: <code style="color:#60a5fa;">{_e(encoded[:80])}{"…" if len(encoded) > 80 else ""}</code>
  </div>
</div>
"""
