"""
XOR File Encryption (Module 5B)
=================================
XOR cipher with a repeating key — symmetric (encrypt == decrypt),
simple to visualise step-by-step.
NOT production-grade security — purely educational DSA demonstration.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from file_ops.metadata import FileMetadata


@dataclass
class EncryptedFile:
    original_filename: str
    key_used: str                  # NOT stored in plaintext in real systems
    hex_data: str                  # XOR'd bytes as hex string
    encrypted_at: datetime


class XOREncryptor:
    """
    XOR cipher that operates on a UTF-8 JSON serialisation of FileMetadata.
    The key repeats cyclically over the entire byte string.
    """

    def encrypt(self, filename: str, key: str, tree) -> EncryptedFile:
        """
        XOR every byte of JSON(metadata) with the repeating key bytes.
        Stores result as hex string.
        """
        meta = tree.search(filename)
        if meta is None:
            raise ValueError(f"File '{filename}' not found in B+ Tree")

        text = self._serialise(meta)
        xored = self._xor(text.encode("utf-8"), key)
        hex_data = xored.hex()

        return EncryptedFile(
            original_filename=filename,
            key_used=key,
            hex_data=hex_data,
            encrypted_at=datetime.now(),
        )

    def decrypt(self, encrypted: EncryptedFile, key: str) -> "FileMetadata":
        """
        XOR again with the same key to reverse the encryption.
        Returns the original FileMetadata.
        """
        raw_bytes = bytes.fromhex(encrypted.hex_data)
        xored = self._xor(raw_bytes, key)
        text = xored.decode("utf-8")
        return self._deserialise(text)

    def verify(self, original_text: str, decrypted_text: str) -> bool:
        """True if the decrypted text exactly matches the original."""
        return original_text == decrypted_text

    def show_xor_visualization(self, text: str, key: str) -> str:
        """
        Return an HTML table showing the XOR process for the first 10 characters:
          | Char | ASCII | Key Char | Key ASCII | XOR Result |
        """
        key_bytes = key.encode("utf-8") or b"\x00"
        text_bytes = text.encode("utf-8")

        rows_html = ""
        n = min(10, len(text_bytes))
        for i in range(n):
            tb = text_bytes[i]
            kb = key_bytes[i % len(key_bytes)]
            xb = tb ^ kb
            char_disp = chr(tb) if 32 <= tb < 127 else f"\\x{tb:02x}"
            key_disp  = chr(kb) if 32 <= kb < 127 else f"\\x{kb:02x}"
            xor_disp  = chr(xb) if 32 <= xb < 127 else f"\\x{xb:02x}"
            rows_html += f"""
            <tr>
              <td>{_esc(char_disp)}</td>
              <td style="color:#4a90d9">{tb}</td>
              <td style="color:#f59e0b">{_esc(key_disp)}</td>
              <td style="color:#f59e0b">{kb}</td>
              <td style="color:#22c55e">{_esc(xor_disp)} ({xb})</td>
            </tr>"""

        return f"""
<div style="overflow-x:auto;">
<table style="width:100%;border-collapse:collapse;font-family:monospace;font-size:12px;background:#0f1117;">
  <thead>
    <tr style="background:#1a1f2e;color:#7a9bc4;">
      <th style="padding:8px;border:1px solid #2a3550;">Char</th>
      <th style="padding:8px;border:1px solid #2a3550;">ASCII</th>
      <th style="padding:8px;border:1px solid #2a3550;">Key Char</th>
      <th style="padding:8px;border:1px solid #2a3550;">Key ASCII</th>
      <th style="padding:8px;border:1px solid #2a3550;">XOR Result</th>
    </tr>
  </thead>
  <tbody style="color:#e8f0fe;">
    {rows_html}
  </tbody>
</table>
<p style="color:#6b7280;font-size:11px;margin-top:4px;">
  Showing first {n} of {len(text_bytes)} bytes. XOR flips bits; apply the same key again to reverse.</p>
</div>
"""

    # ── Internal ─────────────────────────────────────────────────────────────

    @staticmethod
    def _xor(data: bytes, key: str) -> bytes:
        key_bytes = key.encode("utf-8") or b"\x00"
        return bytes(b ^ key_bytes[i % len(key_bytes)] for i, b in enumerate(data))

    @staticmethod
    def _serialise(meta: "FileMetadata") -> str:
        return json.dumps({
            "filename":   meta.filename,
            "extension":  meta.extension,
            "size_bytes": meta.size_bytes,
            "created_at": str(meta.created_at),
            "modified_at": str(meta.modified_at),
            "path":       meta.path,
            "tags":       meta.tags,
            "is_directory": meta.is_directory,
        })

    @staticmethod
    def _deserialise(text: str) -> "FileMetadata":
        from file_ops.metadata import FileMetadata
        from datetime import datetime
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


import html as _html_mod

def _esc(s: str) -> str:
    return _html_mod.escape(str(s), quote=False)
