"""
Semantic diff for Specter entries.

Shows what the *meaning* of code changed, not what the lines changed.
"""

import json
from pathlib import Path
from typing import Optional
from anthropic import Anthropic

from .schema import SpectreEntry, DiffResult, get_timestamp
from .compressor import SpectreCompressor
from .store import SpectreStore
from . import prompts


class SpectreDigger:
    """Generate semantic diffs for changed code."""
    
    def __init__(self, api_key: str, compressor: Optional[SpectreCompressor] = None):
        """
        Initialize the differ.
        
        Args:
            api_key: Anthropic API key
            compressor: SpectreCompressor instance (creates default if None)
        """
        self.client = Anthropic(api_key=api_key)
        self.model = "claude-3-5-sonnet-20241022"
        self.compressor = compressor or SpectreCompressor(api_key)
    
    def diff(
        self,
        file_path: Path,
        store: SpectreStore,
        existing_entries: list[SpectreEntry]
    ) -> DiffResult:
        """
        Generate a semantic diff for a changed file.
        
        Args:
            file_path: Path to the changed file
            store: Specter store
            existing_entries: All existing entries for context
            
        Returns:
            DiffResult showing semantic changes
        """
        # Step 1: Find the entry that covers this file
        file_str = str(file_path)
        prior_entry = None
        
        for entry in existing_entries:
            if file_str in entry.source_files:
                prior_entry = entry
                break
        
        if not prior_entry:
            raise ValueError(f"No existing entry found for {file_path}")
        
        # Step 2: Re-compress the current file
        new_entry = self.compressor.compress_file(
            file_path=file_path,
            entry_id=prior_entry.id,
            existing_entries=[e for e in existing_entries if e.id != prior_entry.id]
        )
        
        # Step 3: Compare entries
        description_changed = prior_entry.description != new_entry.description
        
        # Interface delta
        interface_delta = self._compute_interface_delta(
            prior_entry.interface,
            new_entry.interface
        )
        
        # Invariants changes
        prior_invariants = set(prior_entry.invariants)
        new_invariants = set(new_entry.invariants)
        invariants_added = list(new_invariants - prior_invariants)
        invariants_removed = list(prior_invariants - new_invariants)
        
        # Patterns changed
        patterns_changed = set(prior_entry.patterns) != set(new_entry.patterns)
        
        # Step 4: Generate semantic summary
        semantic_summary = self._generate_semantic_summary(prior_entry, new_entry)
        
        # Step 5: Find dependents and mark them stale
        dependents_marked_stale = []
        for entry in existing_entries:
            if prior_entry.id in entry.dependencies:
                store.mark_stale(entry.id)
                dependents_marked_stale.append(entry.id)
        
        # Step 6: Save the new entry
        store.save_entry(new_entry)
        
        # Step 7: Mark prior entry as superseded
        if prior_entry.id != new_entry.id:
            new_entry.supersedes = prior_entry.id
            store.save_entry(new_entry)
        
        return DiffResult(
            entry_id=prior_entry.id,
            prior_entry=prior_entry,
            new_entry=new_entry,
            description_changed=description_changed,
            interface_delta=interface_delta,
            invariants_added=invariants_added,
            invariants_removed=invariants_removed,
            patterns_changed=patterns_changed,
            dependents_marked_stale=dependents_marked_stale,
            semantic_summary=semantic_summary
        )
    
    def _compute_interface_delta(self, prior: str, new: str) -> list[str]:
        """
        Compute interface changes.
        
        Args:
            prior: Prior interface text
            new: New interface text
            
        Returns:
            List of changes (prefixed with + or -)
        """
        # Simple line-based diff for now
        prior_lines = set(line.strip() for line in prior.split('\n') if line.strip())
        new_lines = set(line.strip() for line in new.split('\n') if line.strip())
        
        delta = []
        
        # Removed items
        for line in sorted(prior_lines - new_lines):
            delta.append(f"- {line}")
        
        # Added items
        for line in sorted(new_lines - prior_lines):
            delta.append(f"+ {line}")
        
        return delta
    
    def _generate_semantic_summary(
        self,
        prior_entry: SpectreEntry,
        new_entry: SpectreEntry
    ) -> str:
        """
        Generate a semantic summary of changes using LLM.
        
        Args:
            prior_entry: Prior entry
            new_entry: New entry
            
        Returns:
            Semantic summary text
        """
        prompt = prompts.SEMANTIC_DIFF_PROMPT.format(
            prior_entry=json.dumps(prior_entry.to_dict(), indent=2),
            new_entry=json.dumps(new_entry.to_dict(), indent=2)
        )
        
        response = self.client.messages.create(
            model=self.model,
            max_tokens=1024,
            system=prompts.SYSTEM_PROMPT,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )
        
        return response.content[0].text.strip()
    
    def format_diff(self, diff: DiffResult) -> str:
        """
        Format a DiffResult for display.
        
        Args:
            diff: Diff result to format
            
        Returns:
            Formatted text for terminal output
        """
        lines = []
        
        lines.append(f"Semantic diff: {diff.entry_id}")
        lines.append("─" * (15 + len(diff.entry_id)))
        lines.append("")
        
        # Description
        lines.append("Description")
        if diff.description_changed:
            lines.append("  ~ Changed (see below)")
            lines.append(f"  - {diff.prior_entry.description[:80]}...")
            lines.append(f"  + {diff.new_entry.description[:80]}...")
        else:
            lines.append("  ✓ Unchanged")
        lines.append("")
        
        # Interface
        lines.append("Interface")
        if diff.interface_delta:
            for change in diff.interface_delta:
                if change.startswith("+"):
                    lines.append(f"  {change}  ← ADDED")
                else:
                    lines.append(f"  {change}  ← REMOVED")
        else:
            lines.append("  ✓ Unchanged")
        lines.append("")
        
        # Invariants
        lines.append("Invariants")
        if diff.invariants_removed:
            for inv in diff.invariants_removed:
                lines.append(f"  - {inv}  ← REMOVED")
        if diff.invariants_added:
            for inv in diff.invariants_added:
                lines.append(f"  + {inv}  ← ADDED")
        if not diff.invariants_added and not diff.invariants_removed:
            # Show unchanged invariants
            for inv in diff.new_entry.invariants:
                lines.append(f"  ✓ {inv}  (unchanged)")
        lines.append("")
        
        # Patterns
        lines.append("Patterns")
        if diff.patterns_changed:
            lines.append("  ~ Changed")
            for pat in diff.prior_entry.patterns:
                if pat not in diff.new_entry.patterns:
                    lines.append(f"    - {pat}")
            for pat in diff.new_entry.patterns:
                if pat not in diff.prior_entry.patterns:
                    lines.append(f"    + {pat}")
        else:
            for pat in diff.new_entry.patterns:
                lines.append(f"  ~ \"{pat}\" (unchanged)")
        lines.append("")
        
        # Semantic summary
        if diff.semantic_summary:
            lines.append("Semantic Summary")
            lines.append("────────────────")
            lines.append(diff.semantic_summary)
            lines.append("")
        
        # Downstream impact
        if diff.dependents_marked_stale:
            lines.append("Downstream impact")
            lines.append("─────────────────")
            for dep_id in diff.dependents_marked_stale:
                lines.append(f"  ⚠ {dep_id} — marked stale (depends on {diff.entry_id})")
            lines.append("")
            lines.append("  Run `specter diff` on these files if they were also changed.")
            lines.append("")
        
        # Entry update info
        confidence_change = f"{diff.prior_entry.confidence} → {diff.new_entry.confidence}"
        lines.append(f"Entry updated: {diff.entry_id} ({confidence_change})")
        
        return "\n".join(lines)


