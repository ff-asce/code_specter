"""
Command-line interface for Code Specter.

Provides commands for initializing, building, running, and inspecting Specters.
"""

import argparse
import os
import sys
from pathlib import Path
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.syntax import Syntax

from .store import SpectreStore
from .compressor import SpectreCompressor
from .retriever import SpectreRetriever
from .tagger import Tagger
from .builder import SpectreBuilder
from .runner import SpectreRunner


def get_api_key() -> str:
    """Get Anthropic API key from environment."""
    api_key = os.environ.get('ANTHROPIC_API_KEY')
    if not api_key:
        print("Error: ANTHROPIC_API_KEY environment variable not set")
        print("Please set it with: export ANTHROPIC_API_KEY='your-key-here'")
        sys.exit(1)
    return api_key


def cmd_init(args):
    """Initialize .specter/ directory."""
    console = Console()
    store = SpectreStore(Path.cwd())
    
    if store.exists():
        console.print("[yellow]⚠ .specter/ directory already exists[/yellow]")
        return
    
    store.init()
    console.print("[green]✓ Initialized .specter/ directory[/green]")
    console.print(f"  Location: {store.specter_dir}")


def cmd_build(args):
    """Build Specter from existing codebase."""
    console = Console()
    
    # Check if .specter/ exists
    store = SpectreStore(Path.cwd())
    if not store.exists():
        console.print("[red]Error: .specter/ not found. Run 'specter init' first.[/red]")
        sys.exit(1)
    
    # Get API key
    api_key = get_api_key()
    
    # Initialize components
    compressor = SpectreCompressor(api_key)
    retriever = SpectreRetriever(store)
    builder = SpectreBuilder(store, compressor, retriever)
    
    # Build
    source_root = Path(args.root) if args.root else Path.cwd()
    builder.build(source_root)


def cmd_run(args):
    """Run feature development loop."""
    console = Console()
    
    # Check if .specter/ exists
    store = SpectreStore(Path.cwd())
    if not store.exists():
        console.print("[red]Error: .specter/ not found. Run 'specter init' first.[/red]")
        sys.exit(1)
    
    # Get API key
    api_key = get_api_key()
    
    # Initialize components
    compressor = SpectreCompressor(api_key)
    retriever = SpectreRetriever(store)
    tagger = Tagger()
    runner = SpectreRunner(store, compressor, retriever, tagger)
    
    # Run
    output_file = Path(args.output) if args.output else None
    runner.run(args.intent, output_file)


def cmd_show(args):
    """Show a Specter entry."""
    console = Console()
    
    store = SpectreStore(Path.cwd())
    if not store.exists():
        console.print("[red]Error: .specter/ not found.[/red]")
        sys.exit(1)
    
    entry = store.load_entry(args.entry_id)
    if not entry:
        console.print(f"[red]Error: Entry '{args.entry_id}' not found.[/red]")
        sys.exit(1)
    
    # Display entry
    console.print(f"\n[bold cyan]Specter Entry: {entry.id}[/bold cyan]\n")
    
    console.print(f"[bold]Description:[/bold]")
    console.print(f"  {entry.description}\n")
    
    console.print(f"[bold]Interface:[/bold]")
    console.print(f"  {entry.interface}\n")
    
    if entry.invariants:
        console.print(f"[bold]Invariants:[/bold]")
        for inv in entry.invariants:
            console.print(f"  • {inv}")
        console.print()
    
    if entry.patterns:
        console.print(f"[bold]Patterns:[/bold]")
        for pat in entry.patterns:
            console.print(f"  • {pat}")
        console.print()
    
    if entry.dependencies:
        console.print(f"[bold]Dependencies:[/bold]")
        console.print(f"  {', '.join(entry.dependencies)}\n")
    
    console.print(f"[bold]Metadata:[/bold]")
    console.print(f"  State: {entry.state}")
    console.print(f"  Source files: {len(entry.source_files)}")
    console.print(f"  Token count: {entry.token_count()}")
    console.print(f"  Created: {entry.created_at}")
    console.print(f"  Lower confidence: {entry.lower_confidence}\n")
    
    if entry.anchor:
        console.print(f"[bold]Anchor Code:[/bold]")
        syntax = Syntax(entry.anchor, "python", theme="monokai")
        console.print(Panel(syntax, border_style="dim"))


def cmd_list(args):
    """List all Specter entries."""
    console = Console()
    
    store = SpectreStore(Path.cwd())
    if not store.exists():
        console.print("[red]Error: .specter/ not found.[/red]")
        sys.exit(1)
    
    entries = store.load_all()
    
    if not entries:
        console.print("[yellow]No entries found.[/yellow]")
        return
    
    # Create table
    table = Table(title="Specter Entries")
    table.add_column("ID", style="cyan")
    table.add_column("State", style="green")
    table.add_column("Files", justify="right")
    table.add_column("Tokens", justify="right")
    table.add_column("Confidence")
    
    for entry in sorted(entries, key=lambda e: e.id):
        confidence = "✓" if not entry.lower_confidence else "⚠"
        state_color = "green" if entry.state == "active" else "yellow"
        
        table.add_row(
            entry.id,
            f"[{state_color}]{entry.state}[/{state_color}]",
            str(len(entry.source_files)),
            str(entry.token_count()),
            confidence
        )
    
    console.print(table)


def cmd_stats(args):
    """Show Specter statistics."""
    console = Console()
    
    store = SpectreStore(Path.cwd())
    if not store.exists():
        console.print("[red]Error: .specter/ not found.[/red]")
        sys.exit(1)
    
    summary = store.summary()
    
    console.print("\n[bold]Specter Statistics[/bold]\n")
    console.print(f"  Total entries: {summary['total_entries']}")
    console.print(f"  Active entries: {summary['active_entries']}")
    console.print(f"  Stale entries: {summary['stale_entries']}")
    console.print(f"  Bootstrap entries: {summary['bootstrap_entries']}")
    console.print(f"  Total tokens: {summary['total_tokens']}")
    
    if summary['total_entries'] > 0:
        avg_tokens = summary['total_tokens'] / summary['total_entries']
        console.print(f"  Average tokens per entry: {avg_tokens:.0f}\n")


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Code Specter - Semantic code compression and retrieval",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Commands')
    
    # init command
    parser_init = subparsers.add_parser('init', help='Initialize .specter/ directory')
    parser_init.set_defaults(func=cmd_init)
    
    # build command
    parser_build = subparsers.add_parser('build', help='Build Specter from existing codebase')
    parser_build.add_argument('--root', help='Root directory of codebase (default: current directory)')
    parser_build.set_defaults(func=cmd_build)
    
    # run command
    parser_run = subparsers.add_parser('run', help='Run feature development loop')
    parser_run.add_argument('intent', help='Feature intent description')
    parser_run.add_argument('-o', '--output', help='Output file for generated code')
    parser_run.set_defaults(func=cmd_run)
    
    # show command
    parser_show = subparsers.add_parser('show', help='Show a Specter entry')
    parser_show.add_argument('entry_id', help='Entry ID to show')
    parser_show.set_defaults(func=cmd_show)
    
    # list command
    parser_list = subparsers.add_parser('list', help='List all Specter entries')
    parser_list.set_defaults(func=cmd_list)
    
    # stats command
    parser_stats = subparsers.add_parser('stats', help='Show Specter statistics')
    parser_stats.set_defaults(func=cmd_stats)
    
    # Parse arguments
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    # Execute command
    args.func(args)


if __name__ == '__main__':
    main()

# Made with Bob
