# Code Specter - Quick Start Guide

Get started with Code Specter in 5 minutes.

## Prerequisites

- Python 3.10 or higher
- Anthropic API key ([get one here](https://console.anthropic.com/))

## Installation

```bash
# Clone the repository
git clone https://github.com/ff-asce/code_specter.git
cd code_specter

# Install dependencies
pip install -e .

# Set your API key
export ANTHROPIC_API_KEY='your-api-key-here'
```

## Your First Specter

### 1. Try the Demo with Test Fixture

```bash
# Navigate to the test fixture
cd tests/fixture_codebase

# Initialize Specter
specter init

# Build Specter from the payment system code
specter build

# View what was created
specter list
specter stats
```

**Expected output:**
```
Building Specter from tests/fixture_codebase

📁 Discovering files...
   Found 4 Python files

📦 Grouping into modules...
   Created 3 entry groups

🔄 Compressing modules...
[1/3] Compressing payments...
   ✓ 92 lines → ~70 tokens
[2/3] Compressing transactions...
   ✓ 155 lines → ~120 tokens
[3/3] Compressing api...
   ✓ 110 lines → ~85 tokens

Total Compression: ~14%
```

### 2. Generate a New Feature

```bash
# Generate refund processing feature
specter run "add refund processing with idempotency guarantees" -o refunds.py
```

**What happens:**
1. Claude generates a Feature Spec
2. Relevant Specter entries are retrieved
3. Code is generated with semantic tags
4. You review and activate tags interactively
5. Activated code is compressed into a new entry

**Interactive review example:**
```
──────────────────────────────────────────
Tag 1/4 · @invariant
  "Refunds are idempotent - duplicate requests return same result"

  [a]ctivate  [r]eject  [e]dit  [s]kip
> a ✓
```

### 3. Inspect the Specter

```bash
# List all entries
specter list

# Show detailed entry
specter show payments

# View statistics
specter stats
```

## Use on Your Own Project

```bash
# Navigate to your project
cd /path/to/your/project

# Initialize
specter init

# Build from your source code
specter build --root ./src

# Generate features as needed
specter run "your feature description" -o new_feature.py
```

## Common Commands

| Command | Description |
|---------|-------------|
| `specter init` | Initialize .specter/ directory |
| `specter build [--root PATH]` | Build Specter from existing code |
| `specter run "<intent>" [-o FILE]` | Generate new feature |
| `specter list` | List all entries |
| `specter show <id>` | Show entry details |
| `specter stats` | Show statistics |

## Tips

### 1. Start Small
Begin with a small module (100-500 lines) to see how compression works.

### 2. Review Tags Carefully
The interactive review is where semantic validation happens. Take time to:
- Activate accurate tags
- Reject incorrect ones
- Edit tags that need refinement

### 3. Check Compression Ratio
Good entries compress to <15% of original tokens. If you see warnings, the LLM may be including too much detail.

### 4. Use Descriptive Intents
Better: "add refund processing with idempotency guarantees and fraud detection"
Worse: "add refunds"

### 5. Inspect Retrieved Entries
When running `specter run`, check which entries were retrieved. This shows what context the LLM is using.

## Example Workflow

```bash
# Day 1: Initialize project
cd my_payment_api
specter init
specter build --root ./src

# Day 2: Add webhook feature
specter run "add webhook notifications for payment events" -o webhooks.py
# Review tags, activate relevant ones
# Code is generated and compressed

# Day 3: Add fraud detection
specter run "add fraud detection to payment processing" -o fraud_detector.py
# Specter retrieves payment entries automatically
# New code follows existing patterns

# Check what's in the Specter
specter list
specter stats
```

## Troubleshooting

### "ANTHROPIC_API_KEY not set"
```bash
export ANTHROPIC_API_KEY='your-key-here'
```

### "Import errors"
```bash
pip install -e .
```

### "No entries found"
Run `specter build` first to create entries from existing code.

### "Compression ratio too high"
This is a warning, not an error. The entry is still saved. Consider:
- Simplifying the code
- Breaking into smaller modules
- Adjusting the LLM prompt (advanced)

## What's Next?

1. **Read the full README** for detailed documentation
2. **Try the self-referential test**: Run `specter build` on the specter/ directory itself
3. **Experiment with different intents** to see how retrieval works
4. **Check PROJECT_SUMMARY.md** for implementation details

## Getting Help

- Check the README.md for detailed documentation
- Review PROJECT_SUMMARY.md for architecture details
- Examine the test fixture code for examples

## Key Concepts Recap

- **Specter Entry**: Compressed semantic summary of code (~85% smaller)
- **Semantic Tags**: Comment annotations that capture meaning
- **SCP Gate**: Human review ensures only validated semantics enter the Specter
- **Retrieval**: Embedding-based search finds relevant entries for new features
- **Bootstrap Entries**: Created by `specter build`, marked lower confidence
- **Verified Entries**: Created by `specter run` after human tag activation

---

**Ready to start?** Run the test fixture example above, then try it on your own code!