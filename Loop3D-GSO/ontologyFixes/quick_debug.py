#!/usr/bin/env python3
"""
Quick debug test with HermiT debug output.
"""

import sys
import os
import tempfile
import glob
import time

# Force unbuffered output
sys.stdout = os.fdopen(sys.stdout.fileno(), 'w', 1)

# Check for 64-bit Java
java_home = os.environ.get('JAVA_HOME_64', r'C:\Program Files\OpenJDK\jdk-25')
if os.path.exists(java_home):
    os.environ['JAVA_HOME'] = java_home
    os.environ['PATH'] = os.path.join(java_home, 'bin') + os.pathsep + os.environ.get('PATH', '')
    print(f"Using 64-bit Java: {os.path.join(java_home, 'bin', 'java.exe')}")

import owlready2
from owlready2 import get_ontology, sync_reasoner_hermit, default_world, OwlReadyInconsistentOntologyError
from rdflib import Graph, OWL, RDF, RDFS, URIRef, Namespace

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

    # Find Ischart
    ischart_idx = None
    for i, f in enumerate(module_files):
        if 'Time_Ischart' in f:
            ischart_idx = i
            break

    print(f"Testing with Ischart module (index {ischart_idx})")

    # Load all files including Ischart
    test_files = base_files + module_files[:ischart_idx + 1]

    g = Graph()
    for f in test_files:
        g.parse(f, format='turtle')

    # Remove owl:imports
    for s, p, o in list(g.triples((None, OWL.imports, None))):
        g.remove((s, p, o))

    fd, temp_file = tempfile.mkstemp(suffix='.rdf')
    os.close(fd)
    g.serialize(destination=temp_file, format='xml')

    print(f"Merged to {temp_file}")
    print(f"Total triples: {len(g)}")

    # Load and run reasoner with debug=2 to see what's happening
    print("\nLoading ontology...")
    default_world.ontologies.clear()
    onto = get_ontology(f"file://{os.path.abspath(temp_file)}").load()

    classes = list(onto.classes())
    individuals = list(onto.individuals())
    print(f"Loaded {len(classes)} classes, {len(individuals)} individuals")

    print("\nRunning HermiT with debug=2...")
    start = time.time()
    try:
        sync_reasoner_hermit(onto, infer_property_values=False, debug=2,
                           ignore_unsupported_datatypes=True)
        elapsed = time.time() - start
        print(f"\nReasoner finished in {elapsed:.1f}s")

        unsatisfiable = list(default_world.inconsistent_classes())
        unsatisfiable = [str(c) for c in unsatisfiable if str(c) != 'owl.Nothing']
        if unsatisfiable:
            print(f"Unsatisfiable classes: {unsatisfiable[:20]}")
        else:
            print("All classes satisfiable")

    except OwlReadyInconsistentOntologyError:
        elapsed = time.time() - start
        print(f"\n*** INCONSISTENT ONTOLOGY *** ({elapsed:.1f}s)")

    os.remove(temp_file)


if __name__ == "__main__":
    main()
