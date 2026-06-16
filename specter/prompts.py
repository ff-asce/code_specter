"""
LLM prompt templates for Code Specter.

All prompts are centralized here for easy iteration and maintenance.
"""


COMPRESS_EXISTING_CODE_PROMPT = """You are compressing a verified, human-reviewed piece of code into a Specter Entry.

A Specter Entry is a structured semantic summary designed for future LLM agents to consume instead of reading raw code. It must be:
- Accurate: only claim what the code actually does
- Compressed: target <15% of the raw code's token count
- LLM-native: written so another LLM can understand the system without reading source files

You are given:
1. Source code (verified, working)
2. Active semantic tags (human-approved claims about the code)
3. Existing Specter entries this code depends on

Produce a JSON object matching this schema:
{
  "description": "...",      // What this module does. <200 tokens. Present tense.
  "interface": "...",        // Public functions/endpoints. Include signatures.
  "invariants": ["..."],     // Behavioral guarantees. Each one falsifiable.
  "dependencies": ["..."],   // IDs of other Specter entries this relies on
  "patterns": ["..."],       // Conventions future code in this domain should follow
  "anchor": "..." | null     // Only if behavior cannot be expressed in prose
}

Active tags are your primary signal. Where tags conflict with what you see in the code, flag the discrepancy in your description.

Source Code:
{source_code}

Active Tags:
{active_tags}

Existing Dependencies:
{dependencies}

Generate the Specter Entry JSON now:"""


COMPRESS_FILE_PROMPT = """You are compressing verified source code into a Specter Entry — a structured semantic summary designed for future LLM agents to consume instead of reading raw code.

Rules:
1. Be accurate. Only claim what the code demonstrably does.
2. Be compressed. Target under 15% of the source token count.
3. Be LLM-native. Write so another LLM can understand the system without seeing source files.
4. Anchor sparingly. Use the anchor field only for behavior that cannot be expressed in prose (complex algorithms, non-obvious data transformations). Most entries should have anchor: null.

Context (existing Specter entries this code may depend on):
{dependency_context}

Source files to compress:
{source_files}

{active_tags_section}

Produce a JSON object with exactly these fields:
{{
  "description": "...",      // What this module does. Present tense. <150 tokens.
  "interface": "...",        // Public functions/classes/endpoints. Include signatures.
  "invariants": ["..."],     // Behavioral guarantees. Each must be falsifiable.
                              // 0-5 items. Omit if nothing meaningful to guarantee.
  "dependencies": ["..."],   // IDs from the context above that this code relies on.
                              // Only include real dependencies visible in the code.
  "patterns": ["..."],       // Conventions future code in this domain should follow.
                              // 0-3 items. Only patterns actually established here.
  "anchor": "..." | null,    // Raw code excerpt. Null unless prose is insufficient.
  "questions": ["..."]       // 3-5 questions a developer would ask that this answers.
                              // Think: what would someone search for to find this?
}}"""


GENERATE_SPEC_PROMPT = """You are generating a Feature Specification from a human intent string.

A Feature Spec structures the intent into actionable components that guide code generation.

Produce a JSON object matching this schema:
{
  "goal": "...",                           // Clear statement of what to build
  "constraints": ["..."],                  // Technical constraints and requirements
  "invariants_to_preserve": ["..."],      // Existing behavioral guarantees that must not break
  "affected_modules_estimate": ["..."]    // Module IDs likely to be affected (best guess)
}

Human Intent:
{intent}

Existing Specter Entries (for context):
{existing_entries_summary}

Generate the Feature Spec JSON now:"""


GENERATE_CODE_PROMPT = """You are generating Python code for a feature, informed by the Code Specter — a compressed semantic representation of the existing codebase.

Feature Spec:
{feature_spec}

Relevant Specter Entries (pre-derived meaning from verified code):
{specter_slice}

Instructions:
1. Generate complete, working Python code for the feature
2. Follow patterns established by the Specter entries
3. Preserve every invariant listed in the retrieved entries
4. Annotate every significant function with @specter: comment tags in INACTIVE state
5. Use this exact format for tags:
   # @specter:intent[INACTIVE] <what this function does>
   # @specter:interface[INACTIVE] <function_name(params) -> return_type>
   # @specter:invariant[INACTIVE] <behavioral guarantee>
   # @specter:dependency[INACTIVE] <specter_entry_id>
   # @specter:pattern[INACTIVE] <convention being followed>
   # @specter:scope[INACTIVE] <what this code affects>

6. Tag placement:
   - Place tags immediately before the function/class they describe
   - Use multiple tags per function when appropriate
   - Every function should have at least @intent and @interface tags

7. Code quality:
   - Include docstrings
   - Add type hints
   - Handle errors appropriately
   - Follow Python best practices

Generate the complete Python code now:"""


SYSTEM_PROMPT = """You are an expert software engineer with deep knowledge of code architecture, design patterns, and semantic compression techniques. You understand how to distill code into its essential meaning while preserving accuracy."""


def format_active_tags(tags: list) -> str:
    """Format active tags for prompt inclusion."""
    if not tags:
        return "No active tags provided."
    
    formatted = []
    for tag in tags:
        formatted.append(f"- @{tag.tag_type}: {tag.value}")
    return "\n".join(formatted)


def format_dependencies(entries: list) -> str:
    """Format Specter entries for prompt inclusion."""
    if not entries:
        return "No dependencies provided."
    
    formatted = []
    for entry in entries:
        formatted.append(f"""
Entry ID: {entry.id}
Description: {entry.description}
Interface: {entry.interface}
Invariants: {', '.join(entry.invariants) if entry.invariants else 'None'}
""")
    return "\n".join(formatted)


def format_specter_slice(entries: list) -> str:
    """Format Specter entries for code generation."""
    if not entries:
        return "No relevant entries found."
    
    formatted = []
    for entry in entries:
        formatted.append(f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Entry: {entry.id}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Description:
{entry.description}

Interface:
{entry.interface}

Invariants:
{chr(10).join(f'  • {inv}' for inv in entry.invariants) if entry.invariants else '  None'}

Patterns:
{chr(10).join(f'  • {pat}' for pat in entry.patterns) if entry.patterns else '  None'}

Dependencies: {', '.join(entry.dependencies) if entry.dependencies else 'None'}
""")
    return "\n".join(formatted)


def format_entries_summary(entries: list) -> str:
    """Format a brief summary of entries."""
    if not entries:
        return "No existing entries."
    
    formatted = []
    for entry in entries:
        formatted.append(f"- {entry.id}: {entry.description[:100]}...")
    return "\n".join(formatted)



# ============================================================================
# V2 Prompts - Query, Diff, and Tighten
# ============================================================================

QUERY_PROMPT = """You are answering a developer's question about a codebase using its Code Specter — a compressed semantic representation of what the code means.

Rules:
1. Answer only from the provided Specter entries. Do not invent behavior.
2. If the Specter doesn't contain enough information, say so explicitly. Name what's missing. Do not guess.
3. Be concise. Developers want answers, not essays.
4. Cite which entries your answer comes from.
5. If entries conflict or seem stale, flag it.

Question: {question}

Specter entries (ordered by relevance):
{slice}

Answer the question. If you cannot answer from these entries, explain what's missing and what command might help (e.g. `specter diff <file>`).

Respond in this JSON format:
{{
  "answer": "...",
  "sources": ["entry_id", ...],
  "confidence": "high|medium|low|gap",
  "gap_note": "..." | null
}}"""


SEMANTIC_DIFF_PROMPT = """You are comparing two versions of a Specter Entry to produce a semantic diff — what changed about the *meaning* of this code, not the lines.

Prior entry:
{prior_entry}

New entry (just compressed from updated source):
{new_entry}

Describe what semantically changed. Focus on:
- Interface additions/removals/changes
- New or removed invariants
- Pattern changes
- Whether the core purpose changed

Be specific. "Interface expanded to include refund operations" is better than "interface changed." If nothing meaningful changed (refactor, rename, formatting), say "No semantic change detected."

Respond in plain prose, 2-5 sentences."""


TIGHTEN_PROMPT = """This Specter Entry exceeds the token budget (target: <15% of source tokens).
Current ratio: {ratio:.1%}

Entry to tighten:
{entry}

Reduce it by:
1. Removing or drastically shortening the anchor field — if prose can express the behavior, the anchor should be null
2. Condensing the description to its essential claim
3. Merging redundant invariants

Do not drop information that can't be expressed in other fields.
Produce a tightened version of the same JSON schema."""
