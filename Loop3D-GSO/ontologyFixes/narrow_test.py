#!/usr/bin/env python3
"""
Narrow down exactly what causes the inconsistency.
"""

import sys
import os
import tempfile
import glob
import time

# Check for 64-bit Java
java_home = os.environ.get('JAVA_HOME_64', r'C:\Program Files\\OpenJDK\\jdk-25')
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


def test_ontology(file_list, test_name, extra_triples=None):
    """Test ontology consistency."""
    print(f"\n{test_name}", flush=True)
    print("=" * 70, flush=True)

    g = Graph()
    for f in file_list:
        g.parse(f, format='turtle')

    # Remove owl:imports
    for s, p, o in list(g.triples((None, OWL.imports, None))):
        g.remove((s, p, o))

    if extra_triples:
        for triple in extra_triples:
            g.add(triple)

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
        try:
            sync_reasoner_hermit(onto, infer_property_values=False, debug=0,
                               ignore_unsupported_datatypes=True)
        except OwlReadyInconsistentOntologyError:
            elapsed = time.time() - start
            print(f"  Result: INCONSISTENT ({elapsed:.1f}s)")
            return "INCONSISTENT"

        unsatisfiable = list(default_world.inconsistent_classes())
        unsatisfiable = [str(c) for c in unsatisfiable if str(c) != 'owl.Nothing']

        elapsed = time.time() - start
        if unsatisfiable:
            print(f"  Result: UNSATISFIABLE ({len(unsatisfiable)}) ({elapsed:.1f}s)")
            for u in unsatisfiable[:10]:
                print(f"    - {u}")
            return "UNSATISFIABLE"
        else:
            print(f"  Result: CONSISTENT ({elapsed:.1f}s)")
            return "CONSISTENT"

    finally:
        os.remove(temp_file)


def main():
    all_files = get_all_ontology_files(BASE_DIR)

    base_files = [f for f in all_files if 'Modules' not in f]
    module_files = [f for f in all_files if 'Modules' in f]

    # Find Time module (not Ischart)
    time_idx = None
    for i, f in enumerate(module_files):
        if 'GSO-Geologic_Time.ttl' in f and 'Ischart' not in f:
            time_idx = i
            break

    print(f"Time index: {time_idx}")

    GSTIME = Namespace("https://w3id.org/gso/1.0/ischart/")
    GST = Namespace("https://w3id.org/gso/1.0/geologictime/")
    GSOG = Namespace("https://w3id.org/gso/1.0/geology/")
    GSOC = Namespace("https://w3id.org/gso/1.0/common/")

    base_test_files = base_files + module_files[:time_idx + 1]

    # Test 1: Individual typed as Age + Specific, with isPartOf to AalenianAge (Generic)
    test_ind = GSTIME["Test1"]
    extra = [
        (test_ind, RDF.type, GST["Age"]),
        (test_ind, RDF.type, GSOG["Specific_Geologic_Time_Unit"]),
        (test_ind, GSOC["isPartOf"], GST["AalenianAge"]),  # AalenianAge is Generic
    ]
    test_ontology(base_test_files,
                  "Test 1: Age+Specific with isPartOf to Generic (AalenianAge)",
                  extra_triples=extra)

    # Test 2: Individual typed as ONLY Age (not Specific), with isPartOf to AalenianAge
    test_ind = GSTIME["Test2"]
    extra = [
        (test_ind, RDF.type, GST["Age"]),
        (test_ind, GSOC["isPartOf"], GST["AalenianAge"]),
    ]
    test_ontology(base_test_files,
                  "Test 2: Age only (no Specific), with isPartOf to Generic",
                  extra_triples=extra)

    # Test 3: Individual typed as Age + Specific, with isPartOf to something that's NOT Generic
    # Create a new individual that's just an Age (not Generic)
    parent_ind = GSTIME["ParentAge"]
    test_ind = GSTIME["Test3"]
    extra = [
        (parent_ind, RDF.type, GST["Age"]),  # NOT Generic_Geologic_Time_Unit
        (test_ind, RDF.type, GST["Age"]),
        (test_ind, RDF.type, GSOG["Specific_Geologic_Time_Unit"]),
        (test_ind, GSOC["isPartOf"], parent_ind),
    ]
    test_ontology(base_test_files,
                  "Test 3: Age+Specific with isPartOf to Age-only (not Generic)",
                  extra_triples=extra)

    # Test 4: Individual typed as Age + Specific, NO isPartOf relationship
    test_ind = GSTIME["Test4"]
    extra = [
        (test_ind, RDF.type, GST["Age"]),
        (test_ind, RDF.type, GSOG["Specific_Geologic_Time_Unit"]),
    ]
    test_ontology(base_test_files,
                  "Test 4: Age+Specific, NO isPartOf (baseline)",
                  extra_triples=extra)

    # Test 5: Check what happens if we just say something is isPartOf a Generic
    test_ind = GSTIME["Test5"]
    extra = [
        (test_ind, RDF.type, GSOG["Geologic_Time_Interval"]),  # Just Geologic_Time_Interval, not Age or Specific
        (test_ind, GSOC["isPartOf"], GST["AalenianAge"]),
    ]
    test_ontology(base_test_files,
                  "Test 5: Geologic_Time_Interval with isPartOf Generic",
                  extra_triples=extra)

    # Test 6: Individual typed as Specific_Geologic_Time_Unit only, with isPartOf to Generic
    test_ind = GSTIME["Test6"]
    extra = [
        (test_ind, RDF.type, GSOG["Specific_Geologic_Time_Unit"]),
        (test_ind, GSOC["isPartOf"], GST["AalenianAge"]),
    ]
    test_ontology(base_test_files,
                  "Test 6: Specific only, with isPartOf Generic",
                  extra_triples=extra)


if __name__ == "__main__":
    main()
