from typing import List, Optional, TYPE_CHECKING
from .constants import MAX_KEYS, MIN_KEYS

if TYPE_CHECKING:
    from file_ops.metadata import FileMetadata


class BPlusNode:
    """
    A node in a B+ Tree.
    - Internal nodes: have keys and children, no values
    - Leaf nodes: have keys and values, plus a .next pointer forming a linked list
    """

    def __init__(self, is_leaf: bool = False):
        self.keys: List[str] = []                          # sorted list of keys (filenames, lowercase)
        self.children: List['BPlusNode'] = []              # INTERNAL nodes only: child node pointers
        self.values: List['FileMetadata'] = []             # LEAF nodes only: actual data records
        self.next: Optional['BPlusNode'] = None            # LEAF nodes only: pointer to next leaf
        self.is_leaf: bool = is_leaf
        self.parent: Optional['BPlusNode'] = None          # back-pointer for split propagation

    @property
    def is_full(self) -> bool:
        """True when node has MAX_KEYS keys (needs split on next insert)."""
        return len(self.keys) >= MAX_KEYS

    @property
    def is_overflowing(self) -> bool:
        """True when node has MORE than MAX_KEYS keys (must split immediately)."""
        return len(self.keys) > MAX_KEYS

    @property
    def is_underflow(self) -> bool:
        """True when non-root node falls below MIN_KEYS keys."""
        return len(self.keys) < MIN_KEYS

    def __repr__(self) -> str:
        tag = "LEAF" if self.is_leaf else "INTERNAL"
        return f"BPlusNode({tag}, keys={self.keys})"
