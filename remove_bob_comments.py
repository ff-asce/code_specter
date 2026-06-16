#!/usr/bin/env python3
"""
Script to remove "Made with Bob" comments from all Python files.
"""

import os
from pathlib import Path


def remove_bob_comments(file_path: Path) -> bool:
    """
    Remove "Made with Bob" comments from a Python file.
    
    Args:
        file_path: Path to the Python file
        
    Returns:
        True if file was modified, False otherwise
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        # Find and remove lines containing "Made with Bob"
        modified = False
        new_lines = []
        for line in lines:
            if 'Made with Bob' not in line and '# Made with Bob' not in line:
                new_lines.append(line)
            else:
                modified = True
                print(f"  Removed from {file_path.name}")
        
        # Write back if modified
        if modified:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.writelines(new_lines)
        
        return modified
    
    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        return False


def main():
    """Main function to process all Python files."""
    project_root = Path(__file__).parent
    specter_dir = project_root / 'specter'
    
    print("Removing 'Made with Bob' comments from Python files...\n")
    
    modified_count = 0
    total_count = 0
    
    # Process all Python files in specter directory
    for py_file in specter_dir.glob('*.py'):
        total_count += 1
        if remove_bob_comments(py_file):
            modified_count += 1
    
    print(f"\nProcessed {total_count} files, modified {modified_count} files.")


if __name__ == '__main__':
    main()