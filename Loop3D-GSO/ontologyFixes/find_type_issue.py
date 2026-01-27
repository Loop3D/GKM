#!/usr/bin/env python3
"""Find which type assertions cause inconsistency."""

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
from rdflib import Graph, OWL, RDF, URIRef, Namespace

owlready2.reasoning.JAVA_MEMORY = 4000

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

GSTIME = Namespace("https://w3id.org/gso/1.0/ischart/")


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


def quick_test(g):
    """Quick consistency test."""
    fd, temp_file = tempfile.mkstemp(suffix='.rdf')
    os.close(fd)
    g.serialize(destination=temp_file, format='xml')

    try:
        default_world.ontologies.clear()
        onto = get_ontology(f"file://{os.path.abspath(temp_file)}").load()

        try:
            sync_reasoner_hermit(onto, infer_property_values=False, debug=0,
                               ignore_unsupported_datatypes=True)
        except OwlReadyInconsistentOntologyError:
            return False

        unsatisfiable = list(default_world.inconsistent_classes())
        unsatisfiable = [c for c in unsatisfiable if str(c) != 'owl.Nothing']
        return len(unsatisfiable) == 0

    finally:
        os.remove(temp_file)


def main():
    all_files = get_all_ontology_files(BASE_DIR)

    base_files = [f for f in all_files if 'Modules' not in f]
    module_files = [f for f in all_files if 'Modules' in f]

    # Find indices
    time_idx = None
    ischart_idx = None
    for i, f in enumerate(module_files):
        if 'GSO-Geologic_Time.ttl' in f and 'Ischart' not in f:
            time_idx = i
        if 'Time_Ischart' in f:
            ischart_idx = i

    # Load base ontology
    base_test_files = base_files + module_files[:time_idx + 1]
    base_g = Graph()
    for f in base_test_files:
        base_g.parse(f, format='turtle')

    for s, p, o in list(base_g.triples((None, OWL.imports, None))):
        base_g.remove((s, p, o))

    print(f"Base ontology: {len(base_g)} triples", flush=True)

    # Load Ischart
    ischart_file = module_files[ischart_idx]
    ischart_g = Graph()
    ischart_g.parse(ischart_file, format='turtle')

    # Get type assertions
    type_triples = []
    for s, p, o in ischart_g:
        s_str = str(s)
        if isinstance(s, URIRef) and s_str.startswith(str(GSTIME)) and s_str != str(GSTIME) + "ontology":
            if p == RDF.type:
                type_triples.append((s, p, o))

    print(f"Type triples: {len(type_triples)}", flush=True)

    # Group by type
    by_type = {}
    for s, p, o in type_triples:
        type_str = str(o).split('/')[-1]
        if type_str not in by_type:
            by_type[type_str] = []
        by_type[type_str].append((s, p, o))

    print(f"\nType distribution:", flush=True)
    for t, triples in sorted(by_type.items(), key=lambda x: -len(x[1])):
        print(f"  {t}: {len(triples)}", flush=True)

    # Test each type alone
    print(f"\n{'='*70}", flush=True)
    print(f"Testing each type alone:", flush=True)
    print(f"{'='*70}", flush=True)

    for type_name, triples in sorted(by_type.items(), key=lambda x: -len(x[1])):
        test_g = Graph()
        for triple in base_g:
            test_g.add(triple)
        for triple in triples:
            test_g.add(triple)

        print(f"  {type_name} ({len(triples)} triples)...", end=" ", flush=True)
        start = time.time()
        if quick_test(test_g):
            print(f"CONSISTENT ({time.time()-start:.1f}s)", flush=True)
        else:
            print(f"INCONSISTENT ({time.time()-start:.1f}s)", flush=True)

    # Test without each type
    print(f"\n{'='*70}", flush=True)
    print(f"Testing all types EXCEPT one:", flush=True)
    print(f"{'='*70}", flush=True)

    for exclude_type in sorted(by_type.keys(), key=lambda x: -len(by_type[x])):
        test_g = Graph()
        for triple in base_g:
            test_g.add(triple)
        for type_name, triples in by_type.items():
            if type_name != exclude_type:
                for triple in triples:
                    test_g.add(triple)

        print(f"  Without {exclude_type}...", end=" ", flush=True)
        start = time.time()
        if quick_test(test_g):
            print(f"CONSISTENT ({time.time()-start:.1f}s)", flush=True)
        else:
            print(f"INCONSISTENT ({time.time()-start:.1f}s)", flush=True)


if __name__ == "__main__":
    main()
