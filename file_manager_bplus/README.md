# 🌲 B+ Tree File Management System

A fully interactive **File Management System** powered by a **B+ Tree** data structure, with a real-time Streamlit frontend that visualizes the tree as every operation happens — showing internal nodes, leaf nodes, splits, merges, and linked-list traversals live.

---

## 📸 Preview

| Full Tree View | Animate Build | Leaf Chain |
|:---:|:---:|:---:|
| Blue internal nodes routing keys | Files inserted one by one, watch splits happen | Orange dashed arrows showing linked list |

---

## 📁 Project Structure

```
file_manager_bplus/
├── app.py                    ← Streamlit entry point (UI + animation driver)
├── bplus/
│   ├── __init__.py
│   ├── constants.py          ← ORDER=4, MAX_KEYS=3, MIN_KEYS=2
│   ├── node.py               ← BPlusNode (internal + leaf)
│   └── bplus_tree.py         ← Full B+ Tree implementation
├── file_ops/
│   ├── __init__.py
│   └── metadata.py           ← FileMetadata dataclass
├── visualizer/
│   ├── __init__.py
│   └── tree_viz.py           ← Graphviz-based live tree renderer
├── requirements.txt
└── README.md
```

---

## ⚙️ Setup & Installation

### Prerequisites

- Python 3.9+
- **Graphviz binary** (required for tree visualization)

```bash
# macOS
brew install graphviz

# Ubuntu / Debian
sudo apt-get install graphviz

# Windows (via Chocolatey)
choco install graphviz
```

### Install Python Dependencies

```bash
cd file_manager_bplus
pip install -r requirements.txt
```

### Run the App

```bash
streamlit run app.py
```

Open **http://localhost:8501** in your browser.

---

## 🚀 Features

### 📂 File Operations

| Operation | Description |
|---|---|
| ➕ **Insert** | Add a new file with name, extension, size, path, and tags |
| 🔍 **Search** | Find a file by exact name — highlights the traversal path |
| 🗑️ **Delete** | Remove a file — triggers borrow or merge if needed |
| ✏️ **Rename** | Rename a file (delete + re-insert with same metadata) |
| 🔎 **Prefix Search** | Find all files starting with a prefix (e.g. `test`, `2024_`) |
| 📅 **Range Query** | Get all files alphabetically between two names — O(log n + k) |
| 📊 **All Files** | View all files in sorted order via leaf linked-list traversal |

### 🌲 Live Visualization

- **Full Tree Tab** — Complete B+ Tree rendered with Graphviz
  - 🔵 Blue internal nodes (routing keys only)
  - 🟢 Green leaf nodes (actual file records)
  - 🟡 Gold highlight on search path / recently inserted node
  - Orange dashed arrows on leaf → next-leaf linked list
- **Leaf Chain Tab** — Horizontal view of the sorted linked list
- **Search Path Tab** — Highlights the exact nodes traversed during the last search
- **Statistics Tab** — Height, fill factor, node counts, complexity comparison table

### 🎬 Animate Build

Click **🎬 Animate Build** in the sidebar to:
- Clear the tree completely
- Insert all 15 demo files **one by one** with a live delay
- Watch the tree grow — single leaf → root + splits → full 3-level tree
- Each frame highlights the just-inserted file in gold
- A **⏹ Stop Animation** button appears to cancel mid-way

---

## 🧠 B+ Tree Theory

### Why B+ Tree?

| Feature | Unsorted Array | BST (avg) | B+ Tree (ORDER=4) |
|---|:---:|:---:|:---:|
| Search | O(n) | O(log n) | O(log₄ n) |
| Insert | O(1) | O(log n) | O(log n) |
| Delete | O(n) | O(log n) | O(log n) |
| **Range query** | O(n) | O(n) | **O(log n + k)** |
| Used in | — | — | **MySQL, PostgreSQL, NTFS** |

### Key Invariants (ORDER = 4)

```
MAX_KEYS      = ORDER - 1  = 3   (max keys per node)
MIN_KEYS      = ORDER // 2 = 2   (min keys, non-root nodes)
MAX_CHILDREN  = ORDER      = 4   (max children per internal node)
```

- All **data lives in leaf nodes only** — internal nodes are pure routing indexes
- All **leaves are at the same depth** — guaranteed O(log n) traversal
- Leaves form a **doubly-linked list** — O(k) range scans after O(log n) jump
- Root is exempt from the MIN_KEYS rule

### Split on Insert

```
Before (leaf full):   [ A | B | C ]
Insert D:             [ A | B | C | D ]  ← overflow!

After split:
  Left leaf:  [ A | B ]
  Right leaf: [ C | D ]
  Promote C to parent (COPY for leaf split)
```

### Merge on Delete

```
Before:   [ X ] ← underflow after delete
Siblings: [ A | B | C ]  (rich sibling → borrow)
          or
          [ A | B ]      (at min → merge + remove separator from parent)
```

---

## 📊 Demo Dataset

On first load, 15 pre-seeded files demonstrate multiple split events:

| File | Path | Size |
|---|---|---|
| `main.py` | `/root/src/` | ~4 KB |
| `README.md` | `/root/` | ~2 KB |
| `utils.py` | `/root/src/` | ~8 KB |
| `data.csv` | `/root/data/` | ~500 KB |
| `report.pdf` | `/root/docs/` | ~2 MB |
| `image.jpg` | `/root/assets/` | ~1 MB |
| `config.txt` | `/root/` | ~1 KB |
| `test_main.py` | `/root/tests/` | ~3 KB |
| `output.mp4` | `/root/media/` | ~50 MB |
| `notes.txt` | `/root/docs/` | ~512 B |
| `schema.sql` | `/root/db/` | ~6 KB |
| `backup.zip` | `/root/` | ~10 MB |
| `index.html` | `/root/web/` | ~4 KB |
| `app.js` | `/root/web/` | ~8 KB |
| `style.css` | `/root/web/` | ~3 KB |

---

## 🎨 Visual Design

| Element | Color |
|---|---|
| Page background | `#0f1117` |
| Internal node fill | `#1e2a40` + blue border `#4a90d9` |
| Leaf node fill | `#1a2e1a` + green border `#4caf50` |
| Search highlight | Gold border `#f5c518` |
| Split flash | Purple border `#a855f7` |
| Merge flash | Red border `#ef4444` |
| Leaf chain arrows | Orange dashed `#f59e0b` |

---

## 📦 Dependencies

```
streamlit>=1.32.0
graphviz>=0.20.1
pandas>=2.0.0
```

Plus the **Graphviz system binary** (see Setup above).

---

## 🏗️ Architecture Notes

### `bplus/bplus_tree.py`

The core engine. Key methods:

```python
tree.insert(filename, metadata)       # Insert + auto-split
tree.search(filename)                 # Exact search → O(log n)
tree.search_range(start, end)         # Range scan → O(log n + k)
tree.search_prefix(prefix)            # Prefix match → O(log n + k)
tree.delete(filename)                 # Delete + borrow/merge
tree.rename(old_name, new_name)       # Delete + re-insert
tree.get_all_sorted()                 # Leaf linked-list walk → O(n)
tree.get_level_order()                # BFS → used for visualization
```

### `visualizer/tree_viz.py`

Renders the tree using the `graphviz` Python binding:

```python
render_bplus_tree(tree, highlight_keys, highlight_path)  # Full tree
render_leaf_chain(tree)                                   # Horizontal leaf view
get_search_path(tree, key)                                # Returns traversal nodes
```

### Animation Driver (`app.py`)

Uses a **step-driven session state loop** — each `st.rerun()` inserts exactly one file and re-renders the full tree graph, giving a true live animation effect:

```python
# On button click:
st.session_state.animating = True
st.session_state.anim_index = 0

# Each rerun:
if animating:
    insert DEMO_FILES[anim_index]
    anim_index += 1
    sleep(0.55)
    st.rerun()
```

---

## 📄 License

MIT License — free to use, modify, and distribute.

---

*Built as a demonstration of B+ Tree data structures applied to a real-world file management scenario.*
