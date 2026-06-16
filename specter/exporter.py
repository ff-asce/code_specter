"""
Export the Specter to navigable documents.

Produces Markdown or JSON representations of the full Specter.
"""

import json
from pathlib import Path
from typing import Literal

from .schema import SpectreEntry


class SpectreExporter:
    """Export Specter entries to various formats."""
    
    def export_markdown(
        self,
        entries: list[SpectreEntry],
        output_path: Path,
        include_metadata: bool = True
    ) -> None:
        """
        Export Specter to a navigable Markdown document.
        
        Args:
            entries: All Specter entries
            output_path: Path to write the Markdown file
            include_metadata: Whether to include metadata section
        """
        lines = []
        
        # Header
        lines.append("# Code Specter")
        lines.append("")
        lines.append("*A compressed semantic representation of the codebase*")
        lines.append("")
        
        # Metadata
        if include_metadata:
            lines.append("## Metadata")
            lines.append("")
            lines.append(f"- **Total Entries:** {len(entries)}")
            
            total_raw = sum(e.raw_token_count for e in entries)
            total_entry = sum(e.entry_token_count for e in entries)
            overall_ratio = total_entry / total_raw if total_raw > 0 else 0
            
            lines.append(f"- **Total Raw Tokens:** {total_raw:,}")
            lines.append(f"- **Total Entry Tokens:** {total_entry:,}")
            lines.append(f"- **Overall Compression:** {overall_ratio:.1%}")
            
            bootstrap_count = sum(1 for e in entries if e.confidence == "bootstrap")
            verified_count = sum(1 for e in entries if e.confidence == "verified")
            
            lines.append(f"- **Bootstrap Entries:** {bootstrap_count}")
            lines.append(f"- **Verified Entries:** {verified_count}")
            
            stale_count = sum(1 for e in entries if e.state == "stale")
            if stale_count > 0:
                lines.append(f"- **Stale Entries:** {stale_count}")
            
            lines.append("")
        
        # Table of Contents
        lines.append("## Table of Contents")
        lines.append("")
        for entry in sorted(entries, key=lambda e: e.id):
            lines.append(f"- [{entry.id}](#{self._anchor_id(entry.id)})")
        lines.append("")
        
        # Entries
        lines.append("## Entries")
        lines.append("")
        
        for entry in sorted(entries, key=lambda e: e.id):
            lines.extend(self._format_entry_markdown(entry))
            lines.append("")
        
        # Write to file
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w') as f:
            f.write("\n".join(lines))
    
    def export_json(
        self,
        entries: list[SpectreEntry],
        output_path: Path,
        pretty: bool = True
    ) -> None:
        """
        Export Specter to JSON.
        
        Args:
            entries: All Specter entries
            output_path: Path to write the JSON file
            pretty: Whether to pretty-print the JSON
        """
        data = {
            "version": "2",
            "entries": [entry.to_dict() for entry in entries],
            "metadata": {
                "total_entries": len(entries),
                "total_raw_tokens": sum(e.raw_token_count for e in entries),
                "total_entry_tokens": sum(e.entry_token_count for e in entries),
                "bootstrap_count": sum(1 for e in entries if e.confidence == "bootstrap"),
                "verified_count": sum(1 for e in entries if e.confidence == "verified"),
                "stale_count": sum(1 for e in entries if e.state == "stale")
            }
        }
        
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w') as f:
            if pretty:
                json.dump(data, f, indent=2)
            else:
                json.dump(data, f)
    
    def _format_entry_markdown(self, entry: SpectreEntry) -> list[str]:
        """
        Format a single entry as Markdown.
        
        Args:
            entry: Entry to format
            
        Returns:
            List of lines
        """
        lines = []
        
        # Header
        lines.append(f"### {entry.id}")
        lines.append("")
        
        # Badges
        badges = []
        badges.append(f"![confidence]({entry.confidence})")
        badges.append(f"![state]({entry.state})")
        
        ratio = entry.compression_ratio()
        if ratio > 0:
            badges.append(f"![ratio]({ratio:.1%})")
        
        lines.append(" ".join(badges))
        lines.append("")
        
        # Description
        lines.append("**Description:**")
        lines.append("")
        lines.append(entry.description)
        lines.append("")
        
        # Interface
        lines.append("**Interface:**")
        lines.append("")
        lines.append("```")
        lines.append(entry.interface)
        lines.append("```")
        lines.append("")
        
        # Invariants
        if entry.invariants:
            lines.append("**Invariants:**")
            lines.append("")
            for inv in entry.invariants:
                lines.append(f"- {inv}")
            lines.append("")
        
        # Patterns
        if entry.patterns:
            lines.append("**Patterns:**")
            lines.append("")
            for pat in entry.patterns:
                lines.append(f"- {pat}")
            lines.append("")
        
        # Questions
        if entry.questions:
            lines.append("**Questions this entry answers:**")
            lines.append("")
            for q in entry.questions:
                lines.append(f"- {q}")
            lines.append("")
        
        # Dependencies
        if entry.dependencies:
            lines.append("**Dependencies:**")
            lines.append("")
            for dep in entry.dependencies:
                lines.append(f"- [{dep}](#{self._anchor_id(dep)})")
            lines.append("")
        
        # Anchor (if present)
        if entry.anchor:
            lines.append("**Anchor:**")
            lines.append("")
            lines.append("```python")
            lines.append(entry.anchor)
            lines.append("```")
            lines.append("")
        
        # Metadata
        lines.append("<details>")
        lines.append("<summary>Metadata</summary>")
        lines.append("")
        lines.append(f"- **Source Files:** {', '.join(entry.source_files)}")
        lines.append(f"- **Created:** {entry.created_at}")
        lines.append(f"- **Updated:** {entry.updated_at}")
        lines.append(f"- **Raw Tokens:** {entry.raw_token_count:,}")
        lines.append(f"- **Entry Tokens:** {entry.entry_token_count:,}")
        
        if entry.commit_hash:
            lines.append(f"- **Commit:** `{entry.commit_hash}`")
        
        if entry.supersedes:
            lines.append(f"- **Supersedes:** [{entry.supersedes}](#{self._anchor_id(entry.supersedes)})")
        
        if entry.budget_exceeded:
            lines.append("- **⚠ Budget Exceeded:** This entry exceeds the token budget")
        
        lines.append("")
        lines.append("</details>")
        
        lines.append("")
        lines.append("---")
        
        return lines
    
    def _anchor_id(self, entry_id: str) -> str:
        """
        Convert entry ID to Markdown anchor.
        
        Args:
            entry_id: Entry ID
            
        Returns:
            Anchor string
        """
        return entry_id.lower().replace(".", "").replace("_", "-")


# Made with Bob