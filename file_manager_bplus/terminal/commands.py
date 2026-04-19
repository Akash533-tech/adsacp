"""
Command implementations for the Virtual Terminal.
Every function takes (shell, args, flags) and returns ShellResult.
CommandRegistry maps command names → handler callables.
"""

from __future__ import annotations

import fnmatch
import json
import re
from datetime import datetime, timedelta
from typing import List, Dict, Callable, TYPE_CHECKING

from file_ops.metadata import FileMetadata
from terminal.shell import ShellResult, VirtualShell

if TYPE_CHECKING:
    pass


# ─────────────────────────────────────────────────────────────────────────────
# Helper: permissions string (simulated)
# ─────────────────────────────────────────────────────────────────────────────
def _perms(meta: FileMetadata) -> str:
    """Return a simulated rwxr-xr-x string."""
    if meta.is_directory:
        return "drwxr-xr-x"
    ext = meta.extension.lower()
    if ext in (".py", ".sh", ".js"):
        return "-rwxr-xr-x"
    return "-rw-r--r--"


def _fmt_date(dt: datetime) -> str:
    return dt.strftime("%b %d %H:%M") if dt else "---"


def _human(n: int) -> str:
    if n < 1024:
        return f"{n}B"
    if n < 1024 ** 2:
        return f"{n / 1024:.1f}K"
    if n < 1024 ** 3:
        return f"{n / 1024 ** 2:.1f}M"
    return f"{n / 1024 ** 3:.2f}G"


# ─────────────────────────────────────────────────────────────────────────────
# COMMAND REGISTRY
# ─────────────────────────────────────────────────────────────────────────────

class CommandRegistry:
    """Maps command strings → handler methods bound to a VirtualShell."""

    def __init__(self, shell: VirtualShell):
        self.shell = shell
        self._map: Dict[str, Callable] = {
            # Navigation
            "pwd":         self._pwd,
            "cd":          self._cd,
            # Listing
            "ls":          self._ls,
            "tree":        self._tree,
            # File ops
            "touch":       self._touch,
            "mkdir":       self._mkdir,
            "cp":          self._cp,
            "mv":          self._mv,
            "rm":          self._rm,
            "cat":         self._cat,
            "echo":        self._echo,
            "chmod":       self._chmod,
            # Search
            "find":        self._find,
            "grep":        self._grep,
            # Information
            "stat":        self._stat,
            "du":          self._du,
            "df":          self._df,
            "wc":          self._wc,
            "head":        self._head,
            "tail":        self._tail,
            "sort":        self._sort,
            "history":     self._history,
            # Compression bridge
            "compress":    self._compress,
            "decompress":  self._decompress,
            "compressdir": self._compressdir,
            # Misc
            "clear":       self._clear,
            "alias":       self._alias,
            "export":      self._export,
            "help":        self._help,
            "exit":        self._exit,
        }

    def get(self, cmd: str) -> Callable | None:
        return self._map.get(cmd)

    # ── NAVIGATION ────────────────────────────────────────────────────────────

    def _pwd(self, args, flags) -> ShellResult:
        return ShellResult(stdout=self.shell.cwd)

    def _cd(self, args, flags) -> ShellResult:
        if not args:
            self.shell.cwd = "/root"
            return ShellResult(stdout="/root")
        target = args[0]
        resolved = self.shell.resolve_path(target)
        if self.shell.is_dir(resolved):
            self.shell.cwd = resolved
            return ShellResult(stdout=f"Changed to {resolved}")
        return ShellResult(stderr=f"cd: {target}: No such directory", exit_code=1)

    # ── LISTING ───────────────────────────────────────────────────────────────

    def _ls(self, args, flags) -> ShellResult:
        target_path = self.shell.resolve_path(args[0]) if args else self.shell.cwd
        files = self.shell.files_in_dir(target_path)

        show_all = "a" in flags
        long_fmt = "l" in flags
        sort_size = "s" in flags
        sort_time = "t" in flags

        if not show_all:
            files = [f for f in files if not f.filename.startswith(".")]

        if sort_size:
            files = sorted(files, key=lambda f: f.size_bytes, reverse=True)
        elif sort_time:
            files = sorted(files, key=lambda f: f.modified_at or datetime.min, reverse=True)
        else:
            files = sorted(files, key=lambda f: f.filename.lower())

        if not files:
            return ShellResult(stdout=f"(empty directory: {target_path})")

        if long_fmt:
            lines = [f"total {sum(f.size_bytes for f in files)}"]
            for f in files:
                lines.append(
                    f"{_perms(f)}  1 user  staff  {f.size_bytes:>10}  "
                    f"{_fmt_date(f.modified_at)}  {f.filename}"
                )
            return ShellResult(stdout="\n".join(lines), highlight_files=[f.filename for f in files])

        # Short format — 4 per row
        names = [f.filename for f in files]
        col_w = max((len(n) for n in names), default=10) + 2
        rows = []
        for i in range(0, len(names), 4):
            rows.append("  ".join(n.ljust(col_w) for n in names[i:i+4]))
        return ShellResult(stdout="\n".join(rows), highlight_files=names)

    def _tree(self, args, flags) -> ShellResult:
        """Draw an ASCII B+ tree structure mirroring the virtual filesystem."""
        lines = ["."]
        # Build { dir: [files] }
        dir_files: Dict[str, List[FileMetadata]] = {}
        for meta in self.shell.tree.get_all_sorted():
            d = meta.path.rsplit("/", 1)[0] if "/" in meta.path else self.shell.cwd
            dir_files.setdefault(d, []).append(meta)

        all_dirs = sorted(set(list(dir_files.keys()) + list(self.shell._dirs.keys())))
        for di, d in enumerate(all_dirs):
            is_last_dir = di == len(all_dirs) - 1
            prefix = "└── " if is_last_dir else "├── "
            lines.append(f"{prefix}📁 {d}/")
            flist = dir_files.get(d, [])
            for fi, f in enumerate(sorted(flist, key=lambda x: x.filename.lower())):
                is_last_f = fi == len(flist) - 1
                bar = "    " if is_last_dir else "│   "
                fp = "└── " if is_last_f else "├── "
                lines.append(f"{bar}{fp}📄 {f.filename} ({f.size_display()})")

        total = self.shell.tree.get_total_records()
        lines.append(f"\n{len(all_dirs)} directories, {total} files")
        return ShellResult(stdout="\n".join(lines))

    # ── FILE OPERATIONS ───────────────────────────────────────────────────────

    def _touch(self, args, flags) -> ShellResult:
        if not args:
            return ShellResult(stderr="touch: missing file operand", exit_code=1)
        created = []
        for name in args:
            ext = ""
            if "." in name:
                ext = "." + name.rsplit(".", 1)[-1]
            meta = FileMetadata(
                filename=name,
                extension=ext,
                size_bytes=0,
                created_at=datetime.now(),
                modified_at=datetime.now(),
                path=self.shell.cwd.rstrip("/") + "/" + name,
                tags=["empty"],
            )
            self.shell.tree.insert(name, meta)
            created.append(name)
        return ShellResult(
            stdout=f"Created: {', '.join(created)}",
            tree_changed=True,
            highlight_files=created,
        )

    def _mkdir(self, args, flags) -> ShellResult:
        if not args:
            return ShellResult(stderr="mkdir: missing operand", exit_code=1)
        for name in args:
            path = self.shell.resolve_path(name)
            self.shell.add_dir(path)
        return ShellResult(stdout=f"Directory created: {args[0]}")

    def _cp(self, args, flags) -> ShellResult:
        if len(args) < 2:
            return ShellResult(stderr="cp: missing operand", exit_code=1)
        src, dst = args[0], args[1]
        meta = self.shell.tree.search(src)
        if meta is None:
            return ShellResult(stderr=f"cp: {src}: No such file", exit_code=1)
        new_meta = FileMetadata(
            filename=dst,
            extension=meta.extension,
            size_bytes=meta.size_bytes,
            created_at=datetime.now(),
            modified_at=datetime.now(),
            path=self.shell.cwd.rstrip("/") + "/" + dst,
            tags=meta.tags[:] + ["copy"],
        )
        self.shell.tree.insert(dst, new_meta)
        return ShellResult(stdout=f"Copied {src} → {dst}", tree_changed=True, highlight_files=[dst])

    def _mv(self, args, flags) -> ShellResult:
        if len(args) < 2:
            return ShellResult(stderr="mv: missing operand", exit_code=1)
        src, dst = args[0], args[1]
        success = self.shell.tree.rename(src, dst)
        if success:
            return ShellResult(stdout=f"Moved {src} → {dst}", tree_changed=True, highlight_files=[dst])
        return ShellResult(stderr=f"mv: {src}: No such file", exit_code=1)

    def _rm(self, args, flags) -> ShellResult:
        if not args:
            return ShellResult(stderr="rm: missing operand", exit_code=1)
        removed = []
        errors = []
        for name in args:
            ok = self.shell.tree.delete(name)
            if ok:
                removed.append(name)
            else:
                errors.append(f"rm: {name}: No such file")
        out = f"Removed: {', '.join(removed)}" if removed else ""
        err = "\n".join(errors)
        return ShellResult(
            stdout=out,
            stderr=err,
            exit_code=0 if not errors else 1,
            tree_changed=bool(removed),
        )

    def _cat(self, args, flags) -> ShellResult:
        if not args:
            return ShellResult(stderr="cat: missing operand", exit_code=1)
        name = args[0]
        meta = self.shell.tree.search(name)
        if meta is None:
            return ShellResult(stderr=f"cat: {name}: No such file", exit_code=1)
        lines = [
            f"=== {meta.filename} ===",
            f"  Path     : {meta.path}",
            f"  Extension: {meta.extension}",
            f"  Size     : {meta.size_display()} ({meta.size_bytes} bytes)",
            f"  Created  : {meta.created_at.strftime('%Y-%m-%d %H:%M:%S') if meta.created_at else '—'}",
            f"  Modified : {meta.modified_at.strftime('%Y-%m-%d %H:%M:%S') if meta.modified_at else '—'} ({meta.age_display()})",
            f"  Tags     : {', '.join(meta.tags) if meta.tags else '(none)'}",
            f"  Type     : {'Directory' if meta.is_directory else 'Regular file'}",
        ]
        return ShellResult(stdout="\n".join(lines), highlight_files=[name])

    def _echo(self, args, flags) -> ShellResult:
        redirect = flags.get("_redirect")
        text = " ".join(args)
        # expand $VAR in text
        for k, v in self.shell.env.items():
            text = text.replace(f"${k}", v)
        if redirect:
            filename = redirect.strip()
            ext = ""
            if "." in filename:
                ext = "." + filename.rsplit(".", 1)[-1]
            meta = FileMetadata(
                filename=filename,
                extension=ext,
                size_bytes=len(text.encode()),
                created_at=datetime.now(),
                modified_at=datetime.now(),
                path=self.shell.cwd.rstrip("/") + "/" + filename,
                tags=["text"],
            )
            self.shell.tree.insert(filename, meta)
            return ShellResult(stdout=f"Written to {filename}", tree_changed=True, highlight_files=[filename])
        return ShellResult(stdout=text)

    def _chmod(self, args, flags) -> ShellResult:
        if len(args) < 2:
            return ShellResult(stderr="chmod: missing operand", exit_code=1)
        octal, filename = args[0], args[1]
        meta = self.shell.tree.search(filename)
        if meta is None:
            return ShellResult(stderr=f"chmod: {filename}: No such file", exit_code=1)
        # Store perm in tags
        meta.tags = [t for t in meta.tags if not t.startswith("perm:")]
        meta.tags.append(f"perm:{octal}")
        return ShellResult(stdout=f"chmod {octal} {filename}: permissions updated")

    # ── SEARCH & FILTER ───────────────────────────────────────────────────────

    def _find(self, args, flags) -> ShellResult:
        # find . -name <pat> | -size +<n>k | -type f|d
        all_files = self.shell.tree.get_all_sorted()
        results = []

        name_pat = flags.get("name")
        size_spec = flags.get("size")
        type_f = flags.get("type")

        for meta in all_files:
            match = True
            if name_pat:
                if not fnmatch.fnmatch(meta.filename.lower(), name_pat.lower()):
                    match = False
            if size_spec and match:
                # e.g. +10k  or  -5k
                m = re.match(r"([+-]?)(\d+)([kmgKMG]?)", size_spec)
                if m:
                    sign, num, unit = m.group(1), int(m.group(2)), m.group(3).lower()
                    mult = {"k": 1024, "m": 1024**2, "g": 1024**3}.get(unit, 1)
                    thresh = num * mult
                    if sign == "+" and not meta.size_bytes > thresh:
                        match = False
                    elif sign == "-" and not meta.size_bytes < thresh:
                        match = False
                    elif sign == "" and meta.size_bytes != thresh:
                        match = False
            if type_f and match:
                if type_f == "f" and meta.is_directory:
                    match = False
                if type_f == "d" and not meta.is_directory:
                    match = False
            if match:
                results.append(meta)

        if not results:
            return ShellResult(stdout="(no matches)")
        lines = [f"./{m.filename}  ({m.size_display()})  {m.path}" for m in results]
        return ShellResult(stdout="\n".join(lines), highlight_files=[m.filename for m in results])

    def _grep(self, args, flags) -> ShellResult:
        if not args:
            return ShellResult(stderr="grep: missing pattern", exit_code=1)
        pattern = args[0].lower()
        all_files = self.shell.tree.get_all_sorted()
        matches = []
        for meta in all_files:
            haystack = " ".join([meta.filename, meta.path, meta.extension] + meta.tags).lower()
            if pattern in haystack:
                tag_str = ", ".join(meta.tags)
                matches.append(f"{meta.filename}: tags=[{tag_str}]  path={meta.path}")
        if not matches:
            return ShellResult(stdout=f"(no files match pattern '{pattern}')")
        return ShellResult(stdout="\n".join(matches))

    # ── INFORMATION ───────────────────────────────────────────────────────────

    def _stat(self, args, flags) -> ShellResult:
        if not args:
            return ShellResult(stderr="stat: missing operand", exit_code=1)
        name = args[0]
        meta = self.shell.tree.search(name)
        if meta is None:
            return ShellResult(stderr=f"stat: {name}: No such file", exit_code=1)
        lines = [
            f"  File: {meta.filename}",
            f"  Size: {meta.size_bytes}  ({meta.size_display()})",
            f"  Type: {'directory' if meta.is_directory else 'regular file'}",
            f"  Ext : {meta.extension or '(none)'}",
            f"  Path: {meta.path}",
            f"Access: {_perms(meta)}",
            f"Modify: {_fmt_date(meta.modified_at)}  ({meta.age_display()})",
            f"Create: {_fmt_date(meta.created_at)}",
            f"  Tags: {', '.join(meta.tags) if meta.tags else '(none)'}",
        ]
        return ShellResult(stdout="\n".join(lines), highlight_files=[name])

    def _du(self, args, flags) -> ShellResult:
        target = self.shell.resolve_path(args[0]) if args else self.shell.cwd
        all_files = self.shell.tree.get_all_sorted()
        total = sum(f.size_bytes for f in all_files if f.path.startswith(target))
        human = "h" in flags or "s" in flags
        if human:
            return ShellResult(stdout=f"{_human(total)}\t{target}")
        return ShellResult(stdout=f"{total // 1024}\t{target}")

    def _df(self, args, flags) -> ShellResult:
        all_files = self.shell.tree.get_all_sorted()
        used = sum(f.size_bytes for f in all_files)
        total_sim = 10 * 1024 ** 3   # simulated 10 GB disk
        free = total_sim - used
        lines = [
            "Filesystem       Size    Used    Avail   Use%  Mounted on",
            f"bplus-vfs       {_human(total_sim):>6}  {_human(used):>6}  {_human(free):>6}  "
            f"{used*100//total_sim}%   /",
        ]
        return ShellResult(stdout="\n".join(lines))

    def _wc(self, args, flags) -> ShellResult:
        if not args:
            return ShellResult(stderr="wc: missing file operand", exit_code=1)
        name = args[0]
        meta = self.shell.tree.search(name)
        if meta is None:
            return ShellResult(stderr=f"wc: {name}: No such file", exit_code=1)
        # Approximate: 1 word ≈ 5 bytes, 1 line ≈ 60 bytes
        words = meta.size_bytes // 5
        lines_est = meta.size_bytes // 60
        chars = meta.size_bytes
        return ShellResult(stdout=f"  {lines_est:>6}  {words:>6}  {chars:>6} {name}")

    def _head(self, args, flags) -> ShellResult:
        n = int(flags.get("n", 5))
        target = self.shell.resolve_path(args[0]) if args else self.shell.cwd
        files = self.shell.files_in_dir(target)
        files = sorted(files, key=lambda f: f.filename.lower())[:n]
        lines = [f"{f.filename}  {f.size_display()}  {_fmt_date(f.modified_at)}" for f in files]
        return ShellResult(stdout="\n".join(lines) if lines else "(empty)", highlight_files=[f.filename for f in files])

    def _tail(self, args, flags) -> ShellResult:
        n = int(flags.get("n", 5))
        target = self.shell.resolve_path(args[0]) if args else self.shell.cwd
        files = self.shell.files_in_dir(target)
        files = sorted(files, key=lambda f: f.filename.lower())[-n:]
        lines = [f"{f.filename}  {f.size_display()}  {_fmt_date(f.modified_at)}" for f in files]
        return ShellResult(stdout="\n".join(lines) if lines else "(empty)", highlight_files=[f.filename for f in files])

    def _sort(self, args, flags) -> ShellResult:
        """Sort all files in cwd alphabetically (default), or by size/time."""
        files = self.shell.files_in_dir(self.shell.cwd)
        if "s" in flags:
            files = sorted(files, key=lambda f: f.size_bytes, reverse=True)
            key_label = "size"
        elif "t" in flags:
            files = sorted(files, key=lambda f: f.modified_at or datetime.min, reverse=True)
            key_label = "modification time"
        else:
            files = sorted(files, key=lambda f: f.filename.lower())
            key_label = "name"
        lines = [f"{f.filename}  {f.size_display()}  {_fmt_date(f.modified_at)}" for f in files]
        header = f"(sorted by {key_label})\n"
        return ShellResult(stdout=header + "\n".join(lines), highlight_files=[f.filename for f in files])

    def _history(self, args, flags) -> ShellResult:
        hist = self.shell.history[-20:]
        lines = [f"  {i+1:3}  {cmd}" for i, cmd in enumerate(hist)]
        return ShellResult(stdout="\n".join(lines) if lines else "(no history)")

    # ── COMPRESSION BRIDGE ─────────────────────────────────────────────────────

    def _compress(self, args, flags) -> ShellResult:
        if not args:
            return ShellResult(stderr="compress: missing filename", exit_code=1)
        name = args[0]
        meta = self.shell.tree.search(name)
        if meta is None:
            return ShellResult(stderr=f"compress: {name}: No such file", exit_code=1)
        try:
            import sys, os
            _here = os.path.dirname(os.path.abspath(__file__))
            parent = os.path.dirname(_here)
            if parent not in sys.path:
                sys.path.insert(0, parent)
            from lzw_compression.lzw import LZWCodec
            codec = LZWCodec()
            text = json.dumps({
                "filename": meta.filename,
                "extension": meta.extension,
                "size_bytes": meta.size_bytes,
                "path": meta.path,
                "tags": meta.tags,
            })
            codes, steps = codec.encode(text)
            stats = codec.get_compression_stats(text, codes)
            return ShellResult(
                stdout=(
                    f"LZW compressed: {name}\n"
                    f"  Original : {stats.original_bytes} bytes\n"
                    f"  Compressed: {stats.compressed_bytes} bytes\n"
                    f"  Ratio    : {stats.ratio:.2f}x  ({stats.space_saved_pct:.1f}% saved)\n"
                    f"  Dict size: {stats.dict_final_size} entries"
                )
            )
        except Exception as e:
            return ShellResult(stderr=f"compress error: {e}", exit_code=1)

    def _decompress(self, args, flags) -> ShellResult:
        if not args:
            return ShellResult(stderr="decompress: missing filename", exit_code=1)
        return ShellResult(stdout=f"decompress: use the 🗜️ Compress tab for full decompression UI for '{args[0]}'")

    def _compressdir(self, args, flags) -> ShellResult:
        target = self.shell.resolve_path(args[0]) if args else self.shell.cwd
        files = self.shell.files_in_dir(target)
        if not files:
            return ShellResult(stdout=f"(no files in {target})")
        lines = [f"Compressing {len(files)} files in {target}:"]
        for f in files:
            lines.append(f"  ✓ {f.filename} — use Compress tab for details")
        return ShellResult(stdout="\n".join(lines))

    # ── MISC ──────────────────────────────────────────────────────────────────

    def _clear(self, args, flags) -> ShellResult:
        return ShellResult(stdout="__CLEAR__")

    def _alias(self, args, flags) -> ShellResult:
        if not args:
            # List all aliases
            if not self.shell.alias:
                return ShellResult(stdout="(no aliases defined)")
            lines = [f"alias {k}='{v}'" for k, v in self.shell.alias.items()]
            return ShellResult(stdout="\n".join(lines))
        # Parse name=cmd
        raw = " ".join(args)
        if "=" in raw:
            name, cmd = raw.split("=", 1)
            cmd = cmd.strip("'\"")
            self.shell.alias[name.strip()] = cmd.strip()
            return ShellResult(stdout=f"Alias set: {name.strip()} → {cmd.strip()}")
        return ShellResult(stderr="alias: use format: alias name='command'", exit_code=1)

    def _export(self, args, flags) -> ShellResult:
        if not args:
            if not self.shell.env:
                return ShellResult(stdout="(no environment variables)")
            lines = [f"export {k}={v}" for k, v in self.shell.env.items()]
            return ShellResult(stdout="\n".join(lines))
        raw = " ".join(args)
        if "=" in raw:
            k, v = raw.split("=", 1)
            self.shell.env[k.strip()] = v.strip()
            return ShellResult(stdout=f"Exported: {k.strip()}={v.strip()}")
        return ShellResult(stderr="export: use format: export KEY=VALUE", exit_code=1)

    def _help(self, args, flags) -> ShellResult:
        if args:
            cmd = args[0]
            details = {
                "ls":    "ls [-la] [-s] [-t] [path]  — list files",
                "cd":    "cd <path>  — change directory (supports .., ~, absolute)",
                "pwd":   "pwd  — print current directory",
                "touch": "touch <file>  — create empty file",
                "mkdir": "mkdir <dir>  — create virtual directory",
                "rm":    "rm [-f] <file>  — delete file from B+ Tree",
                "cp":    "cp <src> <dst>  — copy file",
                "mv":    "mv <src> <dst>  — move/rename file",
                "cat":   "cat <file>  — display file metadata",
                "stat":  "stat <file>  — detailed file information",
                "find":  "find . [-name <pat>] [-size +/-Nk] [-type f|d]",
                "grep":  "grep <pattern> [.]  — search in tags/path/name",
                "du":    "du [-sh] [path]  — disk usage",
                "df":    "df  — simulated disk free/used",
                "wc":    "wc <file>  — estimated word/line/char count",
                "head":  "head [-n N] [path]  — first N files",
                "tail":  "tail [-n N] [path]  — last N files",
                "sort":  "sort [-s|-t]  — sort files in cwd",
                "history":"history  — show last 20 commands",
                "echo":  "echo <text> [> <file>]  — print text or write to file",
                "chmod": "chmod <octal> <file>  — update file permissions tag",
                "tree":  "tree  — ASCII directory + B+ Tree structure",
                "compress":   "compress <file>  — LZW compress metadata",
                "decompress": "decompress <file>  — LZW decompress",
                "compressdir":"compressdir [dir]  — compress all files in dir",
                "alias": "alias [name='cmd']  — create/list aliases",
                "export":"export [KEY=VALUE]  — set/list env variables",
                "clear": "clear  — clear terminal output",
                "exit":  "exit  — reset terminal session",
                "help":  "help [cmd]  — show help",
            }
            if cmd in details:
                return ShellResult(stdout=f"  {details[cmd]}")
            return ShellResult(stderr=f"help: no help for '{cmd}'", exit_code=1)

        # General help
        groups = {
            "Navigation": ["pwd", "cd", "tree"],
            "Listing":    ["ls", "head", "tail", "sort"],
            "File Ops":   ["touch", "mkdir", "cp", "mv", "rm", "cat", "echo", "chmod"],
            "Search":     ["find", "grep"],
            "Info":       ["stat", "du", "df", "wc", "history"],
            "Compression":["compress", "decompress", "compressdir"],
            "Misc":       ["alias", "export", "clear", "exit", "help"],
        }
        lines = ["Available commands (type 'help <cmd>' for details):\n"]
        for group, cmds in groups.items():
            lines.append(f"  {group}:  {', '.join(cmds)}")
        return ShellResult(stdout="\n".join(lines))

    def _exit(self, args, flags) -> ShellResult:
        return ShellResult(stdout="__EXIT__")
