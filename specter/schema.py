"""
Data models for Code Specter.

Defines the core data structures: SpectreEntry, SemanticTag, and FeatureSpec.
"""

from dataclasses import dataclass, field, asdict
from typing import Optional
from datetime import datetime
import re


@dataclass
class SemanticTag:
    """Represents a semantic tag in generated code."""
    
    tag_type: str  # "intent" | "invariant" | "interface" | "dependency" | "pattern" | "scope"
    value: str
    line_number: int
    state: str = "inactive"  # "inactive" | "active" | "rejected"
    
    def to_comment(self) -> str:
        """Convert tag to comment format."""
        return f"# @specter:{self.tag_type}[{self.state.upper()}] {self.value}"
    
    @staticmethod
    def from_comment(line: str, line_number: int) -> Optional['SemanticTag']:
        """Parse a tag from a comment line."""
        pattern = r'#\s*@specter:(\w+)\[(\w+)\]\s+(.*)'
        match = re.match(pattern, line.strip())
        if match:
            tag_type, state, value = match.groups()
            return SemanticTag(
                tag_type=tag_type,
                value=value.strip(),
                line_number=line_number,
                state=state.lower()
            )
        return None
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return asdict(self)
    
    @staticmethod
    def from_dict(data: dict) -> 'SemanticTag':
        """Create from dictionary."""
        return SemanticTag(**data)


@dataclass
class SpectreEntry:
    """Represents a compressed semantic entry for a code module."""
    
    id: str
    description: str
    interface: str
    invariants: list[str]
    dependencies: list[str]
    patterns: list[str]
    source_files: list[str]
    created_at: str
    state: str = "active"  # "active" | "stale" | "deprecated"
    anchor: Optional[str] = None
    commit_hash: Optional[str] = None
    supersedes: Optional[str] = None
    embedding: list[float] = field(default_factory=list)
    lower_confidence: bool = False  # True for bootstrap entries
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)
    
    @staticmethod
    def from_dict(data: dict) -> 'SpectreEntry':
        """Create from dictionary."""
        return SpectreEntry(**data)
    
    def token_count(self) -> int:
        """Rough estimate of token count (1 token ≈ 4 chars)."""
        text = (
            self.description + " " +
            self.interface + " " +
            " ".join(self.invariants) + " " +
            " ".join(self.patterns)
        )
        if self.anchor:
            text += " " + self.anchor
        return len(text) // 4
    
    def semantic_surface(self) -> str:
        """Get the semantic surface for embedding."""
        return (
            self.description + " " +
            self.interface + " " +
            " ".join(self.invariants)
        )


@dataclass
class FeatureSpec:
    """Specification for a new feature to be generated."""
    
    goal: str
    constraints: list[str]
    invariants_to_preserve: list[str]
    affected_modules_estimate: list[str]
    embedding: list[float] = field(default_factory=list)
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return asdict(self)
    
    @staticmethod
    def from_dict(data: dict) -> 'FeatureSpec':
        """Create from dictionary."""
        return FeatureSpec(**data)
    
    def embedding_text(self) -> str:
        """Get text for embedding computation."""
        return (
            self.goal + " " +
            " ".join(self.constraints) + " " +
            " ".join(self.invariants_to_preserve)
        )


def create_entry_id(name: str) -> str:
    """Create a valid entry ID from a name."""
    # Convert to snake_case and remove invalid characters
    name = name.lower().strip()
    name = re.sub(r'[^\w\s-]', '', name)
    name = re.sub(r'[-\s]+', '_', name)
    return name


def get_timestamp() -> str:
    """Get current timestamp in ISO format."""
    return datetime.utcnow().isoformat() + "Z"

# Made with Bob
