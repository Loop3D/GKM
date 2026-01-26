#!/usr/bin/env python3
"""Quick check to find unsatisfiable class and test minimal individual."""

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
            return "INCONSISTENT", []

        unsatisfiable = list(default_world.inconsistent_classes())
        unsatisfiable = [c for c in unsatisfiable if str(c) != 'owl.Nothing']

        elapsed = time.time() - start
        if unsatisfiable:
            print(f"  Result: UNSATISFIABLE ({len(unsatisfiable)}) ({elapsed:.1f}s)", flush=True)
            for c in unsatisfiable[:5]:
                print(f"    - {c}", flush=True)
            return "UNSATISFIABLE", unsatisfiable
        else:
            print(f"  Result: CONSISTENT ({elapsed:.1f}s)", flush=True)
            return "CONSISTENT", []

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

    # Test 1: Base + modules up to and including Geologic_Time (no Ischart)
    test_files = base_files + module_files[:time_idx + 1]
    result, unsat = test_ontology(test_files, "Test 1: Base + modules 0-19 (no Ischart)")

    if unsat:
        print(f"\nUnsatisfiable classes:", flush=True)
        for c in unsat:
            print(f"  {c}", flush=True)

    # Test 2: Just add a Specific_Geologic_Time_Unit individual (not Age)
    GSTIME = Namespace("https://w3id.org/gso/1.0/ischart/")
    GSOG = Namespace("https://w3id.org/gso/1.0/geology/")

    specific_only = [
        (GSTIME["TestSpecific"], RDF.type, GSOG["Specific_Geologic_Time_Unit"]),
    ]
    test_ontology(test_files, "Test 2: Add individual typed only as Specific_Geologic_Time_Unit",
                  extra_triples=specific_only)

    # Test 3: Add individual typed only as Age
    GST = Namespace("https://w3id.org/gso/1.0/geologictime/")
    age_only = [
        (GSTIME["TestAge"], RDF.type, GST["Age"]),
    ]
    test_ontology(test_files, "Test 3: Add individual typed only as Age",
                  extra_triples=age_only)

    # Test 4: Add individual typed as both Age and Specific
    both = [
        (GSTIME["TestBoth"], RDF.type, GST["Age"]),
        (GSTIME["TestBoth"], RDF.type, GSOG["Specific_Geologic_Time_Unit"]),
    ]
    test_ontology(test_files, "Test 4: Add individual typed as both Age and Specific",
                  extra_triples=both)


if __name__ == "__main__":
    main()
