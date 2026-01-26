#!/usr/bin/env python3
"""
Remove all owl:equivalentClass statements from GSO-Common.ttl.

This converts necessary-and-sufficient conditions to just necessary conditions,
which prevents unintended classification conflicts in OWL reasoners.
"""

import re
import os

def find_matching_bracket(text, start):
    """Find the position of the matching closing bracket."""
    depth = 0
    i = start
    while i < len(text):
        if text[i] == '[':
            depth += 1
        elif text[i] == ']':
            depth -= 1
            if depth == 0:
                return i
        i += 1
    return -1


def remove_equivalent_classes(input_file, output_file):
    """Remove all owl:equivalentClass blocks from the TTL file."""

    with open(input_file, 'r', encoding='utf-8') as f:
        content = f.read()

    removed_blocks = []
    removed_count = 0

    # Pattern to find the start of an equivalentClass declaration with anonymous class
    equiv_pattern = re.compile(r'(\s*)owl:equivalentClass\s*\[')

    while True:
        match = equiv_pattern.search(content)
        if not match:
            break

        start = match.start()
        bracket_start = match.end() - 1  # Position of opening bracket
        bracket_end = find_matching_bracket(content, bracket_start)

        if bracket_end == -1:
            print(f"Warning: Could not find matching bracket at position {bracket_start}")
            break

        # Find the end of the statement (either ; or .)
        end = bracket_end + 1
        while end < len(content) and content[end] in ' \t\n':
            end += 1
        if end < len(content) and content[end] in ';.':
            end += 1

        # Extract and save the removed block
        removed_block = content[start:end].strip()
        removed_blocks.append(removed_block)

        # Remove the block
        content = content[:start] + content[end:]
        removed_count += 1

    # Also handle simple equivalentClass (URI reference, not anonymous class)
    simple_pattern = re.compile(r'\s*owl:equivalentClass\s+gsoc:\w+\s*[;.]')
    for match in simple_pattern.finditer(content):
        removed_blocks.append(match.group().strip())
        removed_count += 1
    content = simple_pattern.sub('', content)

    # Clean up any double semicolons
    content = re.sub(r';\s*;', ';', content)

    # Fix cases where removing equivalentClass leaves only whitespace before .
    content = re.sub(r';\s*\.', '.', content)

    # Clean up excessive blank lines
    content = re.sub(r'\n\s*\n\s*\n', '\n\n', content)

    print(f"Removed {removed_count} owl:equivalentClass statements")

    # Write the modified content
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(content)

    return removed_count, removed_blocks


def main():
    base_path = os.path.dirname(os.path.abspath(__file__))

    input_file = os.path.join(base_path, "GSO-Common.ttl")
    output_file = input_file  # Overwrite

    print(f"Processing: {input_file}")
    count, removed = remove_equivalent_classes(input_file, output_file)
    print(f"Done. Removed {count} equivalentClass statements.")

    # Save removed axioms summary
    removed_file = os.path.join(base_path, "removed_equivalentclass_axioms.txt")
    with open(removed_file, 'w', encoding='utf-8') as f:
        f.write(f"# Removed {count} owl:equivalentClass statements from GSO-Common.ttl\n")
        f.write("# These were removed to achieve OWL 2 DL consistency\n\n")
        for i, block in enumerate(removed, 1):
            f.write(f"# {i}.\n{block}\n\n")
    print(f"Removed axioms saved to: {removed_file}")


if __name__ == "__main__":
    main()
