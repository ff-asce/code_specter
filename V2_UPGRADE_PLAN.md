# Code Specter v2 Upgrade Plan

## Current Status: v1 Implementation Complete

The current implementation follows the v1 spec with full `runner.py` (feature generation loop). 

## V2 Changes Required

### Philosophy Shift
**v1:** Build → Run (generate features)  
**v2:** Build → Query → Diff → Export (understand codebase)

**Rationale:** Prove compression and retrieval work before attempting generation. Query is demonstrable without changing workflow.

---

## Required Changes

### 1. Schema Updates ✅ Minor

**Add to `SpectreEntry`:**
```python
questions: list[str]        # 3-5 questions this entry answers
confidence: str             # "bootstrap" | "verified" 
updated_at: str             # ISO timestamp of last update
raw_token_count: int        # Source file token count
entry_token_count: int      # Entry token count
```

**Update `retrieval_text()`:**
```python
def retrieval_text(self) -> str:
    parts = [self.description, self.interface]
    parts.extend(self.invariants)
    parts.extend(self.questions)  # NEW
    return " ".join(parts)
```

### 2. NEW: `querier.py` (~300 lines) ⭐ FLAGSHIP

**Purpose:** Answer natural language questions about the codebase using only the Specter.

**Key Features:**
- RAG over Specter entries
- Explicit gap handling ("I don't know" vs hallucination)
- Source citation with confidence levels
- Efficiency metrics (Specter tokens vs raw code tokens)

**Commands:**
```bash
specter query "how does idempotency work?"
specter query "what would break if I changed Transaction model?"
```

**Output Format:**
```
Answer
──────
[Synthesized answer from Specter entries]

Sources
───────
  transactions.idempotency  (relevance: 0.94)  [bootstrap]
  payments.processor        (relevance: 0.81)  [bootstrap]

Efficiency
──────────
  Answered from 380 Specter tokens
  Estimated raw code equivalent: 3,200 tokens
  Compression factor: 8.4×
```

### 3. NEW: `differ.py` (~200 lines) ⭐ KEY FEATURE

**Purpose:** Show semantic diff (meaning changes) not line diff.

**Key Features:**
- Re-compress changed file
- Compare: description, interface, invariants, patterns
- Mark dependents as stale
- Show downstream impact

**Command:**
```bash
specter diff payments/processor.py
```

**Output Format:**
```
Semantic diff: payments.processor
──────────────────────────────────

Interface
  + refund(transaction_id: str, amount: Decimal) -> RefundResult  ← ADDED

Invariants
  ✓ Charges are idempotent (unchanged)
  + Refund amount cannot exceed original transaction amount  ← ADDED

Downstream
  ⚠ transactions.ledger — marked stale
  ⚠ api.routes — marked stale
```

### 4. NEW: `exporter.py` (~200 lines)

**Purpose:** Export Specter as navigable Markdown document.

**Key Features:**
- Table of contents with links
- Dependency-ordered sections
- ASCII dependency graph
- Stats footer

**Commands:**
```bash
specter export --format md --output specter.md
specter export --format json --output specter.json
```

### 5. Update `compressor.py` ✅ Minor

**Add to compression prompt:**
- Generate `questions` field (3-5 questions this entry answers)
- Set `confidence` field ("bootstrap" for build, "verified" for run)
- Track `raw_token_count` and `entry_token_count`

**Add retry logic:**
- If ratio > 0.20, call with `TIGHTEN_PROMPT`
- Maximum 2 attempts
- Flag `budget_exceeded: true` if still over

### 6. Update `builder.py` ✅ Minor

**Add incremental build:**
- Compare file `mtime` vs entry `updated_at`
- Skip unchanged files
- Only re-compress modified files

**Add to BuildReport:**
```python
entries_skipped: int       # unchanged since last build
entries_updated: int       # re-compressed
```

### 7. Update `prompts.py` ✅ Moderate

**Add new prompts:**
- `QUERY_PROMPT` - For querier.py
- `SEMANTIC_DIFF_PROMPT` - For differ.py  
- `TIGHTEN_PROMPT` - For compression retry

**Update `COMPRESS_PROMPT`:**
- Add `questions` field generation
- Emphasize anchor sparsity

### 8. Stub `runner.py` ✅ Easy

Replace with:
```python
def run(self, intent: str, output_file: Path | None = None):
    print("Feature generation loop coming in v3")
    print("Focus: specter query + specter diff")
    sys.exit(0)
```

### 9. Update `cli.py` ✅ Minor

**Add commands:**
```python
specter query "<question>"
specter diff <file>
specter export [--format md|json] [--output PATH]
```

**Update help text** to emphasize query as flagship.

### 10. Enhanced Fixture ✅ Moderate

**Expand from 357 lines to ~840 lines:**

Current fixture:
- payments/processor.py (92 lines)
- transactions/models.py (68 lines)
- transactions/idempotency.py (87 lines)
- api/routes.py (110 lines)

Add:
- payments/validator.py (~80 lines)
- payments/gateway.py (~100 lines)
- transactions/ledger.py (~110 lines)
- api/auth.py (~70 lines)
- config.py (~40 lines)

---

## Implementation Priority

### Phase 1: Core Updates (Required for v2)
1. ✅ Update schema.py (add questions, confidence, timestamps)
2. ✅ Update prompts.py (add new prompts)
3. ✅ Update compressor.py (generate questions, retry logic)
4. ⭐ Implement querier.py (NEW - flagship)
5. ⭐ Implement differ.py (NEW - key differentiator)
6. ⭐ Implement exporter.py (NEW - documentation use case)

### Phase 2: Polish
7. ✅ Update builder.py (incremental builds)
8. ✅ Stub runner.py (simple)
9. ✅ Update cli.py (wire new commands)
10. ✅ Enhance fixture (more realistic)

### Phase 3: Testing
11. Self-referential test on specter/ itself
12. Query testing with fixture
13. Diff testing with file changes
14. Export validation

---

## Estimated Effort

| Task | Lines | Complexity | Time |
|------|-------|------------|------|
| Schema updates | +30 | Low | 30min |
| Prompts updates | +100 | Medium | 1hr |
| Compressor updates | +50 | Medium | 1hr |
| **querier.py** | **300** | **High** | **3hrs** |
| **differ.py** | **200** | **Medium** | **2hrs** |
| **exporter.py** | **200** | **Low** | **1.5hrs** |
| Builder updates | +50 | Low | 30min |
| Runner stub | -400 | Low | 15min |
| CLI updates | +20 | Low | 30min |
| Fixture expansion | +483 | Low | 2hrs |
| **Total** | **~1,033 net** | | **~12hrs** |

---

## Decision Point

**Option A: Upgrade to v2**
- Implement querier, differ, exporter
- Stub runner.py
- Focus on query/diff demo
- More demonstrable without API key
- Better for showcasing compression value

**Option B: Keep v1**
- Current implementation is complete
- Runner.py fully implemented
- Follows original spec
- Already pushed to GitHub

**Recommendation:** 
Since v1 is complete and pushed, we could:
1. Keep v1 as `main` branch
2. Create `v2` branch for the refactor
3. Document both approaches

The v2 approach is smarter for a demo (query is more impressive than generation), but v1 is already done and working.

---

## What v2 Proves Better

1. **Compression works** - Build stats show 85% reduction
2. **Retrieval works** - Query answers questions accurately
3. **Stays in sync** - Diff shows semantic changes
4. **Reduces cognitive load** - Export creates navigable doc

v1 proves generation works but requires full API access and human interaction to demonstrate.

---

## Next Steps

**If upgrading to v2:**
1. Create v2 branch
2. Implement querier.py first (flagship)
3. Implement differ.py second (differentiator)
4. Implement exporter.py third (documentation)
5. Update supporting modules
6. Test with enhanced fixture
7. Run self-referential test

**If keeping v1:**
1. Document v2 as future roadmap
2. Add note about v2 philosophy to README
3. Consider v2 features as separate PRs

The current v1 implementation is solid and complete. V2 is a strategic pivot, not a bug fix.