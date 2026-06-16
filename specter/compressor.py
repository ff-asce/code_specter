"""
LLM-based compression of code into Specter Entries.

Handles both verified code with active tags and bootstrap compression.
"""

import json
from pathlib import Path
from typing import Optional
from anthropic import Anthropic

from .schema import SpectreEntry, SemanticTag, get_timestamp
from . import prompts


class SpectreCompressor:
    """Compresses code into Specter Entries using Claude."""
    
    def __init__(self, api_key: str):
        """
        Initialize the compressor.
        
        Args:
            api_key: Anthropic API key
        """
        self.client = Anthropic(api_key=api_key)
        self.model = "claude-3-5-sonnet-20241022"
    
    def compress(
        self,
        source_code: str,
        active_tags: list[SemanticTag],
        existing_dependencies: list[SpectreEntry],
        entry_id: str,
        source_files: Optional[list[str]] = None
    ) -> SpectreEntry:
        """
        Compress verified code with active tags into a Specter Entry.
        
        Args:
            source_code: The source code to compress
            active_tags: Human-activated semantic tags
            existing_dependencies: Related Specter entries
            entry_id: ID for the new entry
            source_files: List of source file paths
            
        Returns:
            SpectreEntry object
        """
        # Calculate raw token count
        raw_token_count = self._estimate_tokens(source_code)
        
        # Build the prompt
        active_tags_section = ""
        if active_tags:
            active_tags_section = f"Active tags (human-validated):\n{prompts.format_active_tags(active_tags)}"
        
        prompt = prompts.COMPRESS_FILE_PROMPT.format(
            dependency_context=prompts.format_dependencies(existing_dependencies),
            source_files=source_code,
            active_tags_section=active_tags_section
        )
        
        # Call Claude with JSON mode
        response = self.client.messages.create(
            model=self.model,
            max_tokens=4096,
            system=prompts.SYSTEM_PROMPT,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )
        
        # Parse JSON response
        response_text = response.content[0].text
        json_text = self._extract_json(response_text)
        entry_data = json.loads(json_text)
        
        # Create SpectreEntry
        timestamp = get_timestamp()
        entry = SpectreEntry(
            id=entry_id,
            description=entry_data.get("description", ""),
            interface=entry_data.get("interface", ""),
            invariants=entry_data.get("invariants", []),
            dependencies=entry_data.get("dependencies", []),
            patterns=entry_data.get("patterns", []),
            anchor=entry_data.get("anchor"),
            questions=entry_data.get("questions", []),
            source_files=source_files or [],
            created_at=timestamp,
            updated_at=timestamp,
            state="active",
            confidence="verified" if active_tags else "bootstrap",
            raw_token_count=raw_token_count,
            entry_token_count=0,  # Will be calculated below
            budget_exceeded=False
        )
        
        # Calculate entry token count
        entry.entry_token_count = self._estimate_tokens(entry.retrieval_text())
        
        # Check compression ratio and retry if needed
        ratio = entry.compression_ratio()
        if ratio > 0.20:
            print(f"⚠ Compression ratio {ratio:.1%} exceeds budget, attempting to tighten...")
            entry = self._tighten_entry(entry, ratio)
            ratio = entry.compression_ratio()
            
            if ratio > 0.20:
                print(f"⚠ Still over budget after tightening: {ratio:.1%}")
                entry.budget_exceeded = True
        
        if ratio > 0.15:
            print(f"⚠ Warning: Compression ratio {ratio:.1%} exceeds 15% target for {entry_id}")
        
        return entry
    
    def compress_file(
        self,
        file_path: Path,
        entry_id: str,
        existing_entries: list[SpectreEntry]
    ) -> SpectreEntry:
        """
        Compress a file in bootstrap mode (no human-validated tags).
        
        Args:
            file_path: Path to the file to compress
            entry_id: ID for the new entry
            existing_entries: Previously compressed entries for context
            
        Returns:
            SpectreEntry object with confidence="bootstrap"
        """
        # Read source code
        with open(file_path, 'r') as f:
            source_code = f.read()
        
        # Use the main compress method with no active tags
        return self.compress(
            source_code=source_code,
            active_tags=[],
            existing_dependencies=existing_entries,
            entry_id=entry_id,
            source_files=[str(file_path)]
        )
    
    def _estimate_tokens(self, text: str) -> int:
        """
        Estimate token count for text.
        
        Uses rough approximation: 1 token ≈ 4 characters.
        
        Args:
            text: Text to estimate
            
        Returns:
            Estimated token count
        """
        return len(text) // 4
    
    def _tighten_entry(self, entry: SpectreEntry, current_ratio: float) -> SpectreEntry:
        """
        Attempt to tighten an entry that exceeds the token budget.
        
        Args:
            entry: Entry to tighten
            current_ratio: Current compression ratio
            
        Returns:
            Tightened entry
        """
        # Build tighten prompt
        entry_json = json.dumps(entry.to_dict(), indent=2)
        prompt = prompts.TIGHTEN_PROMPT.format(
            ratio=current_ratio,
            entry=entry_json
        )
        
        # Call Claude
        response = self.client.messages.create(
            model=self.model,
            max_tokens=4096,
            system=prompts.SYSTEM_PROMPT,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )
        
        # Parse response
        response_text = response.content[0].text
        json_text = self._extract_json(response_text)
        tightened_data = json.loads(json_text)
        
        # Update entry with tightened data
        entry.description = tightened_data.get("description", entry.description)
        entry.interface = tightened_data.get("interface", entry.interface)
        entry.invariants = tightened_data.get("invariants", entry.invariants)
        entry.dependencies = tightened_data.get("dependencies", entry.dependencies)
        entry.patterns = tightened_data.get("patterns", entry.patterns)
        entry.anchor = tightened_data.get("anchor", entry.anchor)
        entry.questions = tightened_data.get("questions", entry.questions)
        
        # Recalculate entry token count
        entry.entry_token_count = self._estimate_tokens(entry.retrieval_text())
        entry.updated_at = get_timestamp()
        
        return entry
    
    def _extract_json(self, text: str) -> str:
        """
        Extract JSON from response text.
        
        Handles cases where Claude wraps JSON in markdown code blocks.
        
        Args:
            text: Response text
            
        Returns:
            Clean JSON string
        """
        # Remove markdown code blocks if present
        text = text.strip()
        
        if text.startswith("```json"):
            text = text[7:]  # Remove ```json
        elif text.startswith("```"):
            text = text[3:]  # Remove ```
        
        if text.endswith("```"):
            text = text[:-3]  # Remove trailing ```
        
        return text.strip()
    
    def generate_spec(self, intent: str, existing_entries: list[SpectreEntry]) -> dict:
        """
        Generate a Feature Spec from human intent.
        
        Args:
            intent: Human intent string
            existing_entries: Existing Specter entries for context
            
        Returns:
            Dictionary with spec data
        """
        prompt = prompts.GENERATE_SPEC_PROMPT.format(
            intent=intent,
            existing_entries_summary=prompts.format_entries_summary(existing_entries)
        )
        
        response = self.client.messages.create(
            model=self.model,
            max_tokens=2048,
            system=prompts.SYSTEM_PROMPT,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )
        
        response_text = response.content[0].text
        json_text = self._extract_json(response_text)
        return json.loads(json_text)
    
    def generate_code(
        self,
        feature_spec: dict,
        specter_slice: list[SpectreEntry]
    ) -> str:
        """
        Generate code with inactive semantic tags.
        
        Args:
            feature_spec: Feature specification
            specter_slice: Relevant Specter entries
            
        Returns:
            Generated Python code with inactive tags
        """
        prompt = prompts.GENERATE_CODE_PROMPT.format(
            feature_spec=json.dumps(feature_spec, indent=2),
            specter_slice=prompts.format_specter_slice(specter_slice)
        )
        
        response = self.client.messages.create(
            model=self.model,
            max_tokens=8192,
            system=prompts.SYSTEM_PROMPT,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )
        
        code = response.content[0].text
        
        # Remove markdown code blocks if present
        if code.startswith("```python"):
            code = code[9:]
        elif code.startswith("```"):
            code = code[3:]
        
        if code.endswith("```"):
            code = code[:-3]
        
        return code.strip()

