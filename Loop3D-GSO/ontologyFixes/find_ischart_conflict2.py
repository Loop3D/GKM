#!/usr/bin/env python3
"""
Find which module combination causes Time_Ischart to become inconsistent.
This script matches the exact file list used by check_owl2dl.py.
"""

import sys
import os
import tempfile
import glob

# Check for 64-bit Java
java_home = os.environ.get('JAVA_HOME_64', r'C:\Program Files\OpenJDK\jdk-25')
if os.path.exists(java_home):
    os.environ['JAVA_HOME'] = java_home
    os.environ['PATH'] = os.path.join(java_home, 'bin') + os.pathsep + os.environ.get('PATH', '')
    print(f"Using 64-bit Java: {os.path.join(java_home, 'bin', 'java.exe')}")

import owlready2
from owlready2 import get_ontology, sync_reasoner_hermit, World
from rdflib import Graph, OWL, URIRef

# Set heap size for HermiT
owlready2.JAVA_MEMORY = 8000

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


def merge_and_load(files, quiet=True):
    """Merge files with rdflib and load into owlready2."""
    g = Graph()
    for f in files:
        if not quiet:
            print(f"  Loading: {os.path.basename(f)}")
        g.parse(f, format="turtle")

    # Remove owl:imports
    imports_to_remove = list(g.triples((None, OWL.imports, None)))
    for triple in imports_to_remove:
        g.remove(triple)

    # Save merged RDF/XML to temp file
    temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.rdf', delete=False)
    g.serialize(temp_file.name, format="xml")
    temp_file.close()

    # Load into owlready2
    world = World()
    onto = world.get_ontology(f"file://{temp_file.name}").load()

    # Cleanup temp file
    try:
        os.unlink(temp_file.name)
    except:
        pass

    return world, onto


def test_consistency(world):
    """Test ontology consistency."""
    try:
        with world:
            sync_reasoner_hermit(infer_property_values=False, debug=0)
        return True, []
    except owlready2.OwlReadyInconsistentOntologyError:
        return False, []


def main():
    all_files = get_all_ontology_files(BASE_DIR)

    # Categorize files same as check_owl2dl.py
    base_files = [f for f in all_files if 'Modules' not in f]
    module_files = sorted([f for f in all_files if 'Modules' in f])

    print(f"Base files ({len(base_files)}): {[os.path.basename(f) for f in base_files]}")
    print(f"Module files ({len(module_files)}): {[os.path.basename(f) for f in module_files]}")

    # Find which module is Time_Ischart
    ischart_idx = None
    for i, f in enumerate(module_files):
        if 'Time_Ischart' in f:
            ischart_idx = i
            break

    if ischart_idx is None:
        print("Error: Time_Ischart not found!")
        return

    print(f"\nTime_Ischart is module {ischart_idx + 1} of {len(module_files)}")

    # Test 1: Base + Time_Ischart only (no other modules)
    print("\n" + "=" * 60)
    print("Test 1: Base + Time_Ischart only...")
    ischart_file = module_files[ischart_idx]

    # Also need Time module since Ischart imports it
    time_idx = None
    for i, f in enumerate(module_files):
        if 'GSO-Geologic_Time.ttl' in f and 'Ischart' not in f:
            time_idx = i
            break

    test_files = base_files + [module_files[time_idx], ischart_file]
    world1, _ = merge_and_load(test_files)
    result1, _ = test_consistency(world1)
    print(f"  Result: {'PASS' if result1 else 'INCONSISTENT'}")

    # Test 2: Base + all modules up to Time + Ischart
    print("\n" + "=" * 60)
    print(f"Test 2: Base + modules 1-{ischart_idx + 1} (including Time_Ischart)...")
    test_files = base_files + module_files[:ischart_idx + 1]
    world2, _ = merge_and_load(test_files)
    result2, _ = test_consistency(world2)
    print(f"  Result: {'PASS' if result2 else 'INCONSISTENT'}")

    if not result2:
        print("\n" + "=" * 60)
        print("Binary search to find the conflicting module...")

        # We know base + Time + Ischart passes
        # Binary search among the modules before Ischart

        # First verify base + Time + Ischart passes
        low = 0
        high = ischart_idx  # Not including Ischart in search

        while low < high:
            mid = (low + high) // 2
            test_files = base_files + module_files[:mid + 1] + [ischart_file]
            print(f"  Testing with modules 0-{mid} + Ischart...")
            world, _ = merge_and_load(test_files)
            result, _ = test_consistency(world)

            if result:
                print(f"    PASS (modules 0-{mid} are fine)")
                low = mid + 1
            else:
                print(f"    FAIL (conflict in modules 0-{mid})")
                high = mid

        if low < ischart_idx:
            print(f"\n>>> Conflicting module found: {os.path.basename(module_files[low])}")
            print(f"    (module index {low})")
        else:
            print("\n>>> Conflict appears to be cumulative or in Ischart itself")


if __name__ == "__main__":
    main()
