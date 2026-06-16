"""
Parse and manipulate @specter: semantic tags in Python source code.

Handles tag extraction, activation, rejection, and interactive review.
"""

import re
from typing import Tuple
from .schema import SemanticTag


class Tagger:
    """Manages semantic tags in source code."""
    
    TAG_PATTERN = re.compile(
        r'#\s*@specter:(\w+)\[(\w+)\]\s+(.*)'
    )
    
    # Tags that are auto-activated (low risk per Auto-Commit Spectrum)
    AUTO_ACTIVATE_TAGS = {'scope', 'dependency'}
    
    def parse_tags(self, source: str) -> list[SemanticTag]:
        """
        Parse all @specter: tags from source code.
        
        Args:
            source: Source code string
            
        Returns:
            List of SemanticTag objects
        """
        tags = []
        lines = source.split('\n')
        
        for line_num, line in enumerate(lines, start=1):
            tag = SemanticTag.from_comment(line, line_num)
            if tag:
                tags.append(tag)
        
        return tags
    
    def activate_tag(self, source: str, tag: SemanticTag) -> str:
        """
        Activate a tag by changing [INACTIVE] to [ACTIVE].
        
        Args:
            source: Source code string
            tag: Tag to activate
            
        Returns:
            Modified source code
        """
        lines = source.split('\n')
        if 0 < tag.line_number <= len(lines):
            line = lines[tag.line_number - 1]
            # Replace [INACTIVE] with [ACTIVE] on this specific line
            lines[tag.line_number - 1] = line.replace('[INACTIVE]', '[ACTIVE]')
        
        return '\n'.join(lines)
    
    def reject_tag(self, source: str, tag: SemanticTag) -> str:
        """
        Reject a tag by changing [INACTIVE] to [REJECTED].
        
        Args:
            source: Source code string
            tag: Tag to reject
            
        Returns:
            Modified source code
        """
        lines = source.split('\n')
        if 0 < tag.line_number <= len(lines):
            line = lines[tag.line_number - 1]
            lines[tag.line_number - 1] = line.replace('[INACTIVE]', '[REJECTED]')
        
        return '\n'.join(lines)
    
    def strip_inactive(self, source: str) -> str:
        """
        Remove all [INACTIVE] and [REJECTED] tag lines from source.
        
        Used before compression - only ACTIVE tags feed the compressor.
        
        Args:
            source: Source code string
            
        Returns:
            Source with only active tags
        """
        lines = source.split('\n')
        filtered_lines = []
        
        for line in lines:
            # Check if line contains an inactive or rejected tag
            if '[INACTIVE]' in line or '[REJECTED]' in line:
                continue
            filtered_lines.append(line)
        
        return '\n'.join(filtered_lines)
    
    def get_active_tags(self, source: str) -> list[SemanticTag]:
        """
        Get all active tags from source code.
        
        Args:
            source: Source code string
            
        Returns:
            List of active SemanticTag objects
        """
        all_tags = self.parse_tags(source)
        return [tag for tag in all_tags if tag.state == 'active']
    
    def interactive_review(self, source: str) -> Tuple[str, list[SemanticTag]]:
        """
        Interactive CLI prompt for reviewing and activating tags.
        
        Auto-activates @scope and @dependency tags.
        Requires explicit activation for @invariant and @pattern tags.
        
        Args:
            source: Source code with inactive tags
            
        Returns:
            Tuple of (modified source, list of activated tags)
        """
        tags = self.parse_tags(source)
        inactive_tags = [tag for tag in tags if tag.state == 'inactive']
        
        if not inactive_tags:
            print("No inactive tags found.")
            return source, []
        
        activated_tags = []
        modified_source = source
        
        print(f"\n{'='*60}")
        print(f"Reviewing {len(inactive_tags)} semantic tags")
        print(f"{'='*60}\n")
        
        for i, tag in enumerate(inactive_tags, start=1):
            # Auto-activate low-risk tags
            if tag.tag_type in self.AUTO_ACTIVATE_TAGS:
                modified_source = self.activate_tag(modified_source, tag)
                tag.state = 'active'
                activated_tags.append(tag)
                print(f"[{i}/{len(inactive_tags)}] Auto-activated @{tag.tag_type}")
                continue
            
            # Manual review for high-risk tags
            print(f"\n{'─'*60}")
            print(f"Tag {i}/{len(inactive_tags)} · @{tag.tag_type}")
            print(f"{'─'*60}")
            print(f'  "{tag.value}"')
            print()
            
            while True:
                choice = input("  [a]ctivate  [r]eject  [e]dit  [s]kip  > ").strip().lower()
                
                if choice == 'a':
                    modified_source = self.activate_tag(modified_source, tag)
                    tag.state = 'active'
                    activated_tags.append(tag)
                    print("  ✓ Activated")
                    break
                elif choice == 'r':
                    modified_source = self.reject_tag(modified_source, tag)
                    print("  ✗ Rejected")
                    break
                elif choice == 'e':
                    new_value = input(f"  New value: ").strip()
                    if new_value:
                        # Update the tag value in source
                        lines = modified_source.split('\n')
                        if 0 < tag.line_number <= len(lines):
                            line = lines[tag.line_number - 1]
                            # Replace the value part
                            new_line = re.sub(
                                r'(#\s*@specter:\w+\[INACTIVE\])\s+.*',
                                f'\\1 {new_value}',
                                line
                            )
                            lines[tag.line_number - 1] = new_line
                            modified_source = '\n'.join(lines)
                            tag.value = new_value
                        print("  ✓ Edited")
                    continue  # Ask again after edit
                elif choice == 's':
                    print("  ⊘ Skipped")
                    break
                else:
                    print("  Invalid choice. Please enter a, r, e, or s.")
        
        print(f"\n{'='*60}")
        print(f"Review complete: {len(activated_tags)} tags activated")
        print(f"{'='*60}\n")
        
        return modified_source, activated_tags
    
    def count_tags_by_state(self, source: str) -> dict:
        """
        Count tags by their state.
        
        Args:
            source: Source code string
            
        Returns:
            Dictionary with counts: {'active': n, 'inactive': n, 'rejected': n}
        """
        tags = self.parse_tags(source)
        counts = {'active': 0, 'inactive': 0, 'rejected': 0}
        
        for tag in tags:
            counts[tag.state] = counts.get(tag.state, 0) + 1
        
        return counts

