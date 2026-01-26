#!/usr/bin/env python3
"""
Compare file lists used in different test approaches.
"""

import sys
import os
import glob

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def get_all_ontology_files(base_path):
    """Get list of all ontology files, filtered and sorted - same as check_owl2dl.py"""
    patterns = [
        os.path.join(base_path, "*.ttl"),
        os.path.join(base_path, "Modules", "*.ttl"),
    ]

    files = []
    for pattern in patterns:
        files.extend(glob.glob(pattern))

    # Filter out backups, temp files, and inconsistent files
    # Also skip GSO-Geologic_Mineral.ttl (too slow)
    files = [f for f in files if
             not f.endswith('.bak') and
             '~$' not in f and
             '-SMR-' not in f and
             '.inconsistent' not in f and
             'GSO-Geologic_Mineral.ttl' not in f]
    return sorted(set(files))


def main():
    all_files = get_all_ontology_files(BASE_DIR)

    # Categorize files same as check_owl2dl.py
    base_files = [f for f in all_files if 'Modules' not in f]
    module_files = sorted([f for f in all_files if 'Modules' in f])

    print("=" * 70)
    print("BASE FILES:")
    print("=" * 70)
    for i, f in enumerate(base_files):
        print(f"  {i}: {os.path.basename(f)}")

    print()
    print("=" * 70)
    print("MODULE FILES:")
    print("=" * 70)
    for i, f in enumerate(module_files):
        print(f"  {i}: {os.path.basename(f)}")

    # Find Time_Ischart index
    ischart_idx = None
    time_idx = None
    for i, f in enumerate(module_files):
        basename = os.path.basename(f)
        if basename == 'GSO-Geologic_Time_Ischart.ttl':
            ischart_idx = i
        if basename == 'GSO-Geologic_Time.ttl':
            time_idx = i

    print()
    print("=" * 70)
    print(f"Time module index: {time_idx}")
    print(f"Time_Ischart module index: {ischart_idx}")
    print()

    # Files for check_owl2dl.py incremental test at Time_Ischart step
    # (assuming all previous modules passed)
    check_files = base_files + module_files[:ischart_idx] + [module_files[ischart_idx]]
    print(f"check_owl2dl.py would test with {len(check_files)} files:")
    print(f"  Base: {len(base_files)}")
    print(f"  Modules 0-{ischart_idx-1}: {ischart_idx} files")
    print(f"  + Time_Ischart: 1 file")
    print(f"  Total: {len(check_files)}")

    # Files for my test
    my_files = base_files + module_files[:ischart_idx + 1]
    print(f"\nMy test would load with {len(my_files)} files:")
    print(f"  Base: {len(base_files)}")
    print(f"  Modules 0-{ischart_idx}: {ischart_idx + 1} files")
    print(f"  Total: {len(my_files)}")

    # Check if they're the same
    if set(check_files) == set(my_files):
        print("\n>>> File lists are IDENTICAL")
    else:
        print("\n>>> File lists are DIFFERENT!")
        diff1 = set(check_files) - set(my_files)
        diff2 = set(my_files) - set(check_files)
        if diff1:
            print(f"  In check_owl2dl but not in my test: {[os.path.basename(f) for f in diff1]}")
        if diff2:
            print(f"  In my test but not in check_owl2dl: {[os.path.basename(f) for f in diff2]}")


if __name__ == "__main__":
    main()
