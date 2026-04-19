"""
RLE Animator — Module 5 of RLE Compression
===========================================
Renders each animation frame as a self-contained HTML string for
st.empty().markdown(). All HTML uses inline CSS only — no <style>
blocks, no class names, Streamlit-safe.

Architecture:
  - render_frame()        → encode phase frame (pure function)
  - render_decode_frame() → decode phase frame (pure function)
  - render_final_summary()→ completion metrics panel (pure function)

All three are PURE FUNCTIONS: same inputs → same HTML string, no side
effects, no session state touched. The caller (app.py) owns state.

Animation is driven by:
  SYSTEM A: time.sleep() loop in app.py → calls render_frame() each iteration
  SYSTEM B: slider in app.py            → replays steps 0..idx, calls render_frame()
"""

from __future__ import annotations

import html as _html_lib
from typing import List, Optional, Tuple

from rle_compression.rle_codec import RLECodec, RLEStep, RLEResult, RLEPair


# ─── COLOR CONSTANTS ─────────────────────────────────────────────────────────
# All inline — no CSS classes, Streamlit-safe

CLR_DONE_BG     = "#1a2e1a"    # processed char background
CLR_DONE_BD     = "#4caf50"    # processed char border
CLR_DONE_FG     = "#a8d5a2"    # processed char text

CLR_ACTIVE_BG   = "#2d2a00"    # current char (head of active run) background
CLR_ACTIVE_BD   = "#f5c518"    # current char border (gold)
CLR_ACTIVE_FG   = "#f5c518"    # current char text

CLR_RUN_BG      = "#0f1f3d"    # same-run char (tail) background
CLR_RUN_BD      = "#4a90d9"    # same-run char border (blue)
CLR_RUN_FG      = "#b8d4f5"    # same-run char text

CLR_FUTURE_BG   = "transparent"
CLR_FUTURE_BD   = "#2a2a3a"
CLR_FUTURE_FG   = "#444466"

# Pair badge colors by efficiency
CLR_PAIR_WIN    = ("#1a2e1a", "#4caf50", "#a8d5a2")    # count>=3: green
CLR_PAIR_EVEN   = ("#2d2a00", "#f59e0b", "#fcd34d")    # count==2: yellow
CLR_PAIR_LOSS   = ("#2d0a0a", "#ef4444", "#fca5a5")    # count==1: red

CLR_BUILDING    = ("#2d2a00", "#f5c518", "#f5c518")    # currently building

CLR_BAR_ORIG    = "#4a90d9"
CLR_BAR_GOOD    = "#4caf50"
CLR_BAR_BAD     = "#ef4444"
CLR_BAR_BG      = "#1a1f2e"
CLR_BAR_TRACK   = "#0f1117"


def _e(s: str) -> str:
    """HTML-escape a string."""
    return _html_lib.escape(str(s), quote=False)


def _pair_colors(count: int) -> Tuple[str, str, str]:
    """Return (bg, border, fg) for a pair badge based on efficiency."""
    if count >= 3:
        return CLR_PAIR_WIN
    elif count == 2:
        return CLR_PAIR_EVEN
    else:
        return CLR_PAIR_LOSS


def _count_encoded_bytes(pairs: List[RLEPair]) -> int:
    """Tally encoded byte cost of a list of pairs."""
    return sum(1 if p.count == 1 else len(str(p.count)) + 1 for p in pairs)


# ─── ANIMATOR CLASS ───────────────────────────────────────────────────────────

class RLEAnimator:
    """
    Renders RLE animation frames as HTML strings for st.markdown().

    All render_*() methods are PURE FUNCTIONS — no side effects,
    no session state, no st.* calls. Inputs fully determine output.
    """

    def __init__(self, codec: RLECodec):
        self.codec = codec

    # ── SECTION BUILDERS (private helpers) ────────────────────────────────────

    def _section_char_row(
        self,
        text: str,
        current_run_start: int,
        current_run_len: int,
    ) -> str:
        """
        Build the character row section.

        States:
          i < current_run_start          → done (green)
          i == current_run_start         → active/head (gold, scaled up)
          run_start < i < run_end        → in-run tail (blue)
          i >= current_run_start + run_len → future (muted/dimmed)
        """
        current_run_end = current_run_start + current_run_len  # exclusive

        parts = [
            '<div style="display:flex;gap:3px;flex-wrap:wrap;'
            'align-items:flex-end;margin-bottom:6px;min-height:60px;">'
        ]

        for i, ch in enumerate(text):
            display_ch = _e(ch) if ch not in ('\n', '\r') else '↵'

            if i < current_run_start:
                # Already fully processed
                bg, bd, fg = CLR_DONE_BG, CLR_DONE_BD, CLR_DONE_FG
                font_size   = "13px"
                font_weight = "500"
                extra_style = ""
                opacity     = "1"
            elif i == current_run_start:
                # Active head of current run — gold, slightly larger
                bg, bd, fg = CLR_ACTIVE_BG, CLR_ACTIVE_BD, CLR_ACTIVE_FG
                font_size   = "15px"
                font_weight = "700"
                extra_style = "box-shadow:0 0 6px #f5c51880;"
                opacity     = "1"
            elif current_run_start < i < current_run_end:
                # Tail of current run — blue
                bg, bd, fg = CLR_RUN_BG, CLR_RUN_BD, CLR_RUN_FG
                font_size   = "13px"
                font_weight = "600"
                extra_style = ""
                opacity     = "1"
            else:
                # Not yet reached — dimmed
                bg, bd, fg = CLR_FUTURE_BG, CLR_FUTURE_BD, CLR_FUTURE_FG
                font_size   = "12px"
                font_weight = "400"
                extra_style = ""
                opacity     = "0.3"

            box_style = (
                f"width:28px;height:28px;display:flex;align-items:center;"
                f"justify-content:center;font-size:{font_size};font-weight:{font_weight};"
                f"border-radius:4px;border:1px solid {bd};background:{bg};color:{fg};"
                f"{extra_style}"
            )
            idx_style = (
                "font-size:9px;color:#555;margin-top:2px;"
                "font-family:'Courier New',monospace;text-align:center;"
            )
            parts.append(
                f'<div style="display:flex;flex-direction:column;align-items:center;'
                f'gap:2px;opacity:{opacity};">'
                f'<div style="{box_style}">{display_ch}</div>'
                f'<div style="{idx_style}">{i}</div>'
                f'</div>'
            )

        parts.append('</div>')
        return ''.join(parts)

    def _section_run_badge(self, step: RLEStep, building_pair: Optional[Tuple[str, int]]) -> str:
        """Build the animated run-counter badge."""
        if step.phase == 'done':
            badge_text  = '✓ Encoding complete'
            badge_color = CLR_DONE_FG
            badge_bg    = CLR_DONE_BG
            badge_bd    = CLR_DONE_BD
        elif step.phase == 'emit':
            pair_str    = step.pair_emitted or f"{step.run_count}{step.current_char}"
            badge_text  = f"⚡ Emitted → '{_e(pair_str)}'"
            badge_color = CLR_ACTIVE_FG
            badge_bg    = CLR_ACTIVE_BG
            badge_bd    = CLR_ACTIVE_BD
        elif building_pair:
            ch, cnt     = building_pair
            badge_text  = f"Run: {cnt}× '{_e(ch)}'"
            badge_color = CLR_ACTIVE_FG
            badge_bg    = CLR_ACTIVE_BG
            badge_bd    = CLR_ACTIVE_BD
        else:
            badge_text  = 'Scanning...'
            badge_color = '#888888'
            badge_bg    = '#1a1f2e'
            badge_bd    = '#2a2a3a'

        return (
            f'<div style="display:inline-block;font-size:12px;padding:4px 14px;'
            f'border-radius:20px;border:1px solid {badge_bd};background:{badge_bg};'
            f'color:{badge_color};font-family:monospace;margin-bottom:8px;'
            f'font-weight:600;">'
            f'{badge_text}</div>'
        )

    def _section_output_pairs(
        self,
        emitted_pairs: List[RLEPair],
        building_pair: Optional[Tuple[str, int]],
    ) -> str:
        """Build the output pairs row."""
        parts = [
            '<div style="font-size:10px;color:#555;letter-spacing:.08em;'
            'text-transform:uppercase;margin-bottom:5px;font-family:monospace;">'
            'Output — RLE pairs</div>',
            '<div style="display:flex;gap:6px;flex-wrap:wrap;'
            'align-items:center;min-height:38px;margin-bottom:8px;">',
        ]

        if not emitted_pairs and building_pair is None:
            parts.append(
                '<span style="font-size:12px;color:#444;">pairs appear here...</span>'
            )
        else:
            for p in emitted_pairs:
                bg, bd, fg = _pair_colors(p.count)
                pair_str   = str(p.count) + p.character if p.count > 1 else p.character
                if p.count >= 3:
                    tooltip = f"Run of {p.count} — saved {p.count - p.byte_cost()} byte(s)"
                elif p.count == 2:
                    tooltip = f"Run of 2 — break-even (2B in, 2B out)"
                else:
                    tooltip = f"Run of 1 — no savings (1B in but still just 1B out, optimal single-char)"
                parts.append(
                    f'<span title="{tooltip}" style="font-size:13px;font-weight:600;'
                    f'padding:5px 11px;border-radius:6px;border:1px solid {bd};'
                    f'background:{bg};color:{fg};font-family:monospace;">'
                    f'{_e(pair_str)}</span>'
                )

            # Building pair preview (currently being counted, not yet emitted)
            if building_pair:
                ch, cnt    = building_pair
                bg, bd, fg = CLR_BUILDING
                preview    = f"{cnt}{_e(ch)}…" if cnt > 1 else f"{_e(ch)}…"
                parts.append(
                    f'<span style="font-size:13px;font-weight:600;'
                    f'padding:5px 11px;border-radius:6px;border:1px dashed {bd};'
                    f'background:{bg};color:{fg};font-family:monospace;opacity:0.8;">'
                    f'{preview}</span>'
                )

        parts.append('</div>')
        return ''.join(parts)

    def _section_byte_bars(self, text: str, emitted_pairs: List[RLEPair]) -> str:
        """Build the side-by-side original vs encoded byte comparison bars."""
        orig_bytes = len(text)
        enc_bytes  = _count_encoded_bytes(emitted_pairs)
        if orig_bytes == 0:
            return ''

        enc_pct    = min(100.0, enc_bytes / orig_bytes * 100)
        bar_color  = CLR_BAR_GOOD if enc_bytes <= orig_bytes else CLR_BAR_BAD

        # Ratio label
        if enc_bytes > 0 and emitted_pairs:
            ratio_val  = orig_bytes / enc_bytes
            ratio_str  = f"  ({ratio_val:.2f}×)" if ratio_val > 1 else f"  (+{enc_bytes - orig_bytes}B over)"
        else:
            ratio_str = ''

        orig_bar = (
            f'<div style="height:14px;border-radius:3px;background:{CLR_BAR_ORIG};width:100%;'
            f'display:flex;align-items:center;padding-left:6px;box-sizing:border-box;">'
            f'<span style="font-size:9px;color:#b8d4f5;font-family:monospace;">'
            f'original&nbsp;{orig_bytes}B</span></div>'
        )
        enc_inner_w = f"{enc_pct:.1f}%" if enc_pct >= 8 else "8px"
        enc_bar = (
            f'<div style="height:14px;border-radius:3px;background:{CLR_BAR_TRACK};'
            f'border:1px solid #2a2a3a;overflow:hidden;">'
            f'<div style="height:100%;width:{enc_inner_w};background:{bar_color};'
            f'display:flex;align-items:center;padding-left:6px;box-sizing:border-box;">'
            f'<span style="font-size:9px;color:#fff;font-family:monospace;white-space:nowrap;">'
            f'{"encoded&nbsp;" + str(enc_bytes) + "B" + ratio_str if enc_pct >= 18 else ""}'
            f'</span></div></div>'
        )

        label_color = CLR_BAR_GOOD if enc_bytes <= orig_bytes else CLR_BAR_BAD
        summary     = (
            f'<span style="font-size:10px;color:{label_color};'
            f'font-family:monospace;font-weight:600;">'
            f'encoded {enc_bytes}B / original {orig_bytes}B{ratio_str}</span>'
        )

        return (
            f'<div style="margin-bottom:8px;">'
            f'<div style="font-size:9px;color:#555;margin-bottom:2px;font-family:monospace;">'
            f'Byte comparison</div>'
            f'{orig_bar}'
            f'<div style="height:3px;"></div>'
            f'{enc_bar}'
            f'<div style="margin-top:3px;">{summary}</div>'
            f'</div>'
        )

    def _section_step_description(
        self,
        step: RLEStep,
        building_pair: Optional[Tuple[str, int]],
    ) -> str:
        """Build the step description line at the bottom."""
        ch = _e(step.current_char) if step.current_char else '?'

        if step.phase == 'done':
            desc  = "✓ All input consumed — encoding complete."
            color = CLR_DONE_FG
        elif step.phase == 'start':
            desc  = (
                f"Position {step.position}: found '{ch}' — starting new run. "
                f"Next: '{_e(step.next_char)}'"
                if step.next_char
                else f"Position {step.position}: found '{ch}' — last character."
            )
            color = CLR_ACTIVE_FG
        elif step.phase == 'extend':
            desc  = (
                f"Position {step.position}: '{ch}' again — "
                f"run extends to {step.run_count}. "
                f"Next: '{_e(step.next_char)}'"
                if step.next_char
                else f"Position {step.position}: '{ch}' ends the input — run = {step.run_count}."
            )
            color = CLR_RUN_FG
        elif step.phase == 'emit':
            pair_str = step.pair_emitted or f"{step.run_count}{step.current_char}"
            cost     = 1 if step.run_count == 1 else len(str(step.run_count)) + 1
            saved    = step.run_count - cost
            if saved > 0:
                verdict = f"saved {saved} byte{'s' if saved > 1 else ''} ✓"
                color   = CLR_DONE_FG
            elif saved == 0:
                verdict = "break-even — no savings"
                color   = "#fcd34d"
            else:
                verdict = f"overhead: run-of-1 costs same as original"
                color   = "#fca5a5"
            desc = (
                f"Run of {step.run_count}× '{ch}' complete — "
                f"emit '{_e(pair_str)}' ({cost}B) — {verdict}"
            )
        else:
            desc  = ""
            color = "#888"

        return (
            f'<div style="font-size:11px;color:{color};font-family:monospace;'
            f'min-height:18px;margin-top:2px;">{desc}</div>'
        )

    # ── MAIN FRAME RENDERER ───────────────────────────────────────────────────

    def render_frame(
        self,
        text: str,
        step: RLEStep,
        emitted_pairs: List[RLEPair],
        building_pair: Optional[Tuple[str, int]],
        current_run_start: int,
        current_run_len: int,
        show_ratio_bar: bool = True,
    ) -> str:
        """
        Build one complete animation frame as an HTML string.

        PURE FUNCTION — same arguments always produce the same HTML string.

        Sections (top to bottom):
          1. Character row with per-char state coloring
          2. Run-counter badge
          3. Output pairs row (emitted + building preview)
          4. Byte comparison bars (if show_ratio_bar)
          5. Step description text
        """
        sections = [
            self._section_char_row(text, current_run_start, current_run_len),
            self._section_run_badge(step, building_pair),
            self._section_output_pairs(emitted_pairs, building_pair),
        ]
        if show_ratio_bar:
            sections.append(self._section_byte_bars(text, emitted_pairs))
        sections.append(self._section_step_description(step, building_pair))

        return (
            '<div style="background:#0f1117;border:1px solid #2a3550;'
            'border-radius:10px;padding:16px 20px;font-family:monospace;">'
            + ''.join(sections) +
            '</div>'
        )

    # ── DECODE FRAME RENDERER ─────────────────────────────────────────────────

    def render_decode_frame(
        self,
        pairs: List[RLEPair],
        current_pair_idx: int,
        chars_revealed: int,
        total_chars: int,
    ) -> str:
        """
        Render the decode-phase animation frame.

        PURE FUNCTION.

        Sections:
          1. Pairs row (highlight which pair is currently being decoded)
          2. "Expanding X" label for current pair
          3. Reconstructed character boxes
          4. Completion message when done
        """
        # Rebuild all chars from pairs (needed for the output row)
        all_chars: List[str] = []
        for p in pairs:
            all_chars.extend([p.character] * p.count)

        parts: List[str] = [
            '<div style="margin-top:16px;border-top:1px solid #2a3550;'
            'padding-top:14px;background:#0f1117;border-radius:0 0 10px 10px;'
            'padding:14px 20px;border:1px solid #2a3550;border-top:none;">'
        ]

        # SECTION: Pairs row
        parts.append(
            '<div style="font-size:10px;color:#555;letter-spacing:.08em;'
            'text-transform:uppercase;margin-bottom:6px;font-family:monospace;">'
            'Decode — reading pairs</div>'
        )
        parts.append('<div style="display:flex;gap:6px;flex-wrap:wrap;margin-bottom:10px;">')
        for i, p in enumerate(pairs):
            pair_str = str(p.count) + p.character if p.count > 1 else p.character
            if i < current_pair_idx:
                bg, bd, fg = CLR_DONE_BG, CLR_DONE_BD, CLR_DONE_FG
            elif i == current_pair_idx:
                bg, bd, fg = CLR_ACTIVE_BG, CLR_ACTIVE_BD, CLR_ACTIVE_FG
            else:
                bg, bd, fg = '#1a1f2e', '#2a2a3a', '#444466'
            parts.append(
                f'<span style="font-size:13px;font-weight:600;padding:4px 11px;'
                f'border-radius:6px;border:1px solid {bd};background:{bg};'
                f'color:{fg};font-family:monospace;">{_e(pair_str)}</span>'
            )
        parts.append('</div>')

        # SECTION: Current pair expansion label
        if current_pair_idx < len(pairs):
            cp       = pairs[current_pair_idx]
            pair_str = str(cp.count) + cp.character if cp.count > 1 else cp.character
            expanded = _e(cp.character * min(cp.count, 20))
            suffix   = '…' if cp.count > 20 else ''
            parts.append(
                f'<div style="font-size:11px;color:#b8d4f5;margin-bottom:8px;'
                f'font-family:monospace;background:#0f1f3d;border-radius:4px;'
                f'padding:4px 10px;display:inline-block;">'
                f"Expanding '{_e(pair_str)}' → {expanded}{suffix}</div>"
            )

        # SECTION: Reconstructed char boxes
        parts.append(
            '<div style="font-size:10px;color:#555;letter-spacing:.08em;'
            'text-transform:uppercase;margin-bottom:6px;font-family:monospace;">'
            'Output — reconstructed</div>'
        )
        parts.append(
            '<div style="display:flex;gap:3px;flex-wrap:wrap;'
            'min-height:36px;margin-bottom:8px;">'
        )
        for i, ch in enumerate(all_chars):
            if i < chars_revealed:
                bg, bd, fg = CLR_DONE_BG, CLR_DONE_BD, CLR_DONE_FG
                opacity    = "1"
            elif i == chars_revealed:
                bg, bd, fg = CLR_ACTIVE_BG, CLR_ACTIVE_BD, CLR_ACTIVE_FG
                opacity    = "1"
            else:
                bg, bd, fg = "transparent", "#2a2a3a", "#333"
                opacity    = "0.15"
            parts.append(
                f'<div style="width:26px;height:26px;display:flex;align-items:center;'
                f'justify-content:center;font-size:12px;font-weight:600;'
                f'border-radius:4px;border:1px solid {bd};background:{bg};color:{fg};'
                f'opacity:{opacity};font-family:monospace;">{_e(ch)}</div>'
            )
        parts.append('</div>')

        # SECTION: Completion message
        if chars_revealed >= total_chars:
            parts.append(
                f'<div style="font-size:12px;color:{CLR_DONE_FG};font-weight:600;'
                f'font-family:monospace;background:{CLR_DONE_BG};border-radius:4px;'
                f'border:1px solid {CLR_DONE_BD};padding:6px 12px;display:inline-block;">'
                f'✓ Decoded {total_chars} chars — lossless round-trip verified</div>'
            )

        parts.append('</div>')
        return ''.join(parts)

    # ── FINAL SUMMARY ─────────────────────────────────────────────────────────

    def render_final_summary(self, result: RLEResult) -> str:
        """
        Render the completion metrics card.

        PURE FUNCTION.

        Shows 6 metric tiles in a 3-column grid:
          Original | Encoded | Ratio
          Runs     | Space   | Longest run
        """
        good       = result.is_beneficial
        ratio_bg   = "#1a2e1a" if good else "#2d0a0a"
        ratio_bd   = "#4caf50" if good else "#ef4444"
        ratio_fg   = "#a8d5a2" if good else "#fca5a5"

        if good:
            verdict    = f"{result.ratio:.2f}× smaller"
            space_str  = f"+{result.space_saved_pct:.1f}% saved"
        else:
            inv        = 1 / result.ratio if result.ratio > 0 else float('inf')
            verdict    = f"{inv:.2f}× LARGER"
            space_str  = f"{result.space_saved_pct:.1f}% (expanded)"

        lr_ch, lr_cnt = result.longest_run
        lr_label      = f"{lr_cnt}× '{lr_ch}'" if lr_ch else "—"

        metrics = [
            ("Original",    f"{result.original_bytes}B",  "#1a1f2e", "#2a2a3a", "#b8d4f5"),
            ("Encoded",     f"{result.encoded_bytes}B",   ratio_bg,  ratio_bd,  ratio_fg),
            ("Ratio",       verdict,                       ratio_bg,  ratio_bd,  ratio_fg),
            ("Runs",        str(result.num_runs),          "#1a1f2e", "#2a2a3a", "#b8d4f5"),
            ("Space",       space_str,                     ratio_bg,  ratio_bd,  ratio_fg),
            ("Longest run", lr_label,                      "#0f1f3d", "#4a90d9", "#b8d4f5"),
        ]

        tiles = []
        for label, val, bg, bd, fg in metrics:
            tiles.append(
                f'<div style="background:{bg};border:1px solid {bd};border-radius:8px;'
                f'padding:10px 14px;">'
                f'<div style="font-size:16px;font-weight:600;color:{fg};">{_e(str(val))}</div>'
                f'<div style="font-size:10px;color:#666;margin-top:3px;">{_e(label)}</div>'
                f'</div>'
            )

        return (
            '<div style="margin-top:12px;">'
            '<div style="font-size:10px;color:#555;text-transform:uppercase;'
            'letter-spacing:.08em;margin-bottom:8px;font-family:monospace;">'
            'Animation complete — final results</div>'
            '<div style="display:grid;grid-template-columns:repeat(3,1fr);'
            'gap:8px;font-family:monospace;">'
            + ''.join(tiles) +
            '</div></div>'
        )

    # ── STATE RECONSTRUCTION HELPER ───────────────────────────────────────────

    @staticmethod
    def reconstruct_state_at(
        steps: List[RLEStep],
        step_idx: int,
    ) -> dict:
        """
        Replay steps[0..step_idx] to determine:
          emitted_pairs, building_pair, current_run_start, current_run_len

        Called by slider mode so state is always computed fresh from steps.
        This ensures correctness even if the user jumps the slider.

        Returns a dict with keys:
          emitted_pairs, building_pair, current_run_start, current_run_len
        """
        emitted_pairs: List[RLEPair] = []
        building_pair: Optional[Tuple[str, int]] = None
        current_run_start = 0
        current_run_len   = 0

        for i in range(min(step_idx + 1, len(steps))):
            s = steps[i]
            if s.phase == 'start':
                current_run_start = s.position
                current_run_len   = 1
                building_pair     = (s.current_char, 1)
            elif s.phase == 'extend':
                current_run_len   = s.run_count
                building_pair     = (s.current_char, s.run_count)
            elif s.phase == 'emit':
                emitted_pairs.append(RLEPair(s.run_count, s.current_char))
                building_pair     = None
                current_run_start = s.position + 1   # next run starts after this one
                current_run_len   = 0
            elif s.phase == 'done':
                building_pair     = None
                current_run_len   = 0

        return {
            'emitted_pairs':     emitted_pairs,
            'building_pair':     building_pair,
            'current_run_start': current_run_start,
            'current_run_len':   current_run_len,
        }
