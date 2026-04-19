"""
LZW (Lempel-Ziv-Welch) Codec — Module 2
=========================================
Dictionary-based compression that builds its codebook on-the-fly while
scanning the input.  No separate frequency table is needed; the decoder
can rebuild the same dictionary from the compressed stream alone.

WHY not Huffman:
  Huffman builds a frequency table FIRST then assigns variable-length codes.
  LZW scans once and updates the dictionary live — you can watch it grow.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Dict, Tuple, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from file_ops.metadata import FileMetadata


# ─────────────────────────────────────────────────────────────────────────────
# Data classes
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class LZWStep:
    """One encoding step — captured for the educational step-by-step trace."""
    step_num: int
    buffer: str                        # current buffer being built
    current_char: str                  # character being processed
    match: str                         # buffer + current_char
    in_dict: bool                      # was the match in dictionary?
    code_emitted: int                  # code output (-1 if none this step)
    new_entry: str                     # new dictionary entry added (or "")
    new_code: int                      # code assigned to new_entry (-1 if none)
    dict_snapshot: Dict[str, int] = field(default_factory=dict)


@dataclass
class CompressionStats:
    original_bytes: int
    compressed_bytes: int
    ratio: float
    space_saved_pct: float
    dict_final_size: int
    steps_count: int


@dataclass
class CompressedFile:
    original_filename: str
    compressed_filename: str          # original + ".lzw"
    codes: List[int]
    stats: CompressionStats
    compressed_at: datetime = field(default_factory=datetime.now)


# ─────────────────────────────────────────────────────────────────────────────
# LZW Codec
# ─────────────────────────────────────────────────────────────────────────────

class LZWCodec:
    """
    Full LZW encoder/decoder with step-by-step trace capability.
    Initial dictionary: 128 single ASCII characters (codes 0–127).
    """

    # ── Encoding ────────────────────────────────────────────────────────────

    def encode(self, text: str) -> Tuple[List[int], List[LZWStep]]:
        """
        LZW Encoding Algorithm.

        1. Init dict with all 128 ASCII single chars.
        2. buffer = first char.
        3. For each remaining char c:
              candidate = buffer + c
              if candidate in dict:  buffer = candidate  (extend match)
              else:  emit dict[buffer]; dict[candidate] = next_code; buffer = c
        4. Emit dict[buffer] for the final buffer.

        Returns (codes, steps).
        """
        if not text:
            return [], []

        # Initialise dictionary
        dictionary: Dict[str, int] = {chr(i): i for i in range(128)}
        next_code = 128

        codes: List[int] = []
        steps: List[LZWStep] = []
        step_num = 0

        buffer = text[0]

        for i in range(1, len(text)):
            c = text[i]
            candidate = buffer + c

            if candidate in dictionary:
                # Match extended — no output yet
                step = LZWStep(
                    step_num=step_num,
                    buffer=buffer,
                    current_char=c,
                    match=candidate,
                    in_dict=True,
                    code_emitted=-1,
                    new_entry="",
                    new_code=-1,
                    dict_snapshot=dict(dictionary),
                )
                buffer = candidate
            else:
                # Emit code for current buffer, add candidate
                emitted = dictionary[buffer]
                codes.append(emitted)
                dictionary[candidate] = next_code
                step = LZWStep(
                    step_num=step_num,
                    buffer=buffer,
                    current_char=c,
                    match=candidate,
                    in_dict=False,
                    code_emitted=emitted,
                    new_entry=candidate,
                    new_code=next_code,
                    dict_snapshot=dict(dictionary),
                )
                next_code += 1
                buffer = c

            steps.append(step)
            step_num += 1

        # Emit final buffer
        if buffer in dictionary:
            emitted = dictionary[buffer]
            codes.append(emitted)
            steps.append(LZWStep(
                step_num=step_num,
                buffer=buffer,
                current_char="",
                match=buffer,
                in_dict=True,
                code_emitted=emitted,
                new_entry="",
                new_code=-1,
                dict_snapshot=dict(dictionary),
            ))

        return codes, steps

    # ── Decoding ────────────────────────────────────────────────────────────

    def decode(self, codes: List[int]) -> str:
        """
        LZW Decoding Algorithm.

        1. Init inverse dict {code: string} for 128 ASCII chars.
        2. output = inverse_dict[codes[0]]
        3. prev = inverse_dict[codes[0]]
        4. For each subsequent code:
              if code in dict:  entry = dict[code]
              else (special case code == next_code):  entry = prev + prev[0]
              output += entry
              dict[next_code] = prev + entry[0]
              next_code += 1
              prev = entry
        Returns decoded string (MUST be identical to original).
        """
        if not codes:
            return ""

        inverse: Dict[int, str] = {i: chr(i) for i in range(128)}
        next_code = 128

        output_parts = [inverse[codes[0]]]
        prev = inverse[codes[0]]

        for code in codes[1:]:
            if code in inverse:
                entry = inverse[code]
            else:
                # Special case: code not yet in dict
                entry = prev + prev[0]

            output_parts.append(entry)
            inverse[next_code] = prev + entry[0]
            next_code += 1
            prev = entry

        return "".join(output_parts)

    # ── Metadata helpers ─────────────────────────────────────────────────────

    def compress_metadata(self, metadata: "FileMetadata") -> "CompressedFile":
        """Serialise metadata to JSON string and LZW-encode it."""
        from file_ops.metadata import FileMetadata  # avoid circular at module level
        text = json.dumps({
            "filename":   metadata.filename,
            "extension":  metadata.extension,
            "size_bytes": metadata.size_bytes,
            "created_at": str(metadata.created_at),
            "modified_at": str(metadata.modified_at),
            "path":       metadata.path,
            "tags":       metadata.tags,
            "is_directory": metadata.is_directory,
        })
        codes, _steps = self.encode(text)
        stats = self.get_compression_stats(text, codes)
        return CompressedFile(
            original_filename=metadata.filename,
            compressed_filename=metadata.filename + ".lzw",
            codes=codes,
            stats=stats,
        )

    def decompress_metadata(self, compressed: "CompressedFile") -> "FileMetadata":
        """Decode codes back to JSON and parse FileMetadata."""
        from file_ops.metadata import FileMetadata
        text = self.decode(compressed.codes)
        data = json.loads(text)
        return FileMetadata(
            filename=data["filename"],
            extension=data["extension"],
            size_bytes=data["size_bytes"],
            created_at=datetime.fromisoformat(data["created_at"]),
            modified_at=datetime.fromisoformat(data["modified_at"]),
            path=data["path"],
            tags=data.get("tags", []),
            is_directory=data.get("is_directory", False),
        )

    # ── Statistics ──────────────────────────────────────────────────────────

    def get_compression_stats(self, original: str, codes: List[int]) -> CompressionStats:
        """
        Compute compression statistics.
        We assume 16-bit (2-byte) codes → compressed_bytes = len(codes) * 2.
        """
        orig_bytes = len(original.encode("utf-8"))
        comp_bytes = max(1, len(codes) * 2)          # 16-bit per code
        ratio = orig_bytes / comp_bytes if comp_bytes else 1.0
        saved_pct = (1.0 - comp_bytes / orig_bytes) * 100 if orig_bytes else 0.0

        # Count non-ASCII-base entries (LZW built entries)
        # dict_final_size estimated from steps would need encode output —
        # approximate from the code range
        dict_size = 128 + len(set(c for c in codes if c >= 128))

        return CompressionStats(
            original_bytes=orig_bytes,
            compressed_bytes=comp_bytes,
            ratio=round(ratio, 4),
            space_saved_pct=round(saved_pct, 2),
            dict_final_size=dict_size,
            steps_count=len(codes),
        )
