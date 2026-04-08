"""
B+ Tree Implementation (ORDER = 4)
===================================
Invariants maintained at all times:
  - All data lives in leaf nodes only
  - Internal nodes hold only keys as routing guides
  - Leaves are linked left→right as a sorted linked list
  - Tree is always balanced (all leaves at same depth)
  - Root may have fewer than MIN_KEYS; all other nodes must have >= MIN_KEYS

Key Convention:
  - All filename keys are stored and compared in LOWERCASE for case-insensitive matching
"""

import bisect
from datetime import datetime
from typing import List, Optional, Tuple, Dict, Any
from collections import deque

from .node import BPlusNode
from .constants import ORDER, MAX_KEYS, MIN_KEYS
from file_ops.metadata import FileMetadata


class BPlusTree:
    def __init__(self, order: int = ORDER):
        self.root: BPlusNode = BPlusNode(is_leaf=True)
        self.order: int = order
        self.total_records: int = 0
        self.operation_log: List[Dict[str, Any]] = []

    # ═══════════════════════════════════════════════════════════════
    # UTILITY
    # ═══════════════════════════════════════════════════════════════

    @staticmethod
    def _normalize(key: str) -> str:
        """Normalize key to lowercase for case-insensitive comparison."""
        return key.lower()

    def _log(
        self,
        operation: str,
        filename: str,
        result: str,
        nodes_affected: int = 1,
        split_occurred: bool = False,
        merge_occurred: bool = False,
    ) -> None:
        self.operation_log.append({
            "timestamp": datetime.now().strftime("%H:%M:%S"),
            "operation": operation,
            "filename": filename,
            "result": result,
            "nodes_affected": nodes_affected,
            "split_occurred": split_occurred,
            "merge_occurred": merge_occurred,
        })

    # ═══════════════════════════════════════════════════════════════
    # NAVIGATION / FIND LEAF
    # ═══════════════════════════════════════════════════════════════

    def find_leaf(self, key: str) -> BPlusNode:
        """
        Traverse internal nodes to find the leaf node where `key` belongs.
        At each internal node, find the rightmost key <= search key to
        determine which child to descend into.
        """
        key = self._normalize(key)
        node = self.root

        while not node.is_leaf:
            # Find insertion position using bisect
            i = bisect.bisect_right(node.keys, key)
            node = node.children[i]

        return node

    def get_search_path(self, key: str) -> List[BPlusNode]:
        """Return the list of nodes visited during a search traversal."""
        key = self._normalize(key)
        path: List[BPlusNode] = []
        node = self.root

        while not node.is_leaf:
            path.append(node)
            i = bisect.bisect_right(node.keys, key)
            node = node.children[i]

        path.append(node)
        return path

    # ═══════════════════════════════════════════════════════════════
    # SEARCH
    # ═══════════════════════════════════════════════════════════════

    def search(self, filename: str) -> Optional[FileMetadata]:
        """
        Search for a file by exact filename.
        Returns FileMetadata if found, None otherwise.
        O(log n) traversal of internal nodes, O(k) scan at leaf.
        """
        key = self._normalize(filename)
        leaf = self.find_leaf(key)

        for i, k in enumerate(leaf.keys):
            if k == key:
                self._log("SEARCH", filename, "FOUND")
                return leaf.values[i]

        self._log("SEARCH", filename, "NOT_FOUND")
        return None

    def search_range(self, start: str, end: str) -> List[FileMetadata]:
        """
        Find all files with keys in [start, end] (inclusive).
        B+ Tree advantage: jump to start leaf, then walk linked list.
        O(log n + k) where k = number of results.
        """
        start = self._normalize(start)
        end = self._normalize(end)

        if start > end:
            start, end = end, start

        results: List[FileMetadata] = []
        leaf = self.find_leaf(start)

        # Walk the leaf linked list
        while leaf is not None:
            for i, k in enumerate(leaf.keys):
                if start <= k <= end:
                    results.append(leaf.values[i])
                elif k > end:
                    return results
            leaf = leaf.next

        self._log("RANGE_QUERY", f"{start}→{end}", f"FOUND {len(results)}")
        return results

    def search_prefix(self, prefix: str) -> List[FileMetadata]:
        """
        Find all files whose filenames start with the given prefix.
        Searches using leaf linked list after jumping to the start position.
        """
        prefix = self._normalize(prefix)
        results: List[FileMetadata] = []

        leaf = self.find_leaf(prefix)

        # Also check one leaf before in case prefix sorts before start of current leaf
        # Walk from the beginning of this leaf
        while leaf is not None:
            for i, k in enumerate(leaf.keys):
                if k.startswith(prefix):
                    results.append(leaf.values[i])
                elif k > prefix and not k.startswith(prefix):
                    # Past possible matches
                    if results:  # if we already found some, we're done
                        self._log("PREFIX_SEARCH", prefix, f"FOUND {len(results)}")
                        return results
            leaf = leaf.next

        self._log("PREFIX_SEARCH", prefix, f"FOUND {len(results)}")
        return results

    # ═══════════════════════════════════════════════════════════════
    # INSERTION
    # ═══════════════════════════════════════════════════════════════

    def insert(self, filename: str, metadata: FileMetadata) -> None:
        """
        Insert a (filename, metadata) record into the B+ Tree.
        1. Find the correct leaf node
        2. Insert in sorted order
        3. If leaf overflows → split
        4. Propagate splits up as needed
        """
        key = self._normalize(filename)
        # Update metadata filename to normalized? No — keep original filename in metadata
        # but use lowercase key for indexing

        # Check for duplicate
        existing = self.search(filename)
        if existing is not None:
            self._log("INSERT", filename, "DUPLICATE_SKIPPED")
            return

        leaf = self.find_leaf(key)

        # Insert in sorted order into leaf
        pos = bisect.bisect_left(leaf.keys, key)
        leaf.keys.insert(pos, key)
        leaf.values.insert(pos, metadata)

        self.total_records += 1
        split_occurred = False

        if leaf.is_overflowing:
            split_occurred = True
            self._split_leaf(leaf)

        self._log(
            "INSERT", filename, "SUCCESS",
            nodes_affected=1,
            split_occurred=split_occurred
        )

    def _split_leaf(self, leaf: BPlusNode) -> None:
        """
        Split an overflowing leaf node.
        - Left half stays in `leaf`
        - Right half goes to `new_leaf`
        - COPY middle key up to parent (leaf split: key stays in both)
        - Update leaf linked list pointers
        """
        mid = len(leaf.keys) // 2  # split point (right half starts here)

        new_leaf = BPlusNode(is_leaf=True)
        # Right half goes to new_leaf
        new_leaf.keys = leaf.keys[mid:]
        new_leaf.values = leaf.values[mid:]

        # Left half stays in leaf
        leaf.keys = leaf.keys[:mid]
        leaf.values = leaf.values[:mid]

        # Fix leaf linked list: leaf → new_leaf → leaf.next
        new_leaf.next = leaf.next
        leaf.next = new_leaf

        # The separator key promoted to parent is the FIRST key of the right leaf
        separator = new_leaf.keys[0]

        self._insert_into_parent(leaf, separator, new_leaf)

    def _split_internal(self, node: BPlusNode) -> None:
        """
        Split an overflowing internal node.
        - Left half stays in `node`
        - Middle key is MOVED up to parent (not copied — it leaves the node)
        - Right half goes to `new_node`
        """
        mid = len(node.keys) // 2  # index of the key to push up

        separator = node.keys[mid]  # this key moves UP, not copied

        new_node = BPlusNode(is_leaf=False)
        # Right keys: everything after mid
        new_node.keys = node.keys[mid + 1:]
        # Right children: everything after mid
        new_node.children = node.children[mid + 1:]

        # Update parent pointers for moved children
        for child in new_node.children:
            child.parent = new_node

        # Left keys: everything before mid
        node.keys = node.keys[:mid]
        # Left children: first mid+1 children
        node.children = node.children[:mid + 1]

        self._insert_into_parent(node, separator, new_node)

    def _insert_into_parent(self, left: BPlusNode, key: str, right: BPlusNode) -> None:
        """
        Insert the separator `key` and child pointer `right` into the parent of `left`.
        If `left` is root → create a new root.
        If parent overflows after insert → split parent recursively.
        """
        parent = left.parent

        if parent is None:
            # `left` is the root → create a brand new root
            new_root = BPlusNode(is_leaf=False)
            new_root.keys = [key]
            new_root.children = [left, right]
            left.parent = new_root
            right.parent = new_root
            self.root = new_root
            return

        # Find position of `left` in parent's children list
        pos = parent.children.index(left)

        # Insert key and right child into parent at position pos
        parent.keys.insert(pos, key)
        parent.children.insert(pos + 1, right)
        right.parent = parent

        # If parent now overflows → split it
        if parent.is_overflowing:
            self._split_internal(parent)

    # ═══════════════════════════════════════════════════════════════
    # DELETION
    # ═══════════════════════════════════════════════════════════════

    def delete(self, filename: str) -> bool:
        """
        Delete a file record from the B+ Tree.
        1. Find leaf containing the key
        2. Remove the record
        3. If underflow → try borrow from sibling, else merge
        4. Propagate merges upward as needed
        Returns True if deleted, False if not found.
        """
        key = self._normalize(filename)
        leaf = self.find_leaf(key)

        # Find key in leaf
        if key not in leaf.keys:
            self._log("DELETE", filename, "NOT_FOUND")
            return False

        idx = leaf.keys.index(key)
        leaf.keys.pop(idx)
        leaf.values.pop(idx)
        self.total_records -= 1

        merge_occurred = False

        # Root case: if this is the root leaf, no underflow rules apply
        if leaf is self.root:
            self._log("DELETE", filename, "SUCCESS", merge_occurred=False)
            return True

        # Handle underflow
        if leaf.is_underflow:
            merge_occurred = self._fix_leaf_underflow(leaf)

        self._log("DELETE", filename, "SUCCESS", merge_occurred=merge_occurred)
        return True

    def _get_left_sibling(self, node: BPlusNode, parent: BPlusNode) -> Optional[Tuple[BPlusNode, int]]:
        """Return (left sibling, its index in parent.children)."""
        idx = parent.children.index(node)
        if idx > 0:
            return parent.children[idx - 1], idx - 1
        return None

    def _get_right_sibling(self, node: BPlusNode, parent: BPlusNode) -> Optional[Tuple[BPlusNode, int]]:
        """Return (right sibling, its index in parent.children)."""
        idx = parent.children.index(node)
        if idx < len(parent.children) - 1:
            return parent.children[idx + 1], idx + 1
        return None

    def _fix_leaf_underflow(self, leaf: BPlusNode) -> bool:
        """
        Fix leaf underflow via borrow or merge.
        Returns True if a merge occurred (need to propagate upward).
        """
        parent = leaf.parent
        if parent is None:
            return False

        leaf_idx = parent.children.index(leaf)

        # Try borrow from left sibling
        if leaf_idx > 0:
            left_sib = parent.children[leaf_idx - 1]
            if len(left_sib.keys) > MIN_KEYS:
                self._borrow_from_left_leaf(leaf, left_sib, parent, leaf_idx)
                return False

        # Try borrow from right sibling
        if leaf_idx < len(parent.children) - 1:
            right_sib = parent.children[leaf_idx + 1]
            if len(right_sib.keys) > MIN_KEYS:
                self._borrow_from_right_leaf(leaf, right_sib, parent, leaf_idx)
                return False

        # Must merge
        if leaf_idx > 0:
            # Merge leaf with its left sibling
            left_sib = parent.children[leaf_idx - 1]
            self._merge_leaves(left_sib, leaf, parent, leaf_idx)
        else:
            # Merge leaf with its right sibling
            right_sib = parent.children[leaf_idx + 1]
            self._merge_leaves(leaf, right_sib, parent, leaf_idx + 1)

        return True

    def _borrow_from_left_leaf(
        self, leaf: BPlusNode, left_sib: BPlusNode, parent: BPlusNode, leaf_idx: int
    ) -> None:
        """
        Borrow the rightmost record from left sibling and put it at the
        beginning of `leaf`. Update the separator key in parent.
        """
        borrow_key = left_sib.keys.pop(-1)
        borrow_val = left_sib.values.pop(-1)

        leaf.keys.insert(0, borrow_key)
        leaf.values.insert(0, borrow_val)

        # Update parent separator: parent.keys[leaf_idx - 1] must be the new first key of leaf
        parent.keys[leaf_idx - 1] = leaf.keys[0]

    def _borrow_from_right_leaf(
        self, leaf: BPlusNode, right_sib: BPlusNode, parent: BPlusNode, leaf_idx: int
    ) -> None:
        """
        Borrow the leftmost record from right sibling and put it at the
        end of `leaf`. Update the separator key in parent.
        """
        borrow_key = right_sib.keys.pop(0)
        borrow_val = right_sib.values.pop(0)

        leaf.keys.append(borrow_key)
        leaf.values.append(borrow_val)

        # Update parent separator: parent.keys[leaf_idx] must be new first key of right_sib
        parent.keys[leaf_idx] = right_sib.keys[0]

    def _merge_leaves(
        self, left: BPlusNode, right: BPlusNode, parent: BPlusNode, right_idx: int
    ) -> None:
        """
        Merge `right` leaf into `left` leaf.
        `right_idx` is the index of `right` in parent.children.
        After merge: remove right from parent and remove separator from parent.keys.
        """
        # Move all records from right to left
        left.keys.extend(right.keys)
        left.values.extend(right.values)

        # Fix linked list: left.next should skip right
        left.next = right.next

        # Remove right from parent
        # The separator key for right is at parent.keys[right_idx - 1]
        separator_idx = right_idx - 1
        parent.keys.pop(separator_idx)
        parent.children.pop(right_idx)

        # If parent is root and now has no keys
        if parent is self.root and len(parent.keys) == 0:
            # Left becomes the new root
            self.root = left
            left.parent = None
            return

        # If parent is not root and underflows
        if parent is not self.root and parent.is_underflow:
            self._fix_internal_underflow(parent)

    def _fix_internal_underflow(self, node: BPlusNode) -> None:
        """
        Fix internal node underflow via borrow or merge.
        """
        parent = node.parent
        if parent is None:
            return

        node_idx = parent.children.index(node)

        # Try borrow from left sibling
        if node_idx > 0:
            left_sib = parent.children[node_idx - 1]
            if len(left_sib.keys) > MIN_KEYS:
                self._borrow_from_left_internal(node, left_sib, parent, node_idx)
                return

        # Try borrow from right sibling
        if node_idx < len(parent.children) - 1:
            right_sib = parent.children[node_idx + 1]
            if len(right_sib.keys) > MIN_KEYS:
                self._borrow_from_right_internal(node, right_sib, parent, node_idx)
                return

        # Must merge
        if node_idx > 0:
            left_sib = parent.children[node_idx - 1]
            self._merge_internals(left_sib, node, parent, node_idx)
        else:
            right_sib = parent.children[node_idx + 1]
            self._merge_internals(node, right_sib, parent, node_idx + 1)

    def _borrow_from_left_internal(
        self, node: BPlusNode, left_sib: BPlusNode, parent: BPlusNode, node_idx: int
    ) -> None:
        """
        Borrow the rightmost key+child from left_sib into node via parent rotation.
        parent.keys[node_idx-1] is the separator between left_sib and node.
        """
        sep_idx = node_idx - 1

        # Pull parent separator down into node (at the front)
        node.keys.insert(0, parent.keys[sep_idx])
        # Pull rightmost child of left_sib into node
        moved_child = left_sib.children.pop(-1)
        node.children.insert(0, moved_child)
        moved_child.parent = node

        # Push rightmost key of left_sib up to parent separator
        parent.keys[sep_idx] = left_sib.keys.pop(-1)

    def _borrow_from_right_internal(
        self, node: BPlusNode, right_sib: BPlusNode, parent: BPlusNode, node_idx: int
    ) -> None:
        """
        Borrow the leftmost key+child from right_sib into node via parent rotation.
        parent.keys[node_idx] is the separator between node and right_sib.
        """
        sep_idx = node_idx

        # Pull parent separator down into node (at the end)
        node.keys.append(parent.keys[sep_idx])
        # Pull leftmost child of right_sib into node
        moved_child = right_sib.children.pop(0)
        node.children.append(moved_child)
        moved_child.parent = node

        # Push leftmost key of right_sib up to parent separator
        parent.keys[sep_idx] = right_sib.keys.pop(0)

    def _merge_internals(
        self, left: BPlusNode, right: BPlusNode, parent: BPlusNode, right_idx: int
    ) -> None:
        """
        Merge `right` internal node into `left`.
        `right_idx` is the index of `right` in parent.children.
        The separator from parent comes down into the merged node.
        """
        sep_idx = right_idx - 1
        separator = parent.keys.pop(sep_idx)

        # Bring separator down and merge all right keys/children into left
        left.keys.append(separator)
        left.keys.extend(right.keys)
        for child in right.children:
            child.parent = left
            left.children.append(child)

        parent.children.pop(right_idx)

        # Handle root collapse
        if parent is self.root and len(parent.keys) == 0:
            self.root = left
            left.parent = None
            return

        # If parent underflows and is not root → recurse
        if parent is not self.root and parent.is_underflow:
            self._fix_internal_underflow(parent)

    # ═══════════════════════════════════════════════════════════════
    # UPDATE / RENAME
    # ═══════════════════════════════════════════════════════════════

    def update(self, filename: str, **kwargs) -> bool:
        """
        Update metadata fields for an existing file.
        Key (filename) does NOT change in update.
        Supported kwargs: size_bytes, tags, path, modified_at, extension
        """
        key = self._normalize(filename)
        leaf = self.find_leaf(key)

        for i, k in enumerate(leaf.keys):
            if k == key:
                meta = leaf.values[i]
                for field, value in kwargs.items():
                    if hasattr(meta, field):
                        setattr(meta, field, value)
                meta.modified_at = datetime.now()
                self._log("UPDATE", filename, "SUCCESS")
                return True

        self._log("UPDATE", filename, "NOT_FOUND")
        return False

    def rename(self, old_name: str, new_name: str) -> bool:
        """
        Rename a file: delete(old_name) then insert(new_name, same_metadata).
        Returns False if old_name not found.
        """
        old_key = self._normalize(old_name)
        leaf = self.find_leaf(old_key)

        metadata = None
        for i, k in enumerate(leaf.keys):
            if k == old_key:
                metadata = leaf.values[i]
                break

        if metadata is None:
            self._log("RENAME", old_name, "NOT_FOUND")
            return False

        # Update the metadata to reflect new filename
        new_metadata = FileMetadata(
            filename=new_name,
            extension=metadata.extension,
            size_bytes=metadata.size_bytes,
            created_at=metadata.created_at,
            modified_at=datetime.now(),
            path=metadata.path,
            tags=metadata.tags[:],
            is_directory=metadata.is_directory,
        )

        self.delete(old_name)
        self.insert(new_name, new_metadata)
        self._log("RENAME", f"{old_name}→{new_name}", "SUCCESS")
        return True

    # ═══════════════════════════════════════════════════════════════
    # TRAVERSAL
    # ═══════════════════════════════════════════════════════════════

    def get_leftmost_leaf(self) -> BPlusNode:
        """Traverse left-most children from root until reaching a leaf."""
        node = self.root
        while not node.is_leaf:
            node = node.children[0]
        return node

    def get_all_leaves(self) -> List[BPlusNode]:
        """Walk the leaf linked list and collect all leaf nodes."""
        leaves = []
        current = self.get_leftmost_leaf()
        while current is not None:
            leaves.append(current)
            current = current.next
        return leaves

    def get_all_sorted(self) -> List[FileMetadata]:
        """
        Return ALL records in alphabetical order by walking the leaf linked list.
        O(n) — no tree traversal needed, only linked list walk.
        This demonstrates the B+ Tree range scan advantage.
        """
        results = []
        current = self.get_leftmost_leaf()
        while current is not None:
            results.extend(current.values)
            current = current.next
        return results

    def get_level_order(self) -> List[List[BPlusNode]]:
        """
        BFS traversal returning nodes grouped by level.
        Used for visualization. Returns list of levels, each level is a list of nodes.
        """
        if self.root is None:
            return []

        levels = []
        queue = deque([self.root])

        while queue:
            level_size = len(queue)
            level_nodes = []

            for _ in range(level_size):
                node = queue.popleft()
                level_nodes.append(node)
                if not node.is_leaf:
                    for child in node.children:
                        queue.append(child)

            levels.append(level_nodes)

        return levels

    # ═══════════════════════════════════════════════════════════════
    # STATISTICS
    # ═══════════════════════════════════════════════════════════════

    def get_height(self) -> int:
        """Return the height of the tree (number of levels)."""
        height = 1
        node = self.root
        while not node.is_leaf:
            node = node.children[0]
            height += 1
        return height

    def get_node_count(self) -> int:
        """Return total number of nodes (internal + leaf)."""
        count = 0
        queue = deque([self.root])
        while queue:
            node = queue.popleft()
            count += 1
            if not node.is_leaf:
                for child in node.children:
                    queue.append(child)
        return count

    def get_leaf_count(self) -> int:
        """Return number of leaf nodes."""
        return len(self.get_all_leaves())

    def get_internal_node_count(self) -> int:
        """Return number of internal nodes."""
        return self.get_node_count() - self.get_leaf_count()

    def get_fill_factor(self) -> float:
        """
        Fill factor = (total keys across all nodes) / (max possible keys).
        Measures how full the tree is (0.0 to 1.0).
        """
        total_keys = 0
        total_capacity = 0
        queue = deque([self.root])
        while queue:
            node = queue.popleft()
            total_keys += len(node.keys)
            total_capacity += MAX_KEYS
            if not node.is_leaf:
                for child in node.children:
                    queue.append(child)
        if total_capacity == 0:
            return 0.0
        return total_keys / total_capacity

    def get_total_records(self) -> int:
        """Return total number of file records stored."""
        return self.total_records

    def get_min_key(self) -> Optional[str]:
        """Return the smallest key in the tree."""
        leaf = self.get_leftmost_leaf()
        if leaf.keys:
            return leaf.keys[0]
        return None

    def get_max_key(self) -> Optional[str]:
        """Return the largest key in the tree."""
        leaves = self.get_all_leaves()
        if leaves and leaves[-1].keys:
            return leaves[-1].keys[-1]
        return None
