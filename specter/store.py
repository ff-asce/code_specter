"""
File system operations for the .specter/ directory.

Manages reading and writing Specter entries as JSON files.
"""

import json
from pathlib import Path
from typing import Optional
from .schema import SpectreEntry


class SpectreStore:
    """Manages the .specter/ directory and entry persistence."""
    
    def __init__(self, root: Path):
        """
        Initialize the store.
        
        Args:
            root: Root directory containing or to contain .specter/
        """
        self.root = Path(root)
        self.specter_dir = self.root / ".specter"
        self.entries_dir = self.specter_dir / "entries"
        self.index_file = self.specter_dir / "index.json"
    
    def init(self) -> None:
        """Create .specter/ directory structure if it doesn't exist."""
        self.specter_dir.mkdir(exist_ok=True)
        self.entries_dir.mkdir(exist_ok=True)
        
        if not self.index_file.exists():
            self._write_index({
                "entries": {},
                "version": "0.1.0",
                "created_at": self._get_timestamp()
            })
    
    def save_entry(self, entry: SpectreEntry) -> None:
        """
        Save a Specter entry to disk.
        
        Args:
            entry: The entry to save
        """
        # Write entry file
        entry_path = self.entries_dir / f"{entry.id}.json"
        with open(entry_path, 'w') as f:
            json.dump(entry.to_dict(), f, indent=2)
        
        # Update index
        index = self._read_index()
        index["entries"][entry.id] = {
            "state": entry.state,
            "file": f"entries/{entry.id}.json",
            "source_files": entry.source_files,
            "dependencies": entry.dependencies,
            "created_at": entry.created_at,
            "lower_confidence": entry.lower_confidence
        }
        self._write_index(index)
    
    def load_entry(self, entry_id: str) -> Optional[SpectreEntry]:
        """
        Load a Specter entry from disk.
        
        Args:
            entry_id: ID of the entry to load
            
        Returns:
            The entry, or None if not found
        """
        entry_path = self.entries_dir / f"{entry_id}.json"
        if not entry_path.exists():
            return None
        
        with open(entry_path, 'r') as f:
            data = json.load(f)
        
        return SpectreEntry.from_dict(data)
    
    def load_all(self) -> list[SpectreEntry]:
        """
        Load all entries from the store.
        
        Returns:
            List of all entries
        """
        index = self._read_index()
        entries = []
        
        for entry_id in index["entries"].keys():
            entry = self.load_entry(entry_id)
            if entry:
                entries.append(entry)
        
        return entries
    
    def mark_stale(self, entry_id: str) -> None:
        """
        Mark an entry as stale.
        
        Args:
            entry_id: ID of the entry to mark stale
        """
        entry = self.load_entry(entry_id)
        if entry:
            entry.state = "stale"
            self.save_entry(entry)
    
    def detect_conflicts(self, new_entry: SpectreEntry) -> list[str]:
        """
        Detect entries that conflict with a new entry.
        
        Conflicts occur when:
        - Entries depend on files that the new entry modifies
        - Entries have overlapping dependencies
        
        Args:
            new_entry: The new entry to check for conflicts
            
        Returns:
            List of conflicting entry IDs
        """
        conflicts = []
        all_entries = self.load_all()
        
        for entry in all_entries:
            if entry.id == new_entry.id:
                continue
            
            # Check if entry depends on files the new entry modifies
            file_overlap = set(entry.source_files) & set(new_entry.source_files)
            if file_overlap:
                conflicts.append(entry.id)
                continue
            
            # Check if dependencies overlap
            dep_overlap = set(entry.dependencies) & set(new_entry.dependencies)
            if dep_overlap and entry.id not in new_entry.dependencies:
                conflicts.append(entry.id)
        
        return conflicts
    
    def summary(self) -> dict:
        """
        Get summary statistics about the store.
        
        Returns:
            Dictionary with stats
        """
        entries = self.load_all()
        
        total_tokens = sum(entry.token_count() for entry in entries)
        stale_count = sum(1 for entry in entries if entry.state == "stale")
        active_count = sum(1 for entry in entries if entry.state == "active")
        bootstrap_count = sum(1 for entry in entries if entry.lower_confidence)
        
        return {
            "total_entries": len(entries),
            "active_entries": active_count,
            "stale_entries": stale_count,
            "bootstrap_entries": bootstrap_count,
            "total_tokens": total_tokens
        }
    
    def exists(self) -> bool:
        """Check if .specter/ directory exists."""
        return self.specter_dir.exists() and self.index_file.exists()
    
    def _read_index(self) -> dict:
        """Read the index file."""
        if not self.index_file.exists():
            return {"entries": {}, "version": "0.1.0"}
        
        with open(self.index_file, 'r') as f:
            return json.load(f)
    
    def _write_index(self, index: dict) -> None:
        """Write the index file."""
        with open(self.index_file, 'w') as f:
            json.dump(index, f, indent=2)
    
    @staticmethod
    def _get_timestamp() -> str:
        """Get current timestamp."""
        from datetime import datetime
        return datetime.utcnow().isoformat() + "Z"

