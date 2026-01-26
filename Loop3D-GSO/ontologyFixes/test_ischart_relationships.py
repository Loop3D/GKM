#!/usr/bin/env python3
"""
Test which relationships in Time_Ischart individuals cause the inconsistency.
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


def test_ontology(file_list, test_name, extra_triples=None, remove_patterns=None):
    """Test ontology consistency."""
    print(f"\n{test_name}")
    print("=" * 70)

    g = Graph()
    for f in file_list:
        g.parse(f, format='turtle')

    # Remove owl:imports
    for s, p, o in list(g.triples((None, OWL.imports, None))):
        g.remove((s, p, o))

    if remove_patterns:
        removed = 0
        for s, p, o in list(g):
            for pattern in remove_patterns:
                if pattern in str(s) or pattern in str(o) or pattern in str(p):
                    g.remove((s, p, o))
                    removed += 1
                    break
        print(f"  Removed {removed} triples matching patterns")

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
    ischart_idx = None
    for i, f in enumerate(module_files):
        if 'Time_Ischart' in f:
            ischart_idx = i
            break

    print(f"Ischart index: {ischart_idx}")
    ischart_file = module_files[ischart_idx]
    print(f"Ischart file: {ischart_file}")

    # Load Ischart and count relationships
    g = Graph()
    g.parse(ischart_file, format='turtle')

    print(f"\nIschart has {len(g)} triples")

    # Count predicates
    predicates = {}
    for s, p, o in g:
        p_str = str(p)
        predicates[p_str] = predicates.get(p_str, 0) + 1

    print("\nPredicate counts:")
    for p, count in sorted(predicates.items(), key=lambda x: -x[1])[:15]:
        p_short = p.split('/')[-1].split('#')[-1]
        print(f"  {p_short}: {count}")

    # Test with full Ischart
    test_files = base_files + module_files[:ischart_idx + 1]
    test_ontology(test_files, "Test 1: Full Ischart (baseline)")

    # Test removing gstime: individuals (keeping everything else)
    test_ontology(test_files,
                  "Test 2: Remove gstime: URIs",
                  remove_patterns=['ischart/'])

    # Test removing isPartOf relationships
    test_ontology(test_files,
                  "Test 3: Remove isPartOf relationships",
                  remove_patterns=['isPartOf'])

    # Test removing timeStartedBy/timeFinishedBy relationships
    test_ontology(test_files,
                  "Test 4: Remove time boundary relationships",
                  remove_patterns=['timeStartedBy', 'timeFinishedBy'])

    # Test removing nextTimeInterval/previousTimeInterval
    test_ontology(test_files,
                  "Test 5: Remove next/previous time relationships",
                  remove_patterns=['nextTimeInterval', 'previousTimeInterval'])

    # Test with minimal individual - just type assertions
    print("\n" + "=" * 70)
    print("Test 6: Creating minimal Ischart-style individual")
    print("=" * 70)

    GSTIME = Namespace("https://w3id.org/gso/1.0/ischart/")
    GST = Namespace("https://w3id.org/gso/1.0/geologictime/")
    GSOG = Namespace("https://w3id.org/gso/1.0/geology/")
    GSOC = Namespace("https://w3id.org/gso/1.0/common/")

    # Copy what Aalenian2004 does: typed as Age and Specific, with isPartOf gst:AalenianAge
    test_ind = GSTIME["TestAalenian"]
    extra = [
        (test_ind, RDF.type, GST["Age"]),
        (test_ind, RDF.type, GSOG["Specific_Geologic_Time_Unit"]),
        (test_ind, GSOC["isPartOf"], GST["AalenianAge"]),
    ]

    test_files_no_ischart = base_files + module_files[:ischart_idx]
    test_ontology(test_files_no_ischart,
                  "Test 6: Base + Time (no Ischart) + minimal individual with isPartOf",
                  extra_triples=extra)


if __name__ == "__main__":
    main()
