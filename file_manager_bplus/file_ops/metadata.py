from dataclasses import dataclass, field
from datetime import datetime
from typing import List


@dataclass
class FileMetadata:
    filename: str
    extension: str              # .py .txt .pdf .jpg .mp4 .csv .sql .zip .html .js
    size_bytes: int
    created_at: datetime
    modified_at: datetime
    path: str                   # virtual path: /root/docs/file.txt
    tags: List[str] = field(default_factory=list)
    is_directory: bool = False

    def size_display(self) -> str:
        """Return '12.4 KB', '3.2 MB', '1.1 GB' etc."""
        if self.size_bytes < 1024:
            return f"{self.size_bytes} B"
        elif self.size_bytes < 1024 ** 2:
            return f"{self.size_bytes / 1024:.1f} KB"
        elif self.size_bytes < 1024 ** 3:
            return f"{self.size_bytes / 1024 ** 2:.1f} MB"
        else:
            return f"{self.size_bytes / 1024 ** 3:.2f} GB"

    def age_display(self) -> str:
        """Return '3 days ago', '2 hours ago', 'just now'"""
        delta = datetime.now() - self.modified_at
        total_seconds = int(delta.total_seconds())
        if total_seconds < 60:
            return "just now"
        elif total_seconds < 3600:
            return f"{total_seconds // 60}m ago"
        elif delta.days == 0:
            return f"{total_seconds // 3600}h ago"
        elif delta.days < 7:
            return f"{delta.days}d ago"
        elif delta.days < 30:
            return f"{delta.days // 7}w ago"
        else:
            return f"{delta.days // 30}mo ago"

    def ext_icon(self) -> str:
        """Return text icon for extension"""
        icons = {
            '.py': 'PY',
            '.txt': 'TXT',
            '.pdf': 'PDF',
            '.md': 'MD',
            '.jpg': 'IMG',
            '.png': 'IMG',
            '.mp4': 'VID',
            '.csv': 'CSV',
            '.sql': 'SQL',
            '.zip': 'ZIP',
            '.html': 'WEB',
            '.js': 'JS',
            '.json': 'JSON',
            '.css': 'CSS',
        }
        return icons.get(self.extension.lower(), 'FILE')
