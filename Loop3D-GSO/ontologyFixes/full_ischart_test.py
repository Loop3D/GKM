#!/usr/bin/env python3
"""Test full ontology including Ischart module."""

import sys
import os
import tempfile
import glob
import time

java_home = os.environ.get('JAVA_HOME_64', r'C:\Program Files\OpenJDK\jdk-25')
if os.path.exists(java_home):
    os.environ['JAVA_HOME'] = java_home
    os.environ['PATH'] = os.path.join(java_home, 'bin') + os.pathsep + os.environ.get('PATH', '')

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


def test_ontology(file_list, test_name):
    """Test ontology consistency."""
    print(f"\n{test_name}", flush=True)
    print("=" * 70, flush=True)

    g = Graph()
    for f in file_list:
        print(f"  Loading: {os.path.basename(f)}", flush=True)
        g.parse(f, format='turtle')

    for s, p, o in list(g.triples((None, OWL.imports, None))):
        g.remove((s, p, o))

    print(f"  Total triples: {len(g)}", flush=True)

    fd, temp_file = tempfile.mkstemp(suffix='.rdf')
    os.close(fd)
    g.serialize(destination=temp_file, format='xml')

    try:
        default_world.ontologies.clear()
        onto = get_ontology(f"file://{os.path.abspath(temp_file)}").load()

        classes = list(onto.classes())
        individuals = list(onto.individuals())
        print(f"  Loaded {len(classes)} classes, {len(individuals)} individuals", flush=True)

        start = time.time()
        print("  Running HermiT reasoner...", flush=True)
        try:
            sync_reasoner_hermit(onto, infer_property_values=False, debug=0,
                               ignore_unsupported_datatypes=True)
        except OwlReadyInconsistentOntologyError:
            elapsed = time.time() - start
            print(f"  Result: INCONSISTENT ({elapsed:.1f}s)", flush=True)
            return "INCONSISTENT"

        unsatisfiable = list(default_world.inconsistent_classes())
        unsatisfiable = [c for c in unsatisfiable if str(c) != 'owl.Nothing']

        elapsed = time.time() - start
        if unsatisfiable:
            print(f"  Result: UNSATISFIABLE ({len(unsatisfiable)}) ({elapsed:.1f}s)", flush=True)
            for c in unsatisfiable[:10]:
                print(f"    - {c}", flush=True)
            return "UNSATISFIABLE"
        else:
            print(f"  Result: CONSISTENT ({elapsed:.1f}s)", flush=True)
            return "CONSISTENT"

    finally:
        os.remove(temp_file)


def main():
    all_files = get_all_ontology_files(BASE_DIR)

    base_files = [f for f in all_files if 'Modules' not in f]
    module_files = [f for f in all_files if 'Modules' in f]

    # Find Ischart index
    ischart_idx = None
    for i, f in enumerate(module_files):
        if 'Time_Ischart' in f:
            ischart_idx = i
            break

    print(f"Testing with Ischart module (index {ischart_idx})", flush=True)
    print(f"Base files: {len(base_files)}", flush=True)
    print(f"Module files (including Ischart): {ischart_idx + 1}", flush=True)

    # Test with all modules up to and including Ischart
    test_files = base_files + module_files[:ischart_idx + 1]
    result = test_ontology(test_files, "Full ontology with Ischart module")

    print(f"\n{'='*70}", flush=True)
    print(f"FINAL RESULT: {result}", flush=True)
    print(f"{'='*70}", flush=True)


if __name__ == "__main__":
    main()
