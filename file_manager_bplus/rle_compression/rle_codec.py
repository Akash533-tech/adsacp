"""
RLE Core Engine — Module 1 of RLE Compression
==============================================
Run-Length Encoding: replaces consecutive repeated characters
with (count, character) pairs.

Example:
  Input:   "AAAABBBCCDDDDDDEE"
  Output:  "4A3B2C6D2E"
  Savings: 17 bytes → 10 bytes (41% reduction)

Worst case (random, no repetition):
  Input:   "ABCDEF"
  Output:  "1A1B1C1D1E1F" → LARGER than original

This is the KEY educational point: RLE is great for repetitive data
and terrible for random or diverse data.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Tuple, Optional


# ─────────────────────────────────────────────────────────────────────────────
# Data Classes
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class RLEStep:
    """
    One character-level step captured during encoding.

    phase values:
      'start'  — first character of a new run found
      'extend' — same character extending the current run
      'emit'   — run has ended, pair being emitted to output
      'done'   — sentinel final step after all input processed
    """
    step_num: int
    position: int            # index in original string being processed
    current_char: str        # character currently being counted
    run_count: int           # how many times current_char has appeared so far
    next_char: str           # character that broke the run (or "" if end)
    run_ended: bool          # True = emitted a pair this step
    pair_emitted: str        # e.g. "4A" or "" if run still going
    input_so_far: str        # portion of input processed
    output_so_far: str       # encoded output built so far
    bytes_in: int            # original bytes consumed so far
    bytes_out: int           # encoded bytes produced so far
    phase: str = 'start'     # 'start' | 'extend' | 'emit' | 'done'


@dataclass
class RLEPair:
    """A single (count, character) encoding pair."""
    count: int
    character: str

    def __str__(self) -> str:
        # Optimization: skip count=1 prefix for single chars
        if self.count == 1:
            return self.character
        return f"{self.count}{self.character}"

    def byte_cost(self) -> int:
        """Bytes this pair costs in the encoded output."""
        if self.count == 1:
            return 1
        return len(str(self.count)) + 1


@dataclass
class RLEResult:
    """Full result of an RLE encoding operation."""
    original: str
    encoded: str                        # human-readable: "4A3B2C"
    pairs: List[RLEPair]                # structured pairs
    steps: List[RLEStep]                # step-by-step trace
    original_bytes: int
    encoded_bytes: int
    ratio: float                        # original / encoded (>1 = compression, <1 = expansion)
    space_saved_pct: float              # negative if RLE made it worse
    longest_run: Tuple[str, int]        # (char, length) of longest run
    num_runs: int                       # total distinct runs
    is_beneficial: bool                 # True if encoded_bytes < original_bytes


@dataclass
class RLEDecodeStep:
    """One step captured during decoding."""
    step_num: int
    token: str              # e.g. "4A"
    count: int
    character: str
    decoded_so_far: str
    position_in_output: int


# ─────────────────────────────────────────────────────────────────────────────
# RLE Codec
# ─────────────────────────────────────────────────────────────────────────────

class RLECodec:
    """
    Full RLE encoder/decoder with step-by-step tracing.
    Implements character-level encode() with per-character steps so the
    slider animates one character at a time, not one run at a time.

    Each step has a 'phase' field used by RLEAnimator:
      'start'  — first char of a new run
      'extend' — same char continuing the run (run_count increases)
      'emit'   — run ended, pair emitted (run_ended=True)
      'done'   — final sentinel after all input consumed
    """

    # ── Encoding ─────────────────────────────────────────────────────────────

    def encode(self, text: str, track_steps: bool = True) -> RLEResult:
        """
        RLE Encoding with character-level step tracing and phase labels.

        Algorithm:
          i = 0
          while i < len(text):
              current_char = text[i]
              run_count = 1
              record step: phase='start', run_ended=False

              while i + run_count < len(text) and text[i+run_count] == current_char:
                  run_count += 1
                  record step: phase='extend', run_ended=False

              pairs.append(RLEPair(run_count, current_char))
              record step: phase='emit', run_ended=True
              i += run_count

          record final step: phase='done'

        Byte cost per pair:
          count == 1 → 1 byte (just the char, no prefix)
          count > 1  → len(str(count)) + 1 bytes
        """
        if not text:
            return RLEResult(
                original='', encoded='', pairs=[], steps=[],
                original_bytes=0, encoded_bytes=0,
                ratio=0.0, space_saved_pct=0.0,
                longest_run=('', 0), num_runs=0, is_beneficial=False,
            )

        pairs: List[RLEPair] = []
        steps: List[RLEStep] = []
        step_num = 0
        i = 0
        output_so_far = ''
        bytes_out_running = 0

        while i < len(text):
            current_char = text[i]
            run_count = 1

            # ── Step: phase='start' (first char of new run) ──────────────────
            if track_steps:
                next_ch = text[i + 1] if (i + 1) < len(text) else ''
                steps.append(RLEStep(
                    step_num=step_num,
                    position=i,
                    current_char=current_char,
                    run_count=1,
                    next_char=next_ch,
                    run_ended=False,
                    pair_emitted='',
                    input_so_far=text[:i + 1],
                    output_so_far=output_so_far,
                    bytes_in=i + 1,
                    bytes_out=bytes_out_running,
                    phase='start',
                ))
                step_num += 1

            # ── Extend the run — one step per additional matching character ──
            while (i + run_count) < len(text) and text[i + run_count] == current_char:
                run_count += 1
                if track_steps:
                    next_ch = text[i + run_count] if (i + run_count) < len(text) else ''
                    steps.append(RLEStep(
                        step_num=step_num,
                        position=i + run_count - 1,
                        current_char=current_char,
                        run_count=run_count,
                        next_char=next_ch,
                        run_ended=False,
                        pair_emitted='',
                        input_so_far=text[:i + run_count],
                        output_so_far=output_so_far,
                        bytes_in=i + run_count,
                        bytes_out=bytes_out_running,
                        phase='extend',
                    ))
                    step_num += 1

            # ── Emit the pair ─────────────────────────────────────────────────
            pair = RLEPair(run_count, current_char)
            pairs.append(pair)
            pair_str = str(pair)
            output_so_far += pair_str
            pair_cost = pair.byte_cost()
            bytes_out_running += pair_cost

            # ── Step: phase='emit' (run complete, pair written to output) ─────
            if track_steps:
                next_ch = text[i + run_count] if (i + run_count) < len(text) else ''
                steps.append(RLEStep(
                    step_num=step_num,
                    position=i + run_count - 1,
                    current_char=current_char,
                    run_count=run_count,
                    next_char=next_ch,
                    run_ended=True,
                    pair_emitted=pair_str,
                    input_so_far=text[:i + run_count],
                    output_so_far=output_so_far,
                    bytes_in=i + run_count,
                    bytes_out=bytes_out_running,
                    phase='emit',
                ))
                step_num += 1

            i += run_count

        # ── Final sentinel step: phase='done' ─────────────────────────────────
        if track_steps and steps:
            last = steps[-1]
            steps.append(RLEStep(
                step_num=step_num,
                position=len(text) - 1,
                current_char=last.current_char,
                run_count=last.run_count,
                next_char='',
                run_ended=True,
                pair_emitted=last.pair_emitted,
                input_so_far=text,
                output_so_far=output_so_far,
                bytes_in=len(text),
                bytes_out=bytes_out_running,
                phase='done',
            ))

        encoded = ''.join(str(p) for p in pairs)
        original_bytes = len(text)
        encoded_bytes = max(bytes_out_running, 1)
        ratio = round(original_bytes / encoded_bytes, 4)
        space_saved_pct = round((1.0 - encoded_bytes / original_bytes) * 100, 2) if original_bytes > 0 else 0.0
        longest = max(pairs, key=lambda p: p.count) if pairs else RLEPair(0, '')

        return RLEResult(
            original=text,
            encoded=encoded,
            pairs=pairs,
            steps=steps,
            original_bytes=original_bytes,
            encoded_bytes=encoded_bytes,
            ratio=ratio,
            space_saved_pct=space_saved_pct,
            longest_run=(longest.character, longest.count),
            num_runs=len(pairs),
            is_beneficial=encoded_bytes < original_bytes,
        )

    # ── Decoding ─────────────────────────────────────────────────────────────

    def decode(self, encoded: str) -> Tuple[str, List[RLEDecodeStep]]:
        """
        RLE Decoding with step tracing.

        Algorithm:
          i = 0
          while i < len(encoded):
              Read digit sequence → count_str
              Read next char → character
              count = int(count_str) if count_str else 1
              append char * count to result
              record RLEDecodeStep

        Edge cases:
          - count_str empty → count = 1 (bare char with no digit prefix)
          - encoded is empty → return ''
        """
        if not encoded:
            return '', []

        result_parts: List[str] = []
        steps: List[RLEDecodeStep] = []
        step_num = 0
        i = 0

        while i < len(encoded):
            # Collect digit characters
            count_str = ''
            while i < len(encoded) and encoded[i].isdigit():
                count_str += encoded[i]
                i += 1

            if i >= len(encoded):
                break

            char = encoded[i]
            i += 1

            count = int(count_str) if count_str else 1
            result_parts.append(char * count)

            decoded_so_far = ''.join(result_parts)
            steps.append(RLEDecodeStep(
                step_num=step_num,
                token=count_str + char,
                count=count,
                character=char,
                decoded_so_far=decoded_so_far,
                position_in_output=len(decoded_so_far) - count,
            ))
            step_num += 1

        return ''.join(result_parts), steps

    # ── Verification ──────────────────────────────────────────────────────────

    def verify(self, original: str, encoded: str) -> bool:
        """
        Decode encoded and compare to original.
        Returns True if the round-trip is lossless.
        """
        decoded, _ = self.decode(encoded)
        return decoded == original

    # ── Binary Variant ────────────────────────────────────────────────────────

    def encode_binary(self, data: bytes) -> List[Tuple[int, int]]:
        """
        Binary RLE: encode bytes as (count, byte_value) tuples.
        Max count per pair = 255 (single-byte count field).
        When a run exceeds 255, split into multiple pairs of same byte.
        Used for simulating image/bitmap compression.
        """
        if not data:
            return []

        pairs: List[Tuple[int, int]] = []
        i = 0
        while i < len(data):
            current_byte = data[i]
            count = 1
            while (
                i + count < len(data)
                and data[i + count] == current_byte
                and count < 255
            ):
                count += 1
            pairs.append((count, current_byte))
            i += count

        return pairs

    def decode_binary(self, pairs: List[Tuple[int, int]]) -> bytes:
        """Reconstruct bytes from (count, byte_value) pairs."""
        result = bytearray()
        for count, byte_val in pairs:
            result.extend([byte_val] * count)
        return bytes(result)

    def binary_stats(self, data: bytes, pairs: List[Tuple[int, int]]) -> dict:
        """
        Compute binary RLE statistics.
        Encoded bytes = len(pairs) * 2  (1 byte count + 1 byte value).
        """
        original_bytes = len(data)
        encoded_bytes = max(len(pairs) * 2, 1)
        ratio = round(original_bytes / encoded_bytes, 4) if encoded_bytes > 0 else 0.0
        space_saved_pct = round((1.0 - encoded_bytes / original_bytes) * 100, 2) if original_bytes > 0 else 0.0
        return {
            'original_bytes': original_bytes,
            'encoded_bytes': encoded_bytes,
            'ratio': ratio,
            'space_saved_pct': space_saved_pct,
        }

    # ── Suitability Analysis ──────────────────────────────────────────────────

    def analyze_rle_suitability(self, text: str) -> dict:
        """
        Analyse how suitable the data is for RLE compression.

        Logic:
          result = encode(text, track_steps=False)
          repetition_score = 1 - (result.num_runs / len(text))
          avg_run = len(text) / result.num_runs

          if avg_run >= 5: "Excellent"
          elif avg_run >= 3: "Good"
          elif avg_run >= 2: "Poor"
          else: "Terrible"

        Returns all analysis values needed by the visualizer.
        """
        if not text:
            return {
                'repetition_score': 0.0,
                'avg_run_length': 0.0,
                'max_run_length': 0,
                'num_unique_chars': 0,
                'recommendation': 'Terrible',
                'reason': 'Empty input — nothing to compress',
                'estimated_ratio': 0.0,
                'content_type': 'unknown',
            }

        result = self.encode(text, track_steps=False)
        n = len(text)
        num_runs = result.num_runs if result.num_runs > 0 else 1

        repetition_score = round(1.0 - (num_runs / n), 4)
        avg_run = round(n / num_runs, 2)
        max_run = result.longest_run[1]
        num_unique = len(set(text))

        if avg_run >= 5:
            recommendation = 'Excellent'
            reason = (
                f'Average run of {avg_run:.1f} chars — long repetitive regions. '
                f'RLE achieves {result.ratio:.1f}× compression. '
                f'Best for bitmaps, DNA, satellite images.'
            )
            content_type = 'bitmap'
        elif avg_run >= 3:
            recommendation = 'Good'
            reason = (
                f'Average run of {avg_run:.1f} chars — moderate repetition. '
                f'RLE achieves {result.ratio:.1f}× compression. '
                f'Works well for logs, CSV with padding, structured data.'
            )
            content_type = 'log'
        elif avg_run >= 2:
            recommendation = 'Poor'
            reason = (
                f'Average run of {avg_run:.1f} chars — mostly short runs. '
                f'RLE achieves {result.ratio:.1f}× — marginal benefit. '
                f'Text and source code rarely benefit from RLE.'
            )
            content_type = 'text'
        else:
            recommendation = 'Terrible'
            reason = (
                f'Average run of {avg_run:.1f} chars — near-random data. '
                f'RLE ratio is {result.ratio:.1f}× (EXPANSION, not compression). '
                f'Never use RLE on binary archives, video, or encrypted data.'
            )
            content_type = 'binary'

        return {
            'repetition_score': repetition_score,
            'avg_run_length': avg_run,
            'max_run_length': max_run,
            'num_unique_chars': num_unique,
            'recommendation': recommendation,
            'reason': reason,
            'estimated_ratio': result.ratio,
            'content_type': content_type,
        }
