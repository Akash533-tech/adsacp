"""
B+ Tree Visualizer using Graphviz
===================================
Renders the live B+ Tree as a directed graph with:
  - Internal nodes: dark blue with record-style labels showing keys
  - Leaf nodes: dark green with key|ext|size per record
  - Blue tree edges: parent → child
  - Orange dashed edges: leaf → next leaf (linked list)
  - Highlighted nodes: gold border (search path), purple (split), red (merge)
"""

import html
from typing import List, Optional

try:
    import graphviz
    GRAPHVIZ_AVAILABLE = True
except ImportError:
    GRAPHVIZ_AVAILABLE = False

from bplus.bplus_tree import BPlusTree
from bplus.node import BPlusNode


# ── Color Constants ────────────────────────────────────────────────────────────
C_INTERNAL_FILL   = "#1e2a40"
C_INTERNAL_BORDER = "#4a90d9"
C_LEAF_FILL       = "#1a2e1a"
C_LEAF_BORDER     = "#4caf50"
C_HIGHLIGHT       = "#f5c518"   # gold — search path
C_SPLIT           = "#a855f7"   # purple — just split
C_MERGE           = "#ef4444"   # red — just merged
C_EDGE            = "#4a90d9"   # blue — tree edge
C_LEAF_CHAIN      = "#f59e0b"   # orange — leaf linked list
C_TEXT_INTERNAL   = "#b8d4f5"
C_TEXT_LEAF       = "#a8d5a2"


def _esc(s: str) -> str:
    """HTML-escape a string for use in Graphviz HTML labels."""
    return html.escape(str(s), quote=True)


def _node_id(node: BPlusNode) -> str:
    """Unique ID for a node based on its Python object id."""
    return f"n{id(node)}"


def _make_internal_label(node: BPlusNode) -> str:
    """
    Build an HTML-like record label for an internal node.
    Format: <p0>·|<k0>key0|<p1>·|<k1>key1|<p2>·| ...
    Each key separated by child pointer slots (ports).
    """
    parts = [f'<p0>·']
    for i, key in enumerate(node.keys):
        parts.append(f'<k{i}>{_esc(key)}')
        parts.append(f'<p{i+1}>·')
    return "{" + " | ".join(parts) + "}"


def _make_leaf_label(node: BPlusNode) -> str:
    """
    Build a record label for a leaf node.
    Each slot shows: filename | ext | size | [RLE ratio badge if compressed]
    """
    if not node.keys:
        return "{∅}"
    slots = []
    for i, (key, val) in enumerate(zip(node.keys, node.values)):
        size_str = val.size_display() if val else "?"
        ext_str  = val.extension if val else ""
        # RLE compression badge
        rle_badge = ""
        if val and getattr(val, 'is_compressed', False) and getattr(val, 'rle_ratio', None):
            ratio = val.rle_ratio
            rle_badge = f" [{ratio:.1f}x]"
        slot = f'<k{i}>{_esc(key)} | {_esc(ext_str)} | {_esc(size_str)}{_esc(rle_badge)}'
        slots.append(slot)
    return "{" + " | ".join(slots) + "}"


def render_bplus_tree(
    tree: BPlusTree,
    highlight_keys: Optional[List[str]] = None,
    highlight_path: Optional[List[BPlusNode]] = None,
    split_nodes: Optional[List[BPlusNode]] = None,
    merge_nodes: Optional[List[BPlusNode]] = None,
    mode: str = "full",
) -> "graphviz.Digraph":
    """
    Render the full B+ Tree as a Graphviz Digraph.

    Parameters
    ----------
    tree          : The BPlusTree instance to visualize
    highlight_keys: Filename keys to highlight (gold border on their leaf nodes)
    highlight_path: List of BPlusNode visited during last search (gold border + thick edge)
    split_nodes   : Nodes that were recently split (purple border)
    merge_nodes   : Nodes that were recently merged (red border)
    mode          : "full" | "compact" | "leaves_only"
    """
    if not GRAPHVIZ_AVAILABLE:
        raise ImportError("graphviz Python package not installed.")

    dot = graphviz.Digraph(
        name="BPlusTree",
        graph_attr={
            "bgcolor": "transparent",
            "rankdir": "TB",
            "splines": "polyline",
            "nodesep": "0.4",
            "ranksep": "0.7",
            "fontname": "Courier New",
            "fontsize": "12",
        },
        node_attr={
            "shape": "record",
            "style": "filled",
            "fontname": "Courier New",
            "fontsize": "11",
            "margin": "0.1,0.05",
        },
        edge_attr={
            "fontname": "Courier New",
            "fontsize": "9",
        },
    )

    highlight_keys_lower = set(k.lower() for k in (highlight_keys or []))
    highlight_path_set   = set(id(n) for n in (highlight_path or []))
    split_set            = set(id(n) for n in (split_nodes or []))
    merge_set            = set(id(n) for n in (merge_nodes or []))

    # Collect all nodes via BFS
    from collections import deque
    all_nodes: List[BPlusNode] = []
    queue = deque([tree.root])
    while queue:
        node = queue.popleft()
        all_nodes.append(node)
        if not node.is_leaf:
            for child in node.children:
                queue.append(child)

    if mode == "leaves_only":
        all_nodes = [n for n in all_nodes if n.is_leaf]

    # Determine if any leaf contains a highlighted key
    leaf_has_highlight: dict = {}  # id(node) → bool
    for node in all_nodes:
        if node.is_leaf:
            leaf_has_highlight[id(node)] = any(k in highlight_keys_lower for k in node.keys)

    # ── Render each node ────────────────────────────────────────────────────
    for node in all_nodes:
        nid = _node_id(node)

        if node.is_leaf:
            # Determine styling
            if id(node) in merge_set:
                fill_color   = "#2d0a0a"
                border_color = C_MERGE
                border_width = "3"
            elif id(node) in split_set:
                fill_color   = "#0a1a2d"
                border_color = C_SPLIT
                border_width = "3"
            elif leaf_has_highlight.get(id(node)):
                fill_color   = "#2d2a00"
                border_color = C_HIGHLIGHT
                border_width = "3"
            elif id(node) in highlight_path_set:
                fill_color   = "#2d2a00"
                border_color = C_HIGHLIGHT
                border_width = "3"
            else:
                fill_color   = C_LEAF_FILL
                border_color = C_LEAF_BORDER
                border_width = "2"

            label = _make_leaf_label(node)
            dot.node(
                nid,
                label=label,
                fillcolor=fill_color,
                color=border_color,
                fontcolor=C_TEXT_LEAF,
                penwidth=border_width,
            )
        else:
            # Internal node
            if id(node) in split_set:
                fill_color   = "#2d1f40"
                border_color = C_SPLIT
                border_width = "3"
            elif id(node) in highlight_path_set:
                fill_color   = "#1e2a40"
                border_color = C_HIGHLIGHT
                border_width = "3"
            else:
                fill_color   = C_INTERNAL_FILL
                border_color = C_INTERNAL_BORDER
                border_width = "2"

            if mode == "compact" and len(node.keys) > 2:
                # Show only first and last key in compact mode
                keys_display = [node.keys[0], "...", node.keys[-1]]
                label_parts = [f'<p0>·']
                for i, k in enumerate(keys_display):
                    label_parts.append(f'<k{i}>{_esc(str(k))}')
                    label_parts.append(f'<p{i+1}>·')
                label = "{" + " | ".join(label_parts) + "}"
            else:
                label = _make_internal_label(node)

            dot.node(
                nid,
                label=label,
                fillcolor=fill_color,
                color=border_color,
                fontcolor=C_TEXT_INTERNAL,
                penwidth=border_width,
            )

    # ── Render tree edges (internal → child) ───────────────────────────────
    for node in all_nodes:
        if not node.is_leaf:
            nid = _node_id(node)
            for i, child in enumerate(node.children):
                cid = _node_id(child)
                port = f"{nid}:p{i}"

                # Highlight path edge
                in_path = id(node) in highlight_path_set and id(child) in highlight_path_set
                edge_color  = C_HIGHLIGHT if in_path else C_EDGE
                edge_width  = "3" if in_path else "1.5"

                dot.edge(
                    f"{port}",
                    cid,
                    color=edge_color,
                    penwidth=edge_width,
                    arrowhead="vee",
                )

    # ── Render leaf linked-list edges (leaf → next) ─────────────────────────
    if mode != "leaves_only":  # in leaves_only mode, edges are added separately
        leaves = tree.get_all_leaves()
        for leaf in leaves:
            if leaf.next is not None:
                dot.edge(
                    _node_id(leaf),
                    _node_id(leaf.next),
                    color=C_LEAF_CHAIN,
                    style="dashed",
                    arrowhead="normal",
                    constraint="false",
                    label="next→",
                    fontcolor=C_LEAF_CHAIN,
                )

    # ── Legend subgraph ─────────────────────────────────────────────────────
    with dot.subgraph(name="cluster_legend") as legend:
        legend.attr(
            label="Legend",
            bgcolor="#1a1f2e",
            color="#4a90d9",
            fontcolor="#b8d4f5",
            fontsize="10",
            style="filled,rounded",
        )
        legend.node(
            "leg_internal",
            label="Internal Node\n(routing only)",
            fillcolor=C_INTERNAL_FILL,
            color=C_INTERNAL_BORDER,
            fontcolor=C_TEXT_INTERNAL,
            shape="rectangle",
            style="filled",
            penwidth="2",
        )
        legend.node(
            "leg_leaf",
            label="Leaf Node\n(file data)",
            fillcolor=C_LEAF_FILL,
            color=C_LEAF_BORDER,
            fontcolor=C_TEXT_LEAF,
            shape="rectangle",
            style="filled",
            penwidth="2",
        )
        legend.edge(
            "leg_internal", "leg_leaf",
            style="invis",
        )

    return dot


def render_leaf_chain(tree: BPlusTree) -> "graphviz.Digraph":
    """
    Render ONLY the leaf linked list horizontally.
    Each leaf is shown as a box with all its records.
    Orange dashed arrows connect leaves left-to-right.
    Used in the 'Leaf Chain' tab.
    """
    if not GRAPHVIZ_AVAILABLE:
        raise ImportError("graphviz Python package not installed.")

    dot = graphviz.Digraph(
        name="LeafChain",
        graph_attr={
            "bgcolor": "transparent",
            "rankdir": "LR",   # left-to-right layout for the chain
            "splines": "line",
            "nodesep": "0.5",
            "fontname": "Courier New",
        },
        node_attr={
            "shape": "record",
            "style": "filled",
            "fontname": "Courier New",
            "fontsize": "11",
            "margin": "0.15,0.10",
        },
        edge_attr={
            "fontname": "Courier New",
            "fontsize": "9",
        },
    )

    leaves = tree.get_all_leaves()

    for i, leaf in enumerate(leaves):
        nid = _node_id(leaf)
        label = _make_leaf_label(leaf)
        dot.node(
            nid,
            label=label,
            fillcolor=C_LEAF_FILL,
            color=C_LEAF_BORDER,
            fontcolor=C_TEXT_LEAF,
            penwidth="2",
        )

        if leaf.next is not None:
            dot.edge(
                nid,
                _node_id(leaf.next),
                color=C_LEAF_CHAIN,
                style="dashed",
                arrowhead="normal",
                penwidth="2",
                label="next→",
                fontcolor=C_LEAF_CHAIN,
            )

    return dot


def get_search_path(tree: BPlusTree, key: str) -> List[BPlusNode]:
    """
    Return the list of nodes traversed during a search for `key`.
    Used by the UI to highlight the search path in the visualization.
    """
    return tree.get_search_path(key)
