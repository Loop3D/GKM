#!/usr/bin/env python3
"""Test full GSO ontology INCLUDING Ischart module.

GSO-Feature is excluded because the GSO-Master comment says
'Shell to load all GSO files, except GSO-Feature' and the Feature
module itself says it is not imported into the master ontology.

GSO-Geologic_Time_Ischart IS included to verify the fix that added
Geologic_Time_Boundary to the Epoch/Period timeIncludes unions.
"""

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


def get_ontology_files(base_path):
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
             '.inconsistent' not in f]

    # Exclude only Feature (not imported by Master per design)
    excluded = []
    result = []
    for f in files:
        basename = os.path.basename(f).lower()
        if basename == 'gso-feature.ttl':
            excluded.append(f)
        else:
            result.append(f)

    return sorted(set(result)), excluded


def main():
    all_files, excluded = get_ontology_files(BASE_DIR)

    print(f"Loading {len(all_files)} ontology files:", flush=True)
    for f in all_files:
        print(f"  {os.path.basename(f)}", flush=True)

    if excluded:
        print(f"\nExcluded {len(excluded)} files:", flush=True)
        for f in excluded:
            print(f"  {os.path.basename(f)}", flush=True)

    g = Graph()
    for f in all_files:
        g.parse(f, format='turtle')

    # Remove owl:imports
    imports_removed = 0
    for s, p, o in list(g.triples((None, OWL.imports, None))):
        g.remove((s, p, o))
        imports_removed += 1

    print(f"\nTotal triples: {len(g)}", flush=True)
    print(f"Imports removed: {imports_removed}", flush=True)

    # Save to temp file
    fd, temp_file = tempfile.mkstemp(suffix='.rdf')
    os.close(fd)
    print(f"Serializing to RDF/XML...", flush=True)
    g.serialize(destination=temp_file, format='xml')

    try:
        default_world.ontologies.clear()
        print(f"Loading into owlready2...", flush=True)
        onto = get_ontology(f"file://{os.path.abspath(temp_file)}").load()

        classes = list(onto.classes())
        individuals = list(onto.individuals())
        print(f"Loaded {len(classes)} classes, {len(individuals)} individuals", flush=True)

        print(f"\nRunning HermiT reasoner...", flush=True)
        start = time.time()
        try:
            sync_reasoner_hermit(onto, infer_property_values=False, debug=0,
                               ignore_unsupported_datatypes=True)
        except OwlReadyInconsistentOntologyError:
            elapsed = time.time() - start
            print(f"\nResult: INCONSISTENT ({elapsed:.1f}s)", flush=True)
            sys.exit(1)

        unsatisfiable = list(default_world.inconsistent_classes())
        unsatisfiable = [c for c in unsatisfiable if str(c) != 'owl.Nothing']

        elapsed = time.time() - start
        if unsatisfiable:
            unsat_names = sorted(set(str(c) for c in unsatisfiable))
            print(f"\nResult: UNSATISFIABLE ({len(unsatisfiable)} classes) ({elapsed:.1f}s)", flush=True)
            for name in unsat_names:
                print(f"  - {name}", flush=True)
            sys.exit(1)
        else:
            print(f"\nResult: CONSISTENT ({elapsed:.1f}s)", flush=True)
            print(f"All classes are satisfiable!", flush=True)

    finally:
        os.remove(temp_file)


if __name__ == "__main__":
    main()
