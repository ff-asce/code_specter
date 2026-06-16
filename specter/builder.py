"""
Mode A: Build a Specter from an existing codebase.

Walks a codebase, groups files into modules, and compresses them into Specter entries.
"""

import ast
import os
from pathlib import Path
from collections import defaultdict
from datetime import datetime
from typing import Dict, List, Set
from rich.console import Console
from rich.table import Table

from .store import SpectreStore
from .compressor import SpectreCompressor
from .retriever import SpectreRetriever
from .schema import create_entry_id, BuildReport


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
        file_patterns: List[str] = None,
        force_rebuild: bool = False
    ) -> BuildReport:
        """
        Build a Specter from a codebase.
        
        Args:
            source_root: Root directory of the codebase
            file_patterns: Glob patterns for files to include (default: ["**/*.py"])
            force_rebuild: If True, rebuild all entries even if unchanged
            
        Returns:
            BuildReport with statistics
        """
        if file_patterns is None:
            file_patterns = ["**/*.py"]
        
        source_root = Path(source_root)
        
        self.console.print(f"\n[bold]Building Specter from {source_root}[/bold]\n")
        
        # Load existing entries for incremental build
        existing_entries_map = {}
        if not force_rebuild:
            try:
                existing_entries = self.store.load_all()
                existing_entries_map = {e.id: e for e in existing_entries}
            except:
                pass
        
        # 1. DISCOVER
        self.console.print("📁 Discovering files...")
        files = self._discover_files(source_root, file_patterns)
        self.console.print(f"   Found {len(files)} Python files\n")
        
        if not files:
            self.console.print("[yellow]No files found. Exiting.[/yellow]")
            return BuildReport(
                total_files=0,
                entries_created=0,
                entries_skipped=0,
                entries_updated=0,
                entries_stale=0,
                total_raw_tokens=0,
                total_entry_tokens=0,
                overall_ratio=0.0,
                warnings=[]
            )
        
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
        
        # 5. COMPRESS (with incremental build logic)
        self.console.print("[bold]🔄 Compressing modules...[/bold]\n")
        compressed_entries = []
        entries_created = 0
        entries_skipped = 0
        entries_updated = 0
        warnings = []
        
        for i, entry_id in enumerate(ordered_ids, 1):
            file_paths = groups[entry_id]
            
            # Check if we can skip this entry (incremental build)
            if not force_rebuild and entry_id in existing_entries_map:
                existing_entry = existing_entries_map[entry_id]
                should_skip = self._should_skip_entry(existing_entry, file_paths)
                
                if should_skip:
                    self.console.print(f"[{i}/{len(ordered_ids)}] Skipping {entry_id} (unchanged)")
                    compressed_entries.append(existing_entry)
                    entries_skipped += 1
                    continue
            
            self.console.print(f"[{i}/{len(ordered_ids)}] Compressing {entry_id}...")
            
            # Get previously compressed entries as context
            all_existing = list(existing_entries_map.values()) + compressed_entries
            dep_entries = [e for e in all_existing if e.id in import_graph.get(entry_id, [])]
            
            # Compress the files
            if len(file_paths) == 1:
                entry = self.compressor.compress_file(
                    file_paths[0],
                    entry_id,
                    dep_entries
                )
            else:
                # Multiple files - combine them
                combined_code = ""
                for fp in file_paths:
                    with open(fp, 'r') as f:
                        combined_code += f"\n# File: {fp.name}\n" + f.read() + "\n"
                
                entry = self.compressor.compress_file(
                    file_paths[0],
                    entry_id,
                    dep_entries
                )
                entry.source_files = [str(fp) for fp in file_paths]
            
            compressed_entries.append(entry)
            
            # Track if this is new or updated
            if entry_id in existing_entries_map:
                entries_updated += 1
            else:
                entries_created += 1
            
            # Check for warnings
            if entry.budget_exceeded:
                warnings.append(f"{entry_id}: Token budget exceeded ({entry.compression_ratio():.1%})")
            
            # Show compression stats
            ratio = entry.compression_ratio()
            self.console.print(f"   ✓ {entry.raw_token_count} → {entry.entry_token_count} tokens ({ratio:.1%})")
        
        # 6. EMBED
        self.console.print("\n🧮 Computing embeddings...")
        compressed_entries = self.retriever.update_embeddings(compressed_entries)
        
        # 7. SAVE
        self.console.print("💾 Saving entries...")
        for entry in compressed_entries:
            self.store.save_entry(entry)
        
        # 8. BUILD REPORT
        total_raw_tokens = sum(e.raw_token_count for e in compressed_entries)
        total_entry_tokens = sum(e.entry_token_count for e in compressed_entries)
        overall_ratio = total_entry_tokens / total_raw_tokens if total_raw_tokens > 0 else 0.0
        
        report = BuildReport(
            total_files=len(files),
            entries_created=entries_created,
            entries_skipped=entries_skipped,
            entries_updated=entries_updated,
            entries_stale=0,  # TODO: Track stale entries
            total_raw_tokens=total_raw_tokens,
            total_entry_tokens=total_entry_tokens,
            overall_ratio=overall_ratio,
            warnings=warnings
        )
        
        # 9. DISPLAY REPORT
        self.console.print("\n")
        self.report(report)
        
        return report
    
    def _should_skip_entry(self, entry, file_paths: List[Path]) -> bool:
        """
        Check if an entry can be skipped (unchanged files).
        
        Args:
            entry: Existing entry
            file_paths: Current file paths for this entry
            
        Returns:
            True if entry can be skipped
        """
        # Parse entry updated_at timestamp
        try:
            entry_time = datetime.fromisoformat(entry.updated_at.replace('Z', '+00:00'))
        except:
            return False
        
        # Check if any file is newer than the entry
        for fp in file_paths:
            try:
                file_mtime = datetime.fromtimestamp(os.path.getmtime(fp))
                if file_mtime > entry_time:
                    return False
            except:
                return False
        
        return True
    
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
    
    def report(self, build_report: BuildReport) -> None:
        """
        Print a summary report of the build.
        
        Args:
            build_report: Build report with statistics
        """
        entries = self.store.load_all()
        
        # Create table
        table = Table(title="Specter Build Summary")
        table.add_column("Entry ID", style="cyan")
        table.add_column("Files", justify="right")
        table.add_column("Raw Tokens", justify="right")
        table.add_column("Entry Tokens", justify="right")
        table.add_column("Ratio", justify="right")
        table.add_column("Confidence", style="green")
        
        for entry in sorted(entries, key=lambda e: e.id):
            ratio = entry.compression_ratio()
            
            table.add_row(
                entry.id,
                str(len(entry.source_files)),
                f"{entry.raw_token_count:,}",
                f"{entry.entry_token_count:,}",
                f"{ratio:.1%}",
                entry.confidence
            )
        
        self.console.print(table)
        
        # Overall stats
        self.console.print(f"\n[bold]Build Summary[/bold]")
        self.console.print(f"  Total files: {build_report.total_files}")
        self.console.print(f"  Entries created: {build_report.entries_created}")
        self.console.print(f"  Entries updated: {build_report.entries_updated}")
        self.console.print(f"  Entries skipped: {build_report.entries_skipped} (unchanged)")
        
        self.console.print(f"\n[bold]Compression:[/bold] {build_report.overall_ratio:.1%}")
        self.console.print(f"  {build_report.total_raw_tokens:,} raw tokens → {build_report.total_entry_tokens:,} entry tokens")
        
        # Warnings
        if build_report.warnings:
            self.console.print(f"\n[yellow]Warnings:[/yellow]")
            for warning in build_report.warnings:
                self.console.print(f"  ⚠ {warning}")
        
        self.console.print("\n[yellow]Note:[/yellow] All entries are bootstrap confidence (LLM-derived, no human verification).")
        self.console.print("      Use [bold]specter query[/bold] to explore. Use [bold]specter diff <file>[/bold] after changes.\n")

