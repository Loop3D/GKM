#!/usr/bin/env python3
"""Test if blank node structures from Ischart cause inconsistency."""

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
from rdflib import Graph, OWL, RDF, URIRef, Namespace, BNode

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


def test_ontology(g, name):
    """Test ontology consistency."""
    print(f"\n{name}", flush=True)
    print("=" * 70, flush=True)
    print(f"  Triples: {len(g)}", flush=True)

    fd, temp_file = tempfile.mkstemp(suffix='.rdf')
    os.close(fd)
    g.serialize(destination=temp_file, format='xml')

    try:
        default_world.ontologies.clear()
        onto = get_ontology(f"file://{os.path.abspath(temp_file)}").load()

        classes = list(onto.classes())
        individuals = list(onto.individuals())
        print(f"  Classes: {len(classes)}, Individuals: {len(individuals)}", flush=True)

        start = time.time()
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
            for c in unsatisfiable[:5]:
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

    # Find indices
    time_idx = None
    ischart_idx = None
    for i, f in enumerate(module_files):
        if 'GSO-Geologic_Time.ttl' in f and 'Ischart' not in f:
            time_idx = i
        if 'Time_Ischart' in f:
            ischart_idx = i

    # Load base ontology (no Ischart)
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

    # Categorize Ischart triples
    gstime_uri_triples = []  # gstime: subject, URI objects only
    gstime_all_triples = []  # gstime: subject, all objects
    blank_node_triples = []  # blank node subjects
    ontology_triples = []  # ontology declaration

    for s, p, o in ischart_g:
        s_str = str(s)
        if not isinstance(s, URIRef):
            blank_node_triples.append((s, p, o))
        elif s_str == str(GSTIME) + "ontology":
            ontology_triples.append((s, p, o))
        elif s_str.startswith(str(GSTIME)):
            gstime_all_triples.append((s, p, o))
            if isinstance(o, URIRef) or p == RDF.type:
                gstime_uri_triples.append((s, p, o))

    print(f"\nIschart breakdown:", flush=True)
    print(f"  gstime URI-only: {len(gstime_uri_triples)}", flush=True)
    print(f"  gstime all: {len(gstime_all_triples)}", flush=True)
    print(f"  Blank nodes: {len(blank_node_triples)}", flush=True)
    print(f"  Ontology: {len(ontology_triples)}", flush=True)

    # Test 1: Base only
    test_ontology(base_g, "Test 1: Base ontology only")

    # Test 2: Add gstime URI-only triples (no blank nodes)
    test_g2 = Graph()
    for triple in base_g:
        test_g2.add(triple)
    for triple in gstime_uri_triples:
        test_g2.add(triple)

    test_ontology(test_g2, "Test 2: Base + gstime URI-only triples")

    # Test 3: Add blank node triples too
    test_g3 = Graph()
    for triple in base_g:
        test_g3.add(triple)
    for triple in gstime_all_triples:
        test_g3.add(triple)
    for triple in blank_node_triples:
        test_g3.add(triple)

    test_ontology(test_g3, "Test 3: Base + all gstime + blank nodes")


if __name__ == "__main__":
    main()
