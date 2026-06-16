# Code Specter

**Semantic code compression and retrieval for LLM-native development**

Code Specter is a CLI tool that compresses codebases into semantic "Specter Entries" — structured summaries designed for LLM consumption. It enables two key workflows:

1. **Mode A (`specter build`)**: Retroactively spectralize an existing codebase
2. **Mode B (`specter run`)**: Generate new features with semantic tag activation and automatic compression

## Key Concepts

- **Specter Entry**: A compressed semantic summary of a code module (<15% of original tokens)
- **Semantic Tags**: Comment-based annotations (`@specter:intent`, `@specter:invariant`, etc.) that capture code meaning
- **SCP Gate**: Human-in-the-loop tag activation ensures only validated semantics enter the Specter
- **Retrieval**: Embedding-based similarity search finds relevant entries for new features

## Installation

```bash
cd /Users/parthjindal/Parth_Projects/code_specter
pip install -e .
```

### Requirements

- Python 3.10+
- Anthropic API key (set as `ANTHROPIC_API_KEY` environment variable)

```bash
export ANTHROPIC_API_KEY='your-api-key-here'
```

## Quick Start

### 1. Initialize a Specter

```bash
cd your_project/
specter init
```

This creates a `.specter/` directory to store compressed entries.

### 2. Build from Existing Code (Mode A)

Compress your existing codebase into Specter entries:

```bash
specter build --root ./src
```

This will:
- Discover all Python files
- Group them into modules
- Compress each module using Claude
- Compute embeddings for retrieval
- Save entries to `.specter/`

**Example output:**
```
Building Specter from ./src

📁 Discovering files...
   Found 23 Python files

📦 Grouping into modules...
   Created 6 entry groups

🔄 Compressing modules...
[1/6] Compressing payments...
   ✓ 847 lines → 287 tokens

┌──────────────────────────┬───────┬────────────┬───────────────┬───────┐
│ Entry                    │ Files │ Raw Lines  │ Entry Tokens  │ Ratio │
├──────────────────────────┼───────┼────────────┼───────────────┼───────┤
│ payments                 │ 3     │ 2,140      │ 287           │ 0.13  │
│ transactions             │ 2     │ 1,050      │ 164           │ 0.16  │
└──────────────────────────┴───────┴────────────┴───────────────┴───────┘

Total Compression: 14.3%
```

### 3. Generate New Features (Mode B)

Generate a new feature with semantic validation:

```bash
specter run "add refund processing with idempotency guarantees" -o refunds.py
```

This will:
1. **Generate Feature Spec** from your intent
2. **Retrieve relevant entries** from the Specter
3. **Generate code** with inactive semantic tags
4. **Interactive review** - you activate/reject each tag
5. **Compress** activated code into a new Specter entry
6. **Detect conflicts** and mark stale entries

**Example interaction:**
```
Step 4: Reviewing Semantic Tags

──────────────────────────────────────────
Tag 1/4 · @invariant
  "Refunds are idempotent - duplicate requests return same result"

  [a]ctivate  [r]eject  [e]dit  [s]kip
> a ✓

3/4 tags activated, 1 rejected.
Compressing to Specter Entry...
✓ Entry 'payments.refunds' saved.
```

## Commands

### `specter init`
Initialize `.specter/` directory in current project.

### `specter build [--root PATH]`
Build Specter from existing codebase.
- `--root`: Root directory to scan (default: current directory)

### `specter run "<intent>" [-o OUTPUT]`
Run feature development loop.
- `intent`: Natural language description of the feature
- `-o, --output`: Output file for generated code

### `specter show <entry_id>`
Display a Specter entry in detail.

### `specter list`
List all Specter entries with status.

### `specter stats`
Show Specter statistics (entry count, tokens, compression ratio).

## Example Workflow

```bash
# 1. Start a new project
mkdir my_payment_system
cd my_payment_system
specter init

# 2. Build initial Specter from existing code
specter build --root ./src

# 3. Generate a new feature
specter run "add webhook notifications for payment events" -o webhooks.py

# 4. Review the generated code and activate tags interactively

# 5. Check what's in the Specter
specter list
specter stats

# 6. View a specific entry
specter show payments.processor
```

## Testing with Fixture Codebase

A test fixture is included in `tests/fixture_codebase/`:

```bash
cd tests/fixture_codebase
specter init
specter build

# Try generating a feature
specter run "add payment validation with fraud detection" -o validator.py
```

## Architecture

```
specter/
├── schema.py          # Data models (SpectreEntry, SemanticTag, FeatureSpec)
├── store.py           # .specter/ file operations
├── tagger.py          # Parse/activate semantic tags
├── retriever.py       # Embedding-based similarity search
├── compressor.py      # LLM compression logic
├── builder.py         # Mode A: build from existing code
├── runner.py          # Mode B: feature development loop
├── prompts.py         # LLM prompt templates
└── cli.py             # Command-line interface
```

## Semantic Tag Types

- `@specter:intent[STATE]` - What the code does
- `@specter:interface[STATE]` - Function signatures
- `@specter:invariant[STATE]` - Behavioral guarantees
- `@specter:dependency[STATE]` - Other Specter entries used
- `@specter:pattern[STATE]` - Conventions to follow
- `@specter:scope[STATE]` - What the code affects

**States**: `INACTIVE` (pending review), `ACTIVE` (validated), `REJECTED` (dismissed)

## Auto-Commit Spectrum

Tags are auto-activated based on risk:
- **Auto-activated**: `@scope`, `@dependency` (low risk)
- **Manual review**: `@invariant`, `@pattern` (high risk)
- **Configurable**: `@intent`, `@interface`

## Compression Ratio

Target: **<15% of original token count**

The tool warns if compression exceeds this threshold. Bootstrap entries (from `specter build`) are marked `lower_confidence=True` since they haven't been human-validated.

## Limitations (Demo Version)

This is a working demo. Not included:
- Git hooks for automatic updates
- IDE plugin
- Multi-language support (Python only)
- Semantic conflict detection (only structural)
- Web UI
- Team/shared Specter

## Self-Referential Test

Run Code Specter on itself:

```bash
cd /Users/parthjindal/Parth_Projects/code_specter
specter init
specter build --root ./specter
```

If it can accurately describe its own modules, the compression is working correctly.

## Troubleshooting

**Import errors during development:**
```bash
pip install -e .
```

**Missing API key:**
```bash
export ANTHROPIC_API_KEY='your-key-here'
```

**Embeddings not working:**
The tool falls back to TF-IDF if `sentence-transformers` isn't available. For best results:
```bash
pip install sentence-transformers
```

## License

MIT

## Contributing

This is a research prototype demonstrating semantic code compression. Contributions welcome!

## Citation

Based on the Code Specter concept: semantic compression of code into LLM-native representations with human-validated meaning.