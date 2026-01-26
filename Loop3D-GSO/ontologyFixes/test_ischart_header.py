#!/usr/bin/env python3
"""
Test what in Ischart besides individuals causes the inconsistency.
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


def test_ontology(file_list, test_name, extra_graph=None, remove_patterns=None):
    """Test ontology consistency."""
    print(f"\n{test_name}")
    print("=" * 70)

    g = Graph()
    for f in file_list:
        g.parse(f, format='turtle')

    # Remove owl:imports
    for s, p, o in list(g.triples((None, OWL.imports, None))):
        g.remove((s, p, o))

    if extra_graph:
        for triple in extra_graph:
            g.add(triple)

    if remove_patterns:
        removed = 0
        for s, p, o in list(g):
            for pattern in remove_patterns:
                if pattern in str(s) or pattern in str(o):
                    g.remove((s, p, o))
                    removed += 1
                    break
        print(f"  Removed {removed} triples matching patterns")

    print(f"  Total triples: {len(g)}")

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

    # Find indices
    time_idx = None
    ischart_idx = None
    for i, f in enumerate(module_files):
        if 'GSO-Geologic_Time.ttl' in f and 'Ischart' not in f:
            time_idx = i
        if 'Time_Ischart' in f:
            ischart_idx = i

    print(f"Time index: {time_idx}, Ischart index: {ischart_idx}")

    # Test 1: Base + modules 0-19 (baseline - should be consistent)
    test_files = base_files + module_files[:time_idx + 1]
    test_ontology(test_files, "Test 1: Base + modules 0-19 (no Ischart)")

    # Load Ischart and categorize triples
    ischart_file = module_files[ischart_idx]
    ischart_g = Graph()
    ischart_g.parse(ischart_file, format='turtle')

    # Remove imports from Ischart
    for s, p, o in list(ischart_g.triples((None, OWL.imports, None))):
        ischart_g.remove((s, p, o))

    GSTIME = Namespace("https://w3id.org/gso/1.0/ischart/")
    GSOC = Namespace("https://w3id.org/gso/1.0/common/")
    SCHEMA = Namespace("https://schema.org/")

    # Count types of triples in Ischart
    ontology_triples = []
    author_triples = []
    gstime_triples = []
    blank_node_triples = []
    other_triples = []

    for s, p, o in ischart_g:
        s_str = str(s)
        if s_str == "https://w3id.org/gso/1.0/ischart/ontology":
            ontology_triples.append((s, p, o))
        elif "stephen_richard" in s_str or "boyan_brodaric" in s_str:
            author_triples.append((s, p, o))
        elif s_str.startswith(str(GSTIME)):
            gstime_triples.append((s, p, o))
        elif not isinstance(s, URIRef):
            blank_node_triples.append((s, p, o))
        else:
            other_triples.append((s, p, o))

    print(f"\nIschart triple breakdown:")
    print(f"  Ontology declaration: {len(ontology_triples)}")
    print(f"  Author triples: {len(author_triples)}")
    print(f"  gstime: triples: {len(gstime_triples)}")
    print(f"  Blank node triples: {len(blank_node_triples)}")
    print(f"  Other: {len(other_triples)}")

    # Test 2: Add ONLY ontology declaration
    test_ontology(test_files, "Test 2: Add only Ischart ontology declaration",
                  extra_graph=ontology_triples)

    # Test 3: Add gstime individuals (but NOT their blank node values)
    # Filter to only URI objects
    gstime_uri_only = [(s, p, o) for s, p, o in gstime_triples if isinstance(o, URIRef) or not str(p).endswith('hasDataValue')]
    print(f"\ngstime URI-only triples: {len(gstime_uri_only)}")
    test_ontology(test_files, "Test 3: Add gstime individuals (URI-only properties)",
                  extra_graph=gstime_uri_only)

    # Test 4: Add just ONE gstime individual with minimal properties
    one_ind = [(GSTIME["TestAge"], RDF.type, URIRef("https://w3id.org/gso/1.0/geologictime/Age")),
               (GSTIME["TestAge"], RDF.type, URIRef("https://w3id.org/gso/1.0/geology/Specific_Geologic_Time_Unit"))]
    test_ontology(test_files, "Test 4: Add one minimal gstime individual (Age + Specific)",
                  extra_graph=one_ind)

    # Test 5: Same but with isPartOf to AalenianAge
    one_ind_with_ispartof = one_ind + [
        (GSTIME["TestAge"], GSOC["isPartOf"], URIRef("https://w3id.org/gso/1.0/geologictime/AalenianAge"))
    ]
    test_ontology(test_files, "Test 5: Add one gstime individual + isPartOf AalenianAge",
                  extra_graph=one_ind_with_ispartof)


if __name__ == "__main__":
    main()
