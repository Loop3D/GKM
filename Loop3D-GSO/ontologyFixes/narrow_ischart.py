#!/usr/bin/env python3
"""Narrow down what in Ischart causes inconsistency."""

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
from rdflib import Graph, OWL, RDF, RDFS, URIRef, Namespace, Literal

owlready2.reasoning.JAVA_MEMORY = 4000

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

GSTIME = Namespace("https://w3id.org/gso/1.0/ischart/")
GSOG = Namespace("https://w3id.org/gso/1.0/geology/")
GST = Namespace("https://w3id.org/gso/1.0/geologictime/")
GSOC = Namespace("https://w3id.org/gso/1.0/common/")


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


def test_ontology(file_list, test_name, extra_triples=None):
    """Test ontology consistency."""
    print(f"\n{test_name}", flush=True)
    print("=" * 70, flush=True)

    g = Graph()
    for f in file_list:
        g.parse(f, format='turtle')

    for s, p, o in list(g.triples((None, OWL.imports, None))):
        g.remove((s, p, o))

    if extra_triples:
        for triple in extra_triples:
            g.add(triple)

    print(f"  Total triples: {len(g)}", flush=True)

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

    print(f"Time index: {time_idx}, Ischart index: {ischart_idx}", flush=True)

    test_files = base_files + module_files[:time_idx + 1]

    # Test 1: Baseline - just Age individual
    test_ontology(test_files, "Test 1: Individual typed as Age only",
                  extra_triples=[
                      (GSTIME["TestAge"], RDF.type, GST["Age"]),
                  ])

    # Test 2: Age + Specific (no relationships)
    test_ontology(test_files, "Test 2: Individual typed as Age + Specific",
                  extra_triples=[
                      (GSTIME["TestAge"], RDF.type, GST["Age"]),
                      (GSTIME["TestAge"], RDF.type, GSOG["Specific_Geologic_Time_Unit"]),
                  ])

    # Test 3: Age + isPartOf to Generic individual
    test_ontology(test_files, "Test 3: Age + isPartOf GenericTimeUnit individual",
                  extra_triples=[
                      (GSTIME["TestAge"], RDF.type, GST["Age"]),
                      (GSTIME["GenericAge"], RDF.type, GST["Age"]),
                      (GSTIME["GenericAge"], RDF.type, GSOG["Generic_Geologic_Time_Unit"]),
                      (GSTIME["TestAge"], GSOC["isPartOf"], GSTIME["GenericAge"]),
                  ])

    # Test 4: Load one real Aalenian individual from Ischart
    ischart_file = module_files[ischart_idx]
    ischart_g = Graph()
    ischart_g.parse(ischart_file, format='turtle')

    # Get triples for just one individual (Aalenian2004)
    aalenian_uri = URIRef("https://w3id.org/gso/1.0/ischart/Aalenian2004")
    aalenian_triples = []
    for s, p, o in ischart_g.triples((aalenian_uri, None, None)):
        aalenian_triples.append((s, p, o))

    print(f"\nTriples for Aalenian2004: {len(aalenian_triples)}", flush=True)
    for s, p, o in aalenian_triples[:10]:
        p_short = str(p).split('/')[-1]
        o_short = str(o).split('/')[-1] if isinstance(o, URIRef) else str(o)[:50]
        print(f"  {p_short}: {o_short}", flush=True)

    test_ontology(test_files, "Test 4: Real Aalenian2004 individual (all triples)",
                  extra_triples=aalenian_triples)

    # Test 5: Aalenian2004 with only type assertions
    type_triples = [(s, p, o) for s, p, o in aalenian_triples if p == RDF.type]
    print(f"\nType triples for Aalenian2004: {len(type_triples)}", flush=True)
    for s, p, o in type_triples:
        print(f"  type: {str(o).split('/')[-1]}", flush=True)

    test_ontology(test_files, "Test 5: Aalenian2004 with only type assertions",
                  extra_triples=type_triples)

    # Test 6: Aalenian2004 types + isPartOf relations only
    partof_triples = type_triples + [(s, p, o) for s, p, o in aalenian_triples if 'isPartOf' in str(p)]
    print(f"\nType + isPartOf triples for Aalenian2004: {len(partof_triples)}", flush=True)

    test_ontology(test_files, "Test 6: Aalenian2004 types + isPartOf relations",
                  extra_triples=partof_triples)

    # Test 7: Check if there's an AalenianAge defined as Generic that it's isPartOf
    # First, find what Aalenian2004 is part of
    partof_targets = [o for s, p, o in aalenian_triples if 'isPartOf' in str(p)]
    print(f"\nAalenian2004 isPartOf targets:", flush=True)
    for t in partof_targets:
        print(f"  {t}", flush=True)

    # Test 8: Try minimal case - Age typed as Specific with isPartOf to something typed as Generic
    test_ontology(test_files, "Test 8: Minimal - Specific isPartOf Generic",
                  extra_triples=[
                      (GSTIME["SpecificTest"], RDF.type, GSOG["Specific_Geologic_Time_Unit"]),
                      (GSTIME["GenericTest"], RDF.type, GSOG["Generic_Geologic_Time_Unit"]),
                      (GSTIME["SpecificTest"], GSOC["isPartOf"], GSTIME["GenericTest"]),
                  ])


if __name__ == "__main__":
    main()
