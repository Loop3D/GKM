#!/usr/bin/env python3
"""Test if cardinality constraints cause the issue."""

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
GSOC = Namespace("https://w3id.org/gso/1.0/common/")
GSOG = Namespace("https://w3id.org/gso/1.0/geology/")
GST = Namespace("https://w3id.org/gso/1.0/geologictime/")


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


def quick_test(g, name):
    """Quick consistency test."""
    print(f"{name}...", end=" ", flush=True)

    fd, temp_file = tempfile.mkstemp(suffix='.rdf')
    os.close(fd)
    g.serialize(destination=temp_file, format='xml')

    try:
        default_world.ontologies.clear()
        onto = get_ontology(f"file://{os.path.abspath(temp_file)}").load()

        start = time.time()
        try:
            sync_reasoner_hermit(onto, infer_property_values=False, debug=0,
                               ignore_unsupported_datatypes=True)
        except OwlReadyInconsistentOntologyError:
            elapsed = time.time() - start
            print(f"INCONSISTENT ({elapsed:.1f}s)", flush=True)
            return "INCONSISTENT"

        unsatisfiable = list(default_world.inconsistent_classes())
        unsatisfiable = [c for c in unsatisfiable if str(c) != 'owl.Nothing']
        elapsed = time.time() - start

        if unsatisfiable:
            print(f"UNSATISFIABLE ({len(unsatisfiable)}) ({elapsed:.1f}s)", flush=True)
            return "UNSATISFIABLE"
        else:
            print(f"CONSISTENT ({elapsed:.1f}s)", flush=True)
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

    # Collect Ischart URI triples
    ischart_uri_triples = []
    for s, p, o in ischart_g:
        s_str = str(s)
        if isinstance(s, URIRef) and s_str.startswith(str(GSTIME)) and s_str != str(GSTIME) + "ontology":
            if isinstance(o, URIRef) or p == RDF.type:
                ischart_uri_triples.append((s, p, o))

    print(f"Ischart URI triples: {len(ischart_uri_triples)}", flush=True)

    # Test 1: All Ischart (baseline)
    print(f"\n{'='*70}", flush=True)
    test_g = Graph()
    for triple in base_g:
        test_g.add(triple)
    for triple in ischart_uri_triples:
        test_g.add(triple)
    quick_test(test_g, f"Test 1: All Ischart URI triples")

    # Test 2: Remove cardinality restrictions from Specific_Geologic_Time_Unit
    # by modifying the base graph
    print(f"\n{'='*70}", flush=True)
    print("Test 2: Removing exact cardinality restrictions from Specific_Geologic_Time_Unit", flush=True)

    # Find and remove cardinality restrictions
    test_g2 = Graph()
    specific_uri = GSOG["Specific_Geologic_Time_Unit"]

    # Copy all triples except cardinality restrictions on Specific
    removed = 0
    for s, p, o in base_g:
        # Skip blank nodes that are cardinality restrictions on Specific
        if s == specific_uri and p == URIRef("http://www.w3.org/2000/01/rdf-schema#subClassOf"):
            # Check if o is a blank node
            if not isinstance(o, URIRef):
                # Check if this blank node has qualifiedCardinality
                is_cardinality = False
                for _, p2, _ in base_g.triples((o, None, None)):
                    if 'qualifiedCardinality' in str(p2):
                        is_cardinality = True
                        break
                if is_cardinality:
                    removed += 1
                    continue
        test_g2.add((s, p, o))

    print(f"  Removed {removed} cardinality restrictions", flush=True)

    # Add Ischart
    for triple in ischart_uri_triples:
        test_g2.add(triple)

    quick_test(test_g2, f"Without cardinality restrictions ({len(test_g2)} triples)")

    # Test 3: What if we only keep type assertions (no relationships)?
    print(f"\n{'='*70}", flush=True)
    type_triples = [(s, p, o) for s, p, o in ischart_uri_triples if p == RDF.type]
    test_g3 = Graph()
    for triple in base_g:
        test_g3.add(triple)
    for triple in type_triples:
        test_g3.add(triple)

    quick_test(test_g3, f"Test 3: Only type assertions ({len(type_triples)} triples)")


if __name__ == "__main__":
    main()
