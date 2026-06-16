"""
Mode A: Build a Specter from an existing codebase.

Walks a codebase, groups files into modules, and compresses them into Specter entries.
"""

import ast
from pathlib import Path
from collections import defaultdict
from typing import Dict, List, Set
from rich.console import Console
from rich.table import Table

from .store import SpectreStore
from .compressor import SpectreCompressor
from .retriever import SpectreRetriever
from .schema import create_entry_id


class SpectreBuilder:
    """Builds a Specter from an existing codebase."""
    
    def __init__(
        self,
        store: SpectreStore,
        compressor: SpectreCompressor,
        retriever: SpectreRetriever
    ):
        """
        Initialize the builder.
        
        Args:
            store: SpectreStore instance
            compressor: SpectreCompressor instance
            retriever: SpectreRetriever instance
        """
        self.store = store
        self.compressor = compressor
        self.retriever = retriever
        self.console = Console()
    
    def build(
        self,
        source_root: Path,
        file_patterns: List[str] = None
    ) -> None:
        """
        Build a Specter from a codebase.
        
        Args:
            source_root: Root directory of the codebase
            file_patterns: Glob patterns for files to include (default: ["**/*.py"])
        """
        if file_patterns is None:
            file_patterns = ["**/*.py"]
        
        source_root = Path(source_root)
        
        self.console.print(f"\n[bold]Building Specter from {source_root}[/bold]\n")
        
        # 1. DISCOVER
        self.console.print("📁 Discovering files...")
        files = self._discover_files(source_root, file_patterns)
        self.console.print(f"   Found {len(files)} Python files\n")
        
        if not files:
            self.console.print("[yellow]No files found. Exiting.[/yellow]")
            return
        
        # 2. GROUP
        self.console.print("📦 Grouping into modules...")
        groups = self._group_files(files, source_root)
        self.console.print(f"   Created {len(groups)} entry groups\n")
        
        # 3. DETECT IMPORTS
        self.console.print("🔍 Analyzing dependencies...")
        import_graph = self._build_import_graph(groups, source_root)
        
        # 4. ORDER
        self.console.print("📊 Ordering by dependencies...")
        ordered_ids = self._topological_sort(groups, import_graph)
        self.console.print(f"   Processing order determined\n")
        
        # 5. COMPRESS
        self.console.print("[bold]🔄 Compressing modules...[/bold]\n")
        compressed_entries = []
        
        for i, entry_id in enumerate(ordered_ids, 1):
            file_paths = groups[entry_id]
            self.console.print(f"[{i}/{len(ordered_ids)}] Compressing {entry_id}...")
            
            # Get previously compressed entries as context
            existing_entries = [e for e in compressed_entries if e.id in import_graph.get(entry_id, [])]
            
            # Compress each file in the group
            if len(file_paths) == 1:
                entry = self.compressor.compress_file(
                    file_paths[0],
                    entry_id,
                    existing_entries
                )
            else:
                # Multiple files - combine them
                combined_code = ""
                for fp in file_paths:
                    with open(fp, 'r') as f:
                        combined_code += f"\n# File: {fp.name}\n" + f.read() + "\n"
                
                entry = self.compressor.compress_file(
                    file_paths[0],  # Use first file path as reference
                    entry_id,
                    existing_entries
                )
                entry.source_files = [str(fp) for fp in file_paths]
            
            compressed_entries.append(entry)
            
            # Show compression stats
            total_lines = sum(len(open(fp).readlines()) for fp in file_paths)
            self.console.print(f"   ✓ {total_lines} lines → {entry.token_count()} tokens")
        
        # 6. EMBED
        self.console.print("\n🧮 Computing embeddings...")
        compressed_entries = self.retriever.update_embeddings(compressed_entries)
        
        # 7. SAVE
        self.console.print("💾 Saving entries...")
        for entry in compressed_entries:
            self.store.save_entry(entry)
        
        # 8. REPORT
        self.console.print("\n")
        self.report()
    
    def _discover_files(
        self,
        source_root: Path,
        patterns: List[str]
    ) -> List[Path]:
        """Discover all matching files."""
        files = []
        for pattern in patterns:
            files.extend(source_root.glob(pattern))
        
        # Filter out __pycache__ and test files for demo
        files = [
            f for f in files
            if '__pycache__' not in str(f) and not f.name.startswith('test_')
        ]
        
        return sorted(files)
    
    def _group_files(
        self,
        files: List[Path],
        source_root: Path
    ) -> Dict[str, List[Path]]:
        """
        Group files into modules.
        
        Simple heuristic: files in same directory → one entry
        If directory has >500 lines, split by file.
        """
        groups = defaultdict(list)
        
        for file_path in files:
            # Get relative path from source root
            rel_path = file_path.relative_to(source_root)
            
            # Determine entry ID based on directory structure
            if rel_path.parent == Path('.'):
                # Top-level file
                entry_id = create_entry_id(file_path.stem)
            else:
                # Use directory name as module
                entry_id = create_entry_id(str(rel_path.parent).replace('/', '.'))
            
            groups[entry_id].append(file_path)
        
        # Split large groups
        final_groups = {}
        for entry_id, file_paths in groups.items():
            total_lines = sum(len(open(fp).readlines()) for fp in file_paths)
            
            if total_lines > 500 and len(file_paths) > 1:
                # Split into individual files
                for fp in file_paths:
                    file_entry_id = f"{entry_id}.{fp.stem}"
                    final_groups[file_entry_id] = [fp]
            else:
                final_groups[entry_id] = file_paths
        
        return final_groups
    
    def _detect_imports(self, file_path: Path, source_root: Path) -> Set[str]:
        """
        Detect imports from a Python file.
        
        Returns module paths that are part of the project.
        """
        try:
            with open(file_path, 'r') as f:
                tree = ast.parse(f.read(), filename=str(file_path))
        except:
            return set()
        
        imports = set()
        
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.add(alias.name.split('.')[0])
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    imports.add(node.module.split('.')[0])
        
        # Filter to only project imports (heuristic: check if module dir exists)
        project_imports = set()
        for imp in imports:
            module_path = source_root / imp
            if module_path.exists() and module_path.is_dir():
                project_imports.add(imp)
        
        return project_imports
    
    def _build_import_graph(
        self,
        groups: Dict[str, List[Path]],
        source_root: Path
    ) -> Dict[str, Set[str]]:
        """
        Build import dependency graph.
        
        Returns: {entry_id: set of entry_ids it depends on}
        """
        graph = defaultdict(set)
        
        for entry_id, file_paths in groups.items():
            for file_path in file_paths:
                imports = self._detect_imports(file_path, source_root)
                
                # Map imports to entry IDs
                for imp in imports:
                    # Find matching entry ID
                    for other_id in groups.keys():
                        if imp in other_id or other_id.startswith(imp):
                            graph[entry_id].add(other_id)
        
        return graph
    
    def _topological_sort(
        self,
        groups: Dict[str, List[Path]],
        graph: Dict[str, Set[str]]
    ) -> List[str]:
        """
        Topological sort using Kahn's algorithm.
        
        Returns ordered list of entry IDs to process.
        """
        # Calculate in-degrees
        in_degree = {entry_id: 0 for entry_id in groups.keys()}
        
        for entry_id, deps in graph.items():
            for dep in deps:
                if dep in in_degree:
                    in_degree[dep] += 1
        
        # Find nodes with no incoming edges
        queue = [entry_id for entry_id, degree in in_degree.items() if degree == 0]
        result = []
        
        while queue:
            # Sort for deterministic ordering
            queue.sort()
            node = queue.pop(0)
            result.append(node)
            
            # Remove edges from this node
            for dep in graph.get(node, []):
                if dep in in_degree:
                    in_degree[dep] -= 1
                    if in_degree[dep] == 0:
                        queue.append(dep)
        
        # If not all nodes processed, there's a cycle - just append remaining
        remaining = [eid for eid in groups.keys() if eid not in result]
        result.extend(sorted(remaining))
        
        return result
    
    def report(self) -> None:
        """Print a summary report of the built Specter."""
        summary = self.store.summary()
        entries = self.store.load_all()
        
        # Create table
        table = Table(title="Specter Build Summary")
        table.add_column("Entry ID", style="cyan")
        table.add_column("Files", justify="right")
        table.add_column("Raw Lines", justify="right")
        table.add_column("Entry Tokens", justify="right")
        table.add_column("Ratio", justify="right")
        table.add_column("State", style="green")
        
        total_lines = 0
        total_tokens = 0
        
        for entry in sorted(entries, key=lambda e: e.id):
            # Calculate raw lines
            raw_lines = 0
            for source_file in entry.source_files:
                try:
                    with open(source_file, 'r') as f:
                        raw_lines += len(f.readlines())
                except:
                    pass
            
            entry_tokens = entry.token_count()
            ratio = entry_tokens / (raw_lines * 0.25) if raw_lines > 0 else 0
            
            total_lines += raw_lines
            total_tokens += entry_tokens
            
            table.add_row(
                entry.id,
                str(len(entry.source_files)),
                str(raw_lines),
                str(entry_tokens),
                f"{ratio:.2%}",
                entry.state
            )
        
        self.console.print(table)
        
        # Overall stats
        overall_ratio = total_tokens / (total_lines * 0.25) if total_lines > 0 else 0
        
        self.console.print(f"\n[bold]Total Compression:[/bold] {overall_ratio:.1%}")
        self.console.print(f"  {summary['total_entries']} entries")
        self.console.print(f"  {total_lines} raw lines → {total_tokens} entry tokens")
        self.console.print(f"  {summary['bootstrap_entries']} bootstrap entries (lower confidence)")
        self.console.print("\n[yellow]Note:[/yellow] Bootstrap entries haven't been human-validated.")
        self.console.print("      Use [bold]specter run[/bold] for future features with validation.\n")

# Made with Bob
