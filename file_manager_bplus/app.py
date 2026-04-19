"""
B+ Tree File System v2 — Streamlit Frontend
=============================================
Extends the original app with:
  - 💻 Virtual Terminal (tab)
  - 🗜️ RLE Compression — educational step-by-step (tab)
  - 📸 File Versioning / Snapshots (tab)
  - 📊 Disk Analytics / Heatmap (tab)
  - 🔧 Tools: Diff, Encrypt, Duplicates, Export/Import (tab)
  - 🏷️ Smart Tag Cloud (sidebar)
  - ↩ Undo / ↪ Redo (sidebar)
"""

import time
import math
import json
import random
import pandas as pd
import streamlit as st
from datetime import datetime, timedelta

# ── Page config MUST be first Streamlit command ─────────────────────────────
st.set_page_config(
    page_title="B+ Tree File Manager",
    layout="wide",
    page_icon="🗂",
    initial_sidebar_state="expanded",
)

# ── Path setup ───────────────────────────────────────────────────────────────
import sys
import os

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

from bplus.bplus_tree import BPlusTree
from bplus.constants import ORDER, MAX_KEYS, MIN_KEYS
from file_ops.metadata import FileMetadata

try:
    from visualizer.tree_viz import render_bplus_tree, render_leaf_chain, get_search_path
    VIZ_AVAILABLE = True
except ImportError:
    VIZ_AVAILABLE = False

try:
    from terminal.shell import VirtualShell
    TERMINAL_AVAILABLE = True
except ImportError:
    TERMINAL_AVAILABLE = False

try:
    from rle_compression.rle_codec import RLECodec, RLEPair
    from rle_compression.content_sim import ContentSimulator
    from rle_compression.rle_viz import RLEVisualizer
    from rle_compression.compressed_store import CompressedStore, CompressedEntry
    from rle_compression.rle_animator import RLEAnimator
    COMPRESS_AVAILABLE = True
except ImportError:
    COMPRESS_AVAILABLE = False

try:
    from versioning.snapshot import SnapshotManager
    VERSIONING_AVAILABLE = True
except ImportError:
    VERSIONING_AVAILABLE = False

try:
    from analytics.heatmap import DiskAnalyzer
    ANALYTICS_AVAILABLE = True
except ImportError:
    ANALYTICS_AVAILABLE = False

try:
    from extras.file_diff import FileDiff
    from extras.encryptor import XOREncryptor
    from extras.duplicate_finder import DuplicateFinder
    from extras.tag_index import TagIndex
    EXTRAS_AVAILABLE = True
except ImportError:
    EXTRAS_AVAILABLE = False

try:
    import plotly.graph_objects as go
    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False

# ── Global CSS — professional design system ───────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&family=JetBrains+Mono:wght@400;500&display=swap');

/* ── Base ── */
html, body, [class*="css"] {
    font-family: 'Inter', -apple-system, sans-serif;
    letter-spacing: -0.01em;
}

/* ── App Background & Sidebar ── */
.stApp { background-color: #0A0A0A; }
[data-testid="stSidebar"] {
    background-color: #0A0A0A;
    border-right: 1px solid rgba(255, 255, 255, 0.05);
}
[data-testid="stSidebar"] .stMarkdown p { color: #888888 !important; font-size: 13px; }
[data-testid="stSidebar"] h1, h2, h3 {
    color: #FAFAFA !important; font-weight: 500; letter-spacing: -0.02em;
}

/* ── Container padding ── */
.main .block-container { padding: 3rem 4rem; max-width: 1200px; }

/* ── Typography ── */
h1 { color: #FFFFFF !important; font-size: 24px !important; font-weight: 600 !important; letter-spacing: -0.03em !important; }
h2 { color: #EAEAEA !important; font-size: 16px !important; font-weight: 500 !important; margin-top: 2rem !important; }
h3 { color: #888888 !important; font-size: 12px !important; font-weight: 500 !important; text-transform: uppercase; letter-spacing: 0.05em !important; }
p, li { color: #A1A1AA !important; font-size: 14px; line-height: 1.6; }

/* ── Tabs (minimal border-bottom style) ── */
[data-testid="stTabs"] [role="tablist"] { border-bottom: 1px solid rgba(255, 255, 255, 0.1); gap: 16px; padding-bottom: 0; }
[data-testid="stTabs"] [role="tab"] {
    color: #888888 !important; font-size: 13px !important; font-weight: 500 !important;
    padding: 8px 4px !important; border-bottom: 2px solid transparent !important;
    background: transparent !important; transition: all 0.2s ease;
}
[data-testid="stTabs"] [role="tab"][aria-selected="true"] {
    color: #EDEDED !important; border-bottom-color: #EDEDED !important;
}
[data-testid="stTabs"] [role="tab"]:hover { color: #EDEDED !important; }

/* ── Inputs ── */
[data-testid="stTextInput"] input, [data-testid="stNumberInput"] input, [data-testid="stSelectbox"] > div {
    background-color: #111111 !important; border: 1px solid rgba(255, 255, 255, 0.1) !important;
    border-radius: 6px !important; color: #EDEDED !important; font-size: 14px !important;
    padding: 10px 12px !important; transition: border-color 0.15s ease;
    box-shadow: 0 1px 2px rgba(0, 0, 0, 0.2) inset !important;
}
[data-testid="stTextInput"] input:focus, [data-testid="stSelectbox"] > div:focus-within {
    border-color: #3b82f6 !important; box-shadow: 0 0 0 1px #3b82f6 inset !important;
}
[data-testid="stTextInput"] label, [data-testid="stSelectbox"] label, [data-testid="stNumberInput"] label {
    color: #888888 !important; font-size: 12px !important; font-weight: 500 !important; margin-bottom: 4px;
}

/* ── Buttons ── */
[data-testid="stButton"] > button {
    background-color: #111111 !important; border: 1px solid rgba(255, 255, 255, 0.1) !important;
    border-radius: 6px !important; color: #EDEDED !important; font-size: 13px !important;
    font-weight: 500 !important; padding: 6px 14px !important;
    box-shadow: 0 1px 2px rgba(0, 0, 0, 0.3) !important; transition: all 0.1s ease !important;
}
[data-testid="stButton"] > button:hover {
    background-color: #1A1A1A !important; border-color: rgba(255, 255, 255, 0.2) !important;
}
[data-testid="stButton"] > button[kind="primary"] {
    background: linear-gradient(180deg, #3b82f6 0%, #2563eb 100%) !important;
    border: 1px solid #1d4ed8 !important; color: #ffffff !important;
    box-shadow: 0 1px 2px rgba(0, 0, 0, 0.5), inset 0 1px 0 rgba(255, 255, 255, 0.1) !important;
}
[data-testid="stButton"] > button[kind="primary"]:hover {
    background: linear-gradient(180deg, #4f8cf6 0%, #3b82f6 100%) !important;
}

/* ── Metrics ── */
[data-testid="stMetricLabel"] { color: #888888 !important; font-size: 11px !important; font-weight: 500 !important; text-transform: uppercase; letter-spacing: 0.05em; }
[data-testid="stMetricValue"] { color: #EDEDED !important; font-weight: 500 !important; font-size: 28px !important; letter-spacing: -0.04em !important; }

/* ── DataFrames & Expanders ── */
[data-testid="stDataFrame"], [data-testid="stExpander"] {
    border: 1px solid rgba(255, 255, 255, 0.08) !important;
    border-radius: 8px !important; background: #0F0F0F !important;
    box-shadow: 0 2px 8px rgba(0,0,0,0.2) !important;
}
[data-testid="stExpander"] summary { color: #A1A1AA !important; font-weight: 500 !important; font-size: 13px !important; padding: 12px 14px !important; }

/* ── Code Blocks / Terminals ── */
pre, code {
    font-family: 'JetBrains Mono', monospace !important; font-size: 12.5px !important;
    background-color: #111111 !important; border: 1px solid rgba(255, 255, 255, 0.05) !important;
    border-radius: 6px !important; color: #A1A1AA !important;
}

/* ── Dividers ── */
hr { border-color: rgba(255, 255, 255, 0.08) !important; margin: 2rem 0 !important; }

/* ── Custom UI Components (Terminal & Section Headers) ── */
.terminal-output {
    background: #0A0A0A; border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 0 0 8px 8px;
    padding: 16px; height: 380px; overflow-y: auto; font-family: 'JetBrains Mono', monospace;
    font-size: 13px; line-height: 1.6; color: #A1A1AA; box-shadow: inset 0 2px 4px rgba(0,0,0,0.5);
}
.section-header {
    color: #EDEDED; font-size: 12px; font-weight: 500; letter-spacing: 0.05em;
    text-transform: uppercase; margin: 24px 0 12px 0; padding-bottom: 6px;
    border-bottom: 1px solid rgba(255, 255, 255, 0.08);
}
.op-card {
    background: #0F0F0F; border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 10px; padding: 24px; margin-bottom: 16px;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
}

/* ── Custom scrollbars ── */
::-webkit-scrollbar { width: 4px; height: 4px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.1); border-radius: 2px; }
::-webkit-scrollbar-thumb:hover { background: rgba(255,255,255,0.2); }
</style>
""", unsafe_allow_html=True)



# ═══════════════════════════════════════════════════════════════════════════════
# DEMO DATA
# ═══════════════════════════════════════════════════════════════════════════════

DEMO_FILES = [
    ("main",       ".py",   4096,      "/root/src/",    ["source", "python"]),
    ("README",     ".md",   2048,      "/root/",        ["docs", "markdown"]),
    ("utils",      ".py",   8192,      "/root/src/",    ["source", "python", "helpers"]),
    ("data",       ".csv",  512000,    "/root/data/",   ["dataset", "csv"]),
    ("report",     ".pdf",  2097152,   "/root/docs/",   ["report", "pdf"]),
    ("image",      ".jpg",  1048576,   "/root/assets/", ["media", "image"]),
    ("config",     ".txt",  1024,      "/root/",        ["config"]),
    ("test_main",  ".py",   3072,      "/root/tests/",  ["tests", "python"]),
    ("output",     ".mp4",  52428800,  "/root/media/",  ["media", "video"]),
    ("notes",      ".txt",  512,       "/root/docs/",   ["notes", "text"]),
    ("schema",     ".sql",  6144,      "/root/db/",     ["database", "sql"]),
    ("backup",     ".zip",  10485760,  "/root/",        ["backup", "archive"]),
    ("index",      ".html", 4096,      "/root/web/",    ["web", "frontend"]),
    ("app",        ".js",   8192,      "/root/web/",    ["web", "javascript"]),
    ("style",      ".css",  3072,      "/root/web/",    ["web", "styles"]),
]


def build_demo_tree() -> BPlusTree:
    tree = BPlusTree()
    for base, ext, size, path, tags in DEMO_FILES:
        filename = base + ext
        meta = FileMetadata(
            filename=filename,
            extension=ext,
            size_bytes=random.randint(int(size * 0.7), int(size * 1.3)),
            created_at=datetime.now() - timedelta(days=random.randint(10, 365)),
            modified_at=datetime.now() - timedelta(days=random.randint(0, 30)),
            path=path + filename,
            tags=tags,
        )
        tree.insert(filename, meta)
    return tree


# ═══════════════════════════════════════════════════════════════════════════════
# SESSION STATE INITIALIZATION
# ═══════════════════════════════════════════════════════════════════════════════

def _init_state():
    if "tree" not in st.session_state:
        st.session_state.tree = build_demo_tree()
    if "highlight_keys" not in st.session_state:
        st.session_state.highlight_keys = []
    if "highlight_path" not in st.session_state:
        st.session_state.highlight_path = []
    if "last_op" not in st.session_state:
        st.session_state.last_op = ""
    if "last_op_result" not in st.session_state:
        st.session_state.last_op_result = ""
    if "split_nodes" not in st.session_state:
        st.session_state.split_nodes = []
    if "merge_nodes" not in st.session_state:
        st.session_state.merge_nodes = []
    if "animating" not in st.session_state:
        st.session_state.animating = False
    if "anim_index" not in st.session_state:
        st.session_state.anim_index = 0
    # Terminal
    if "terminal_output" not in st.session_state:
        st.session_state.terminal_output = []
    if "shell" not in st.session_state and TERMINAL_AVAILABLE:
        st.session_state.shell = VirtualShell(st.session_state.tree)
    # Compression (RLE)
    if "compress_store" not in st.session_state:
        st.session_state.compress_store = CompressedStore() if COMPRESS_AVAILABLE else None
    if "rle_step_idx" not in st.session_state:
        st.session_state.rle_step_idx = 0
    # Versioning
    if "snap_mgr" not in st.session_state and VERSIONING_AVAILABLE:
        st.session_state.snap_mgr = SnapshotManager()
    # Tag index
    if "tag_index" not in st.session_state and EXTRAS_AVAILABLE:
        ti = TagIndex()
        ti.rebuild_from_tree(st.session_state.tree)
        st.session_state.tag_index = ti
    # Encryption store
    if "encrypted_store" not in st.session_state:
        st.session_state.encrypted_store = {}
    # Search result persistence (so inline tree shows without rerun)
    if "last_search_result" not in st.session_state:
        st.session_state.last_search_result = None
    if "last_search_query" not in st.session_state:
        st.session_state.last_search_query = ""
    if "last_search_path" not in st.session_state:
        st.session_state.last_search_path = []


_init_state()

tree: BPlusTree = st.session_state.tree

# Keep shell synced to current tree
if TERMINAL_AVAILABLE and "shell" in st.session_state:
    st.session_state.shell.tree = tree


# ═══════════════════════════════════════════════════════════════════════════════
# SIDEBAR
# ═══════════════════════════════════════════════════════════════════════════════

with st.sidebar:
    st.markdown("""<div style="font-size:15px;font-weight:600;color:#e2e8f0;
    letter-spacing:-0.02em;padding:4px 0 2px 0">B+ Tree File Manager</div>
    <div style="font-size:11px;color:#5a6175;margin-top:2px;font-family:'JetBrains Mono',monospace">
    order={ORDER} &middot; max={MAX_KEYS} &middot; min={MIN_KEYS}</div>""".format(ORDER=ORDER,MAX_KEYS=MAX_KEYS,MIN_KEYS=MIN_KEYS), unsafe_allow_html=True)
    st.markdown("---")

    # ── Undo / Redo ─────────────────────────────────────────────────────────
    if VERSIONING_AVAILABLE and "snap_mgr" in st.session_state:
        snap_mgr: SnapshotManager = st.session_state.snap_mgr
        col_u, col_r = st.columns(2)
        if col_u.button("↩ Undo", use_container_width=True):
            restored = snap_mgr.undo(tree)
            if restored:
                st.session_state.tree = restored
                if TERMINAL_AVAILABLE and "shell" in st.session_state:
                    st.session_state.shell.tree = restored
                st.toast("↩ Undone!", icon="↩")
                st.rerun()
            else:
                st.toast("Nothing to undo", icon="⚠️")
        if col_r.button("↪ Redo", use_container_width=True):
            restored = snap_mgr.redo(tree)
            if restored:
                st.session_state.tree = restored
                if TERMINAL_AVAILABLE and "shell" in st.session_state:
                    st.session_state.shell.tree = restored
                st.toast("↪ Redone!", icon="↪")
                st.rerun()
            else:
                st.toast("Nothing to redo", icon="⚠️")
        st.markdown("---")

    # ── Stats dashboard ──────────────────────────────────────────────────────
    col1, col2 = st.columns(2)
    col1.metric("📁 Files",    tree.get_total_records())
    col2.metric("📐 Height",   tree.get_height())
    col1.metric("🔵 Internal", tree.get_internal_node_count())
    col2.metric("🟢 Leaves",   tree.get_leaf_count())

    fill = tree.get_fill_factor()
    st.metric("Fill Factor", f"{fill:.1%}")
    st.progress(min(1.0, fill))
    st.caption(f"Min key: `{tree.get_min_key() or '—'}`   Max key: `{tree.get_max_key() or '—'}`")
    st.markdown("---")

    # ── Operation radio ──────────────────────────────────────────────────────
    operation = st.radio(
        "**Operation**",
        ["➕ Insert", "🔍 Search", "🗑️ Delete", "✏️ Rename",
         "🔎 Prefix Search", "📅 Range Query", "📊 All Files"],
        key="operation_radio",
    )
    st.markdown("---")

    # ── Tag Cloud ────────────────────────────────────────────────────────────
    if EXTRAS_AVAILABLE and "tag_index" in st.session_state:
        tag_index: TagIndex = st.session_state.tag_index
        tag_counts = tag_index.get_tag_counts()
        if tag_counts:
            st.markdown("**🏷️ Tag Cloud** *(click to highlight files)*")
            max_count = max(tag_counts.values(), default=1)
            for tag, count in list(tag_counts.items())[:12]:
                font_size = min(18, 10 + int(count * 3))
                if st.button(
                    f"{tag} ({count})",
                    key=f"tag_btn_{tag}",
                    help=f"Click to highlight files tagged '{tag}'",
                ):
                    results = tag_index.search_tags(tag)
                    st.session_state.highlight_keys = results
                    st.rerun()
            st.markdown("---")

    # ── Control buttons ──────────────────────────────────────────────────────
    if st.button("🔄 Reset to Demo Data", use_container_width=True):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()

    if st.button("🗑️ Clear All Files", use_container_width=True):
        st.session_state.tree = BPlusTree()
        st.session_state.highlight_keys = []
        st.session_state.highlight_path = []
        st.session_state.last_search_result = None
        st.session_state.last_search_query  = ""
        st.session_state.last_search_path   = []
        if EXTRAS_AVAILABLE and "tag_index" in st.session_state:
            st.session_state.tag_index = TagIndex()
        st.rerun()

    st.markdown("---")

    # ── Explainer ────────────────────────────────────────────────────────────
    with st.expander("📚 How B+ Tree Works"):
        st.markdown("""
**B+ Tree vs Other Structures:**

| Feature | BST | B-Tree | B+ Tree |
|---|---|---|---|
| Data location | any node | any node | **leaves only** |
| Range queries | O(n) | O(n) | **O(log n+k)** |
| Leaf linked list | ✗ | ✗ | **✓** |
| Used in | — | MongoDB | **MySQL, Postgres** |

**Split on Insert:**
Node overflows → split into 2 → push median key up → tree stays balanced.

**Merge on Delete:**
Node underflows → try borrow from sibling first.
If can't → merge with sibling → remove separator from parent.
        """)


# ═══════════════════════════════════════════════════════════════════════════════
# ANIMATION DRIVER
# ═══════════════════════════════════════════════════════════════════════════════

if st.session_state.animating:
    idx = st.session_state.anim_index
    if idx < len(DEMO_FILES):
        base, ext, size, path, tags = DEMO_FILES[idx]
        fname = base + ext
        meta = FileMetadata(
            filename=fname, extension=ext, size_bytes=size,
            created_at=datetime.now() - timedelta(days=random.randint(1, 30)),
            modified_at=datetime.now(),
            path=path + fname, tags=tags,
        )
        st.session_state.tree.insert(fname, meta)
        st.session_state.highlight_keys = [fname]
        st.session_state.anim_index += 1
    else:
        st.session_state.animating = False
        st.session_state.highlight_keys = []
    tree = st.session_state.tree


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN PAGE HEADER
# ═══════════════════════════════════════════════════════════════════════════════

st.markdown("""
<div style="display:flex;align-items:baseline;gap:10px;margin-bottom:2px">
  <span style="font-size:22px;font-weight:700;color:#e2e8f0;letter-spacing:-0.03em">B+ Tree File Manager</span>
  <span style="font-size:11px;font-weight:500;color:#3b82f6;background:#1d2a4a;padding:2px 8px;border-radius:4px;letter-spacing:0.02em">v2</span>
</div>
""", unsafe_allow_html=True)
if st.session_state.animating:
    idx = st.session_state.anim_index
    st.caption(f"Building tree — inserting file {idx} of {len(DEMO_FILES)}")
else:
    st.caption("Insert, search, delete, and visualize files with terminal, RLE compression, versioning, analytics and diff tools")


# ═══════════════════════════════════════════════════════════════════════════════
# OPERATION PANEL
# ═══════════════════════════════════════════════════════════════════════════════

st.markdown('<div class="op-card">', unsafe_allow_html=True)

if operation == "➕ Insert":
    st.markdown('<div class="section-header">Insert New File</div>', unsafe_allow_html=True)
    col1, col2, col3 = st.columns([3, 2, 2])
    with col1:
        filename_base = st.text_input("Filename (without extension)", placeholder="e.g. report_2024", key="ins_fname")
    with col2:
        ext = st.selectbox("Extension",
            ['.py', '.txt', '.pdf', '.jpg', '.png', '.mp4', '.csv', '.sql', '.zip', '.html', '.js', '.json', '.md', '.css'],
            key="ins_ext")
    with col3:
        size_kb = st.slider("Size (KB)", 1, 102400, 4, key="ins_size")
    col4, col5 = st.columns(2)
    with col4:
        path = st.text_input("Virtual path", value="/root/", key="ins_path")
    with col5:
        tags_raw = st.text_input("Tags (comma-separated)", value="", key="ins_tags")

    if st.button("Insert File 📥", type="primary", key="btn_insert"):
        if filename_base.strip():
            fname = filename_base.strip() + ext
            tags = [t.strip() for t in tags_raw.split(",") if t.strip()]
            meta = FileMetadata(
                filename=fname, extension=ext,
                size_bytes=size_kb * 1024,
                created_at=datetime.now(), modified_at=datetime.now(),
                path=path.rstrip("/") + "/" + fname,
                tags=tags or ["user-file"],
            )
            # Snapshot before insert
            if VERSIONING_AVAILABLE and "snap_mgr" in st.session_state:
                st.session_state.snap_mgr.take_snapshot(tree, f"Before insert {fname}", "insert")

            prev_log_len = len(tree.operation_log)
            tree.insert(fname, meta)
            st.session_state.highlight_keys = [fname]
            st.session_state.highlight_path = []

            # Update tag index
            if EXTRAS_AVAILABLE and "tag_index" in st.session_state:
                st.session_state.tag_index.add_file(fname, meta.tags)

            if len(tree.operation_log) > prev_log_len:
                last_log = tree.operation_log[-1]
                if last_log["result"] == "DUPLICATE_SKIPPED":
                    st.warning(f"⚠️ File '{fname}' already exists.")
                else:
                    st.success(f"✅ Inserted `{fname}`")
                    if last_log.get("split_occurred"):
                        st.warning("⚡ Node split occurred!")
            st.rerun()
        else:
            st.error("❌ Please enter a filename.")

elif operation == "🔍 Search":
    st.markdown('<div class="section-header">Search for a File</div>', unsafe_allow_html=True)
    query = st.text_input("Exact filename", placeholder="e.g. main.py", key="srch_query")
    if st.button("Search 🔍", type="primary", key="btn_search"):
        if query.strip():
            path_nodes = get_search_path(tree, query.strip()) if VIZ_AVAILABLE else []
            result = tree.search(query.strip())
            st.session_state.highlight_path = path_nodes
            st.session_state.highlight_keys = [query.strip()] if result else []
            st.session_state.last_search_result = result
            st.session_state.last_search_query  = query.strip()
            st.session_state.last_search_path   = path_nodes
        else:
            st.warning("Please enter a filename.")

    # ── Display search results (persists without rerun) ───────────────────────
    if st.session_state.get("last_search_query"):
        q      = st.session_state.last_search_query
        result = st.session_state.get("last_search_result")
        path_nodes = st.session_state.get("last_search_path", [])

        if result:
            st.success(f"✅ Found: `{result.filename}`")

            # File details
            with st.expander("📄 File Details", expanded=True):
                c1, c2 = st.columns(2)
                c1.write(f"**Path:** `{result.path}`")
                c1.write(f"**Size:** {result.size_display()}")
                c1.write(f"**Extension:** `{result.extension}`")
                c2.write(f"**Created:** {result.created_at.strftime('%Y-%m-%d %H:%M')}")
                c2.write(f"**Modified:** {result.age_display()}")
                c2.write(f"**Tags:** {', '.join(result.tags) if result.tags else '—'}")

            if path_nodes:
                st.info(
                    f"🔍 Traversed **{len(path_nodes)} node(s)** — "
                    f"tree height = **{tree.get_height()}**"
                )

            # ── Inline tree with highlighted leaf ─────────────────────────────
            if VIZ_AVAILABLE:
                st.markdown(
                    "<div style='background:#1a2e1a;border:1px solid #4caf50;"
                    "border-radius:8px;padding:8px 14px;margin:8px 0;"
                    "font-size:12px;color:#a8d5a2;font-family:monospace;'>"
                    "🌲 Leaf node highlighted below — gold border = matched node, "
                    "green = already-visited, blue = current run</div>",
                    unsafe_allow_html=True,
                )
                try:
                    dot_inline = render_bplus_tree(
                        tree,
                        highlight_keys=st.session_state.highlight_keys,
                        highlight_path=path_nodes,
                    )
                    st.graphviz_chart(dot_inline.source, use_container_width=True)
                except Exception as _viz_e:
                    st.warning(f"Tree preview unavailable: {_viz_e}")

                # Traverse path breakdown
                with st.expander("🧭 Traversal path step-by-step"):
                    for step_i, node in enumerate(path_nodes):
                        node_type = "🍃 Leaf" if node.is_leaf else "🔵 Internal"
                        is_hit    = node.is_leaf and q.lower() in [k.lower() for k in node.keys]
                        badge     = " ← **FOUND HERE** ✅" if is_hit else ""
                        st.markdown(
                            f"**Step {step_i + 1}:** {node_type} — "
                            f"keys: `{node.keys}`{badge}"
                        )
        else:
            st.error(f"❌ `{q}` not found in the tree.")
            # Still show the tree (no highlight — nothing matched)
            if VIZ_AVAILABLE and tree.root:
                with st.expander("🌲 Tree (no match highlighted)"):
                    try:
                        dot_empty = render_bplus_tree(tree)
                        st.graphviz_chart(dot_empty.source, use_container_width=True)
                    except Exception:
                        pass

elif operation == "🗑️ Delete":
    st.markdown('<div class="section-header">Delete a File</div>', unsafe_allow_html=True)
    all_sorted = tree.get_all_sorted()
    existing_files = [m.filename for m in all_sorted]
    if not existing_files:
        st.warning("No files in the tree.")
    else:
        target = st.selectbox("Select file to delete", existing_files, key="del_target")
        c1, c2 = st.columns([1, 4])
        confirm = c1.checkbox("Confirm deletion", key="del_confirm")
        if c2.button("Delete File 🗑️", disabled=not confirm, type="primary", key="btn_delete"):
            # Snapshot before delete
            if VERSIONING_AVAILABLE and "snap_mgr" in st.session_state:
                st.session_state.snap_mgr.take_snapshot(tree, f"Before delete {target}", "delete")
            success = tree.delete(target)
            # Update tag index
            if EXTRAS_AVAILABLE and "tag_index" in st.session_state:
                st.session_state.tag_index.remove_file(target)
            st.session_state.highlight_keys = []
            st.session_state.highlight_path = []
            if success:
                st.success(f"✅ Deleted `{target}`")
                if tree.operation_log and tree.operation_log[-1].get("merge_occurred"):
                    st.warning("🔄 Node merge occurred!")
            else:
                st.error(f"❌ `{target}` not found.")
            st.rerun()

elif operation == "✏️ Rename":
    st.markdown('<div class="section-header">Rename a File</div>', unsafe_allow_html=True)
    all_sorted = tree.get_all_sorted()
    existing_files = [m.filename for m in all_sorted]
    if not existing_files:
        st.warning("No files in the tree.")
    else:
        c1, c2 = st.columns(2)
        with c1:
            old_name = st.selectbox("File to rename", existing_files, key="ren_old")
        with c2:
            new_base = st.text_input("New filename (without extension)", key="ren_new")
        if st.button("Rename ✏️", type="primary", key="btn_rename"):
            if new_base.strip():
                ext_part = ""
                if "." in old_name:
                    ext_part = "." + old_name.split(".")[-1]
                new_full = new_base.strip() + ext_part
                if VERSIONING_AVAILABLE and "snap_mgr" in st.session_state:
                    st.session_state.snap_mgr.take_snapshot(tree, f"Before rename {old_name}", "rename")
                success = tree.rename(old_name, new_full)
                if success:
                    if EXTRAS_AVAILABLE and "tag_index" in st.session_state:
                        st.session_state.tag_index.remove_file(old_name)
                        meta = tree.search(new_full)
                        if meta:
                            st.session_state.tag_index.add_file(new_full, meta.tags)
                    st.success(f"✅ Renamed `{old_name}` → `{new_full}`")
                    st.session_state.highlight_keys = [new_full]
                else:
                    st.error(f"❌ Could not rename `{old_name}`.")
                st.rerun()
            else:
                st.error("❌ Please enter a new filename.")

elif operation == "🔎 Prefix Search":
    st.markdown('<div class="section-header">Prefix Search</div>', unsafe_allow_html=True)
    prefix = st.text_input("Filename prefix", placeholder="e.g. test, report", key="pfx_query")
    if st.button("Search by Prefix 🔎", type="primary", key="btn_prefix"):
        if prefix.strip():
            results = tree.search_prefix(prefix.strip())
            if results:
                st.success(f"✅ Found **{len(results)}** file(s)")
                df = pd.DataFrame([{
                    "Filename": r.filename, "Type": r.ext_icon(),
                    "Size": r.size_display(), "Path": r.path,
                    "Modified": r.age_display(), "Tags": ", ".join(r.tags),
                } for r in results])
                st.dataframe(df, use_container_width=True, hide_index=True)
                st.session_state.highlight_keys = [r.filename for r in results]
            else:
                st.warning(f"No files found with prefix `{prefix.strip()}`")
                st.session_state.highlight_keys = []
            st.rerun()

elif operation == "📅 Range Query":
    st.markdown('<div class="section-header">Range Query</div>', unsafe_allow_html=True)
    st.info("🚀 B+ Tree advantage: O(log n + k) range queries via leaf linked list!")
    all_sorted = tree.get_all_sorted()
    all_filenames = [m.filename for m in all_sorted]
    if len(all_filenames) < 2:
        st.warning("Need at least 2 files.")
    else:
        c1, c2 = st.columns(2)
        start_key = c1.selectbox("Start (inclusive)", all_filenames, index=0, key="rng_start")
        end_key = c2.selectbox("End (inclusive)", all_filenames, index=len(all_filenames)-1, key="rng_end")
        if st.button("Run Range Query 📅", type="primary", key="btn_range"):
            results = tree.search_range(start_key, end_key)
            st.success(f"✅ Found **{len(results)}** files in range")
            if results:
                df = pd.DataFrame([{
                    "Filename": r.filename, "Type": r.ext_icon(),
                    "Size": r.size_display(), "Path": r.path,
                } for r in results])
                st.dataframe(df, use_container_width=True, hide_index=True)
            st.session_state.highlight_keys = [r.filename for r in results]
            st.rerun()

elif operation == "📊 All Files":
    st.markdown('<div class="section-header">All Files (Sorted)</div>', unsafe_allow_html=True)
    all_files = tree.get_all_sorted()
    st.caption(f"**{len(all_files)}** files — sorted via leaf linked-list traversal O(n)")
    if all_files:
        df = pd.DataFrame([{
            "Filename": m.filename, "Type": m.ext_icon(),
            "Size": m.size_display(), "Path": m.path,
            "Modified": m.age_display(), "Tags": ", ".join(m.tags),
        } for m in all_files])
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.info("No files in the tree.")

st.markdown('</div>', unsafe_allow_html=True)
st.markdown("---")


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN TABS
# ═══════════════════════════════════════════════════════════════════════════════

tab_tree, tab_terminal, tab_compress, tab_snapshots, tab_analytics, tab_tools = st.tabs([
    "Tree",
    "Terminal",
    "Compression",
    "Snapshots",
    "Analytics",
    "Tools",
])


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 1: TREE VISUALIZATION (original 4 sub-tabs)
# ═══════════════════════════════════════════════════════════════════════════════

with tab_tree:
    if st.session_state.animating:
        idx = st.session_state.anim_index
        total = len(DEMO_FILES)
        last_file = DEMO_FILES[idx - 1][0] + DEMO_FILES[idx - 1][1] if idx > 0 else ""
        st.markdown(
            f"""<div style="background:#111318;border:1px solid #252836;border-radius:6px;
                        padding:10px 16px;margin-bottom:10px;display:flex;align-items:center;gap:12px">
              <div style="width:6px;height:6px;border-radius:50%;background:#3b82f6;flex-shrink:0"></div>
              <span style="color:#6b7280;font-size:12px;font-weight:500;">Building tree</span>
              <span style="color:#3b82f6;font-size:12px;">file {idx} of {total}</span>
              <code style="color:#9ca3af;font-size:11px;">{last_file}</code>
            </div>""",
            unsafe_allow_html=True,
        )
        st.progress(idx / total)

    viz_tab1, viz_tab2, viz_tab3, viz_tab4 = st.tabs([
        "Full Tree", "Leaf Chain", "Search Path", "Statistics"
    ])

    with viz_tab1:
        st.subheader("Full B+ Tree")
        if not VIZ_AVAILABLE:
            st.error("❌ `graphviz` not installed.")
        else:
            try:
                dot = render_bplus_tree(
                    tree,
                    highlight_keys=st.session_state.highlight_keys,
                    highlight_path=st.session_state.highlight_path,
                    split_nodes=st.session_state.split_nodes,
                    merge_nodes=st.session_state.merge_nodes,
                )
                st.graphviz_chart(dot.source, use_container_width=True)
            except Exception as e:
                st.error(f"⚠️ Visualization error: {e}")
                st.info("Ensure Graphviz binary is installed. macOS: `brew install graphviz`")

        all_files = tree.get_all_sorted()
        if all_files:
            st.markdown("**In-order leaf traversal:**")
            chips = '<div class="chip-row">' + "".join(
                f'<span class="chip">{f.filename}</span>' for f in all_files
            ) + "</div>"
            st.markdown(chips, unsafe_allow_html=True)

    with viz_tab2:
        st.subheader("Leaf Node Linked List")
        if VIZ_AVAILABLE:
            try:
                st.graphviz_chart(render_leaf_chain(tree).source, use_container_width=True)
            except Exception as e:
                st.error(f"⚠️ {e}")
        leaves = tree.get_all_leaves()
        for i, leaf in enumerate(leaves):
            with st.expander(f"Leaf {i+1} — keys: {leaf.keys}"):
                for key, val in zip(leaf.keys, leaf.values):
                    cols = st.columns([3, 2, 3, 2])
                    cols[0].write(f"`{key}`")
                    cols[1].write(val.size_display())
                    cols[2].write(f"`{val.path}`")
                    cols[3].write(val.age_display())

    with viz_tab3:
        st.subheader("Last Search Path")
        if st.session_state.get("highlight_path"):
            path_nodes = st.session_state.highlight_path
            st.info(f"Traversed **{len(path_nodes)} node(s)** — height = {tree.get_height()}")
            if VIZ_AVAILABLE:
                try:
                    st.graphviz_chart(
                        render_bplus_tree(tree, highlight_path=path_nodes).source,
                        use_container_width=True,
                    )
                except Exception as e:
                    st.error(f"Visualization error: {e}")
            for step, node in enumerate(path_nodes):
                node_type = "🍃 Leaf" if node.is_leaf else "🔵 Internal"
                st.markdown(f"**Step {step+1}:** {node_type} — keys: `{node.keys}`")
        else:
            st.info("Run a **🔍 Search** to see traversal path.")

    with viz_tab4:
        st.subheader("Tree Statistics")
        c1, c2, c3 = st.columns(3)
        c1.metric("Total Files", tree.total_records)
        c2.metric("Tree Height", tree.get_height())
        c3.metric("Fill Factor", f"{tree.get_fill_factor():.1%}")
        c1.metric("Internal Nodes", tree.get_internal_node_count())
        c2.metric("Leaf Nodes", tree.get_leaf_count())
        c3.metric("Total Nodes", tree.get_node_count())
        c1.metric("Min File", tree.get_min_key() or "—")
        c2.metric("Max File", tree.get_max_key() or "—")
        st.markdown("---")
        n = max(tree.total_records, 1)
        h = tree.get_height()
        st.markdown(f"**Complexity Comparison for n = {n} files:**")
        st.markdown(f"""
| Operation | Unsorted Array | BST (avg) | B+ Tree (ORDER={ORDER}) |
|:---|:---:|:---:|:---:|
| Search | O(n) = {n} | O(log n) ≈ {int(math.log2(n)+1)} | O(log_{ORDER} n) ≈ {h} |
| Insert | O(1) | O(log n) ≈ {int(math.log2(n)+1)} | O(log n) ≈ {h} |
| Delete | O(n) = {n} | O(log n) ≈ {int(math.log2(n)+1)} | O(log n) ≈ {h} |
| Range query (k results) | O(n) = {n} | O(n) = {n} | **O(log n + k)** |
| Sorted traversal | O(n log n) | O(n) | **O(n) via linked list** |
        """)
        st.markdown("---")
        for lvl_idx, lvl_nodes in enumerate(tree.get_level_order()):
            node_type = "Leaf" if lvl_nodes[0].is_leaf else "Internal"
            total_keys = sum(len(nd.keys) for nd in lvl_nodes)
            st.markdown(f"- **Level {lvl_idx}** ({node_type}): {len(lvl_nodes)} node(s), {total_keys} key(s)")

    if st.session_state.animating:
        time.sleep(0.55)
        st.rerun()

    # Animate build sidebar button (re-placed here for correct scope)
    with st.sidebar:
        st.markdown("---")
        if st.session_state.animating:
            if st.button("⏹ Stop Animation", use_container_width=True, key="btn_stop", type="primary"):
                st.session_state.animating = False
                st.session_state.highlight_keys = []
                st.rerun()
            idx = st.session_state.anim_index
            st.caption(f"Step {idx} / {len(DEMO_FILES)}")
            st.progress(idx / len(DEMO_FILES))
        else:
            if st.button("🎬 Animate Build", use_container_width=True, key="btn_animate"):
                st.session_state.tree = BPlusTree()
                st.session_state.highlight_keys = []
                st.session_state.highlight_path = []
                st.session_state.split_nodes = []
                st.session_state.merge_nodes = []
                st.session_state.anim_index = 0
                st.session_state.animating = True
                st.rerun()


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 2: VIRTUAL TERMINAL
# ═══════════════════════════════════════════════════════════════════════════════

with tab_terminal:
    if not TERMINAL_AVAILABLE:
        st.error("❌ Terminal module not available. Check terminal/shell.py import.")
    else:
        shell: VirtualShell = st.session_state.shell
        cwd = shell.cwd

        # ── Terminal header bar ──────────────────────────────────────────────
        st.markdown(f"""
<div style="background:#1a1f2e;border-radius:8px 8px 0 0;padding:8px 16px;
            display:flex;align-items:center;gap:8px;border:1px solid #2a3550;border-bottom:none;">
  <div style="width:12px;height:12px;border-radius:50%;background:#ef4444"></div>
  <div style="width:12px;height:12px;border-radius:50%;background:#f59e0b"></div>
  <div style="width:12px;height:12px;border-radius:50%;background:#22c55e"></div>
  <span style="color:#6b7db3;font-size:12px;margin-left:8px;font-family:monospace">
    bplus-shell — {cwd}
  </span>
</div>
""", unsafe_allow_html=True)

        # ── Output area ──────────────────────────────────────────────────────
        terminal_output = st.session_state.terminal_output

        def _render_line(text: str) -> str:
            return text.replace("\n", "<br/>").replace(" ", "&nbsp;")

        output_html_parts = []
        for cmd_str, res in terminal_output[-50:]:
            prompt_color = "#ef4444" if res.exit_code != 0 else "#4a90d9"
            if res.stdout == "__CLEAR__":
                output_html_parts = []
                continue
            output_html_parts.append(f"""
<div style="margin-bottom:8px;">
  <div style="font-family:monospace;font-size:13px;">
    <span style="color:#4a90d9">user@bplus</span>:<span style="color:#f59e0b">{cwd}</span><span style="color:#e8f0fe">$ {_render_line(cmd_str)}</span>
  </div>
  {"" if not res.stdout or res.stdout == "__CLEAR__" else
   f'<div style="color:#a8d5a2;font-family:monospace;font-size:12px;line-height:1.6;white-space:pre-wrap">{_render_line(res.stdout)}</div>'}
  {"" if not res.stderr else
   f'<div style="color:#ef4444;font-family:monospace;font-size:12px">{_render_line(res.stderr)}</div>'}
</div>
""")

        full_output = "\n".join(output_html_parts)
        st.markdown(f"""
<div style="background:#0a0d14;padding:16px;border-radius:0;height:380px;overflow-y:auto;
            border:1px solid #2a3550;border-top:none;font-family:monospace;">
{full_output if full_output else
 '<span style="color:#4a5568;font-size:12px;">Type a command below and press Run ▶</span>'}
</div>
""", unsafe_allow_html=True)

        # ── Input row ────────────────────────────────────────────────────────
        # We use a pending_cmd pattern: store the command in session_state
        # before rerun so it survives the widget reset.
        if "pending_terminal_cmd" not in st.session_state:
            st.session_state.pending_terminal_cmd = ""

        def _submit_command(raw: str):
            """Execute raw command and append result to terminal_output."""
            raw = raw.strip()
            if not raw:
                return
            if raw == "exit":
                st.session_state.terminal_output = []
                st.session_state.shell.history = []
                return
            result = shell.execute(raw)
            if result.stdout == "__CLEAR__":
                st.session_state.terminal_output = []
            else:
                st.session_state.terminal_output.append((raw, result))
                if result.tree_changed:
                    if EXTRAS_AVAILABLE and "tag_index" in st.session_state:
                        st.session_state.tag_index.rebuild_from_tree(
                            st.session_state.tree
                        )
                if result.highlight_files:
                    st.session_state.highlight_keys = result.highlight_files

        # Check for a pending command queued from a previous interaction
        if st.session_state.pending_terminal_cmd:
            _submit_command(st.session_state.pending_terminal_cmd)
            st.session_state.pending_terminal_cmd = ""

        col_prompt, col_input, col_run = st.columns([2, 8, 2])
        col_prompt.markdown(
            f'<div style="padding-top:28px;color:#4a90d9;font-family:monospace;font-size:13px">'
            f'user@bplus:{cwd}$</div>', unsafe_allow_html=True
        )

        def _on_enter():
            """Called when user presses Enter in the text_input."""
            val = st.session_state.get("terminal_input", "").strip()
            if val:
                st.session_state.pending_terminal_cmd = val

        cmd_input = col_input.text_input(
            "Command",
            label_visibility="collapsed",
            placeholder="type a command and press Enter or click Run ▶",
            key="terminal_input",
            on_change=_on_enter,
        )
        if col_run.button("Run ▶", key="terminal_run"):
            val = st.session_state.get("terminal_input", "").strip()
            if val:
                st.session_state.pending_terminal_cmd = val
                st.rerun()

        # Trigger rerun if pending from on_change
        if st.session_state.pending_terminal_cmd:
            st.rerun()

        # ── Quick command buttons ─────────────────────────────────────────────
        st.markdown("**Quick commands:**")
        quick_cmds = ["ls -la", "tree", "pwd", "du -sh .", "history", "help", "df"]
        cols = st.columns(len(quick_cmds))
        for col, qcmd in zip(cols, quick_cmds):
            if col.button(qcmd, key=f"quick_{qcmd}"):
                st.session_state.pending_terminal_cmd = qcmd
                st.rerun()

        # ── History expander ─────────────────────────────────────────────────
        with st.expander("📜 Command History"):
            hist = list(reversed(shell.history[-20:]))
            if hist:
                for i, hcmd in enumerate(hist):
                    c1, c2 = st.columns([5, 1])
                    c1.code(hcmd, language=None)
                    if c2.button("↺", key=f"hist_run_{i}", help=f"Re-run: {hcmd}"):
                        result = shell.execute(hcmd)
                        st.session_state.terminal_output.append((hcmd, result))
                        st.rerun()
            else:
                st.caption("No history yet.")


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 3: RLE COMPRESSION
# ═══════════════════════════════════════════════════════════════════════════════

with tab_compress:
    if not COMPRESS_AVAILABLE:
        st.error("❌ RLE Compression module not available.")
    else:
        codec = RLECodec()
        sim = ContentSimulator()
        visualizer = RLEVisualizer()
        compress_store: CompressedStore = st.session_state.compress_store


        animator = RLEAnimator(codec)

        # ══════════════════════════════════════════════════════════════════════
        # 🎬 ANIMATION SECTION
        # ══════════════════════════════════════════════════════════════════════
        st.subheader("Live RLE Encoding Animation")
        st.caption(
            "Watch RLE scan every character, build runs, and emit pairs in real time. "
            "Then the decode phase plays back automatically — proving lossless round-trip."
        )

        # ── Controls ─────────────────────────────────────────────────────────
        _ANIM_PRESETS = {
            "— pick preset —":           None,
            "Bitmap row (great)":        "WWWWWWWWWWWWBBBBBBBBWWWWWWWWWWWW",
            "DNA segment (excellent)":   "AAAAAAAAAATTTTTTTTTCCCCCGGGGGG",
            "Random text (terrible)":    "TheQuickBrownFoxJumps",
            "Log spaces (good)":         "          ERROR          WARNING",
            "All same (perfect)":        "AAAAAAAAAAAAAAAAAAAAAA",
            "Mixed short/long":          "AAAABBBCCDDDDDDEE",
        }

        col_input, col_preset = st.columns([3, 2])
        with col_preset:
            chosen_preset = st.selectbox(
                "Presets", list(_ANIM_PRESETS.keys()), key="anim_preset"
            )
        with col_input:
            _preset_val = _ANIM_PRESETS.get(chosen_preset)
            anim_text = st.text_input(
                "Text to animate",
                value=_preset_val if _preset_val else "AAAABBBCCDDDDDDEE",
                max_chars=40,
                key="anim_text_input",
                help="Keep under 40 chars. Try long runs (AAAA) vs random (ABCD) to see the contrast.",
            )

        speed_lbl, speed_sl = st.columns([2, 5])
        speed_lbl.write("Speed (ms/step)")
        speed_ms = speed_sl.slider(
            "Animation speed (ms/step)", 50, 800, 350, 50,
            key="anim_speed",
            label_visibility="collapsed",
            help="Lower = faster. emit steps always pause 2.5x longer.",
        )

        bc1, bc2, bc3, bc4 = st.columns(4)
        run_anim   = bc1.button("▶ Play",        type="primary", key="btn_play_anim")
        step_mode  = bc2.button("👣 Step Mode",   key="btn_step_mode")
        reset_anim = bc3.button("↺ Reset",        key="btn_reset_anim")
        skip_end   = bc4.button("⏭ Skip to End", key="btn_skip_end")

        anim_placeholder    = st.empty()
        summary_placeholder = st.empty()

        # ── Session state init / reset ────────────────────────────────────────
        _needs_init = (
            "anim_result" not in st.session_state
            or reset_anim
            or st.session_state.get("anim_last_text") != anim_text
        )
        if _needs_init:
            _anim_r = codec.encode(anim_text, track_steps=True)
            st.session_state.anim_result         = _anim_r
            st.session_state.anim_last_text      = anim_text
            st.session_state.anim_step_idx       = 0
            st.session_state.anim_slider_active  = False

        # ── PLAY: frame loop ──────────────────────────────────────────────────
        if run_anim and anim_text:
            st.session_state.anim_slider_active = False
            result = codec.encode(anim_text, track_steps=True)
            steps  = result.steps
            pairs  = result.pairs
            decoded_check, _ = codec.decode(result.encoded)
            _decode_ok = (decoded_check == anim_text)

            emitted_pairs     = []
            current_run_start = 0
            current_run_len   = 0
            building_pair     = None
            last_frame_html   = ""

            for step in steps:
                if step.phase == "start":
                    current_run_start = step.position
                    current_run_len   = 1
                    building_pair     = (step.current_char, 1)
                elif step.phase == "extend":
                    current_run_len   = step.run_count
                    building_pair     = (step.current_char, step.run_count)
                elif step.phase == "emit":
                    emitted_pairs.append(RLEPair(step.run_count, step.current_char))
                    building_pair     = None
                    current_run_start = step.position + 1
                    current_run_len   = 0
                elif step.phase == "done":
                    building_pair   = None
                    current_run_len = 0

                frame_html = animator.render_frame(
                    text=anim_text, step=step,
                    emitted_pairs=emitted_pairs, building_pair=building_pair,
                    current_run_start=current_run_start, current_run_len=current_run_len,
                    show_ratio_bar=True,
                )
                last_frame_html = frame_html
                anim_placeholder.markdown(frame_html, unsafe_allow_html=True)

                if step.phase == "emit":
                    pause = speed_ms / 1000.0 * 2.5
                elif step.phase == "start":
                    pause = speed_ms / 1000.0 * 1.5
                elif step.phase == "done":
                    pause = 0.0
                else:
                    pause = speed_ms / 1000.0
                if pause > 0:
                    time.sleep(pause)

            summary_placeholder.markdown(
                animator.render_final_summary(result), unsafe_allow_html=True
            )
            time.sleep(0.8)

            # Decode phase animation
            if _decode_ok and pairs:
                all_chars_d = []
                for p in pairs:
                    all_chars_d.extend([p.character] * p.count)
                chars_revealed = 0
                for pi, p in enumerate(pairs):
                    for _ in range(p.count):
                        chars_revealed += 1
                        decode_html = animator.render_decode_frame(
                            pairs=pairs, current_pair_idx=pi,
                            chars_revealed=chars_revealed,
                            total_chars=len(all_chars_d),
                        )
                        anim_placeholder.markdown(
                            last_frame_html + decode_html, unsafe_allow_html=True
                        )
                        time.sleep(speed_ms / 1000.0 * 0.4)
                decode_final = animator.render_decode_frame(
                    pairs, len(pairs), len(all_chars_d), len(all_chars_d)
                )
                anim_placeholder.markdown(
                    last_frame_html + decode_final, unsafe_allow_html=True
                )
            else:
                anim_placeholder.markdown(last_frame_html, unsafe_allow_html=True)
                if not _decode_ok:
                    st.error("Round-trip decode mismatch — decode animation skipped.")

        # ── STEP MODE ─────────────────────────────────────────────────────────
        elif step_mode or st.session_state.get("anim_slider_active"):
            st.session_state.anim_slider_active = True
            result = codec.encode(anim_text, track_steps=True)
            steps  = result.steps
            if steps:
                step_idx = st.slider(
                    "Step through encoding",
                    0, len(steps) - 1,
                    st.session_state.get("anim_step_idx", 0),
                    key="anim_step_slider",
                )
                st.session_state.anim_step_idx = step_idx
                state = RLEAnimator.reconstruct_state_at(steps, step_idx)
                step  = steps[step_idx]
                frame_html = animator.render_frame(
                    text=anim_text, step=step,
                    emitted_pairs=state["emitted_pairs"],
                    building_pair=state["building_pair"],
                    current_run_start=state["current_run_start"],
                    current_run_len=state["current_run_len"],
                )
                anim_placeholder.markdown(frame_html, unsafe_allow_html=True)
                phase_emoji = {
                    "start": "🟡 start", "extend": "🔵 extend",
                    "emit": "🟢 emit", "done": "✅ done",
                }.get(step.phase, step.phase)
                st.info(
                    f"Step **{step_idx + 1}** / {len(steps)}  ·  "
                    f"Phase: {phase_emoji}  ·  Position: {step.position}  ·  "
                    f"Run count: {step.run_count}  ·  "
                    f"Bytes in/out: {step.bytes_in}/{step.bytes_out}"
                )
                if step.phase == "done":
                    summary_placeholder.markdown(
                        animator.render_final_summary(result), unsafe_allow_html=True
                    )

        # ── SKIP TO END ───────────────────────────────────────────────────────
        elif skip_end and anim_text:
            st.session_state.anim_slider_active = False
            result    = codec.encode(anim_text, track_steps=True)
            all_chars_s = []
            for p in result.pairs:
                all_chars_s.extend([p.character] * p.count)
            final_encode = animator.render_frame(
                text=anim_text, step=result.steps[-1],
                emitted_pairs=result.pairs, building_pair=None,
                current_run_start=len(anim_text), current_run_len=0,
            )
            final_decode = animator.render_decode_frame(
                result.pairs, len(result.pairs), len(all_chars_s), len(all_chars_s)
            )
            anim_placeholder.markdown(final_encode + final_decode, unsafe_allow_html=True)
            summary_placeholder.markdown(
                animator.render_final_summary(result), unsafe_allow_html=True
            )

        st.markdown("---")

        # ──────────────────────────────────────────────────────────────────────────────
        # A: What is RLE?
        # ──────────────────────────────────────────────────────────────────────────────
        with st.expander("📖 What is Run-Length Encoding?", expanded=False):
            st.markdown("""
**Run-Length Encoding (RLE)** replaces consecutive repeated characters with a *(count, character)* pair.

| Input | Output | Bytes | Ratio |
|---|---|---|---|
| `AAAABBBCC` | `4A3B2C` | 9 → 6 | **1.5× smaller** |
| `WWWWWWWWWWWWWWWWWWWW` | `20W` | 20 → 3 | **6.7× smaller** |
| `AAAAAAAAAATTTTTTTTTCCCCC` | `10A9T5C` | 24 → 7 | **3.4× smaller** |
| `ABCDEFGH` | `1A1B1C1D1E1F1G1H` | 8 → 16 | **0.5× — LARGER!** |

**Best for:** Bitmap images, DNA sequences, log files, whitespace indentation, satellite imagery

**Worst for:** Random text, binary archives (.zip, .mp4), encrypted data, natural language

**Break-even rule:** A run must be ≥ 3 identical chars to save any space.
- Run of 1 → costs 2 bytes to encode 1 byte (loses 1 byte)
- Run of 2 → costs 2 bytes to encode 2 bytes (breaks even)
- Run of 3+ → costs 2 bytes to encode 3+ bytes (saves space!)
""")

        st.markdown("---")

        # ──────────────────────────────────────────────────────────────────────────────
        # B: Interactive Live Demo
        # ──────────────────────────────────────────────────────────────────────────────
        st.subheader("Live RLE Step Trace")
        st.caption("Type any string and watch RLE encode it character by character")

        _PRESETS = {
            "Bitmap row (great)": "WWWWWWWWWWWWBBBBBBBBBBWWWWWWWWWWWWWWWWWW",
            "DNA segment (great)": "AAAAAAAAAATTTTTTTTTCCCCCGGGGGGAAAAAATT",
            "Random text (bad)": "TheQuickBrownFoxJumpsOverTheLazyDog",
            "Log spaces (good)": "          ERROR          WARNING          INFO",
            "All same char (perfect)": "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA",
        }

        col_inp, col_pre = st.columns([3, 1])
        with col_pre:
            preset = st.selectbox(
                "Presets",
                ["Custom"] + list(_PRESETS.keys()),
                key="rle_preset",
            )
        with col_inp:
            default_val = _PRESETS.get(preset, "AAAABBBCCCCDDDDDDDDEE")
            demo_text = st.text_input(
                "Input string",
                value=default_val,
                max_chars=80,
                key="rle_demo_text",
                help="Try repetitive strings for good compression. Random strings show RLE failure.",
            )

        if demo_text:
            rle_result = codec.encode(demo_text)
            rle_analysis = codec.analyze_rle_suitability(demo_text)

            # Suitability gauge
            st.markdown(visualizer.render_suitability_gauge(rle_analysis), unsafe_allow_html=True)

            # Metrics row
            mc1, mc2, mc3, mc4, mc5 = st.columns(5)
            mc1.metric("Original", f"{rle_result.original_bytes}B")
            mc2.metric("Encoded", f"{rle_result.encoded_bytes}B")
            ratio_delta = f"{rle_result.space_saved_pct:+.1f}%"
            mc3.metric(
                "Ratio",
                f"{rle_result.ratio:.2f}×",
                delta=ratio_delta,
                delta_color="normal" if rle_result.is_beneficial else "inverse",
            )
            mc4.metric("Runs", rle_result.num_runs)
            _lr_ch, _lr_cnt = rle_result.longest_run
            mc5.metric("Longest run", f"{_lr_cnt}× '{_lr_ch}'" if _lr_ch else "—")

            # Visual run structure
            st.markdown("**Run structure:**")
            st.markdown(
                visualizer.render_before_after_highlight(demo_text, rle_result.encoded),
                unsafe_allow_html=True,
            )

            # Comparison bar
            st.markdown(visualizer.render_comparison_bar(rle_result), unsafe_allow_html=True)

            # Step-by-step slider
            st.markdown("---")
            st.markdown("**Step-by-step encoding — drag the slider:**")
            if rle_result.steps:
                step_idx = st.slider(
                    "Step",
                    0,
                    len(rle_result.steps) - 1,
                    0,
                    key="rle_step_slider",
                )
                st.markdown(
                    visualizer.render_encode_animation_html(
                        demo_text, rle_result.steps, step_idx
                    ),
                    unsafe_allow_html=True,
                )
                step = rle_result.steps[step_idx]
                ic1, ic2, ic3 = st.columns(3)
                ic1.info(f"📅 Position: **{step.position}**")
                ic2.info(f"🔄 Run so far: **{step.run_count}× '{step.current_char}'**")
                if step.run_ended:
                    ic3.success(f"✅ Emitted: **'{step.pair_emitted}'**")
                else:
                    ic3.warning(
                        f"⏳ Building run... next char: **'{step.next_char}'**"
                        if step.next_char else"⏳ End of string"
                    )

            # Run breakdown table
            st.markdown("**Run breakdown table:**")
            bd_df = visualizer.render_run_breakdown_table(rle_result)
            if not bd_df.empty:
                st.dataframe(bd_df, use_container_width=True, hide_index=True)

        st.markdown("---")

        # ──────────────────────────────────────────────────────────────────────────────
        # C: Compress a file from the tree
        # ──────────────────────────────────────────────────────────────────────────────
        st.subheader("Compress a File from the Tree")
        all_filenames_c = [m.filename for m in tree.get_all_sorted()]

        if not all_filenames_c:
            st.warning("No files in tree. Insert some files first.")
        else:
            sel_file = st.selectbox(
                "Select file to compress", all_filenames_c, key="rle_compress_select"
            )
            if sel_file:
                meta_c = tree.search(sel_file)
                content_c = sim.generate_content(meta_c)
                analysis_c = codec.analyze_rle_suitability(content_c)

                # Content preview
                with st.expander(f"👁 Preview simulated content of `{sel_file}`"):
                    st.code(
                        content_c[:300] + ("..." if len(content_c) > 300 else ""),
                        language=None,
                    )
                    st.caption(
                        f"Content type: {analysis_c.get('content_type', '?')} "
                        f"| Length: {len(content_c)} chars "
                        f"| Unique chars: {analysis_c.get('num_unique_chars', '?')}"
                    )

                # Suitability gauge + recommendation before compressing
                cg1, cg2 = st.columns([3, 2])
                with cg1:
                    st.markdown(
                        visualizer.render_suitability_gauge(analysis_c),
                        unsafe_allow_html=True,
                    )
                with cg2:
                    rec_c = analysis_c.get('recommendation', '')
                    if 'Excellent' in rec_c or 'Good' in rec_c:
                        st.success(f"RLE: {rec_c}")
                    elif 'Poor' in rec_c:
                        st.warning(f"RLE: {rec_c}")
                    else:
                        st.error(f"RLE: {rec_c}")
                    st.caption(analysis_c.get('reason', ''))

                if st.button(f"Compress `{sel_file}` with RLE", type="primary", key="btn_rle_compress"):
                    rle_res_c = codec.encode(content_c)
                    entry_c = CompressedEntry(
                        original_filename=sel_file,
                        compressed_filename=sel_file + ".rle",
                        original_content=content_c,
                        encoded_content=rle_res_c.encoded,
                        pairs=rle_res_c.pairs,
                        stats=rle_res_c,
                        compressed_at=datetime.now(),
                        content_type=analysis_c.get('content_type', 'unknown'),
                    )
                    compress_store.store(entry_c)

                    if meta_c:
                        meta_c.rle_ratio = rle_res_c.ratio
                        meta_c.is_compressed = True
                        meta_c.content_type = analysis_c.get('content_type')

                    st.markdown(
                        visualizer.render_comparison_bar(rle_res_c),
                        unsafe_allow_html=True,
                    )

                    if rle_res_c.is_beneficial:
                        st.success(
                            f"✅ Compressed `{sel_file}`: "
                            f"{rle_res_c.original_bytes}B → {rle_res_c.encoded_bytes}B "
                            f"({rle_res_c.space_saved_pct:.1f}% saved, {rle_res_c.ratio:.2f}× ratio)"
                        )
                    else:
                        st.error(
                            f"❌ RLE EXPANDED `{sel_file}`: "
                            f"{rle_res_c.original_bytes}B → {rle_res_c.encoded_bytes}B "
                            f"({abs(rle_res_c.space_saved_pct):.1f}% larger — unsuitable data type)"
                        )
                        st.info(
                            "💡 Tip: RLE works best on bitmaps (.bmp, .png), DNA sequences, "
                            "and log files. This file type has too much variation."
                        )

                    if meta_c and meta_c.extension in ('.jpg', '.png', '.bmp'):
                        st.markdown("**Per-row pixel compression:**")
                        raw_rows = content_c.split("\n") if "\n" in content_c else [
                            content_c[i:i+20] for i in range(0, min(len(content_c), 200), 20)
                        ]
                        st.markdown(
                            visualizer.render_pixel_art_compression(
                                [r for r in raw_rows if r][:10], codec
                            ),
                            unsafe_allow_html=True,
                        )

                    st.rerun()

        st.markdown("---")

        # ── D: Decompress ─────────────────────────────────────────────────────
        st.subheader("Decompress a File")
        compressed_files_list = [e.original_filename for e in compress_store.all_entries()]

        if compressed_files_list:
            decomp_sel = st.selectbox(
                "Select compressed file", compressed_files_list, key="rle_decomp_select"
            )
            if st.button("Decompress 🔓", key="btn_rle_decompress"):
                entry_d = compress_store.get(decomp_sel)
                if entry_d:
                    decoded_str, decode_steps = codec.decode(entry_d.encoded_content)
                    is_valid = codec.verify(entry_d.original_content, entry_d.encoded_content)
                    if is_valid:
                        st.success(f"✅ Decompressed — output matches original ({len(decoded_str)} chars)")
                    else:
                        st.error("❌ Decompression mismatch — data corrupted")
                    dv1, dv2 = st.columns(2)
                    dv1.markdown("**Original:**")
                    dv1.code(entry_d.original_content[:200], language=None)
                    dv2.markdown("**Decoded:**")
                    dv2.code(decoded_str[:200], language=None)
                    with st.expander("🔍 Decoding steps"):
                        decode_df = pd.DataFrame([{
                            "Step": s.step_num+1, "Token": s.token,
                            "Count": s.count, "Char": repr(s.character),
                            "Output so far": s.decoded_so_far[:50],
                        } for s in decode_steps])
                        st.dataframe(decode_df, use_container_width=True, hide_index=True)
        else:
            st.info("💡 No compressed files yet — compress a file above first.")

        st.markdown("---")

        # ── E: Compression Dashboard ───────────────────────────────────────────
        st.subheader("Compression Dashboard")
        all_entries_dash = compress_store.all_entries()
        if all_entries_dash:
            summary_df = compress_store.get_summary_df()
            st.dataframe(
                summary_df, use_container_width=True, hide_index=True,
                column_config={
                    "Ratio": st.column_config.ProgressColumn("Ratio", min_value=0, max_value=10, format="%.2f×"),
                    "Saved%": st.column_config.NumberColumn("Space saved", format="%.1f%%"),
                    "Suitable?": st.column_config.CheckboxColumn("RLE suitable?"),
                },
            )
            total_saved = compress_store.get_total_saved_bytes()
            total_orig = compress_store.get_total_original_bytes()
            best_e = compress_store.get_best_compressed()
            worst_e = compress_store.get_worst_compressed()
            dc1, dc2, dc3, dc4 = st.columns(4)
            dc1.metric("Files compressed", len(all_entries_dash))
            dc2.metric("Total saved", f"{total_saved:,}B",
                       delta=f"{(total_saved/total_orig*100):.1f}%" if total_orig > 0 else "—",
                       delta_color="normal" if total_saved >= 0 else "inverse")
            if best_e:
                dc3.metric("Best ratio", f"{best_e.stats.ratio:.2f}×", delta=best_e.original_filename)
            if worst_e:
                dc4.metric("Worst ratio", f"{worst_e.stats.ratio:.2f}×",
                           delta=worst_e.original_filename,
                           delta_color="inverse" if worst_e.stats.ratio < 1 else "normal")
            chart_data = [
                {"File": e.original_filename, "Ratio": round(e.stats.ratio, 4)}
                for e in all_entries_dash
                if e.stats.ratio is not None and e.stats.ratio == e.stats.ratio  # drop NaN
            ]
            if chart_data and PLOTLY_AVAILABLE:
                import plotly.graph_objects as _go
                _files  = [r["File"]  for r in chart_data]
                _ratios = [r["Ratio"] for r in chart_data]
                _colors = ["#22c55e" if v >= 1.0 else "#ef4444" for v in _ratios]
                _fig = _go.Figure(_go.Bar(
                    x=_files, y=_ratios,
                    marker_color=_colors,
                    text=[f"{v:.2f}×" for v in _ratios],
                    textposition="outside",
                ))
                _fig.add_hline(y=1.0, line_dash="dash",
                               line_color="#f59e0b",
                               annotation_text="break-even",
                               annotation_position="top right")
                _fig.update_layout(
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(0,0,0,0)",
                    font=dict(color="#e8f0fe"),
                    yaxis=dict(title="Ratio", gridcolor="#2a3550", range=[0, max(_ratios)*1.2 + 0.1]),
                    xaxis=dict(tickangle=-30),
                    height=320,
                    margin=dict(t=20, b=60, l=0, r=0),
                    showlegend=False,
                )
                st.plotly_chart(_fig, use_container_width=True)
                st.caption("🟢 Green ≥ 1.0 = RLE helped   🔴 Red < 1.0 = RLE expanded the file")
            elif chart_data:
                # Plotly not available — plain table instead (never triggers Vega-Lite)
                st.dataframe(pd.DataFrame(chart_data), use_container_width=True, hide_index=True)
        else:
            st.info("💡 Compress some files to see the dashboard.")

        st.markdown("---")

        # ── F: Batch Compress ─────────────────────────────────────────────────
        st.subheader("Batch Compress All Files")
        if st.button("Compress All Files in Tree 🗄️", key="btn_rle_batch"):
            all_metas_b = tree.get_all_sorted()
            if not all_metas_b:
                st.warning("No files in tree.")
            else:
                prog = st.progress(0)
                batch_rows = []
                for bi, meta_b in enumerate(all_metas_b):
                    content_b = sim.generate_content(meta_b)
                    rle_b = codec.encode(content_b)
                    analysis_b = codec.analyze_rle_suitability(content_b)
                    entry_b = CompressedEntry(
                        original_filename=meta_b.filename,
                        compressed_filename=meta_b.filename + ".rle",
                        original_content=content_b,
                        encoded_content=rle_b.encoded,
                        pairs=rle_b.pairs,
                        stats=rle_b,
                        compressed_at=datetime.now(),
                        content_type=analysis_b.get("content_type", "unknown"),
                    )
                    compress_store.store(entry_b)
                    meta_b.rle_ratio = rle_b.ratio
                    meta_b.is_compressed = True
                    meta_b.content_type = analysis_b.get("content_type")
                    batch_rows.append({
                        "File": meta_b.filename, "Ext": meta_b.extension,
                        "Original (B)": rle_b.original_bytes, "Encoded (B)": rle_b.encoded_bytes,
                        "Ratio": f"{rle_b.ratio:.2f}×",
                        "Result": "compressed ✅" if rle_b.is_beneficial else "EXPANDED ❌",
                    })
                    prog.progress((bi + 1) / len(all_metas_b))
                compressed_count = sum(1 for r in batch_rows if "✅" in r["Result"])
                expanded_count = len(batch_rows) - compressed_count
                st.success(
                    f"✅ {compressed_count} compressed, ❌ {expanded_count} expanded — RLE is selective!"
                )
                st.dataframe(pd.DataFrame(batch_rows), use_container_width=True, hide_index=True)
                st.rerun()


# TAB 4: SNAPSHOTS / VERSIONING
# ═══════════════════════════════════════════════════════════════════════════════

with tab_snapshots:
    if not VERSIONING_AVAILABLE or "snap_mgr" not in st.session_state:
        st.error("❌ Versioning module not available.")
    else:
        snap_mgr: SnapshotManager = st.session_state.snap_mgr

        st.subheader("File System Snapshots")
        st.caption("Snapshots are automatically taken before every destructive operation (insert/delete/rename). "
                   "Use ↩ Undo / ↪ Redo in the sidebar for quick access.")

        # ── Manual snapshot ───────────────────────────────────────────────────
        col_lbl, col_btn = st.columns([4, 2])
        snap_label = col_lbl.text_input("Snapshot label", value="Manual checkpoint", key="snap_label")
        if col_btn.button("📸 Take Snapshot Now", key="btn_snap"):
            snap_mgr.take_snapshot(tree, snap_label, "manual")
            st.success(f"✅ Snapshot taken: '{snap_label}'")
            st.rerun()

        st.markdown("---")

        # ── Snapshot timeline ─────────────────────────────────────────────────
        snap_list = snap_mgr.get_snapshot_list()
        if not snap_list:
            st.info("No snapshots yet. Perform insert/delete/rename operations or click 'Take Snapshot Now'.")
        else:
            st.markdown(f"**{len(snap_list)} snapshot(s)** in history:")
            for snap_info in reversed(snap_list):
                col1, col2, col3, col4 = st.columns([5, 2, 2, 2])
                ts = snap_info["timestamp"].strftime("%H:%M:%S")
                ops_icon = {"insert": "➕", "delete": "🗑️", "rename": "✏️", "manual": "📸"}.get(
                    snap_info["operation"], "📸"
                )
                col1.write(f"{ops_icon} **{snap_info['label']}** — {ts}")
                col2.write(f"{snap_info['file_count']} files")
                col3.write(snap_info["operation"])
                if col4.button("Restore", key=f"restore_{snap_info['snapshot_id']}"):
                    restored = snap_mgr.restore_snapshot(snap_info["snapshot_id"], tree)
                    st.session_state.tree = restored
                    if TERMINAL_AVAILABLE and "shell" in st.session_state:
                        st.session_state.shell.tree = restored
                    if EXTRAS_AVAILABLE and "tag_index" in st.session_state:
                        st.session_state.tag_index.rebuild_from_tree(restored)
                    st.success(f"✅ Restored to: {snap_info['label']}")
                    st.rerun()

        st.markdown("---")

        # ── Diff viewer ───────────────────────────────────────────────────────
        st.subheader("Snapshot Diff")
        st.caption("Compare which files changed between any two snapshots")

        snap_list = snap_mgr.get_snapshot_list()
        if len(snap_list) < 2:
            st.info("Need at least 2 snapshots to compare. Perform more operations.")
        else:
            snap_labels_map = {
                f"{s['label']} ({s['timestamp'].strftime('%H:%M:%S')})": s
                for s in snap_list
            }
            snap_label_keys = list(snap_labels_map.keys())
            ca, cb = st.columns(2)
            label_a = ca.selectbox("Snapshot A (older)", snap_label_keys, index=0, key="diff_a")
            label_b = cb.selectbox("Snapshot B (newer)", snap_label_keys,
                                   index=min(1, len(snap_label_keys)-1), key="diff_b")

            if st.button("🔍 Compare Snapshots", key="btn_diff"):
                info_a = snap_labels_map[label_a]
                info_b = snap_labels_map[label_b]
                snap_a_obj = next(s for s in snap_mgr.snapshots if s.snapshot_id == info_a["snapshot_id"])
                snap_b_obj = next(s for s in snap_mgr.snapshots if s.snapshot_id == info_b["snapshot_id"])
                diff = snap_mgr.diff_snapshots(snap_a_obj, snap_b_obj)

                dc1, dc2, dc3 = st.columns(3)
                dc1.success(f"➕ Added: {len(diff.files_added)}")
                dc2.error(f"🗑️ Deleted: {len(diff.files_deleted)}")
                dc3.info(f"≡ Unchanged: {len(diff.files_unchanged)}")

                if diff.files_added:
                    st.markdown("**Added files:**")
                    for f in diff.files_added:
                        st.markdown(f'<span style="color:#22c55e;font-family:monospace">+ {f}</span>',
                                    unsafe_allow_html=True)
                if diff.files_deleted:
                    st.markdown("**Deleted files:**")
                    for f in diff.files_deleted:
                        st.markdown(f'<span style="color:#ef4444;font-family:monospace">- {f}</span>',
                                    unsafe_allow_html=True)
                if not diff.files_added and not diff.files_deleted:
                    st.info("No differences found — both snapshots have identical file sets.")


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 5: DISK ANALYTICS
# ═══════════════════════════════════════════════════════════════════════════════

def _human_size(n: int) -> str:
    """Human-readable file size string."""
    if n < 1024:
        return f"{n} B"
    if n < 1024**2:
        return f"{n/1024:.1f} KB"
    if n < 1024**3:
        return f"{n/1024**2:.1f} MB"
    return f"{n/1024**3:.2f} GB"


with tab_analytics:
    if not ANALYTICS_AVAILABLE:
        st.error("❌ Analytics module not available.")
    else:
        analyzer = DiskAnalyzer()
        all_files = tree.get_all_sorted()

        if not all_files:
            st.warning("No files in the tree. Insert some files first.")
        else:
            # ── Treemap ───────────────────────────────────────────────────────
            st.subheader("Disk Usage Treemap")
            st.caption("Rectangle size = file size.  Top level = file extension.  Click to drill down.")

            treemap_data = analyzer.build_treemap_data(tree)
            if PLOTLY_AVAILABLE:
                fig = go.Figure(go.Treemap(
                    labels=treemap_data["labels"],
                    parents=treemap_data["parents"],
                    values=treemap_data["values"],
                    textinfo="label+percent root",
                    hovertemplate="<b>%{label}</b><br>Size: %{value:,} bytes<extra></extra>",
                    marker=dict(colorscale="Blues"),
                ))
                fig.update_layout(
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(0,0,0,0)",
                    font=dict(color="#e8f0fe"),
                    margin=dict(t=10, l=0, b=0, r=0),
                    height=420,
                )
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("Install `plotly` for the treemap: `pip install plotly`")
                ext_df = analyzer.get_extension_breakdown(tree)
                if not ext_df.empty:
                    st.dataframe(
                        ext_df[["extension", "count", "total_bytes"]],
                        use_container_width=True, hide_index=True,
                    )

            # ── Extension breakdown ───────────────────────────────────────────
            st.subheader("Breakdown by File Type")
            ext_df = analyzer.get_extension_breakdown(tree)
            if not ext_df.empty:
                if PLOTLY_AVAILABLE:
                    fig2 = go.Figure(go.Bar(
                        x=ext_df["extension"],
                        y=ext_df["total_bytes"],
                        marker_color="#4a90d9",
                        text=ext_df["pct_of_total"].apply(lambda x: f"{x:.1f}%"),
                        textposition="auto",
                    ))
                    fig2.update_layout(
                        paper_bgcolor="rgba(0,0,0,0)",
                        plot_bgcolor="rgba(0,0,0,0)",
                        font=dict(color="#e8f0fe"),
                        xaxis=dict(gridcolor="#2a3550"),
                        yaxis=dict(gridcolor="#2a3550", title="Total bytes"),
                        height=300,
                        margin=dict(t=20, b=40),
                    )
                    st.plotly_chart(fig2, use_container_width=True)
                st.dataframe(ext_df, use_container_width=True, hide_index=True)

            # ── Largest files ─────────────────────────────────────────────────
            st.subheader("Largest Files")
            largest = analyzer.get_largest_files(tree, 10)
            if largest:
                max_size = largest[0].size_bytes or 1
                for i, f in enumerate(largest, 1):
                    col1, col2, col3 = st.columns([1, 6, 2])
                    col1.write(f"#{i}")
                    col2.progress(min(1.0, f.size_bytes / max_size), text=f.filename)
                    col3.write(f.size_display())

            # ── Recently modified ─────────────────────────────────────────────
            st.subheader("Recently Modified")
            recent = analyzer.get_recently_modified(tree, 10)
            if recent:
                recent_df = pd.DataFrame([{
                    "File": r.filename,
                    "Modified": r.age_display(),
                    "Size": r.size_display(),
                    "Path": r.path,
                } for r in recent])
                st.dataframe(recent_df, use_container_width=True, hide_index=True)

            # ── Directory sizes ───────────────────────────────────────────────
            st.subheader("Directory Sizes")
            dir_sizes = analyzer.get_directory_sizes(tree)
            if dir_sizes:
                dir_df = pd.DataFrame([
                    {"Directory": d, "Total Size": _human_size(s), "Bytes": s}
                    for d, s in dir_sizes.items()
                ]).sort_values("Bytes", ascending=False).drop(columns=["Bytes"])
                st.dataframe(dir_df, use_container_width=True, hide_index=True)





# ═══════════════════════════════════════════════════════════════════════════════
# TAB 6: TOOLS
# ═══════════════════════════════════════════════════════════════════════════════

with tab_tools:
    if not EXTRAS_AVAILABLE:
        st.error("❌ Extras modules not available.")
    else:
        differ = FileDiff()
        encryptor = XOREncryptor()
        finder = DuplicateFinder()

        tools_tab1, tools_tab2, tools_tab3, tools_tab4 = st.tabs([
            "🔀 File Diff",
            "🔐 Encrypt",
            "🔍 Duplicates",
            "📤 Export / Import",
        ])

        # ── Tools Tab 1: File Diff ─────────────────────────────────────────────
        with tools_tab1:
            st.subheader("Side-by-Side File Diff")
            st.caption("Compare metadata of any two files field-by-field")
            all_fnames = [m.filename for m in tree.get_all_sorted()]
            if len(all_fnames) < 2:
                st.warning("Need at least 2 files to compare.")
            else:
                ca, cb = st.columns(2)
                a_file = ca.selectbox("File A", all_fnames, index=0, key="diff_file_a")
                b_file = cb.selectbox("File B", all_fnames, index=1, key="diff_file_b")

                if st.button("Compare Files 🔀", type="primary", key="btn_file_diff"):
                    meta_a = tree.search(a_file)
                    meta_b = tree.search(b_file)
                    if meta_a and meta_b:
                        diff = differ.diff(meta_a, meta_b)
                        st.markdown(differ.render_side_by_side_html(diff), unsafe_allow_html=True)

                        if diff.changed_fields:
                            st.markdown("**Changed fields:**")
                            for field_name, (old_val, new_val) in diff.changed_fields.items():
                                st.markdown(
                                    f"- **{field_name}:** "
                                    f"<span style='color:#ef4444'>`{old_val}`</span> → "
                                    f"<span style='color:#22c55e'>`{new_val}`</span>",
                                    unsafe_allow_html=True,
                                )
                        else:
                            st.success("✅ No metadata differences found between these files.")

                        c1, c2, c3 = st.columns(3)
                        c1.metric("Added fields", len(diff.added_fields))
                        c2.metric("Changed fields", len(diff.changed_fields))
                        c3.metric("Removed fields", len(diff.removed_fields))
                    else:
                        st.error("Could not load metadata for one or both files.")

        # ── Tools Tab 2: XOR Encryption ────────────────────────────────────────
        with tools_tab2:
            st.subheader("XOR File Encryption")
            st.info(
                "XOR cipher with repeating key — each byte is XOR'd with the cycling key bytes. "
                "Applying the same key again reverses the encryption. "
                "⚠️ This is educational, not production-grade security."
            )
            all_fnames = [m.filename for m in tree.get_all_sorted()]
            if not all_fnames:
                st.warning("No files available.")
            else:
                enc_file = st.selectbox("File to encrypt", all_fnames, key="enc_sel")
                enc_key = st.text_input("Encryption key", value="secret", type="password", key="enc_key")

                col1, col2 = st.columns(2)
                if col1.button("Encrypt 🔒", key="btn_encrypt"):
                    try:
                        enc_result = encryptor.encrypt(enc_file, enc_key, tree)
                        st.session_state.encrypted_store[enc_file] = enc_result
                        st.success(f"✅ Encrypted `{enc_file}` with key '{enc_key}'")
                        st.markdown(f"**Hex preview:** `{enc_result.hex_data[:60]}...`")

                        # XOR visualization table
                        meta = tree.search(enc_file)
                        if meta:
                            raw_text = json.dumps({
                                "filename": meta.filename,
                                "extension": meta.extension,
                                "size_bytes": meta.size_bytes,
                                "path": meta.path,
                                "tags": meta.tags,
                            }, default=str)
                            st.markdown("**XOR step-by-step (first 10 characters):**")
                            st.markdown(
                                encryptor.show_xor_visualization(raw_text, enc_key),
                                unsafe_allow_html=True,
                            )
                    except Exception as e:
                        st.error(f"Encryption error: {e}")

                if col2.button("Decrypt 🔓", key="btn_decrypt"):
                    if enc_file in st.session_state.encrypted_store:
                        try:
                            stored = st.session_state.encrypted_store[enc_file]
                            dec_meta = encryptor.decrypt(stored, enc_key)
                            meta = tree.search(enc_file)
                            if meta:
                                orig = json.dumps({
                                    "filename": meta.filename,
                                    "extension": meta.extension,
                                    "size_bytes": meta.size_bytes,
                                    "path": meta.path,
                                    "tags": meta.tags,
                                }, default=str)
                                dec_text = json.dumps({
                                    "filename": dec_meta.filename,
                                    "extension": dec_meta.extension,
                                    "size_bytes": dec_meta.size_bytes,
                                    "path": dec_meta.path,
                                    "tags": dec_meta.tags,
                                }, default=str)
                                if encryptor.verify(orig, dec_text):
                                    st.success("✅ Decrypted successfully — data intact!")
                                else:
                                    st.warning("⚠️ Decrypted but data differs (wrong key?)")
                                st.json(dec_meta.__dict__ if hasattr(dec_meta, "__dict__") else {})
                        except Exception as e:
                            st.error(f"Decryption error: {e} (check your key)")
                    else:
                        st.warning(f"No encrypted version of `{enc_file}` found. Encrypt it first.")

        # ── Tools Tab 3: Duplicate Finder ──────────────────────────────────────
        with tools_tab3:
            st.subheader("Duplicate File Detector")
            st.caption("Detects duplicates by exact size, same extension+size, or similar filename (Levenshtein ≤ 2)")

            if st.button("Scan for Duplicates 🔍", type="primary", key="btn_scan_dupes"):
                groups = finder.find_duplicates(tree)
                st.session_state.duplicate_groups = groups

            if "duplicate_groups" in st.session_state:
                groups = st.session_state.duplicate_groups
                total_recov = finder.get_space_recoverable(groups)

                if not groups:
                    st.success("✅ No duplicates found!")
                else:
                    st.warning(
                        f"Found **{len(groups)} duplicate group(s)** — "
                        f"**{_human_size(total_recov)}** recoverable"
                    )

                    reason_icons = {
                        "same_size":    "📏",
                        "same_ext_size": "📐",
                        "similar_name": "📝",
                    }
                    for gi, group in enumerate(groups):
                        icon = reason_icons.get(group.reason, "🔍")
                        label = group.reason.replace("_", " ").title()
                        with st.expander(
                            f"{icon} {label} — {len(group.files)} files — "
                            f"{_human_size(group.recoverable_bytes)} recoverable"
                        ):
                            st.write("**Files in group:**")
                            for fn in group.files:
                                st.markdown(f"- `{fn}`")

                            # Show Levenshtein DP table for similar-name pairs
                            if group.reason == "similar_name" and len(group.files) == 2:
                                s1 = group.files[0].rsplit(".", 1)[0]
                                s2 = group.files[1].rsplit(".", 1)[0]
                                dist = finder.levenshtein(s1.lower(), s2.lower())
                                st.markdown(
                                    f"**Edit distance:** `{dist}` between `{s1}` and `{s2}`"
                                )
                                st.caption("Levenshtein DP table (gold = optimal path, green = answer):")
                                st.markdown(
                                    finder.render_dp_table(s1, s2),
                                    unsafe_allow_html=True,
                                )

                            if st.button(
                                f"🗑️ Delete duplicates (keep first)",
                                key=f"del_dupes_{gi}",
                            ):
                                for fn in group.files[1:]:
                                    tree.delete(fn)
                                    if EXTRAS_AVAILABLE and "tag_index" in st.session_state:
                                        st.session_state.tag_index.remove_file(fn)
                                del st.session_state.duplicate_groups
                                st.success(f"✅ Removed {len(group.files)-1} duplicate(s)")
                                st.rerun()

        # ── Tools Tab 4: Export / Import ───────────────────────────────────────
        with tools_tab4:
            st.subheader("Export Filesystem to JSON")
            st.caption("Download a complete snapshot of the virtual filesystem as JSON")

            if st.button("📦 Prepare Export", key="btn_export"):
                all_metas = tree.get_all_sorted()
                export_data = {
                    "metadata": {
                        "exported_at": datetime.now().isoformat(),
                        "file_count": tree.total_records,
                        "bplus_order": ORDER,
                        "app_version": "2.0",
                    },
                    "files": [
                        {
                            "filename":    m.filename,
                            "extension":   m.extension,
                            "size_bytes":  m.size_bytes,
                            "created_at":  str(m.created_at),
                            "modified_at": str(m.modified_at),
                            "path":        m.path,
                            "tags":        m.tags,
                            "is_directory": m.is_directory,
                        }
                        for m in all_metas
                    ],
                }
                json_str = json.dumps(export_data, indent=2, default=str)
                st.session_state.export_json = json_str
                st.success(f"✅ Ready to download — {tree.total_records} files")

            if "export_json" in st.session_state:
                st.download_button(
                    "⬇️ Download filesystem.json",
                    data=st.session_state.export_json,
                    file_name="bplus_filesystem.json",
                    mime="application/json",
                    key="btn_download_json",
                )

            st.markdown("---")

            st.subheader("Import Filesystem from JSON")
            uploaded = st.file_uploader("Upload a filesystem.json file", type=["json"], key="json_upload")
            if uploaded is not None:
                try:
                    data = json.loads(uploaded.read())
                    files_data = data.get("files", [])
                    st.info(f"Ready to import **{len(files_data)} files** from `{uploaded.name}`")

                    meta_info = data.get("metadata", {})
                    if meta_info:
                        st.json(meta_info)

                    merge_mode = st.checkbox(
                        "Merge with existing files (uncheck to replace)",
                        value=True, key="import_merge"
                    )

                    if st.button(f"📥 Import {len(files_data)} files", key="btn_import"):
                        if not merge_mode:
                            new_tree = BPlusTree()
                        else:
                            new_tree = tree

                        imported = 0
                        for f in files_data:
                            try:
                                meta = FileMetadata(
                                    filename=f["filename"],
                                    extension=f.get("extension", ""),
                                    size_bytes=int(f.get("size_bytes", 0)),
                                    created_at=datetime.fromisoformat(f["created_at"]) if f.get("created_at") else datetime.now(),
                                    modified_at=datetime.fromisoformat(f["modified_at"]) if f.get("modified_at") else datetime.now(),
                                    path=f.get("path", "/root/" + f["filename"]),
                                    tags=f.get("tags", []),
                                    is_directory=f.get("is_directory", False),
                                )
                                new_tree.insert(meta.filename, meta)
                                imported += 1
                            except Exception as ie:
                                st.warning(f"Skipped {f.get('filename', '?')}: {ie}")

                        st.session_state.tree = new_tree
                        if EXTRAS_AVAILABLE and "tag_index" in st.session_state:
                            st.session_state.tag_index.rebuild_from_tree(new_tree)
                        if TERMINAL_AVAILABLE and "shell" in st.session_state:
                            st.session_state.shell.tree = new_tree
                        st.success(f"✅ Imported {imported} files into the B+ Tree!")
                        st.rerun()

                except Exception as e:
                    st.error(f"Import error: {e}")


# ═══════════════════════════════════════════════════════════════════════════════
# OPERATION LOG (always shown at bottom)
# ═══════════════════════════════════════════════════════════════════════════════

st.markdown("---")
st.subheader("Operation Log")
if tree.operation_log:
    log_slice = list(reversed(tree.operation_log[-25:]))
    log_df = pd.DataFrame(log_slice)
    st.dataframe(
        log_df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "timestamp":      st.column_config.TextColumn("Time"),
            "operation":      st.column_config.TextColumn("Operation"),
            "filename":       st.column_config.TextColumn("Filename"),
            "result":         st.column_config.TextColumn("Result"),
            "nodes_affected": st.column_config.NumberColumn("Nodes"),
            "split_occurred": st.column_config.CheckboxColumn("Split?"),
            "merge_occurred": st.column_config.CheckboxColumn("Merge?"),
        },
    )
else:
    st.caption("No operations yet.")
