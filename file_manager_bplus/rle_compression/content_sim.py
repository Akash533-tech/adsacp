"""
File Content Simulator — Module 2 of RLE Compression
======================================================
Generates realistic simulated file CONTENT based on file extension.
Each content type demonstrates RLE's performance in a different scenario,
from excellent (bitmap) to terrible (random binary).
"""

from __future__ import annotations

import random
import string
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from file_ops.metadata import FileMetadata

# Fixed seed per session for reproducibility within a run
_RNG = random.Random(42)


class ContentSimulator:
    """
    Generates simulated file content appropriate for each file extension.
    The content is designed to have realistic RLE characteristics:
      - Images (.bmp/.jpg/.png): long pixel runs → Excellent RLE (5-15x)
      - Logs (.log):             repeated prefixes/spaces → Good RLE (2-4x)
      - DNA (.dna):              repeated nucleotide runs → Good-Excellent (3-8x)
      - CSV (.csv):              padded zeros + repeated commas → Good (2-3x)
      - Text (.txt/.py/.sql):    natural language diversity → Poor (0.8-1.2x)
      - Binary (.zip/.mp4):      random bytes → Terrible (<0.7x)
    """

    CONTENT_MAP = {
        '.jpg':  '_gen_bitmap_image',
        '.png':  '_gen_bitmap_image',
        '.bmp':  '_gen_bitmap_image',
        '.log':  '_gen_log_file',
        '.dna':  '_gen_dna_sequence',
        '.csv':  '_gen_csv_data',
        '.txt':  '_gen_simple_text',
        '.sql':  '_gen_simple_text',
        '.py':   '_gen_simple_text',
        '.md':   '_gen_simple_text',
        '.pdf':  '_gen_simple_text',
        '.html': '_gen_simple_text',
        '.js':   '_gen_simple_text',
        '.css':  '_gen_simple_text',
        '.json': '_gen_simple_text',
        '.zip':  '_gen_binary_data',
        '.mp4':  '_gen_binary_data',
    }

    def generate_content(self, metadata: "FileMetadata") -> str:
        """
        Generate simulated content based on file extension and size.
        Returns a string representing the file's content (text representation).
        """
        ext = (metadata.extension or '.txt').lower()
        method_name = self.CONTENT_MAP.get(ext, '_gen_simple_text')
        method = getattr(self, method_name)
        # Scale content length from size — cap at 400 for UI readability
        size = min(max(metadata.size_bytes // 20, 60), 400)
        content = method(size)
        return content

    # ── Content types where RLE EXCELS ───────────────────────────────────────

    def _gen_bitmap_image(self, size_bytes: int) -> str:
        """
        Simulate a grayscale bitmap image as ASCII pixel characters.
        W=white(255), L=light(192), G=gray(128), D=dark(64), B=black(0)

        Realistic images have large uniform regions (sky, background,
        solid shapes) creating many long runs — ideal for RLE.

        Typical ratio: 5-15x
        """
        # Pixel character set representing grayscale levels
        pixels = ['W', 'W', 'W', 'L', 'G', 'G', 'D', 'B']
        result = []
        # Generate rows of pixels with band-like structure (realistic image regions)
        row_width = 20
        # Create bands: background, object, background pattern
        bands = [
            ('W', random.randint(3, 6)),   # white band (sky/background)
            ('G', random.randint(2, 4)),   # gray band
            ('B', random.randint(2, 5)),   # black band (object outline)
            ('D', random.randint(3, 6)),   # dark band
            ('G', random.randint(2, 3)),   # gray band
            ('W', random.randint(4, 8)),   # white band again
        ]
        row_num = 0
        while len(result) < size_bytes:
            # Alternate between solid rows and noisy rows
            if row_num % 4 == 0:
                # Solid row — very compressible
                dominant = random.choice(['W', 'W', 'W', 'G', 'L'])
                row = [dominant] * row_width
            else:
                # Banded row using defined bands
                row = []
                for char, run_len in bands:
                    row.extend([char] * run_len)
                row = row[:row_width]
            result.extend(row)
            result.append('\n')
            row_num += 1

        content = ''.join(result[:size_bytes])
        return content

    def _gen_log_file(self, size_bytes: int) -> str:
        """
        Simulate a server log file with repeated timestamp prefixes and
        many spaces used for indentation/alignment.

        Pattern: large blocks of spaces (indentation) + short message tokens
        Typical ratio: 2-4x
        """
        templates = [
            '          ERROR   ',    # 10 spaces + level (repeated)
            '          WARNING ',
            '          INFO    ',
            '                  ',    # blank separator (all spaces)
            '    [OK]          ',
            '    [FAIL]        ',
        ]
        result = []
        while len(result) < size_bytes:
            line = random.choice(templates)
            # Add a short repeated code (e.g. 404, 200)
            code = random.choice(['404', '200', '500', '404', '200'])
            line = line + code + '  '
            result.extend(list(line))
        return ''.join(result[:size_bytes])

    def _gen_dna_sequence(self, size_bytes: int) -> str:
        """
        Simulate a DNA sequence with long repeated regions.
        Real DNA has repetitive regions (tandem repeats, telomeres).
        Only 4 characters (A, T, G, C), with runs of 3-20.

        Typical ratio: 3-8x
        """
        bases = ['A', 'T', 'G', 'C']
        # Weighted: A and T tend to appear more in some regions
        weights = [0.35, 0.35, 0.15, 0.15]
        result = []
        while len(result) < size_bytes:
            base = random.choices(bases, weights=weights)[0]
            # Telomeric repeats: long runs
            run_len = random.randint(4, 18)
            result.extend([base] * run_len)
        return ''.join(result[:size_bytes])

    def _gen_csv_data(self, size_bytes: int) -> str:
        """
        Simulate CSV data with zero-padded numbers and repeated comma separators.
        The leading zeros create long '0' runs.

        Typical ratio: 2-3x
        """
        result = []
        while len(result) < size_bytes:
            # Zero-padded integers (many leading zeros)
            num = str(random.randint(1, 9999)).zfill(9)   # '000001234'
            sep = ',,,,'   # repeated commas
            row = num + sep
            result.extend(list(row))
        return ''.join(result[:size_bytes])

    # ── Content types where RLE performs poorly ───────────────────────────────

    def _gen_simple_text(self, size_bytes: int) -> str:
        """
        Simulate text/source code. Natural language has:
        - spaces between words (short runs of 1)
        - varied characters
        - some repeated words but no long single-char runs

        RLE works on multi-space indentation but poorly otherwise.
        Typical ratio: 0.8-1.2x (borderline)
        """
        words = [
            'def', 'return', 'if', 'else', 'for', 'in', 'the', 'and',
            'import', 'class', 'self', 'True', 'False', 'None', 'print',
            'range', 'list', 'dict', 'str', 'int', 'not', 'with', 'as',
        ]
        indents = ['    ', '        ', '']   # 4/8/0 spaces
        result = []
        while len(result) < size_bytes:
            indent = random.choice(indents)
            word = random.choice(words)
            line = indent + word + ' '
            result.extend(list(line))
        return ''.join(result[:size_bytes])

    def _gen_binary_data(self, size_bytes: int) -> str:
        """
        Simulate compressed binary (zip/mp4 content-like).
        Uses all printable ASCII chars uniformly — maximum entropy.
        Every character different → RLE EXPANDS this badly.

        Typical ratio: 0.5x or worse
        """
        # Use all printable ASCII for maximum diversity
        chars = string.ascii_letters + string.digits + string.punctuation
        result = []
        for _ in range(size_bytes):
            result.append(random.choice(chars))
        return ''.join(result)

    # ── Demo helpers ──────────────────────────────────────────────────────────

    def get_rle_friendly_content(self, length: int = 80) -> str:
        """
        Hand-crafted string showing RLE at its best.
        A bitmap row with clear pixel regions.
        """
        chunk = 'W' * 18 + 'B' * 12 + 'W' * 20 + 'G' * 14 + 'D' * 8 + 'W' * 8
        reps = (length // len(chunk)) + 1
        return (chunk * reps)[:length]

    def get_rle_hostile_content(self, length: int = 80) -> str:
        """
        Hand-crafted string showing RLE at its worst — all unique chars.
        """
        chars = string.ascii_letters + string.digits
        result = []
        for i in range(length):
            result.append(chars[i % len(chars)])
        return ''.join(result)
