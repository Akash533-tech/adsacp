"""
File Diff Viewer (Module 5A)
==============================
Compares two FileMetadata records — serialises them as JSON and produces
a field-by-field diff with a side-by-side HTML renderer.
"""

from __future__ import annotations

import difflib
import json
from dataclasses import dataclass
from typing import Any, Dict, List, Tuple, TYPE_CHECKING

if TYPE_CHECKING:
    from file_ops.metadata import FileMetadata


@dataclass
class DiffResult:
    file_a: str
    file_b: str
    added_fields: List[str]                          # fields in B not in A
    removed_fields: List[str]                        # fields in A not in B
    changed_fields: Dict[str, Tuple[Any, Any]]       # field: (old, new)
    diff_lines: List[str]                            # unified diff output


class FileDiff:
    """Compare two FileMetadata objects field-by-field and as unified diff."""

    def diff(self, meta_a: "FileMetadata", meta_b: "FileMetadata") -> DiffResult:
        """Compare two FileMetadata objects."""
        dict_a = self._to_dict(meta_a)
        dict_b = self._to_dict(meta_b)

        added   = [k for k in dict_b if k not in dict_a]
        removed = [k for k in dict_a if k not in dict_b]
        changed = {
            k: (dict_a[k], dict_b[k])
            for k in dict_a
            if k in dict_b and str(dict_a[k]) != str(dict_b[k])
        }

        json_a = json.dumps(dict_a, indent=2, default=str).splitlines(keepends=True)
        json_b = json.dumps(dict_b, indent=2, default=str).splitlines(keepends=True)
        diff_lines = list(difflib.unified_diff(
            json_a, json_b,
            fromfile=meta_a.filename,
            tofile=meta_b.filename,
            lineterm="",
        ))

        return DiffResult(
            file_a=meta_a.filename,
            file_b=meta_b.filename,
            added_fields=added,
            removed_fields=removed,
            changed_fields=changed,
            diff_lines=diff_lines,
        )

    def render_side_by_side_html(self, diff: DiffResult) -> str:
        """
        Two-column HTML diff.
        Left = file A (deletions highlighted red).
        Right = file B (additions highlighted green).
        Unchanged lines shown in dim grey.
        """
        left_lines: List[str] = []
        right_lines: List[str] = []

        for line in diff.diff_lines:
            if line.startswith("---") or line.startswith("+++") or line.startswith("@@"):
                left_lines.append(f'<div style="color:#6b7db3;font-size:11px">{_esc(line)}</div>')
                right_lines.append(f'<div style="color:#6b7db3;font-size:11px">&nbsp;</div>')
            elif line.startswith("-"):
                left_lines.append(
                    f'<div style="background:#3d1515;color:#ff8080;padding:1px 4px">{_esc(line)}</div>'
                )
                right_lines.append('<div style="padding:1px 4px">&nbsp;</div>')
            elif line.startswith("+"):
                left_lines.append('<div style="padding:1px 4px">&nbsp;</div>')
                right_lines.append(
                    f'<div style="background:#153d15;color:#80ff80;padding:1px 4px">{_esc(line)}</div>'
                )
            else:
                plain = f'<div style="color:#6b7280;padding:1px 4px">{_esc(line)}</div>'
                left_lines.append(plain)
                right_lines.append(plain)

        left_html = "\n".join(left_lines)
        right_html = "\n".join(right_lines)

        return f"""
<div style="display:flex;gap:12px;font-family:monospace;font-size:12px;">
  <div style="flex:1;background:#0f1117;border:1px solid #2a3550;border-radius:6px;
              padding:10px;overflow-x:auto;">
    <div style="color:#ef4444;font-weight:700;margin-bottom:6px;">◀ {_esc(diff.file_a)}</div>
    {left_html}
  </div>
  <div style="flex:1;background:#0f1117;border:1px solid #2a3550;border-radius:6px;
              padding:10px;overflow-x:auto;">
    <div style="color:#22c55e;font-weight:700;margin-bottom:6px;">▶ {_esc(diff.file_b)}</div>
    {right_html}
  </div>
</div>
"""

    @staticmethod
    def _to_dict(meta: "FileMetadata") -> dict:
        return {
            "filename":    meta.filename,
            "extension":   meta.extension,
            "size_bytes":  meta.size_bytes,
            "created_at":  str(meta.created_at),
            "modified_at": str(meta.modified_at),
            "path":        meta.path,
            "tags":        meta.tags,
            "is_directory": meta.is_directory,
        }


import html as _html_module

def _esc(s: str) -> str:
    return _html_module.escape(str(s), quote=False)
