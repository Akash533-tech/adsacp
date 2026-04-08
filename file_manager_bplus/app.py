"""
B+ Tree File System — Streamlit Frontend
==========================================
A fully interactive file manager backed by a B+ Tree data structure.
Visualizes the tree live as every operation happens.
"""

import time
import math
import random
import pandas as pd
import streamlit as st
from datetime import datetime, timedelta

# ── Page config MUST be first Streamlit command ─────────────────────────────
st.set_page_config(
    page_title="B+ Tree File Manager",
    layout="wide",
    page_icon="🌲",
    initial_sidebar_state="expanded",
)

# ── Path setup so imports resolve from any working dir ──────────────────────
import sys
import os

# Add the file_manager_bplus directory to path
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

# ── Global CSS ───────────────────────────────────────────────────────────────
st.markdown("""
<style>
/* Dark background override */
.stApp { background-color: #0f1117; }

/* Operation panel card */
.op-card {
    background: #1a1f2e;
    border: 1px solid #2a3550;
    border-radius: 10px;
    padding: 18px 22px;
    margin-bottom: 12px;
}

/* Stat metric labels */
[data-testid="stMetricLabel"] { color: #7a9bc4 !important; font-size: 12px; }
[data-testid="stMetricValue"] { color: #e8f0fe !important; font-weight: 700; }

/* File chips */
.chip-row { display: flex; flex-wrap: wrap; gap: 6px; margin: 8px 0; }
.chip {
    background: #1a2e1a;
    color: #a8d5a2;
    padding: 3px 10px;
    border-radius: 12px;
    font-size: 12px;
    border: 1px solid #4caf50;
    font-family: 'Courier New', monospace;
}

/* Section headers */
.section-header {
    color: #4a90d9;
    font-size: 15px;
    font-weight: 600;
    letter-spacing: 0.05em;
    text-transform: uppercase;
    margin: 12px 0 8px 0;
}

/* Tabs styling */
[data-testid="stTab"] { color: #7a9bc4; }

/* Improve visibility of selectbox/input */
[data-testid="stSelectbox"] label,
[data-testid="stTextInput"] label { color: #b8d0e8 !important; }

/* Table styling */
[data-testid="stDataFrame"] { border-radius: 8px; overflow: hidden; }

/* Progress bar */
.stProgress > div > div { background-color: #4caf50; }
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
    """Create and populate a fresh BPlusTree with demo data."""
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
# Animation state
if "animating" not in st.session_state:
    st.session_state.animating = False
if "anim_index" not in st.session_state:
    st.session_state.anim_index = 0

tree: BPlusTree = st.session_state.tree


# ═══════════════════════════════════════════════════════════════════════════════
# SIDEBAR
# ═══════════════════════════════════════════════════════════════════════════════

with st.sidebar:
    st.markdown("## 🌲 B+ Tree File Manager")
    st.caption(f"Order: {ORDER}  ·  Max keys/node: {MAX_KEYS}  ·  Min keys: {MIN_KEYS}")

    st.markdown("---")

    # ── Stats dashboard ─────────────────────────────────────────────────────
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

    # ── Control buttons ──────────────────────────────────────────────────────
    if st.button("🔄 Reset to Demo Data", use_container_width=True):
        for key in ["tree", "highlight_keys", "highlight_path",
                    "last_op", "last_op_result", "split_nodes", "merge_nodes"]:
            if key in st.session_state:
                del st.session_state[key]
        st.rerun()

    if st.button("🗑️ Clear All Files", use_container_width=True):
        st.session_state.tree = BPlusTree()
        st.session_state.highlight_keys = []
        st.session_state.highlight_path = []
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

**Why leaves only?**
- All records at the same depth → predictable I/O
- Leaves form a linked list → range scan = follow pointers
- Internal nodes are pure index → more fits in cache

**Split on Insert:**
Node overflows → split into 2 → push median key up → tree stays balanced.

**Merge on Delete:**
Node underflows → try borrow from sibling first.
If can't → merge with sibling → remove separator from parent.
        """)


# ═══════════════════════════════════════════════════════════════════════════════
# ANIMATION DRIVER — runs one step per rerun, before anything else renders
# ═══════════════════════════════════════════════════════════════════════════════

if st.session_state.animating:
    idx = st.session_state.anim_index
    if idx < len(DEMO_FILES):
        base, ext, size, path, tags = DEMO_FILES[idx]
        fname = base + ext
        meta = FileMetadata(
            filename=fname,
            extension=ext,
            size_bytes=size,
            created_at=datetime.now() - timedelta(days=random.randint(1, 30)),
            modified_at=datetime.now(),
            path=path + fname,
            tags=tags,
        )
        st.session_state.tree.insert(fname, meta)
        st.session_state.highlight_keys = [fname]   # highlight the just-inserted file
        st.session_state.anim_index += 1
    else:
        # Animation complete
        st.session_state.animating = False
        st.session_state.highlight_keys = []

    tree = st.session_state.tree   # re-bind after mutation

# ═══════════════════════════════════════════════════════════════════════════════
# MAIN PAGE HEADER
# ═══════════════════════════════════════════════════════════════════════════════

st.title("🌲 B+ Tree File System Visualizer")
if st.session_state.animating:
    idx = st.session_state.anim_index
    st.caption(f"🎬 Building tree... inserting file {idx} / {len(DEMO_FILES)}")
else:
    st.caption("Insert, search, delete files — watch the tree restructure in real time")

# ═══════════════════════════════════════════════════════════════════════════════
# OPERATION PANEL
# ═══════════════════════════════════════════════════════════════════════════════

st.markdown('<div class="op-card">', unsafe_allow_html=True)

# ── ➕ INSERT ──────────────────────────────────────────────────────────────────
if operation == "➕ Insert":
    st.markdown('<div class="section-header">➕ Insert New File</div>', unsafe_allow_html=True)
    col1, col2, col3 = st.columns([3, 2, 2])
    with col1:
        filename_base = st.text_input("Filename (without extension)", placeholder="e.g. report_2024", key="ins_fname")
    with col2:
        ext = st.selectbox(
            "Extension",
            ['.py', '.txt', '.pdf', '.jpg', '.png', '.mp4', '.csv', '.sql', '.zip', '.html', '.js', '.json', '.md', '.css'],
            key="ins_ext"
        )
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
                filename=fname,
                extension=ext,
                size_bytes=size_kb * 1024,
                created_at=datetime.now(),
                modified_at=datetime.now(),
                path=path.rstrip("/") + "/" + fname,
                tags=tags or ["user-file"],
            )
            prev_log_len = len(tree.operation_log)
            tree.insert(fname, meta)
            st.session_state.highlight_keys = [fname]
            st.session_state.highlight_path = []

            if len(tree.operation_log) > prev_log_len:
                last_log = tree.operation_log[-1]
                if last_log["result"] == "DUPLICATE_SKIPPED":
                    st.warning(f"⚠️ File '{fname}' already exists in the tree.")
                else:
                    st.success(f"✅ Inserted `{fname}`")
                    if last_log.get("split_occurred"):
                        st.warning("⚡ Node split occurred! Tree was restructured to maintain balance.")
            st.rerun()
        else:
            st.error("❌ Please enter a filename.")

# ── 🔍 SEARCH ─────────────────────────────────────────────────────────────────
elif operation == "🔍 Search":
    st.markdown('<div class="section-header">🔍 Search for a File</div>', unsafe_allow_html=True)
    query = st.text_input("Exact filename to search", placeholder="e.g. main.py", key="srch_query")
    if st.button("Search 🔍", type="primary", key="btn_search"):
        if query.strip():
            path_nodes = get_search_path(tree, query.strip()) if VIZ_AVAILABLE else []
            result = tree.search(query.strip())
            st.session_state.highlight_path = path_nodes
            st.session_state.highlight_keys = [query.strip()] if result else []

            if result:
                st.success(f"✅ Found: `{result.filename}`")
                with st.expander("📄 File Details", expanded=True):
                    c1, c2 = st.columns(2)
                    c1.write(f"**Path:** `{result.path}`")
                    c1.write(f"**Size:** {result.size_display()}")
                    c1.write(f"**Extension:** `{result.extension}`")
                    c2.write(f"**Created:** {result.created_at.strftime('%Y-%m-%d %H:%M')}")
                    c2.write(f"**Modified:** {result.age_display()}")
                    c2.write(f"**Tags:** {', '.join(result.tags) if result.tags else '—'}")
                    c2.write(f"**Type:** {'Directory' if result.is_directory else 'File'}")
                if path_nodes:
                    st.info(f"🔍 Search traversed **{len(path_nodes)} node(s)** (Tree height = {tree.get_height()})")
            else:
                st.error(f"❌ File `{query.strip()}` not found in the tree.")
            st.rerun()

# ── 🗑️ DELETE ─────────────────────────────────────────────────────────────────
elif operation == "🗑️ Delete":
    st.markdown('<div class="section-header">🗑️ Delete a File</div>', unsafe_allow_html=True)
    all_sorted = tree.get_all_sorted()
    existing_files = [m.filename for m in all_sorted]

    if not existing_files:
        st.warning("No files in the tree to delete.")
    else:
        target = st.selectbox("Select file to delete", existing_files, key="del_target")
        c1, c2 = st.columns([1, 4])
        confirm = c1.checkbox("Confirm deletion", key="del_confirm")

        if c2.button("Delete File 🗑️", disabled=not confirm, type="primary", key="btn_delete"):
            success = tree.delete(target)
            st.session_state.highlight_keys = []
            st.session_state.highlight_path = []

            if success:
                st.success(f"✅ Deleted `{target}`")
                if tree.operation_log:
                    last_log = tree.operation_log[-1]
                    if last_log.get("merge_occurred"):
                        st.warning("🔄 Node merge occurred! Tree restructured to maintain balance.")
            else:
                st.error(f"❌ File `{target}` not found.")
            st.rerun()

# ── ✏️ RENAME ─────────────────────────────────────────────────────────────────
elif operation == "✏️ Rename":
    st.markdown('<div class="section-header">✏️ Rename a File</div>', unsafe_allow_html=True)
    all_sorted = tree.get_all_sorted()
    existing_files = [m.filename for m in all_sorted]

    if not existing_files:
        st.warning("No files in the tree to rename.")
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
                success = tree.rename(old_name, new_full)
                if success:
                    st.success(f"✅ Renamed `{old_name}` → `{new_full}`")
                    st.session_state.highlight_keys = [new_full]
                else:
                    st.error(f"❌ Could not rename `{old_name}`.")
                st.rerun()
            else:
                st.error("❌ Please enter a new filename.")

# ── 🔎 PREFIX SEARCH ──────────────────────────────────────────────────────────
elif operation == "🔎 Prefix Search":
    st.markdown('<div class="section-header">🔎 Prefix Search</div>', unsafe_allow_html=True)
    st.caption("Find all files whose names begin with a given prefix (case-insensitive)")
    prefix = st.text_input("Filename prefix", placeholder="e.g. test, report, 2024_", key="pfx_query")

    if st.button("Search by Prefix 🔎", type="primary", key="btn_prefix"):
        if prefix.strip():
            results = tree.search_prefix(prefix.strip())
            if results:
                st.success(f"✅ Found **{len(results)}** file(s) matching prefix `{prefix.strip()}`")
                df = pd.DataFrame([{
                    "Filename": r.filename,
                    "Type": r.ext_icon(),
                    "Size": r.size_display(),
                    "Path": r.path,
                    "Modified": r.age_display(),
                    "Tags": ", ".join(r.tags),
                } for r in results])
                st.dataframe(df, use_container_width=True, hide_index=True)
                st.session_state.highlight_keys = [r.filename for r in results]
            else:
                st.warning(f"No files found with prefix `{prefix.strip()}`")
                st.session_state.highlight_keys = []
            st.rerun()

# ── 📅 RANGE QUERY ─────────────────────────────────────────────────────────────
elif operation == "📅 Range Query":
    st.markdown('<div class="section-header">📅 Range Query</div>', unsafe_allow_html=True)
    st.info("🚀 This is where B+ Trees DESTROY regular BSTs — range queries use the leaf linked list for O(log n + k) performance!")

    all_sorted = tree.get_all_sorted()
    all_filenames = [m.filename for m in all_sorted]

    if len(all_filenames) < 2:
        st.warning("Need at least 2 files for a range query.")
    else:
        c1, c2 = st.columns(2)
        with c1:
            start_key = st.selectbox("Start filename (inclusive)", all_filenames, index=0, key="rng_start")
        with c2:
            end_key = st.selectbox("End filename (inclusive)", all_filenames, index=len(all_filenames)-1, key="rng_end")

        if st.button("Run Range Query 📅", type="primary", key="btn_range"):
            results = tree.search_range(start_key, end_key)
            st.success(f"✅ Found **{len(results)}** file(s) in range [`{start_key}` → `{end_key}`]")
            st.caption("Algorithm: jump to start leaf via O(log n) tree traversal, then follow `.next` pointers across leaves")
            if results:
                df = pd.DataFrame([{
                    "Filename": r.filename,
                    "Type": r.ext_icon(),
                    "Size": r.size_display(),
                    "Path": r.path,
                    "Modified": r.age_display(),
                } for r in results])
                st.dataframe(df, use_container_width=True, hide_index=True)
            st.session_state.highlight_keys = [r.filename for r in results]
            st.rerun()

# ── 📊 ALL FILES ───────────────────────────────────────────────────────────────
elif operation == "📊 All Files":
    st.markdown('<div class="section-header">📊 All Files (Sorted)</div>', unsafe_allow_html=True)
    all_files = tree.get_all_sorted()
    st.caption(f"**{len(all_files)}** files — sorted alphabetically via leaf linked-list traversal (O(n))")

    if all_files:
        df = pd.DataFrame([{
            "Filename": m.filename,
            "Type": m.ext_icon(),
            "Size": m.size_display(),
            "Path": m.path,
            "Modified": m.age_display(),
            "Tags": ", ".join(m.tags),
        } for m in all_files])
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.info("No files in the tree. Use ➕ Insert to add files.")

st.markdown('</div>', unsafe_allow_html=True)

st.markdown("---")

# ═══════════════════════════════════════════════════════════════════════════════
# VISUALIZATION TABS
# ═══════════════════════════════════════════════════════════════════════════════

# During animation, show a prominent banner and auto-advance
if st.session_state.animating:
    idx = st.session_state.anim_index   # already incremented above
    total = len(DEMO_FILES)
    progress_pct = idx / total
    last_file = DEMO_FILES[idx - 1][0] + DEMO_FILES[idx - 1][1] if idx > 0 else ""

    st.markdown(
        f"""
        <div style="background:#1a1f2e;border:1px solid #a855f7;border-radius:10px;
                    padding:14px 20px;margin-bottom:12px;">
          <span style="color:#a855f7;font-weight:700;font-size:15px;">🎬 LIVE BUILD</span>
          &nbsp; Inserting file <b style='color:#f5c518'>{idx}</b> of <b>{total}</b>
          &nbsp;·&nbsp; <code style='color:#a8d5a2'>{last_file}</code>
          &nbsp;·&nbsp;
          <span style='color:#7a9bc4'>Watch the tree grow — nodes split when full!</span>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.progress(progress_pct)

viz_tab1, viz_tab2, viz_tab3, viz_tab4 = st.tabs([
    "🌲 Full Tree",
    "🍃 Leaf Chain",
    "🔍 Search Path",
    "📊 Statistics",
])

# ── Tab 1: Full Tree ──────────────────────────────────────────────────────────
with viz_tab1:
    st.subheader("🌲 Full B+ Tree Visualization")

    if not VIZ_AVAILABLE:
        st.error("❌ `graphviz` Python package not installed. Run: `pip install graphviz`")
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
            st.info("Make sure Graphviz binary is installed. macOS: `brew install graphviz`")

    # In-order chip display
    all_files = tree.get_all_sorted()
    if all_files:
        st.markdown("**In-order (sorted) leaf traversal:**")
        chips_html = '<div class="chip-row">' + "".join(
            f'<span class="chip">{f.filename}</span>'
            for f in all_files
        ) + "</div>"
        st.markdown(chips_html, unsafe_allow_html=True)
        st.caption("↑ Filenames read left-to-right from leaf linked list — O(n) range scan with no extra traversal")

# If animation is still in progress, trigger the next frame after a short delay
if st.session_state.animating:
    time.sleep(0.55)   # pause between frames so the graph is visible
    st.rerun()

# ── Tab 2: Leaf Chain ─────────────────────────────────────────────────────────
with viz_tab2:
    st.subheader("🍃 Leaf Node Linked List")
    st.caption("B+ Tree's secret weapon: all leaves connected as a sorted linked list for O(k) range queries")

    if not VIZ_AVAILABLE:
        st.error("❌ `graphviz` Python package not installed.")
    else:
        try:
            dot_chain = render_leaf_chain(tree)
            st.graphviz_chart(dot_chain.source, use_container_width=True)
        except Exception as e:
            st.error(f"⚠️ Leaf chain visualization error: {e}")

    leaves = tree.get_all_leaves()
    st.markdown(f"**{len(leaves)} leaf node(s) in the chain:**")
    for i, leaf in enumerate(leaves):
        with st.expander(f"Leaf {i+1}  —  keys: {leaf.keys}"):
            for key, val in zip(leaf.keys, leaf.values):
                cols = st.columns([3, 2, 3, 2])
                cols[0].write(f"`{key}`")
                cols[1].write(val.size_display())
                cols[2].write(f"`{val.path}`")
                cols[3].write(val.age_display())

# ── Tab 3: Search Path ────────────────────────────────────────────────────────
with viz_tab3:
    st.subheader("🔍 Last Search Path")

    if st.session_state.get("highlight_path"):
        path_nodes = st.session_state.highlight_path
        st.info(f"Search traversed **{len(path_nodes)} node(s)** — Tree height = {tree.get_height()}")

        if VIZ_AVAILABLE:
            try:
                dot_path = render_bplus_tree(
                    tree,
                    highlight_path=path_nodes,
                )
                st.graphviz_chart(dot_path.source, use_container_width=True)
            except Exception as e:
                st.error(f"Visualization error: {e}")

        st.markdown("**Traversal path:**")
        for step, node in enumerate(path_nodes):
            node_type = "🍃 Leaf" if node.is_leaf else "🔵 Internal"
            st.markdown(f"**Step {step+1}:** {node_type} — keys: `{node.keys}`")
    else:
        st.info("Run a **🔍 Search** operation to see the traversal path highlighted here.")

# ── Tab 4: Statistics ─────────────────────────────────────────────────────────
with viz_tab4:
    st.subheader("📊 Tree Statistics")

    c1, c2, c3 = st.columns(3)
    c1.metric("Total Files",    tree.total_records)
    c2.metric("Tree Height",    tree.get_height())
    c3.metric("Fill Factor",    f"{tree.get_fill_factor():.1%}")
    c1.metric("Internal Nodes", tree.get_internal_node_count())
    c2.metric("Leaf Nodes",     tree.get_leaf_count())
    c3.metric("Total Nodes",    tree.get_node_count())
    c1.metric("Min File",       tree.get_min_key() or "—")
    c2.metric("Max File",       tree.get_max_key() or "—")

    st.markdown("---")

    n = max(tree.total_records, 1)
    height = tree.get_height()

    st.markdown(f"**Complexity Comparison for n = {n} files:**")
    st.markdown(f"""
| Operation | Unsorted Array | BST (avg) | B+ Tree (ORDER={ORDER}) |
|:---|:---:|:---:|:---:|
| Search | O(n) = {n} | O(log n) ≈ {int(math.log2(n)+1)} | O(log_{ORDER} n) ≈ {height} |
| Insert | O(1) | O(log n) ≈ {int(math.log2(n)+1)} | O(log n) ≈ {height} |
| Delete | O(n) = {n} | O(log n) ≈ {int(math.log2(n)+1)} | O(log n) ≈ {height} |
| Range query (k results) | O(n) = {n} | O(n) = {n} | **O(log n + k)** |
| Sorted traversal | O(n log n) | O(n) | **O(n) via linked list** |
    """)

    st.markdown("---")

    # Level-order breakdown
    levels = tree.get_level_order()
    st.markdown("**Level-by-level breakdown:**")
    for lvl_idx, lvl_nodes in enumerate(levels):
        node_type = "Leaf" if lvl_nodes[0].is_leaf else "Internal"
        total_keys = sum(len(n.keys) for n in lvl_nodes)
        st.markdown(
            f"- **Level {lvl_idx}** ({node_type}): "
            f"{len(lvl_nodes)} node(s), {total_keys} total key(s)"
        )


# ═══════════════════════════════════════════════════════════════════════════════
# OPERATION LOG
# ═══════════════════════════════════════════════════════════════════════════════

st.markdown("---")
st.subheader("📋 Operation Log")

if tree.operation_log:
    log_slice = list(reversed(tree.operation_log[-25:]))
    log_df = pd.DataFrame(log_slice)
    st.dataframe(
        log_df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "timestamp":     st.column_config.TextColumn("Time"),
            "operation":     st.column_config.TextColumn("Operation"),
            "filename":      st.column_config.TextColumn("Filename"),
            "result":        st.column_config.TextColumn("Result"),
            "nodes_affected": st.column_config.NumberColumn("Nodes Affected"),
            "split_occurred": st.column_config.CheckboxColumn("Split?"),
            "merge_occurred": st.column_config.CheckboxColumn("Merge?"),
        }
    )
else:
    st.caption("No operations yet. Perform an insert, search, or delete to see the log.")


# ═══════════════════════════════════════════════════════════════════════════════
# ANIMATE BUILD (sidebar button) — triggers step-driven animation
# ═══════════════════════════════════════════════════════════════════════════════

with st.sidebar:
    st.markdown("---")
    if st.session_state.animating:
        # Show a stop button during animation
        if st.button("⏹ Stop Animation", use_container_width=True, key="btn_stop",
                     type="primary"):
            st.session_state.animating = False
            st.session_state.highlight_keys = []
            st.rerun()
        idx = st.session_state.anim_index
        st.caption(f"Step {idx} / {len(DEMO_FILES)}")
        st.progress(idx / len(DEMO_FILES))
    else:
        if st.button("🎬 Animate Build", use_container_width=True, key="btn_animate"):
            # Reset tree and kick off step-driven animation
            st.session_state.tree = BPlusTree()
            st.session_state.highlight_keys = []
            st.session_state.highlight_path = []
            st.session_state.split_nodes = []
            st.session_state.merge_nodes = []
            st.session_state.anim_index = 0
            st.session_state.animating = True
            st.rerun()
