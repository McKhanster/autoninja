#!/usr/bin/env python3
"""
Fix trailing spaces in YAML files that can cause CloudFormation errors.
"""

from pathlib import Path


def fix_trailing_spaces(file_path: Path) -> bool:
    """Remove trailing spaces from a file. Returns True if changes were made."""
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    fixed_lines = []
    changes_made = False
    
    for i, line in enumerate(lines, 1):
        original = line
        # Remove trailing spaces but keep newline
        fixed = line.rstrip(' \t') + '\n' if line.endswith('\n') else line.rstrip(' \t')
        
        if original != fixed:
            changes_made = True
            trailing_count = len(original.rstrip('\n')) - len(fixed.rstrip('\n'))
            print(f"  Line {i}: Removed {trailing_count} trailing space(s)")
        
        fixed_lines.append(fixed)
    
    if changes_made:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.writelines(fixed_lines)
    
    return changes_made


def main():
    stacks_dir = Path("infrastructure/cloudformation/stacks")
    
    print("Checking YAML files for trailing spaces...\n")
    
    total_fixed = 0
    for yaml_file in stacks_dir.glob("*.yaml"):
        print(f"Checking: {yaml_file.name}")
        if fix_trailing_spaces(yaml_file):
            print(f"  ✓ Fixed trailing spaces in {yaml_file.name}")
            total_fixed += 1
        else:
            print(f"  ✓ No trailing spaces found")
        print()
    
    print(f"\nSummary: Fixed {total_fixed} file(s)")


if __name__ == "__main__":
    main()
