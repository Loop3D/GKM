#!/usr/bin/env python3
"""
Isolated test - run just one combination in a fresh Python process.
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


def main():
    all_files = get_all_ontology_files(BASE_DIR)

    base_files = [f for f in all_files if 'Modules' not in f]
    module_files = [f for f in all_files if 'Modules' in f]

    # Select which test to run via command line
    test_num = int(sys.argv[1]) if len(sys.argv) > 1 else 1

    if test_num == 1:
        # Base + modules 0-19 (no Ischart)
        test_files = base_files + module_files[:20]
        desc = "Base + modules 0-19"
    elif test_num == 2:
        # Base + modules 0-20 (with Ischart)
        test_files = base_files + module_files[:21]
        desc = "Base + modules 0-20 (including Ischart)"
    elif test_num == 3:
        # All modules
        test_files = base_files + module_files
        desc = "All modules"
    else:
        print(f"Unknown test: {test_num}")
        return

    print(f"\nTest: {desc}")
    print(f"Files: {len(test_files)}")
    for f in test_files:
        print(f"  {os.path.basename(f)}")

    # Merge files
    print("\nMerging...")
    g = Graph()
    for f in test_files:
        g.parse(f, format='turtle')

    for s, p, o in list(g.triples((None, OWL.imports, None))):
        g.remove((s, p, o))

    fd, temp_file = tempfile.mkstemp(suffix='.rdf')
    os.close(fd)
    g.serialize(destination=temp_file, format='xml')

    print(f"Merged to: {temp_file}")

    # Test consistency
    print("\nLoading into owlready2...")
    start = time.time()

    default_world.ontologies.clear()
    onto = get_ontology(f"file://{os.path.abspath(temp_file)}").load()

    classes = list(onto.classes())
    print(f"Loaded {len(classes)} classes")

    print("Running HermiT reasoner...")
    try:
        sync_reasoner_hermit(onto, infer_property_values=False, debug=0,
                           ignore_unsupported_datatypes=True)

        # Check unsatisfiable
        unsatisfiable = list(default_world.inconsistent_classes())
        unsatisfiable = [str(c) for c in unsatisfiable if str(c) != 'owl.Nothing']

        elapsed = time.time() - start

        if unsatisfiable:
            print(f"\n*** UNSATISFIABLE ({len(unsatisfiable)}) ***")
            for c in unsatisfiable[:20]:
                print(f"  - {c}")
        else:
            print(f"\n*** PASSED - consistent ***")

        print(f"Time: {elapsed:.1f}s")

    except OwlReadyInconsistentOntologyError:
        elapsed = time.time() - start
        print(f"\n*** INCONSISTENT ***")
        print(f"Time: {elapsed:.1f}s")

    # Cleanup
    os.remove(temp_file)


if __name__ == "__main__":
    main()
