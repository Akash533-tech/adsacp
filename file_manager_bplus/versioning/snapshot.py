"""
File Versioning — Snapshot Manager (Module 3)
==============================================
Implements undo/redo and named snapshots via deep-copied B+ Tree roots.
copy.deepcopy() is mandatory — shallow copies share node references and
will produce incorrect state when the original tree is modified.
"""

from __future__ import annotations

import copy
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Dict, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from bplus.bplus_tree import BPlusTree
    from bplus.node import BPlusNode


# ─────────────────────────────────────────────────────────────────────────────
# Data classes
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class Snapshot:
    snapshot_id: str                   # UUID
    label: str                         # human-visible name
    operation: str                     # "insert" | "delete" | "rename" | "manual"
    timestamp: datetime
    file_count: int
    tree_root: "BPlusNode"             # deep copy of root at this moment
    tree_order: int = 4                # preserve the tree's order


@dataclass
class SnapshotDiff:
    files_added: List[str]
    files_deleted: List[str]
    files_unchanged: List[str]


# ─────────────────────────────────────────────────────────────────────────────
# SnapshotManager
# ─────────────────────────────────────────────────────────────────────────────

class SnapshotManager:
    """
    Manages named snapshots plus an undo/redo stack for a BPlusTree.

    - take_snapshot()  → capture current state BEFORE a destructive op
    - undo()           → pop undo_stack, push current to redo_stack
    - redo()           → pop redo_stack, push current to undo_stack
    - restore_snapshot()  → jump to any named snapshot
    - diff_snapshots() → compare which files changed between two snapshots
    """

    MAX_SNAPSHOTS = 20

    def __init__(self) -> None:
        self.snapshots: List[Snapshot] = []       # named history
        self.undo_stack: List[Snapshot] = []      # undo history
        self.redo_stack: List[Snapshot] = []      # redo after undo

    # ── CAPTURE ──────────────────────────────────────────────────────────────

    def take_snapshot(
        self,
        tree: "BPlusTree",
        label: str,
        operation: str = "manual",
    ) -> Snapshot:
        """
        Deep-copy the current tree root and store as a Snapshot.
        Clears the redo stack (branching off a new history path).
        Evicts the oldest snapshot if we exceed MAX_SNAPSHOTS.
        """
        snap = Snapshot(
            snapshot_id=str(uuid.uuid4()),
            label=label,
            operation=operation,
            timestamp=datetime.now(),
            file_count=tree.total_records,
            tree_root=copy.deepcopy(tree.root),
            tree_order=tree.order,
        )
        self.snapshots.append(snap)
        self.undo_stack.append(snap)
        self.redo_stack.clear()          # new action invalidates redo history

        if len(self.snapshots) > self.MAX_SNAPSHOTS:
            self.snapshots.pop(0)

        return snap

    # ── UNDO / REDO ───────────────────────────────────────────────────────────

    def undo(self, current_tree: "BPlusTree") -> Optional["BPlusTree"]:
        """
        Pop the most recent snapshot from undo_stack.
        Push the current tree state onto redo_stack.
        Return a new BPlusTree restored to that snapshot.
        Returns None if undo_stack is empty.
        """
        if not self.undo_stack:
            return None

        # Save current state for redo
        redo_snap = Snapshot(
            snapshot_id=str(uuid.uuid4()),
            label="(redo point)",
            operation="undo",
            timestamp=datetime.now(),
            file_count=current_tree.total_records,
            tree_root=copy.deepcopy(current_tree.root),
            tree_order=current_tree.order,
        )
        self.redo_stack.append(redo_snap)

        snap = self.undo_stack.pop()
        return self._rebuild_tree(snap, current_tree)

    def redo(self, current_tree: "BPlusTree") -> Optional["BPlusTree"]:
        """
        Pop the most recent redo snapshot.
        Push current state onto undo_stack.
        Return restored tree.
        """
        if not self.redo_stack:
            return None

        undo_snap = Snapshot(
            snapshot_id=str(uuid.uuid4()),
            label="(undo point)",
            operation="redo",
            timestamp=datetime.now(),
            file_count=current_tree.total_records,
            tree_root=copy.deepcopy(current_tree.root),
            tree_order=current_tree.order,
        )
        self.undo_stack.append(undo_snap)

        snap = self.redo_stack.pop()
        return self._rebuild_tree(snap, current_tree)

    # ── RESTORE ───────────────────────────────────────────────────────────────

    def restore_snapshot(
        self,
        snapshot_id: str,
        current_tree: "BPlusTree",
    ) -> "BPlusTree":
        """
        Restore to any named snapshot by ID.
        Push current state onto undo_stack before restoring.
        """
        target = next((s for s in self.snapshots if s.snapshot_id == snapshot_id), None)
        if target is None:
            return current_tree

        # Save current state for undo
        self.undo_stack.append(Snapshot(
            snapshot_id=str(uuid.uuid4()),
            label="(before restore)",
            operation="manual",
            timestamp=datetime.now(),
            file_count=current_tree.total_records,
            tree_root=copy.deepcopy(current_tree.root),
            tree_order=current_tree.order,
        ))
        self.redo_stack.clear()
        return self._rebuild_tree(target, current_tree)

    # ── DIFF ─────────────────────────────────────────────────────────────────

    def diff_snapshots(self, snap_a: Snapshot, snap_b: Snapshot) -> SnapshotDiff:
        """
        Compare two snapshots.
        files_added   = in B but not A
        files_deleted = in A but not B
        files_unchanged = in both
        """
        keys_a = self._extract_keys(snap_a.tree_root)
        keys_b = self._extract_keys(snap_b.tree_root)

        set_a = set(keys_a)
        set_b = set(keys_b)

        return SnapshotDiff(
            files_added=sorted(set_b - set_a),
            files_deleted=sorted(set_a - set_b),
            files_unchanged=sorted(set_a & set_b),
        )

    # ── LIST ─────────────────────────────────────────────────────────────────

    def get_snapshot_list(self) -> List[Dict]:
        """Return list of {id, label, operation, timestamp, file_count}."""
        return [
            {
                "snapshot_id": s.snapshot_id,
                "label":       s.label,
                "operation":   s.operation,
                "timestamp":   s.timestamp,
                "file_count":  s.file_count,
            }
            for s in self.snapshots
        ]

    # ── INTERNAL ─────────────────────────────────────────────────────────────

    def _rebuild_tree(self, snap: Snapshot, prototype: "BPlusTree") -> "BPlusTree":
        """Create a new BPlusTree instance with the snapshot's root."""
        from bplus.bplus_tree import BPlusTree
        new_tree = BPlusTree(order=snap.tree_order)
        new_tree.root = copy.deepcopy(snap.tree_root)
        # Recount total records from leaf linked list
        new_tree.total_records = 0
        node = new_tree.root
        while not node.is_leaf:
            node = node.children[0]
        current = node
        while current is not None:
            new_tree.total_records += len(current.keys)
            current = current.next
        # Preserve operation log from original
        new_tree.operation_log = prototype.operation_log[:]
        return new_tree

    def _extract_keys(self, root: "BPlusNode") -> List[str]:
        """Walk leaf linked list of a detached root, collect all keys."""
        keys = []
        # Find leftmost leaf
        node = root
        while not node.is_leaf:
            node = node.children[0]
        current = node
        while current is not None:
            keys.extend(current.keys)
            current = current.next
        return keys
