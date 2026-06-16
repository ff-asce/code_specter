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
    # v2 additions
    questions: list[str] = field(default_factory=list)  # Questions this entry answers
    confidence: str = "bootstrap"  # "bootstrap" | "verified"
    updated_at: Optional[str] = None  # ISO timestamp of last update
    raw_token_count: int = 0  # Token count of source files
    entry_token_count: int = 0  # Token count of this entry
    budget_exceeded: bool = False  # True if compression ratio > 0.20
    # Deprecated field (kept for v1 compatibility)
    lower_confidence: bool = False  # Use confidence field instead
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)
    
    @staticmethod
    def from_dict(data: dict) -> 'SpectreEntry':
        """Create from dictionary."""
        # Handle v1 entries without v2 fields
        if 'questions' not in data:
            data['questions'] = []
        if 'confidence' not in data:
            data['confidence'] = "bootstrap" if data.get('lower_confidence', False) else "bootstrap"
        if 'updated_at' not in data:
            data['updated_at'] = data.get('created_at')
        if 'raw_token_count' not in data:
            data['raw_token_count'] = 0
        if 'entry_token_count' not in data:
            data['entry_token_count'] = 0
        if 'budget_exceeded' not in data:
            data['budget_exceeded'] = False
        return SpectreEntry(**data)
    
    def token_count(self) -> int:
        """Rough estimate of token count (1 token ≈ 4 chars)."""
        if self.entry_token_count > 0:
            return self.entry_token_count
        
        text = (
            self.description + " " +
            self.interface + " " +
            " ".join(self.invariants) + " " +
            " ".join(self.patterns) + " " +
            " ".join(self.questions)
        )
        if self.anchor:
            text += " " + self.anchor
        return len(text) // 4
    
    def compression_ratio(self) -> float:
        """Calculate compression ratio (entry tokens / raw tokens)."""
        if self.raw_token_count == 0:
            return 0.0
        return self.entry_token_count / self.raw_token_count
    
    def retrieval_text(self) -> str:
        """Get text for embedding (v2 with questions)."""
        parts = [self.description, self.interface]
        parts.extend(self.invariants)
        parts.extend(self.questions)
        return " ".join(parts)
    
    def semantic_surface(self) -> str:
        """Get the semantic surface for embedding (v1 compatibility)."""
        return self.retrieval_text()


@dataclass
class QueryResult:
    """Result from a Specter query."""
    
    question: str
    answer: str
    sources: list[str]  # Entry IDs used
    confidence: str  # "high" | "medium" | "low" | "gap"
    gap_note: Optional[str] = None
    tokens_used: int = 0
    raw_tokens_would_have_used: int = 0
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return asdict(self)


@dataclass
class DiffResult:
    """Result from a semantic diff."""
    
    entry_id: str
    prior_entry: SpectreEntry
    new_entry: SpectreEntry
    description_changed: bool
    interface_delta: list[str]  # Added/removed interface items
    invariants_added: list[str]
    invariants_removed: list[str]
    patterns_changed: bool
    dependents_marked_stale: list[str]
    semantic_summary: str = ""
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            'entry_id': self.entry_id,
            'prior_entry': self.prior_entry.to_dict(),
            'new_entry': self.new_entry.to_dict(),
            'description_changed': self.description_changed,
            'interface_delta': self.interface_delta,
            'invariants_added': self.invariants_added,
            'invariants_removed': self.invariants_removed,
            'patterns_changed': self.patterns_changed,
            'dependents_marked_stale': self.dependents_marked_stale,
            'semantic_summary': self.semantic_summary
        }


@dataclass
class BuildReport:
    """Report from a Specter build."""
    
    total_files: int
    entries_created: int
    entries_skipped: int  # unchanged since last build
    entries_updated: int  # re-compressed
    entries_stale: int  # marked stale due to dependency changes
    total_raw_tokens: int
    total_entry_tokens: int
    overall_ratio: float
    warnings: list[str] = field(default_factory=list)
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return asdict(self)


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
