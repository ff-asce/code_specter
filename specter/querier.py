"""
RAG-based querying over the Code Specter.

The querier retrieves relevant Specter entries and synthesizes answers
from their semantic content, never from raw code.
"""

import json
from typing import Optional
from anthropic import Anthropic

from .schema import SpectreEntry, QueryResult
from .retriever import SpectreRetriever
from . import prompts


class SpectreQuerier:
    """Query the Specter using natural language questions."""
    
    def __init__(self, api_key: str, retriever: Optional[SpectreRetriever] = None):
        """
        Initialize the querier.
        
        Args:
            api_key: Anthropic API key
            retriever: SpectreRetriever instance (creates default if None)
        """
        self.client = Anthropic(api_key=api_key)
        self.model = "claude-3-5-sonnet-20241022"
        self.retriever = retriever or SpectreRetriever()
    
    def query(
        self,
        question: str,
        entries: list[SpectreEntry],
        top_k: int = 5,
        show_sources: bool = True
    ) -> QueryResult:
        """
        Answer a question using the Specter.
        
        Args:
            question: Natural language question
            entries: All available Specter entries
            top_k: Number of entries to retrieve
            show_sources: Whether to include source citations
            
        Returns:
            QueryResult with answer, sources, and confidence
        """
        # Step 1: Retrieve relevant entries
        results = self.retriever.search(
            query=question,
            entries=entries,
            top_k=top_k,
            include_dependencies=True
        )
        
        if not results:
            return QueryResult(
                question=question,
                answer="No relevant Specter entries found. The codebase may not be indexed yet.",
                sources=[],
                confidence="gap",
                gap_note="No entries in the Specter",
                tokens_used=0,
                raw_tokens_would_have_used=0
            )
        
        # Step 2: Format the slice for the LLM
        slice_text = self._format_query_slice(results)
        
        # Step 3: Build the query prompt
        prompt = prompts.QUERY_PROMPT.format(
            question=question,
            slice=slice_text
        )
        
        # Step 4: Call Claude to synthesize answer
        response = self.client.messages.create(
            model=self.model,
            max_tokens=2048,
            system=prompts.SYSTEM_PROMPT,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )
        
        # Step 5: Parse response
        response_text = response.content[0].text
        json_text = self._extract_json(response_text)
        result_data = json.loads(json_text)
        
        # Step 6: Calculate efficiency metrics
        tokens_used = sum(entry.entry_token_count for entry, _ in results)
        raw_tokens_would_have_used = sum(entry.raw_token_count for entry, _ in results)
        
        # Step 7: Build QueryResult
        return QueryResult(
            question=question,
            answer=result_data.get("answer", ""),
            sources=result_data.get("sources", []),
            confidence=result_data.get("confidence", "medium"),
            gap_note=result_data.get("gap_note"),
            tokens_used=tokens_used,
            raw_tokens_would_have_used=raw_tokens_would_have_used
        )
    
    def _format_query_slice(
        self,
        results: list[tuple[SpectreEntry, float]],
        token_budget: int = 4000
    ) -> str:
        """
        Format retrieved entries for the query prompt.
        
        Args:
            results: List of (entry, score) tuples
            token_budget: Maximum tokens to include
            
        Returns:
            Formatted text for LLM context
        """
        formatted = []
        tokens_used = 0
        
        for entry, score in results:
            # Estimate tokens for this entry
            entry_text = self._format_single_entry(entry, score)
            entry_tokens = len(entry_text) // 4
            
            if tokens_used + entry_tokens > token_budget:
                break
            
            formatted.append(entry_text)
            tokens_used += entry_tokens
        
        return "\n\n".join(formatted)
    
    def _format_single_entry(self, entry: SpectreEntry, score: float) -> str:
        """
        Format a single entry for display.
        
        Args:
            entry: Specter entry
            score: Relevance score
            
        Returns:
            Formatted entry text
        """
        lines = [
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
            f"Entry: {entry.id}",
            f"Relevance: {score:.2f}",
            f"Confidence: {entry.confidence}",
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
            "",
            "Description:",
            entry.description,
            "",
            "Interface:",
            entry.interface,
        ]
        
        if entry.invariants:
            lines.append("")
            lines.append("Invariants:")
            for inv in entry.invariants:
                lines.append(f"  • {inv}")
        
        if entry.patterns:
            lines.append("")
            lines.append("Patterns:")
            for pat in entry.patterns:
                lines.append(f"  • {pat}")
        
        if entry.dependencies:
            lines.append("")
            lines.append(f"Dependencies: {', '.join(entry.dependencies)}")
        
        if entry.questions:
            lines.append("")
            lines.append("Questions this entry answers:")
            for q in entry.questions:
                lines.append(f"  • {q}")
        
        return "\n".join(lines)
    
    def _extract_json(self, text: str) -> str:
        """
        Extract JSON from response text.
        
        Handles cases where Claude wraps JSON in markdown code blocks.
        
        Args:
            text: Response text
            
        Returns:
            Clean JSON string
        """
        text = text.strip()
        
        if text.startswith("```json"):
            text = text[7:]
        elif text.startswith("```"):
            text = text[3:]
        
        if text.endswith("```"):
            text = text[:-3]
        
        return text.strip()
    
    def format_result(self, result: QueryResult, show_efficiency: bool = True) -> str:
        """
        Format a QueryResult for display.
        
        Args:
            result: Query result to format
            show_efficiency: Whether to show efficiency metrics
            
        Returns:
            Formatted text for terminal output
        """
        lines = []
        
        # Answer section
        lines.append("Answer")
        lines.append("──────")
        lines.append(result.answer)
        lines.append("")
        
        # Sources section
        if result.sources:
            lines.append("Sources")
            lines.append("───────")
            for source_id in result.sources:
                # Find the entry to get confidence
                confidence_label = "unknown"
                # This would need access to entries, simplified for now
                lines.append(f"  {source_id}  [{result.confidence}]")
            lines.append("")
        
        # Gap note if present
        if result.gap_note:
            lines.append("Gap")
            lines.append("───")
            lines.append(result.gap_note)
            lines.append("")
        
        # Efficiency metrics
        if show_efficiency and result.tokens_used > 0:
            lines.append("Efficiency")
            lines.append("──────────")
            lines.append(f"  Answered from {result.tokens_used} Specter tokens")
            lines.append(f"  Estimated raw code equivalent: {result.raw_tokens_would_have_used} tokens")
            if result.raw_tokens_would_have_used > 0:
                factor = result.raw_tokens_would_have_used / result.tokens_used
                lines.append(f"  Compression factor: {factor:.1f}×")
            lines.append("")
        
        return "\n".join(lines)


# Made with Bob