#!/usr/bin/env python3
"""Find what in Ischart causes inconsistency by progressively adding individuals."""

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


def quick_test(graph, name):
    """Quick consistency test."""
    print(f"  Testing: {name}...", end=" ", flush=True)

    fd, temp_file = tempfile.mkstemp(suffix='.rdf')
    os.close(fd)
    graph.serialize(destination=temp_file, format='xml')

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
            return False

        unsatisfiable = list(default_world.inconsistent_classes())
        unsatisfiable = [c for c in unsatisfiable if str(c) != 'owl.Nothing']

        elapsed = time.time() - start
        if unsatisfiable:
            print(f"UNSATISFIABLE ({len(unsatisfiable)}) ({elapsed:.1f}s)", flush=True)
            return False
        else:
            print(f"CONSISTENT ({elapsed:.1f}s)", flush=True)
            return True

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

    # Get all gstime: individuals
    gstime_subjects = set()
    for s, p, o in ischart_g:
        if str(s).startswith(str(GSTIME)) and str(s) != str(GSTIME) + "ontology":
            gstime_subjects.add(s)

    print(f"Found {len(gstime_subjects)} gstime: individuals", flush=True)

    # Get triples grouped by subject
    ind_triples = {}
    for s in gstime_subjects:
        ind_triples[s] = list(ischart_g.triples((s, None, None)))

    # Sort individuals by number of triples
    sorted_inds = sorted(ind_triples.keys(), key=lambda x: len(ind_triples[x]))

    # Quick test: add first N individuals
    test_counts = [1, 5, 10, 20, 50]

    for n in test_counts:
        if n > len(sorted_inds):
            break

        test_g = Graph()
        for triple in base_g:
            test_g.add(triple)

        # Add first n individuals
        added_triples = 0
        for i in range(n):
            for triple in ind_triples[sorted_inds[i]]:
                test_g.add(triple)
                added_triples += 1

        print(f"\nAdding {n} individuals ({added_triples} triples):", flush=True)
        if not quick_test(test_g, f"{n} individuals"):
            # Found the breaking point - investigate which individual
            print(f"\n  Narrowing down...", flush=True)

            # Binary search or sequential to find the problematic one
            for i in range(n):
                test_g2 = Graph()
                for triple in base_g:
                    test_g2.add(triple)

                # Add just this one individual
                ind = sorted_inds[i]
                for triple in ind_triples[ind]:
                    test_g2.add(triple)

                print(f"    Individual {i}: {ind}", end=" ", flush=True)
                result = quick_test(test_g2, "single")

                if not result:
                    print(f"\n  PROBLEM: Individual {ind} alone causes inconsistency!", flush=True)
                    print(f"  Triples:", flush=True)
                    for s, p, o in ind_triples[ind]:
                        p_short = str(p).split('/')[-1]
                        o_short = str(o).split('/')[-1] if isinstance(o, URIRef) else str(o)[:50]
                        print(f"    {p_short}: {o_short}", flush=True)
                    break
            else:
                # It's the combination that's problematic
                print(f"\n  Issue is with combination of individuals, not single individual", flush=True)
            break


if __name__ == "__main__":
    main()
