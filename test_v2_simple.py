#!/usr/bin/env python3
"""
Simple test to verify Code Specter v2 can be imported and basic structure is correct.
"""

import sys
from pathlib import Path

# Add specter to path
sys.path.insert(0, str(Path(__file__).parent))

def test_imports():
    """Test that all v2 modules can be imported."""
    print("Testing imports...")
    
    try:
        from specter import schema, prompts, compressor, builder, querier, differ, exporter, retriever, store, cli
        print("✓ All modules imported successfully")
        return True
    except ImportError as e:
        print(f"✗ Import failed: {e}")
        return False

def test_schema_v2_fields():
    """Test that v2 schema fields exist."""
    print("\nTesting v2 schema fields...")
    
    from specter.schema import SpectreEntry, QueryResult, DiffResult, BuildReport
    
    # Create a test entry
    entry = SpectreEntry(
        id="test",
        description="Test description",
        interface="Test interface",
        invariants=["Test invariant"],
        dependencies=[],
        patterns=[],
        source_files=["test.py"],
        created_at="2024-01-01T00:00:00Z",
        questions=["What does this do?"],
        confidence="bootstrap",
        updated_at="2024-01-01T00:00:00Z",
        raw_token_count=100,
        entry_token_count=15
    )
    
    # Check v2 fields
    v2_fields = {
        'questions': entry.questions,
        'confidence': entry.confidence,
        'updated_at': entry.updated_at,
        'raw_token_count': entry.raw_token_count,
        'entry_token_count': entry.entry_token_count,
        'budget_exceeded': entry.budget_exceeded
    }
    
    all_present = True
    for field, value in v2_fields.items():
        if value is None and field != 'budget_exceeded':
            print(f"✗ Field '{field}' is None")
            all_present = False
        else:
            print(f"✓ Field '{field}': {value}")
    
    # Test v2 methods
    try:
        ratio = entry.compression_ratio()
        print(f"✓ compression_ratio() works: {ratio:.2%}")
    except Exception as e:
        print(f"✗ compression_ratio() failed: {e}")
        all_present = False
    
    try:
        text = entry.retrieval_text()
        print(f"✓ retrieval_text() works: {len(text)} chars")
    except Exception as e:
        print(f"✗ retrieval_text() failed: {e}")
        all_present = False
    
    # Test new dataclasses
    try:
        query_result = QueryResult(
            answer="Test answer",
            sources=[],
            knowledge_gaps=[],
            compression_factor=10.0
        )
        print(f"✓ QueryResult dataclass works")
    except Exception as e:
        print(f"✗ QueryResult failed: {e}")
        all_present = False
    
    try:
        diff_result = DiffResult(
            changed_files={},
            added_files=[],
            removed_files=[],
            stale_dependents=[]
        )
        print(f"✓ DiffResult dataclass works")
    except Exception as e:
        print(f"✗ DiffResult failed: {e}")
        all_present = False
    
    try:
        build_report = BuildReport(
            entries_created=1,
            entries_updated=0,
            entries_skipped=0,
            total_entries=1,
            avg_compression_ratio=0.15
        )
        print(f"✓ BuildReport dataclass works")
    except Exception as e:
        print(f"✗ BuildReport failed: {e}")
        all_present = False
    
    return all_present

def test_prompts_v2():
    """Test that v2 prompts exist."""
    print("\nTesting v2 prompts...")
    
    from specter import prompts
    
    v2_prompts = ['QUERY_PROMPT', 'SEMANTIC_DIFF_PROMPT', 'TIGHTEN_PROMPT']
    all_present = True
    
    for prompt_name in v2_prompts:
        if hasattr(prompts, prompt_name):
            prompt = getattr(prompts, prompt_name)
            print(f"✓ {prompt_name} exists ({len(prompt)} chars)")
        else:
            print(f"✗ {prompt_name} missing")
            all_present = False
    
    return all_present

def test_classes_exist():
    """Test that v2 classes exist."""
    print("\nTesting v2 classes...")
    
    classes_to_test = [
        ('specter.builder', 'SpectreBuilder'),
        ('specter.querier', 'SpectreQuerier'),
        ('specter.differ', 'SpectreDigger'),
        ('specter.exporter', 'SpectreExporter'),
        ('specter.compressor', 'SpectreCompressor'),
        ('specter.retriever', 'SpectreRetriever'),
        ('specter.store', 'SpectreStore'),
    ]
    
    all_present = True
    for module_name, class_name in classes_to_test:
        try:
            module = __import__(module_name, fromlist=[class_name])
            cls = getattr(module, class_name)
            print(f"✓ {module_name}.{class_name} exists")
        except (ImportError, AttributeError) as e:
            print(f"✗ {module_name}.{class_name} missing: {e}")
            all_present = False
    
    return all_present

def test_cli_commands():
    """Test that CLI has v2 commands."""
    print("\nTesting CLI commands...")
    
    from specter import cli
    
    # Check if command functions exist
    v2_commands = ['cmd_query', 'cmd_diff', 'cmd_export']
    all_present = True
    
    for cmd in v2_commands:
        if hasattr(cli, cmd):
            print(f"✓ {cmd} exists")
        else:
            print(f"✗ {cmd} missing")
            all_present = False
    
    return all_present

def main():
    """Run all tests."""
    print("="*60)
    print("  CODE SPECTER V2 - SIMPLE VERIFICATION TEST")
    print("="*60)
    
    tests = [
        ("Imports", test_imports),
        ("Schema V2 Fields", test_schema_v2_fields),
        ("V2 Prompts", test_prompts_v2),
        ("V2 Classes", test_classes_exist),
        ("CLI Commands", test_cli_commands),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            success = test_func()
            results.append((name, success))
        except Exception as e:
            print(f"\n✗ ERROR in {name}: {e}")
            import traceback
            traceback.print_exc()
            results.append((name, False))
    
    # Summary
    print("\n" + "="*60)
    print("  TEST SUMMARY")
    print("="*60)
    
    passed = sum(1 for _, success in results if success)
    total = len(results)
    
    for name, success in results:
        status = "✓ PASS" if success else "✗ FAIL"
        print(f"{status}: {name}")
    
    print(f"\n{'='*60}")
    print(f"Results: {passed}/{total} tests passed")
    print(f"{'='*60}")
    
    if passed == total:
        print("\n🎉 ALL TESTS PASSED! V2 implementation structure is correct.")
        return 0
    else:
        print(f"\n⚠ {total - passed} test(s) failed.")
        return 1

if __name__ == "__main__":
    sys.exit(main())

# Made with Bob
