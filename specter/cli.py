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
from .querier import SpectreQuerier
from .differ import SpectreDigger
from .exporter import SpectreExporter


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
    builder.build(source_root, force_rebuild=args.force)


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
    
    if entry.questions:
        console.print(f"[bold]Questions this entry answers:[/bold]")
        for q in entry.questions:
            console.print(f"  • {q}")
        console.print()
    
    console.print(f"[bold]Metadata:[/bold]")
    console.print(f"  State: {entry.state}")
    console.print(f"  Confidence: {entry.confidence}")
    console.print(f"  Source files: {len(entry.source_files)}")
    console.print(f"  Raw tokens: {entry.raw_token_count:,}")
    console.print(f"  Entry tokens: {entry.entry_token_count:,}")
    console.print(f"  Compression ratio: {entry.compression_ratio():.1%}")
    console.print(f"  Created: {entry.created_at}")
    console.print(f"  Updated: {entry.updated_at}\n")
    
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
    table.add_column("Raw Tokens", justify="right")
    table.add_column("Entry Tokens", justify="right")
    table.add_column("Ratio", justify="right")
    table.add_column("Confidence")
    
    for entry in sorted(entries, key=lambda e: e.id):
        state_color = "green" if entry.state == "active" else "yellow"
        confidence_color = "green" if entry.confidence == "verified" else "yellow"
        
        table.add_row(
            entry.id,
            f"[{state_color}]{entry.state}[/{state_color}]",
            str(len(entry.source_files)),
            f"{entry.raw_token_count:,}",
            f"{entry.entry_token_count:,}",
            f"{entry.compression_ratio():.1%}",
            f"[{confidence_color}]{entry.confidence}[/{confidence_color}]"
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
    

def cmd_query(args):
    """Query the Specter with a natural language question."""
    console = Console()
    
    store = SpectreStore(Path.cwd())
    if not store.exists():
        console.print("[red]Error: .specter/ not found. Run 'specter init' and 'specter build' first.[/red]")
        sys.exit(1)
    
    # Get API key
    api_key = get_api_key()
    
    # Load entries
    entries = store.load_all()
    if not entries:
        console.print("[yellow]No entries found. Run 'specter build' first.[/yellow]")
        sys.exit(1)
    
    # Initialize querier
    querier = SpectreQuerier(api_key)
    
    # Query
    result = querier.query(
        question=args.question,
        entries=entries,
        top_k=args.top_k,
        show_sources=not args.no_sources
    )
    
    # Display result
    formatted = querier.format_result(result, show_efficiency=not args.no_efficiency)
    console.print(formatted)


def cmd_diff(args):
    """Show semantic diff for a changed file."""
    console = Console()
    
    store = SpectreStore(Path.cwd())
    if not store.exists():
        console.print("[red]Error: .specter/ not found.[/red]")
        sys.exit(1)
    
    # Get API key
    api_key = get_api_key()
    
    # Load entries
    entries = store.load_all()
    if not entries:
        console.print("[yellow]No entries found. Run 'specter build' first.[/yellow]")
        sys.exit(1)
    
    # Initialize differ
    compressor = SpectreCompressor(api_key)
    differ = SpectreDigger(api_key, compressor)
    
    # Diff
    file_path = Path(args.file)
    if not file_path.exists():
        console.print(f"[red]Error: File '{file_path}' not found.[/red]")
        sys.exit(1)
    
    try:
        diff_result = differ.diff(file_path, store, entries)
        formatted = differ.format_diff(diff_result)
        console.print(formatted)
    except ValueError as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)


def cmd_export(args):
    """Export Specter to Markdown or JSON."""
    console = Console()
    
    store = SpectreStore(Path.cwd())
    if not store.exists():
        console.print("[red]Error: .specter/ not found.[/red]")
        sys.exit(1)
    
    # Load entries
    entries = store.load_all()
    if not entries:
        console.print("[yellow]No entries found. Run 'specter build' first.[/yellow]")
        sys.exit(1)
    
    # Initialize exporter
    exporter = SpectreExporter()
    
    # Determine output path
    if args.output:
        output_path = Path(args.output)
    else:
        if args.format == 'md':
            output_path = Path.cwd() / 'specter.md'
        else:
            output_path = Path.cwd() / 'specter.json'
    
    # Export
    if args.format == 'md':
        exporter.export_markdown(entries, output_path, include_metadata=not args.no_metadata)
        console.print(f"[green]✓ Exported Specter to {output_path}[/green]")
    else:
        exporter.export_json(entries, output_path, pretty=not args.compact)
        console.print(f"[green]✓ Exported Specter to {output_path}[/green]")

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
    parser_build.add_argument('--force', action='store_true', help='Force rebuild all entries (ignore mtime)')
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
    
    # query command
    parser_query = subparsers.add_parser('query', help='Query the Specter with natural language')
    parser_query.add_argument('question', help='Question to ask')
    parser_query.add_argument('--top-k', type=int, default=5, help='Number of entries to retrieve (default: 5)')
    parser_query.add_argument('--no-sources', action='store_true', help='Hide source citations')
    parser_query.add_argument('--no-efficiency', action='store_true', help='Hide efficiency metrics')
    parser_query.set_defaults(func=cmd_query)
    
    # diff command
    parser_diff = subparsers.add_parser('diff', help='Show semantic diff for a changed file')
    parser_diff.add_argument('file', help='File to diff')
    parser_diff.set_defaults(func=cmd_diff)
    
    # export command
    parser_export = subparsers.add_parser('export', help='Export Specter to Markdown or JSON')
    parser_export.add_argument('--format', choices=['md', 'json'], default='md', help='Export format (default: md)')
    parser_export.add_argument('--output', '-o', help='Output file path')
    parser_export.add_argument('--no-metadata', action='store_true', help='Exclude metadata section (Markdown only)')
    parser_export.add_argument('--compact', action='store_true', help='Compact JSON output (JSON only)')
    parser_export.set_defaults(func=cmd_export)
    
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
