#!/usr/bin/env python3
"""
Minimal test to find exactly what combination causes the inconsistency.
"""

import sys
import os
import tempfile
import glob
import time

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


def test_ontology(file_list, test_name, add_individual=None):
    """Test ontology consistency, optionally adding an individual."""
    print(f"\n{test_name}")
    print("=" * 70)

    g = Graph()
    for f in file_list:
        g.parse(f, format='turtle')

    # Remove owl:imports
    for s, p, o in list(g.triples((None, OWL.imports, None))):
        g.remove((s, p, o))

    if add_individual:
        for triple in add_individual:
            g.add(triple)

    fd, temp_file = tempfile.mkstemp(suffix='.rdf')
    os.close(fd)
    g.serialize(destination=temp_file, format='xml')

    try:
        default_world.ontologies.clear()
        onto = get_ontology(f"file://{os.path.abspath(temp_file)}").load()

        classes = list(onto.classes())
        individuals = list(onto.individuals())
        print(f"  Loaded {len(classes)} classes, {len(individuals)} individuals")

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
            for u in unsatisfiable[:5]:
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

    # Find key module indices
    time_idx = None
    ischart_idx = None
    for i, f in enumerate(module_files):
        if 'GSO-Geologic_Time.ttl' in f and 'Ischart' not in f:
            time_idx = i
        if 'Time_Ischart' in f:
            ischart_idx = i

    print(f"Time index: {time_idx}, Ischart index: {ischart_idx}")

    # Define namespaces for test individuals
    GSTIME = Namespace("https://w3id.org/gso/1.0/ischart/")
    GST = Namespace("https://w3id.org/gso/1.0/geologictime/")
    GSOG = Namespace("https://w3id.org/gso/1.0/geology/")
    GSOC = Namespace("https://w3id.org/gso/1.0/common/")

    # Test 1: Base + Time (no Ischart) - baseline
    test_ontology(base_files + module_files[:time_idx + 1],
                  "Test 1: Base + Time module (no Ischart)")

    # Test 2: Just add an individual typed as Age only
    test_ind = GSTIME["TestAge"]
    ind_triples = [
        (test_ind, RDF.type, GST["Age"]),
    ]
    test_ontology(base_files + module_files[:time_idx + 1],
                  "Test 2: Base + Time + individual typed as Age only",
                  add_individual=ind_triples)

    # Test 3: Just add an individual typed as Specific_Geologic_Time_Unit only
    test_ind = GSTIME["TestSpecific"]
    ind_triples = [
        (test_ind, RDF.type, GSOG["Specific_Geologic_Time_Unit"]),
    ]
    test_ontology(base_files + module_files[:time_idx + 1],
                  "Test 3: Base + Time + individual typed as Specific_Geologic_Time_Unit only",
                  add_individual=ind_triples)

    # Test 4: Individual typed as BOTH Age AND Specific_Geologic_Time_Unit
    test_ind = GSTIME["TestBoth"]
    ind_triples = [
        (test_ind, RDF.type, GST["Age"]),
        (test_ind, RDF.type, GSOG["Specific_Geologic_Time_Unit"]),
    ]
    test_ontology(base_files + module_files[:time_idx + 1],
                  "Test 4: Base + Time + individual typed as BOTH Age AND Specific_Geologic_Time_Unit",
                  add_individual=ind_triples)

    # Test 5: Check if Age class itself is somehow becoming Unsatisfiable
    # Let's test just the class definitions without the Ischart module
    print("\n" + "=" * 70)
    print("Checking if any classes become unsatisfiable...")
    print("=" * 70)

    # Is gst:Age satisfiable?
    # Is gsog:Specific_Geologic_Time_Unit satisfiable?
    # Is the intersection (gst:Age AND gsog:Specific_Geologic_Time_Unit) satisfiable?

    # Add an equivalence to test class satisfiability
    test_class = URIRef("https://w3id.org/gso/1.0/test/AgeSpecific")
    ind_triples = [
        (test_class, RDF.type, OWL.Class),
        (test_class, RDFS.subClassOf, GST["Age"]),
        (test_class, RDFS.subClassOf, GSOG["Specific_Geologic_Time_Unit"]),
    ]
    test_ontology(base_files + module_files[:time_idx + 1],
                  "Test 5: Base + Time + new class subClassOf BOTH Age AND Specific_Geologic_Time_Unit",
                  add_individual=ind_triples)


if __name__ == "__main__":
    main()
