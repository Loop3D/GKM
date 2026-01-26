#!/usr/bin/env python3
"""
Binary search to find which module combination causes inconsistency.
"""

import sys
import os
import tempfile
import glob
import time

# Check for 64-bit Java
java_home = os.environ.get('JAVA_HOME_64', r'C:\Program Files\OpenJDK\jdk-25')
if os.path.exists(java_home):
    os.environ['JAVA_HOME'] = java_home
    os.environ['PATH'] = os.path.join(java_home, 'bin') + os.pathsep + os.environ.get('PATH', '')
    print(f"Using 64-bit Java: {os.path.join(java_home, 'bin', 'java.exe')}")

import owlready2
from owlready2 import get_ontology, sync_reasoner_hermit, default_world, OwlReadyInconsistentOntologyError
from rdflib import Graph, OWL

owlready2.reasoning.JAVA_MEMORY = 4000

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def get_all_ontology_files(base_path):
    patterns = [
        os.path.join(base_path, "*.ttl"),
        os.path.join(base_path, "Modules", "*.ttl"),
    ]

    files = []
    for pattern in patterns:
        files.extend(glob.glob(pattern))

    files = [f for f in files if
             not f.endswith('.bak') and
             '~$' not in f and
             '-SMR-' not in f and
             '.inconsistent' not in f and
             'GSO-Geologic_Mineral.ttl' not in f]
    return sorted(set(files))


def merge_ontologies(file_list):
    g = Graph()
    for f in file_list:
        g.parse(f, format='turtle')

    for s, p, o in list(g.triples((None, OWL.imports, None))):
        g.remove((s, p, o))

    fd, target_file = tempfile.mkstemp(suffix='.rdf')
    os.close(fd)
    g.serialize(destination=target_file, format='xml')

    return target_file


def check_consistency(rdfxml_path):
    """Returns True if consistent, False if inconsistent."""
    try:
        default_world.ontologies.clear()
        onto = get_ontology(f"file://{os.path.abspath(rdfxml_path)}").load()

        try:
            sync_reasoner_hermit(onto, infer_property_values=False, debug=0,
                               ignore_unsupported_datatypes=True)
        except OwlReadyInconsistentOntologyError:
            return False

        return True

    except Exception as e:
        print(f"\nError: {e}")
        return None


def test_combination(base_files, module_files, module_indices, desc=""):
    """Test a specific combination of modules."""
    test_files = base_files + [module_files[i] for i in module_indices]

    temp_file = merge_ontologies(test_files)
    try:
        start = time.time()
        result = check_consistency(temp_file)
        elapsed = time.time() - start
        status = "PASS" if result else "INCONSISTENT"
        print(f"  {desc}: {status} ({elapsed:.1f}s)")
        return result
    finally:
        os.remove(temp_file)


def main():
    all_files = get_all_ontology_files(BASE_DIR)

    base_files = [f for f in all_files if 'Modules' not in f]
    module_files = [f for f in all_files if 'Modules' in f]

    print(f"Base files: {[os.path.basename(f) for f in base_files]}")
    print(f"Module files ({len(module_files)}):")
    for i, f in enumerate(module_files):
        print(f"  {i}: {os.path.basename(f)}")

    # Test base only
    print("\n" + "=" * 70)
    print("Phase 1: Test base files only")
    print("=" * 70)
    test_combination(base_files, module_files, [], "Base only")

    # Binary search to find first module that causes inconsistency
    print("\n" + "=" * 70)
    print("Phase 2: Binary search")
    print("=" * 70)

    # First, test with all modules up to Time (index 19)
    result = test_combination(base_files, module_files, list(range(20)), "Modules 0-19")

    if result:
        print("  Modules 0-19 are consistent")
        return

    # Binary search
    low = 0
    high = 19

    while low < high:
        mid = (low + high) // 2
        result = test_combination(base_files, module_files, list(range(mid + 1)), f"Modules 0-{mid}")

        if result:
            # This set is consistent, so problem is in later modules
            low = mid + 1
        else:
            # This set is inconsistent
            high = mid

    print(f"\n>>> First inconsistent combination: Modules 0-{low}")
    print(f">>> Module {low}: {os.path.basename(module_files[low])}")

    # Verify by testing one module earlier
    if low > 0:
        result = test_combination(base_files, module_files, list(range(low)), f"Modules 0-{low-1}")
        if result:
            print(f">>> Confirmed: Adding module {low} ({os.path.basename(module_files[low])}) causes inconsistency")
        else:
            print(f">>> Issue is earlier - modules 0-{low-1} also inconsistent")


if __name__ == "__main__":
    main()
