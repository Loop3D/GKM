#!/usr/bin/env python3
"""Binary search to find which ischart triples cause inconsistency."""

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
    """Quick consistency test - returns True if consistent."""
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

    # Get URI-only triples from gstime individuals
    gstime_uri_triples = []
    for s, p, o in ischart_g:
        s_str = str(s)
        if isinstance(s, URIRef) and s_str.startswith(str(GSTIME)) and s_str != str(GSTIME) + "ontology":
            if isinstance(o, URIRef) or p == RDF.type:
                gstime_uri_triples.append((s, p, o))

    print(f"gstime URI triples: {len(gstime_uri_triples)}", flush=True)

    # Group by predicate
    by_predicate = {}
    for s, p, o in gstime_uri_triples:
        p_str = str(p).split('/')[-1]
        if p_str not in by_predicate:
            by_predicate[p_str] = []
        by_predicate[p_str].append((s, p, o))

    print(f"\nPredicates:", flush=True)
    for p, triples in sorted(by_predicate.items(), key=lambda x: -len(x[1])):
        print(f"  {p}: {len(triples)}", flush=True)

    # Test adding predicates one at a time
    print(f"\n{'='*70}", flush=True)
    print("Testing each predicate group:", flush=True)
    print(f"{'='*70}", flush=True)

    for p_name, triples in sorted(by_predicate.items(), key=lambda x: -len(x[1])):
        test_g = Graph()
        for triple in base_g:
            test_g.add(triple)
        for triple in triples:
            test_g.add(triple)

        print(f"  {p_name} ({len(triples)} triples)...", end=" ", flush=True)
        start = time.time()
        if quick_test(test_g):
            elapsed = time.time() - start
            print(f"CONSISTENT ({elapsed:.1f}s)", flush=True)
        else:
            elapsed = time.time() - start
            print(f"INCONSISTENT ({elapsed:.1f}s)", flush=True)

    # Now test combinations
    print(f"\n{'='*70}", flush=True)
    print("Testing predicate combinations:", flush=True)
    print(f"{'='*70}", flush=True)

    # Start with just type assertions
    type_triples = by_predicate.get('22-rdf-syntax-ns#type', [])
    print(f"\nBase: type assertions ({len(type_triples)} triples)", flush=True)

    test_g = Graph()
    for triple in base_g:
        test_g.add(triple)
    for triple in type_triples:
        test_g.add(triple)

    print(f"  Result: ", end="", flush=True)
    start = time.time()
    if quick_test(test_g):
        elapsed = time.time() - start
        print(f"CONSISTENT ({elapsed:.1f}s)", flush=True)
    else:
        elapsed = time.time() - start
        print(f"INCONSISTENT ({elapsed:.1f}s)", flush=True)

    # Add isPartOf
    if 'isPartOf' in by_predicate:
        partof_triples = by_predicate['isPartOf']
        print(f"\n+ isPartOf ({len(partof_triples)} triples)", flush=True)
        for triple in partof_triples:
            test_g.add(triple)

        print(f"  Result: ", end="", flush=True)
        start = time.time()
        if quick_test(test_g):
            elapsed = time.time() - start
            print(f"CONSISTENT ({elapsed:.1f}s)", flush=True)
        else:
            elapsed = time.time() - start
            print(f"INCONSISTENT ({elapsed:.1f}s)", flush=True)


if __name__ == "__main__":
    main()
