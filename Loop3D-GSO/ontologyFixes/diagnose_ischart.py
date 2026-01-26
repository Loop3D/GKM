#!/usr/bin/env python3
"""
Diagnose the Time_Ischart inconsistency by testing TBox vs ABox.
"""

import sys
import os
import tempfile
import glob
import time
import re

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


def merge_ontologies(file_list, remove_individuals=False):
    """Merge TTL files, optionally removing all individuals."""
    g = Graph()
    for f in file_list:
        g.parse(f, format='turtle')

    # Remove owl:imports
    for s, p, o in list(g.triples((None, OWL.imports, None))):
        g.remove((s, p, o))

    if remove_individuals:
        # Find all named individuals (things that are typed but not classes/properties)
        individuals_to_remove = set()

        # Get all subjects that have rdf:type but are NOT classes, properties, or ontologies
        for s, p, o in g.triples((None, RDF.type, None)):
            # Skip blank nodes
            if not isinstance(s, URIRef):
                continue

            # Check if this is a class (has type owl:Class or is subClassOf something)
            is_class = False
            for _, _, t in g.triples((s, RDF.type, None)):
                if t in [OWL.Class, RDFS.Class, OWL.ObjectProperty, OWL.DatatypeProperty,
                         OWL.AnnotationProperty, OWL.Ontology, OWL.Restriction]:
                    is_class = True
                    break

            if not is_class:
                # Check if it looks like an individual (gstime: namespace typically)
                s_str = str(s)
                if 'gstime:' in s_str or '/gstime/' in s_str or 'isc' in s_str.lower():
                    individuals_to_remove.add(s)

        print(f"  Removing {len(individuals_to_remove)} individuals...")

        # Remove all triples involving these individuals
        for ind in individuals_to_remove:
            for triple in list(g.triples((ind, None, None))):
                g.remove(triple)
            for triple in list(g.triples((None, None, ind))):
                g.remove(triple)

    fd, target_file = tempfile.mkstemp(suffix='.rdf')
    os.close(fd)
    g.serialize(destination=target_file, format='xml')

    return target_file


def check_consistency(rdfxml_path):
    """Check ontology consistency."""
    try:
        default_world.ontologies.clear()
        onto = get_ontology(f"file://{os.path.abspath(rdfxml_path)}").load()

        classes = list(onto.classes())
        individuals = list(onto.individuals())
        print(f"    Loaded {len(classes)} classes, {len(individuals)} individuals")

        try:
            sync_reasoner_hermit(onto, infer_property_values=False, debug=0,
                               ignore_unsupported_datatypes=True)
        except OwlReadyInconsistentOntologyError:
            return "INCONSISTENT", []

        # Check for unsatisfiable classes
        unsatisfiable = list(default_world.inconsistent_classes())
        unsatisfiable = [str(c) for c in unsatisfiable if str(c) != 'owl.Nothing']

        if unsatisfiable:
            return "UNSATISFIABLE", unsatisfiable
        else:
            return "CONSISTENT", []

    except Exception as e:
        return f"ERROR: {e}", []


def main():
    all_files = get_all_ontology_files(BASE_DIR)

    base_files = [f for f in all_files if 'Modules' not in f]
    module_files = [f for f in all_files if 'Modules' in f]

    # Find Time_Ischart
    ischart_idx = None
    for i, f in enumerate(module_files):
        if 'Time_Ischart' in f:
            ischart_idx = i
            break

    print(f"Time_Ischart index: {ischart_idx}")

    # Test 1: Base + modules 0-19 (without Ischart) - should be consistent
    print("\n" + "=" * 70)
    print("Test 1: Base + modules 0-19 (without Ischart)")
    print("=" * 70)
    test_files = base_files + module_files[:ischart_idx]

    temp_file = merge_ontologies(test_files)
    try:
        start = time.time()
        result, unsats = check_consistency(temp_file)
        elapsed = time.time() - start
        print(f"  Result: {result} ({elapsed:.1f}s)")
    finally:
        os.remove(temp_file)

    # Test 2: Base + modules 0-20 (with Ischart) - full ontology with individuals
    print("\n" + "=" * 70)
    print("Test 2: Base + modules 0-20 (with Ischart, WITH individuals)")
    print("=" * 70)
    test_files = base_files + module_files[:ischart_idx + 1]

    temp_file = merge_ontologies(test_files, remove_individuals=False)
    try:
        start = time.time()
        result, unsats = check_consistency(temp_file)
        elapsed = time.time() - start
        print(f"  Result: {result} ({elapsed:.1f}s)")
        if unsats:
            print(f"  Unsatisfiable: {unsats[:10]}")
    finally:
        os.remove(temp_file)

    # Test 3: Base + modules 0-20 (with Ischart) - TBox only, no individuals
    print("\n" + "=" * 70)
    print("Test 3: Base + modules 0-20 (with Ischart, WITHOUT individuals)")
    print("=" * 70)
    test_files = base_files + module_files[:ischart_idx + 1]

    temp_file = merge_ontologies(test_files, remove_individuals=True)
    try:
        start = time.time()
        result, unsats = check_consistency(temp_file)
        elapsed = time.time() - start
        print(f"  Result: {result} ({elapsed:.1f}s)")
        if unsats:
            print(f"  Unsatisfiable: {unsats[:10]}")
    finally:
        os.remove(temp_file)

    # Test 4: Add just ONE individual to see if that's the problem
    print("\n" + "=" * 70)
    print("Test 4: Testing with minimal individuals")
    print("=" * 70)

    # Start with just Time module (no Ischart) and add one specific individual
    test_files = base_files + module_files[:ischart_idx]  # Without Ischart

    g = Graph()
    for f in test_files:
        g.parse(f, format='turtle')

    # Remove imports
    for s, p, o in list(g.triples((None, OWL.imports, None))):
        g.remove((s, p, o))

    # Add one minimal individual - just typed as Age and Specific_Geologic_Time_Unit
    GSTIME = Namespace("http://resource.geosciml.org/classifier/ics/ischart/")
    GST = Namespace("http://loop3d.org/GSO/ontology/2020/1/geologictime/")
    GSOG = Namespace("http://loop3d.org/GSO/ontology/2020/1/geology/")

    # Add a minimal test individual
    test_ind = GSTIME["TestAge2004"]
    g.add((test_ind, RDF.type, GST["Age"]))
    g.add((test_ind, RDF.type, GSOG["Specific_Geologic_Time_Unit"]))

    fd, temp_file = tempfile.mkstemp(suffix='.rdf')
    os.close(fd)
    g.serialize(destination=temp_file, format='xml')

    try:
        start = time.time()
        result, unsats = check_consistency(temp_file)
        elapsed = time.time() - start
        print(f"  Result: {result} ({elapsed:.1f}s)")
        if unsats:
            print(f"  Unsatisfiable: {unsats[:10]}")
    finally:
        os.remove(temp_file)


if __name__ == "__main__":
    main()
