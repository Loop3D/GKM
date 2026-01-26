#!/usr/bin/env python3
"""
Exact match of check_owl2dl.py to diagnose the inconsistency.
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

# Must import after setting JAVA_HOME
import owlready2
from owlready2 import get_ontology, sync_reasoner_hermit, default_world, OwlReadyInconsistentOntologyError
from rdflib import Graph, OWL

owlready2.reasoning.JAVA_MEMORY = 4000

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def get_all_ontology_files(base_path):
    """Get list of all ontology files"""
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
    """Merge TTL files - EXACT same as check_owl2dl.py"""
    g = Graph()
    for f in file_list:
        g.parse(f, format='turtle')

    # Remove owl:imports
    for s, p, o in list(g.triples((None, OWL.imports, None))):
        g.remove((s, p, o))

    fd, target_file = tempfile.mkstemp(suffix='.rdf')
    os.close(fd)
    g.serialize(destination=target_file, format='xml')

    return target_file


def check_merged_ontology(rdfxml_path):
    """Check ontology - EXACT same as check_owl2dl.py"""
    result = {
        'status': 'unknown',
        'time': 0,
        'unsatisfiable': [],
    }

    start_time = time.time()

    try:
        # Clear any previous ontologies - SAME as check_owl2dl.py line 151
        default_world.ontologies.clear()

        # Load ontology - SAME as check_owl2dl.py line 156
        onto = get_ontology(f"file://{os.path.abspath(rdfxml_path)}").load()

        classes = list(onto.classes())
        print(f"    Loaded {len(classes)} classes", end="", flush=True)

        # Run reasoner - SAME as check_owl2dl.py line 166
        try:
            sync_reasoner_hermit(onto, infer_property_values=False, debug=0,
                               ignore_unsupported_datatypes=True)
        except OwlReadyInconsistentOntologyError:
            result['status'] = 'inconsistent'
            result['time'] = time.time() - start_time
            return result

        # Check for unsatisfiable classes - SAME as check_owl2dl.py line 177
        unsatisfiable = list(default_world.inconsistent_classes())

        result['time'] = time.time() - start_time
        result['unsatisfiable'] = [str(c) for c in unsatisfiable if str(c) != 'owl.Nothing']

        if result['unsatisfiable']:
            result['status'] = 'has_unsatisfiable'
        else:
            result['status'] = 'passed'

    except Exception as e:
        result['status'] = 'error'
        result['time'] = time.time() - start_time
        print(f"\nError: {e}")

    return result


def main():
    all_files = get_all_ontology_files(BASE_DIR)

    # EXACT same categorization as check_owl2dl.py
    base_files = [f for f in all_files if 'Modules' not in f]
    module_files = [f for f in all_files if 'Modules' in f]

    # Find key modules
    time_idx = None
    ischart_idx = None
    for i, f in enumerate(module_files):
        if 'GSO-Geologic_Time.ttl' in f and 'Ischart' not in f:
            time_idx = i
        if 'Time_Ischart' in f:
            ischart_idx = i

    print(f"Time index: {time_idx}, Ischart index: {ischart_idx}")

    # Test: base + modules 0-19 + Time_Ischart
    # This is what check_owl2dl.py tests when Time_Ischart fails
    print("\n" + "=" * 70)
    print("Test: Base + modules 0-19 + Time_Ischart (like check_owl2dl.py)")
    print("=" * 70)

    test_files = base_files + module_files[:ischart_idx] + [module_files[ischart_idx]]
    print(f"Total files: {len(test_files)}")
    print(f"Modules: {[os.path.basename(f) for f in module_files[:ischart_idx + 1]]}")

    temp_file = merge_ontologies(test_files)
    try:
        start = time.time()
        result = check_merged_ontology(temp_file)
        print(f"\n  Result: {result['status'].upper()} ({result['time']:.1f}s)")

        if result['unsatisfiable']:
            print(f"  Unsatisfiable: {result['unsatisfiable'][:10]}")
    finally:
        os.remove(temp_file)

    # Also test without Time_Ischart
    print("\n" + "=" * 70)
    print("Test: Base + modules 0-19 (without Time_Ischart)")
    print("=" * 70)

    test_files2 = base_files + module_files[:ischart_idx]
    print(f"Total files: {len(test_files2)}")

    temp_file2 = merge_ontologies(test_files2)
    try:
        result2 = check_merged_ontology(temp_file2)
        print(f"\n  Result: {result2['status'].upper()} ({result2['time']:.1f}s)")
    finally:
        os.remove(temp_file2)


if __name__ == "__main__":
    main()
