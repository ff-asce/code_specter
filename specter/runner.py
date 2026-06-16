"""
Mode B: Feature Development Loop.

Generates features with semantic tag activation and compression.
"""

from pathlib import Path
from typing import Optional
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax

from .store import SpectreStore
from .compressor import SpectreCompressor
from .retriever import SpectreRetriever
from .tagger import Tagger
from .schema import FeatureSpec, create_entry_id


class SpectreRunner:
    """Runs the feature development loop."""
    
    def __init__(
        self,
        store: SpectreStore,
        compressor: SpectreCompressor,
        retriever: SpectreRetriever,
        tagger: Tagger
    ):
        """
        Initialize the runner.
        
        Args:
            store: SpectreStore instance
            compressor: SpectreCompressor instance
            retriever: SpectreRetriever instance
            tagger: Tagger instance
        """
        self.store = store
        self.compressor = compressor
        self.retriever = retriever
        self.tagger = tagger
        self.console = Console()
    
    def run(self, intent: str, output_file: Optional[Path] = None) -> None:
        """
        Run the complete feature development loop.
        
        Args:
            intent: Human intent string describing the feature
            output_file: Optional path to write generated code
        """
        self.console.print("\n[bold cyan]Code Specter - Feature Development Loop[/bold cyan]\n")
        
        # 1. SPEC GENERATION
        self.console.print("[bold]Step 1: Generating Feature Spec[/bold]")
        existing_entries = self.store.load_all()
        spec_data = self.compressor.generate_spec(intent, existing_entries)
        spec = FeatureSpec.from_dict(spec_data)
        
        self._print_spec(spec)
        
        # Confirm spec
        confirm = input("\nProceed with this spec? [y/n/edit]: ").strip().lower()
        if confirm == 'n':
            self.console.print("[yellow]Aborted.[/yellow]")
            return
        elif confirm == 'edit':
            spec = self._edit_spec(spec)
        
        # 2. SPECTER RETRIEVAL
        self.console.print("\n[bold]Step 2: Retrieving from Specter[/bold]")
        specter_slice = self.retriever.retrieve_slice(spec, top_k=5, token_budget=3000)
        
        self._print_slice_summary(specter_slice)
        
        # 3. CODE GENERATION
        self.console.print("\n[bold]Step 3: Generating Code[/bold]")
        self.console.print("Calling Claude to generate code with semantic tags...")
        
        generated_code = self.compressor.generate_code(spec.to_dict(), specter_slice)
        
        # Write to file if specified
        if output_file:
            output_path = Path(output_file)
            output_path.write_text(generated_code)
            self.console.print(f"✓ Code written to {output_path}")
        
        # Display generated code
        self.console.print("\n[bold]Generated Code:[/bold]")
        syntax = Syntax(generated_code, "python", theme="monokai", line_numbers=True)
        self.console.print(Panel(syntax, title="Generated Code", border_style="green"))
        
        # 4. HUMAN REVIEW (tag activation)
        self.console.print("\n[bold]Step 4: Reviewing Semantic Tags[/bold]")
        
        tag_counts = self.tagger.count_tags_by_state(generated_code)
        self.console.print(f"Found {tag_counts['inactive']} inactive tags to review\n")
        
        if tag_counts['inactive'] == 0:
            self.console.print("[yellow]No tags to review. Skipping compression.[/yellow]")
            return
        
        reviewed_code, active_tags = self.tagger.interactive_review(generated_code)
        
        if not active_tags:
            self.console.print("\n[yellow]No tags activated. Skipping compression.[/yellow]")
            
            # Still save the code if output file specified
            if output_file:
                Path(output_file).write_text(reviewed_code)
                self.console.print(f"Code saved to {output_file} (without compression)")
            return
        
        # Update output file with reviewed code
        if output_file:
            Path(output_file).write_text(reviewed_code)
        
        # 5. COMPRESSION (SCP gate passed: human activated tags)
        self.console.print("\n[bold]Step 5: Compressing to Specter Entry[/bold]")
        
        entry_id = self._derive_entry_id(spec)
        self.console.print(f"Entry ID: {entry_id}")
        
        # Strip inactive/rejected tags before compression
        clean_code = self.tagger.strip_inactive(reviewed_code)
        
        new_entry = self.compressor.compress(
            clean_code,
            active_tags,
            specter_slice,
            entry_id
        )
        
        # Set source files
        if output_file:
            new_entry.source_files = [str(output_file)]
        else:
            new_entry.source_files = []
        
        # 6. CONFLICT DETECTION
        self.console.print("\n[bold]Step 6: Checking for Conflicts[/bold]")
        conflicts = self.store.detect_conflicts(new_entry)
        
        if conflicts:
            self.console.print(f"[yellow]⚠ Conflict detected with:[/yellow]")
            for cid in conflicts:
                self.console.print(f"  - {cid}")
            self.console.print("\n[yellow]These entries will be marked stale.[/yellow]")
            
            confirm = input("Continue? [y/n]: ").strip().lower()
            if confirm != 'y':
                self.console.print("[yellow]Aborted.[/yellow]")
                return
            
            for cid in conflicts:
                self.store.mark_stale(cid)
        else:
            self.console.print("✓ No conflicts detected")
        
        # 7. SAVE
        self.console.print("\n[bold]Step 7: Saving Entry[/bold]")
        new_entry.embedding = self.retriever.embed(new_entry.semantic_surface())
        self.store.save_entry(new_entry)
        
        summary = self.store.summary()
        
        self.console.print(f"\n[bold green]✓ Success![/bold green]")
        self.console.print(f"  Entry '{entry_id}' saved to Specter")
        self.console.print(f"  Specter now has {summary['total_entries']} entries")
        self.console.print(f"  Total tokens: {summary['total_tokens']}\n")
    
    def _print_spec(self, spec: FeatureSpec) -> None:
        """Print the feature spec in a readable format."""
        self.console.print("\n[bold]Feature Specification:[/bold]")
        self.console.print(f"\n[cyan]Goal:[/cyan]")
        self.console.print(f"  {spec.goal}")
        
        if spec.constraints:
            self.console.print(f"\n[cyan]Constraints:[/cyan]")
            for constraint in spec.constraints:
                self.console.print(f"  • {constraint}")
        
        if spec.invariants_to_preserve:
            self.console.print(f"\n[cyan]Invariants to Preserve:[/cyan]")
            for inv in spec.invariants_to_preserve:
                self.console.print(f"  • {inv}")
        
        if spec.affected_modules_estimate:
            self.console.print(f"\n[cyan]Affected Modules:[/cyan]")
            self.console.print(f"  {', '.join(spec.affected_modules_estimate)}")
    
    def _print_slice_summary(self, slice: list) -> None:
        """Print summary of retrieved Specter entries."""
        if not slice:
            self.console.print("[yellow]No relevant entries found.[/yellow]")
            return
        
        total_tokens = sum(entry.token_count() for entry in slice)
        
        self.console.print(f"\nRetrieved {len(slice)} entries ({total_tokens} tokens):\n")
        
        for entry in slice:
            confidence = "✓" if not entry.lower_confidence else "⚠"
            self.console.print(f"  {confidence} [cyan]{entry.id}[/cyan]")
            self.console.print(f"    {entry.description[:80]}...")
    
    def _derive_entry_id(self, spec: FeatureSpec) -> str:
        """Derive an entry ID from the feature spec."""
        # Try to use first affected module
        if spec.affected_modules_estimate:
            base = spec.affected_modules_estimate[0]
        else:
            # Use goal
            base = spec.goal[:30]
        
        entry_id = create_entry_id(base)
        
        # Check if ID already exists
        existing = self.store.load_entry(entry_id)
        if existing:
            # Append number
            counter = 2
            while self.store.load_entry(f"{entry_id}_{counter}"):
                counter += 1
            entry_id = f"{entry_id}_{counter}"
        
        return entry_id
    
    def _edit_spec(self, spec: FeatureSpec) -> FeatureSpec:
        """Allow user to edit the spec."""
        self.console.print("\n[bold]Edit Feature Spec[/bold]")
        self.console.print("(Press Enter to keep current value)\n")
        
        new_goal = input(f"Goal [{spec.goal}]: ").strip()
        if new_goal:
            spec.goal = new_goal
        
        # For simplicity, just allow goal editing in this demo
        # Full implementation would allow editing all fields
        
        return spec

# Made with Bob
