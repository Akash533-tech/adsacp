"""Extra tools module for B+ Tree File Manager."""
from .file_diff import FileDiff, DiffResult
from .encryptor import XOREncryptor, EncryptedFile
from .duplicate_finder import DuplicateFinder, DuplicateGroup
from .tag_index import TagIndex

__all__ = [
    "FileDiff", "DiffResult",
    "XOREncryptor", "EncryptedFile",
    "DuplicateFinder", "DuplicateGroup",
    "TagIndex",
]
