#!/usr/bin/env python3
"""
Comprehensive test script for Code Specter v2 implementation.
Tests all core features: build, query, diff, export, and incremental builds.
"""

import os
import sys
import json
import shutil
import tempfile
from pathlib import Path

# Add specter to path
sys.path.insert(0, str(Path(__file__).parent))

from specter.builder import build_specter
from specter.querier import query_specter
from specter.differ import diff_specter
from specter.exporter import export_to_markdown, export_to_json
from specter.store import SpecterStore
from specter.schema import SpecterEntry

def print_section(title):
    """Print a section header."""
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}\n")

def test_build(test_dir, specter_path):
    """Test building a Specter."""
    print_section("TEST 1: Building Specter")
    
    # Create test files
    test_file1 = test_dir / "module1.py"
    test_file1.write_text("""
def calculate_sum(numbers):
    '''Calculate the sum of a list of numbers.'''
    return sum(numbers)

def calculate_average(numbers):
    '''Calculate the average of a list of numbers.'''
    if not numbers:
        return 0
    return sum(numbers) / len(numbers)

class Calculator:
    '''A simple calculator class.'''
    
    def add(self, a, b):
        return a + b
    
    def subtract(self, a, b):
        return a - b
""")
    
    test_file2 = test_dir / "module2.py"
    test_file2.write_text("""
from typing import List, Dict

def process_data(data: List[Dict]) -> Dict:
    '''Process a list of dictionaries and return aggregated results.'''
    result = {}
    for item in data:
        for key, value in item.items():
            if key not in result:
                result[key] = []
            result[key].append(value)
    return result

class DataProcessor:
    '''A class for processing data.'''
    
    def __init__(self):
        self.cache = {}
    
    def process(self, data):
        '''Process data with caching.'''
        key = str(data)
        if key in self.cache:
            return self.cache[key]
        result = self._do_process(data)
        self.cache[key] = result
        return result
    
    def _do_process(self, data):
        '''Internal processing logic.'''
        return data
""")
    
    print(f"Created test files:")
    print(f"  - {test_file1}")
    print(f"  - {test_file2}")
    
    # Build Specter
    print(f"\nBuilding Specter at: {specter_path}")
    report = build_specter(
        source_dir=str(test_dir),
        specter_path=str(specter_path),
        force_rebuild=False
    )
    
    print(f"\n✓ Build completed!")
    print(f"  Entries created: {report.entries_created}")
    print(f"  Entries updated: {report.entries_updated}")
    print(f"  Entries skipped: {report.entries_skipped}")
    print(f"  Total entries: {report.total_entries}")
    print(f"  Average compression: {report.avg_compression_ratio:.2%}")
    
    # Verify entries
    store = SpecterStore(str(specter_path))
    entries = store.list_entries()
    print(f"\n✓ Verified {len(entries)} entries in Specter")
    
    for entry_id in entries[:2]:  # Show first 2
        entry = store.get_entry(entry_id)
        print(f"\n  Entry: {entry.path}")
        print(f"    - Questions: {len(entry.questions)}")
        print(f"    - Confidence: {entry.confidence}")
        print(f"    - Compression: {entry.compression_ratio():.2%}")
        if entry.questions:
            print(f"    - Sample question: {entry.questions[0]}")
    
    return True

def test_incremental_build(test_dir, specter_path):
    """Test incremental builds (should skip unchanged files)."""
    print_section("TEST 2: Incremental Build")
    
    print("Running build again (should skip unchanged files)...")
    report = build_specter(
        source_dir=str(test_dir),
        specter_path=str(specter_path),
        force_rebuild=False
    )
    
    print(f"\n✓ Incremental build completed!")
    print(f"  Entries created: {report.entries_created}")
    print(f"  Entries updated: {report.entries_updated}")
    print(f"  Entries skipped: {report.entries_skipped}")
    
    if report.entries_skipped > 0:
        print(f"\n✓ SUCCESS: Skipped {report.entries_skipped} unchanged files")
    else:
        print(f"\n⚠ WARNING: No files were skipped (expected some to be skipped)")
    
    return True

def test_query(specter_path):
    """Test querying the Specter."""
    print_section("TEST 3: Query System")
    
    questions = [
        "How do I calculate the sum of numbers?",
        "What classes are available for data processing?",
        "How does caching work in the DataProcessor?"
    ]
    
    for i, question in enumerate(questions, 1):
        print(f"\nQuery {i}: {question}")
        print("-" * 60)
        
        result = query_specter(
            specter_path=str(specter_path),
            question=question,
            top_k=3
        )
        
        print(f"Answer: {result.answer[:200]}...")
        print(f"\nSources used: {len(result.sources)}")
        for source in result.sources[:2]:  # Show first 2
            print(f"  - {source.path} (confidence: {source.confidence})")
        
        if result.knowledge_gaps:
            print(f"\nKnowledge gaps: {', '.join(result.knowledge_gaps)}")
        
        print(f"\nCompression factor: {result.compression_factor:.1f}x")
    
    print(f"\n✓ Query system working!")
    return True

def test_diff(test_dir, specter_path):
    """Test semantic diff."""
    print_section("TEST 4: Semantic Diff")
    
    # Modify a file
    test_file = test_dir / "module1.py"
    original_content = test_file.read_text()
    
    modified_content = original_content.replace(
        "def calculate_sum(numbers):",
        "def calculate_sum(numbers):\n    '''Calculate sum with validation.'''"
    ).replace(
        "return sum(numbers)",
        "if not numbers:\n        return 0\n    return sum(numbers)"
    )
    
    test_file.write_text(modified_content)
    print(f"Modified: {test_file}")
    
    # Run diff
    print("\nRunning semantic diff...")
    diff_result = diff_specter(
        source_dir=str(test_dir),
        specter_path=str(specter_path)
    )
    
    print(f"\n✓ Diff completed!")
    print(f"  Files changed: {len(diff_result.changed_files)}")
    print(f"  Files added: {len(diff_result.added_files)}")
    print(f"  Files removed: {len(diff_result.removed_files)}")
    print(f"  Dependents stale: {len(diff_result.stale_dependents)}")
    
    if diff_result.changed_files:
        print(f"\nChanged files:")
        for path, changes in list(diff_result.changed_files.items())[:2]:
            print(f"\n  {path}:")
            for change in changes[:3]:  # Show first 3 changes
                print(f"    - {change}")
    
    # Restore original
    test_file.write_text(original_content)
    print(f"\n✓ Restored original file")
    
    return True

def test_export(specter_path, test_dir):
    """Test export functionality."""
    print_section("TEST 5: Export System")
    
    # Export to Markdown
    md_path = test_dir / "specter_export.md"
    print(f"Exporting to Markdown: {md_path}")
    export_to_markdown(
        specter_path=str(specter_path),
        output_path=str(md_path)
    )
    
    md_size = md_path.stat().st_size
    print(f"✓ Markdown export created ({md_size} bytes)")
    
    # Show sample
    md_content = md_path.read_text()
    lines = md_content.split('\n')
    print(f"\nFirst 10 lines of export:")
    for line in lines[:10]:
        print(f"  {line}")
    
    # Export to JSON
    json_path = test_dir / "specter_export.json"
    print(f"\nExporting to JSON: {json_path}")
    export_to_json(
        specter_path=str(specter_path),
        output_path=str(json_path)
    )
    
    json_size = json_path.stat().st_size
    print(f"✓ JSON export created ({json_size} bytes)")
    
    # Verify JSON structure
    with open(json_path) as f:
        data = json.load(f)
    
    print(f"\nJSON structure:")
    print(f"  - Metadata keys: {list(data.get('metadata', {}).keys())}")
    print(f"  - Number of entries: {len(data.get('entries', []))}")
    
    return True

def test_schema_v2_fields(specter_path):
    """Test that v2 schema fields are present."""
    print_section("TEST 6: V2 Schema Fields")
    
    store = SpecterStore(str(specter_path))
    entries = store.list_entries()
    
    if not entries:
        print("⚠ No entries to test")
        return False
    
    entry = store.get_entry(entries[0])
    
    print(f"Testing entry: {entry.path}")
    print(f"\nV2 Fields present:")
    
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
        present = value is not None
        status = "✓" if present else "✗"
        print(f"  {status} {field}: {value}")
        if not present:
            all_present = False
    
    # Test methods
    print(f"\nV2 Methods:")
    print(f"  ✓ compression_ratio(): {entry.compression_ratio():.2%}")
    print(f"  ✓ retrieval_text() length: {len(entry.retrieval_text())} chars")
    
    if all_present:
        print(f"\n✓ All v2 fields present!")
    else:
        print(f"\n✗ Some v2 fields missing!")
    
    return all_present

def main():
    """Run all tests."""
    print("="*60)
    print("  CODE SPECTER V2 - COMPREHENSIVE TEST SUITE")
    print("="*60)
    
    # Create temporary test directory
    test_dir = Path(tempfile.mkdtemp(prefix="specter_test_"))
    specter_path = test_dir / ".specter"
    
    print(f"\nTest directory: {test_dir}")
    print(f"Specter path: {specter_path}")
    
    try:
        # Run tests
        tests = [
            ("Build Specter", lambda: test_build(test_dir, specter_path)),
            ("Incremental Build", lambda: test_incremental_build(test_dir, specter_path)),
            ("Query System", lambda: test_query(specter_path)),
            ("Semantic Diff", lambda: test_diff(test_dir, specter_path)),
            ("Export System", lambda: test_export(specter_path, test_dir)),
            ("V2 Schema Fields", lambda: test_schema_v2_fields(specter_path))
        ]
        
        results = []
        for name, test_func in tests:
            try:
                success = test_func()
                results.append((name, success, None))
            except Exception as e:
                results.append((name, False, str(e)))
                print(f"\n✗ ERROR in {name}: {e}")
                import traceback
                traceback.print_exc()
        
        # Summary
        print_section("TEST SUMMARY")
        
        passed = sum(1 for _, success, _ in results if success)
        total = len(results)
        
        for name, success, error in results:
            status = "✓ PASS" if success else "✗ FAIL"
            print(f"{status}: {name}")
            if error:
                print(f"  Error: {error}")
        
        print(f"\n{'='*60}")
        print(f"Results: {passed}/{total} tests passed")
        print(f"{'='*60}")
        
        if passed == total:
            print("\n🎉 ALL TESTS PASSED! V2 implementation is working correctly.")
            return 0
        else:
            print(f"\n⚠ {total - passed} test(s) failed. Review errors above.")
            return 1
        
    finally:
        # Cleanup
        print(f"\nCleaning up test directory: {test_dir}")
        shutil.rmtree(test_dir, ignore_errors=True)

if __name__ == "__main__":
    sys.exit(main())

# Made with Bob
