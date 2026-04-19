"""
Virtual Shell — command parser and executor for the B+ Tree filesystem.
Operates entirely on a BPlusTree instance (no real disk access).
"""

from __future__ import annotations

import shlex
from dataclasses import dataclass, field
from typing import List, Dict, Tuple, TYPE_CHECKING

if TYPE_CHECKING:
    from bplus.bplus_tree import BPlusTree


@dataclass
class ShellResult:
    """Result returned by every executed command."""
    stdout: str = ""               # text to display in green
    stderr: str = ""               # error text to display in red
    exit_code: int = 0             # 0 = success, non-zero = error
    tree_changed: bool = False     # True if B+ Tree was modified
    highlight_files: List[str] = field(default_factory=list)  # files to highlight in viz


class VirtualShell:
    """
    A virtual shell that maps Linux/macOS-style commands onto the B+ Tree
    virtual filesystem.  No real disk access is performed.
    """

    def __init__(self, tree: "BPlusTree"):
        self.tree = tree
        self.cwd: str = "/root"
        self.history: List[str] = []          # raw command strings
        self.env: Dict[str, str] = {}         # KEY → value
        self.alias: Dict[str, str] = {}       # name → command string
        # Virtual directories: path → True
        self._dirs: Dict[str, bool] = {
            "/root": True,
            "/root/src": True,
            "/root/docs": True,
            "/root/data": True,
            "/root/assets": True,
            "/root/tests": True,
            "/root/media": True,
            "/root/db": True,
            "/root/web": True,
        }

    # ──────────────────────────────────────────────────────────────────────────
    # PUBLIC API
    # ──────────────────────────────────────────────────────────────────────────

    def execute(self, raw_input: str) -> ShellResult:
        """Parse raw_input, resolve aliases, execute command, return ShellResult."""
        raw = raw_input.strip()
        if not raw:
            return ShellResult()

        # Expand env variables ($VAR)
        for key, val in self.env.items():
            raw = raw.replace(f"${key}", val)

        # Resolve alias
        parts_check = raw.split()
        if parts_check and parts_check[0] in self.alias:
            raw = self.alias[parts_check[0]] + " " + " ".join(parts_check[1:])
            raw = raw.strip()

        self.history.append(raw)

        cmd, args, flags = self.parse(raw)

        from terminal.commands import CommandRegistry
        registry = CommandRegistry(self)
        handler = registry.get(cmd)
        if handler is None:
            return ShellResult(
                stderr=f"bplus-shell: command not found: {cmd}\nType 'help' for available commands.",
                exit_code=127,
            )
        try:
            return handler(args, flags)
        except Exception as exc:  # noqa: BLE001
            return ShellResult(
                stderr=f"{cmd}: unexpected error: {exc}",
                exit_code=1,
            )

    def parse(self, raw: str) -> Tuple[str, List[str], Dict[str, str]]:
        """
        Parse a raw command string.
        Returns (command, positional_args, flags).
        Handles: flags (-la, --all), quotes, redirect (>), pipe (|) — pipe
        runs only first segment (full pipes would need a REPL; we ignore
        the rest gracefully).
        """
        # Strip pipe — handle only first segment
        raw = raw.split("|")[0].strip()

        # Handle redirect: capture destination file but still parse rest
        redirect_dst = None
        if ">" in raw:
            idx = raw.index(">")
            redirect_dst = raw[idx + 1:].strip()
            raw = raw[:idx].strip()

        try:
            tokens = shlex.split(raw)
        except ValueError:
            tokens = raw.split()

        if not tokens:
            return ("", [], {})

        cmd = tokens[0]
        args: List[str] = []
        flags: Dict[str, str] = {}

        i = 1
        while i < len(tokens):
            tok = tokens[i]
            if tok.startswith("--"):
                key = tok[2:]
                if "=" in key:
                    k, v = key.split("=", 1)
                    flags[k] = v
                else:
                    flags[key] = "true"
            elif tok.startswith("-") and len(tok) > 1 and not tok[1:].lstrip("-").isdigit():
                # Short flags like -la, -sh, -r
                for ch in tok[1:]:
                    flags[ch] = "true"
            else:
                args.append(tok)
            i += 1

        if redirect_dst:
            flags["_redirect"] = redirect_dst

        return (cmd, args, flags)

    def resolve_path(self, path: str) -> str:
        """
        Resolve a path relative to self.cwd.
        '.' = cwd, '..' = parent, '~' = /root, absolute = as-is
        """
        if not path or path == ".":
            return self.cwd
        if path == "~":
            return "/root"
        if path.startswith("/"):
            return self._normalise(path)
        if path == "..":
            parts = self.cwd.rstrip("/").rsplit("/", 1)
            return parts[0] if parts[0] else "/"
        # Relative
        base = self.cwd.rstrip("/")
        combined = base + "/" + path
        return self._normalise(combined)

    def tab_complete(self, partial: str) -> List[str]:
        """Return filenames in cwd starting with `partial`."""
        results = []
        for meta in self.tree.get_all_sorted():
            if meta.path.startswith(self.cwd):
                name = meta.filename
                if name.lower().startswith(partial.lower()):
                    results.append(name)
        return sorted(results)

    # ──────────────────────────────────────────────────────────────────────────
    # DIRECTORY HELPERS
    # ──────────────────────────────────────────────────────────────────────────

    def add_dir(self, path: str) -> None:
        self._dirs[self._normalise(path)] = True

    def is_dir(self, path: str) -> bool:
        return self._normalise(path) in self._dirs

    def files_in_dir(self, path: str):
        """Return FileMetadata list for all files in `path` (non-recursive)."""
        norm = self._normalise(path).rstrip("/")
        results = []
        for meta in self.tree.get_all_sorted():
            file_dir = meta.path.rsplit("/", 1)[0] if "/" in meta.path else meta.path
            file_dir = self._normalise(file_dir).rstrip("/")
            if file_dir == norm:
                results.append(meta)
        return results

    # ──────────────────────────────────────────────────────────────────────────
    # INTERNAL
    # ──────────────────────────────────────────────────────────────────────────

    @staticmethod
    def _normalise(path: str) -> str:
        """Resolve '..', strip trailing slash, collapse double slashes."""
        parts = path.replace("\\", "/").split("/")
        stack = []
        for p in parts:
            if p == "" or p == ".":
                continue
            if p == "..":
                if stack:
                    stack.pop()
            else:
                stack.append(p)
        return "/" + "/".join(stack)
