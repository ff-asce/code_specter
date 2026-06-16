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
        entry_id: str
    ) -> SpectreEntry:
        """
        Compress verified code with active tags into a Specter Entry.
        
        Args:
            source_code: The source code to compress
            active_tags: Human-activated semantic tags
            existing_dependencies: Related Specter entries
            entry_id: ID for the new entry
            
        Returns:
            SpectreEntry object
        """
        # Build the prompt
        prompt = prompts.COMPRESS_EXISTING_CODE_PROMPT.format(
            source_code=source_code,
            active_tags=prompts.format_active_tags(active_tags),
            dependencies=prompts.format_dependencies(existing_dependencies)
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
        
        # Extract JSON from response (handle markdown code blocks)
        json_text = self._extract_json(response_text)
        entry_data = json.loads(json_text)
        
        # Create SpectreEntry
        entry = SpectreEntry(
            id=entry_id,
            description=entry_data.get("description", ""),
            interface=entry_data.get("interface", ""),
            invariants=entry_data.get("invariants", []),
            dependencies=entry_data.get("dependencies", []),
            patterns=entry_data.get("patterns", []),
            anchor=entry_data.get("anchor"),
            source_files=[],  # Will be set by caller
            created_at=get_timestamp(),
            state="active",
            lower_confidence=False
        )
        
        # Check compression ratio
        source_tokens = len(source_code) // 4
        entry_tokens = entry.token_count()
        ratio = entry_tokens / source_tokens if source_tokens > 0 else 0
        
        if ratio > 0.15:
            print(f"⚠ Warning: Compression ratio {ratio:.2%} exceeds 15% target")
            print(f"  Source: {source_tokens} tokens, Entry: {entry_tokens} tokens")
        
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
            SpectreEntry object with lower_confidence=True
        """
        # Read source code
        with open(file_path, 'r') as f:
            source_code = f.read()
        
        # Build the prompt
        prompt = prompts.COMPRESS_FILE_PROMPT.format(
            source_code=source_code,
            existing_entries=prompts.format_dependencies(existing_entries)
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
        entry = SpectreEntry(
            id=entry_id,
            description=entry_data.get("description", ""),
            interface=entry_data.get("interface", ""),
            invariants=entry_data.get("invariants", []),
            dependencies=entry_data.get("dependencies", []),
            patterns=entry_data.get("patterns", []),
            anchor=entry_data.get("anchor"),
            source_files=[str(file_path)],
            created_at=get_timestamp(),
            state="active",
            lower_confidence=True  # Bootstrap entries are lower confidence
        )
        
        # Check compression ratio
        source_tokens = len(source_code) // 4
        entry_tokens = entry.token_count()
        ratio = entry_tokens / source_tokens if source_tokens > 0 else 0
        
        if ratio > 0.15:
            print(f"⚠ Warning: Compression ratio {ratio:.2%} exceeds 15% target for {entry_id}")
        
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

# Made with Bob
