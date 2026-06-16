"""
Embedding-based similarity search over Specter entries.

Uses sentence-transformers for local embeddings with fallback to TF-IDF.
"""

import numpy as np
from typing import Optional
from .schema import SpectreEntry, FeatureSpec
from .store import SpectreStore


class SpectreRetriever:
    """Retrieves relevant Specter entries using semantic similarity."""
    
    def __init__(self, store: SpectreStore):
        """
        Initialize the retriever.
        
        Args:
            store: SpectreStore instance
        """
        self.store = store
        self.embedder = None
        self._init_embedder()
    
    def _init_embedder(self):
        """Initialize the embedding model."""
        try:
            from sentence_transformers import SentenceTransformer
            self.embedder = SentenceTransformer('all-MiniLM-L6-v2')
            self.embedding_method = 'transformer'
            print("✓ Using sentence-transformers for embeddings")
        except ImportError:
            print("⚠ sentence-transformers not available, using TF-IDF fallback")
            self.embedding_method = 'tfidf'
            self._init_tfidf()
    
    def _init_tfidf(self):
        """Initialize TF-IDF vectorizer as fallback."""
        try:
            from sklearn.feature_extraction.text import TfidfVectorizer
            self.tfidf = TfidfVectorizer(max_features=384)
            self.embedding_method = 'tfidf'
        except ImportError:
            print("⚠ scikit-learn not available, using simple keyword matching")
            self.embedding_method = 'keyword'
    
    def embed(self, text: str) -> list[float]:
        """
        Generate embedding for text.
        
        Args:
            text: Text to embed
            
        Returns:
            Embedding vector as list of floats
        """
        if self.embedding_method == 'transformer':
            embedding = self.embedder.encode(text, convert_to_numpy=True)
            return embedding.tolist()
        
        elif self.embedding_method == 'tfidf':
            # For TF-IDF, we need to fit on all entries first
            # This is a simplified version - in production, fit once and reuse
            all_entries = self.store.load_all()
            texts = [e.semantic_surface() for e in all_entries] + [text]
            vectors = self.tfidf.fit_transform(texts)
            return vectors[-1].toarray()[0].tolist()
        
        else:
            # Keyword fallback - simple word frequency vector
            words = text.lower().split()
            # Create a simple 100-dim vector based on word hashes
            vector = [0.0] * 100
            for word in words:
                idx = hash(word) % 100
                vector[idx] += 1.0
            # Normalize
            norm = sum(v * v for v in vector) ** 0.5
            if norm > 0:
                vector = [v / norm for v in vector]
            return vector
    
    def cosine_similarity(self, vec1: list[float], vec2: list[float]) -> float:
        """
        Calculate cosine similarity between two vectors.
        
        Args:
            vec1: First vector
            vec2: Second vector
            
        Returns:
            Similarity score between 0 and 1
        """
        if not vec1 or not vec2:
            return 0.0
        
        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        norm1 = sum(a * a for a in vec1) ** 0.5
        norm2 = sum(b * b for b in vec2) ** 0.5
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return dot_product / (norm1 * norm2)
    
    def retrieve_slice(
        self,
        feature_spec: FeatureSpec,
        top_k: int = 5,
        token_budget: int = 3000
    ) -> list[SpectreEntry]:
        """
        Retrieve relevant Specter entries for a feature spec.
        
        Combines:
        1. Semantic search via embedding similarity
        2. Deterministic lookup for explicitly mentioned modules
        3. Dependency expansion
        
        Args:
            feature_spec: Feature specification
            top_k: Maximum number of entries to retrieve
            token_budget: Maximum tokens to return
            
        Returns:
            List of relevant entries, sorted by relevance
        """
        all_entries = self.store.load_all()
        
        if not all_entries:
            return []
        
        # Ensure feature spec has embedding
        if not feature_spec.embedding:
            feature_spec.embedding = self.embed(feature_spec.embedding_text())
        
        # 1. Semantic search
        scored_entries = []
        for entry in all_entries:
            if not entry.embedding:
                entry.embedding = self.embed(entry.semantic_surface())
            
            similarity = self.cosine_similarity(
                feature_spec.embedding,
                entry.embedding
            )
            scored_entries.append((similarity, entry))
        
        # Sort by similarity
        scored_entries.sort(key=lambda x: x[0], reverse=True)
        
        # 2. Deterministic lookup - boost explicitly mentioned modules
        mentioned_ids = set(feature_spec.affected_modules_estimate)
        for i, (score, entry) in enumerate(scored_entries):
            if entry.id in mentioned_ids:
                # Boost score significantly
                scored_entries[i] = (score + 0.5, entry)
        
        # Re-sort after boosting
        scored_entries.sort(key=lambda x: x[0], reverse=True)
        
        # 3. Take top-k
        selected = [entry for _, entry in scored_entries[:top_k]]
        
        # 4. Dependency expansion
        expanded = set(selected)
        for entry in selected:
            for dep_id in entry.dependencies:
                dep_entry = self.store.load_entry(dep_id)
                if dep_entry and dep_entry.state == 'active':
                    expanded.add(dep_entry)
        
        # Convert back to list and sort by original relevance
        result = list(expanded)
        
        # 5. Truncate to token budget
        total_tokens = 0
        final_result = []
        for entry in result:
            entry_tokens = entry.token_count()
            if total_tokens + entry_tokens <= token_budget:
                final_result.append(entry)
                total_tokens += entry_tokens
            else:
                break
        
        return final_result
    
    def update_embeddings(self, entries: list[SpectreEntry]) -> list[SpectreEntry]:
        """
        Compute embeddings for entries that don't have them.
        
        Args:
            entries: List of entries to update
            
        Returns:
            Updated entries with embeddings
        """
        for entry in entries:
            if not entry.embedding:
                entry.embedding = self.embed(entry.semantic_surface())
        
        return entries
    
    def find_similar_entries(
        self,
        entry: SpectreEntry,
        top_k: int = 3
    ) -> list[tuple[float, SpectreEntry]]:
        """
        Find entries similar to a given entry.
        
        Args:
            entry: Entry to find similar entries for
            top_k: Number of similar entries to return
            
        Returns:
            List of (similarity_score, entry) tuples
        """
        all_entries = self.store.load_all()
        
        if not entry.embedding:
            entry.embedding = self.embed(entry.semantic_surface())
        
        scored = []
        for other in all_entries:
            if other.id == entry.id:
                continue
            
            if not other.embedding:
                other.embedding = self.embed(other.semantic_surface())
            
            similarity = self.cosine_similarity(entry.embedding, other.embedding)
            scored.append((similarity, other))
        
        scored.sort(key=lambda x: x[0], reverse=True)
        return scored[:top_k]

# Made with Bob
