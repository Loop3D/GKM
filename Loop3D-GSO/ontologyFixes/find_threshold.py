#!/usr/bin/env python3
"""Find threshold where Scale + Point becomes inconsistent."""

import sys
import os
import tempfile
import glob
import time
from collections import defaultdict

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


def quick_test(g, max_time=60):
    """Quick consistency test."""
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
            return False, time.time() - start

        unsatisfiable = list(default_world.inconsistent_classes())
        unsatisfiable = [c for c in unsatisfiable if str(c) != 'owl.Nothing']
        return len(unsatisfiable) == 0, time.time() - start

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

    # Get subjects by type
    types_by_subject = defaultdict(set)
    for s, p, o in ischart_g:
        s_str = str(s)
        if isinstance(s, URIRef) and s_str.startswith(str(GSTIME)) and s_str != str(GSTIME) + "ontology":
            if p == RDF.type:
                types_by_subject[s].add(str(o).split('/')[-1])

    scale_subjects = [s for s, types in types_by_subject.items() if 'Geologic_Time_Scale' in types]
    point_subjects = [s for s, types in types_by_subject.items() if 'Stratigraphic_Point' in types]

    print(f"Scale subjects: {len(scale_subjects)}", flush=True)
    print(f"Point subjects: {len(point_subjects)}", flush=True)

    # Get all triples for these subjects
    triples_by_subject = defaultdict(list)
    for s, p, o in ischart_g:
        s_str = str(s)
        if isinstance(s, URIRef) and s_str.startswith(str(GSTIME)) and s_str != str(GSTIME) + "ontology":
            if isinstance(o, URIRef) or p == RDF.type:
                triples_by_subject[s].append((s, p, o))

    # Test progressively
    print(f"\n{'='*70}", flush=True)
    print(f"Finding threshold:", flush=True)
    print(f"{'='*70}", flush=True)

    for n_scale in [2, 5, 10, 17]:
        for n_point in [2, 5, 10, 20, 32]:
            if n_scale > len(scale_subjects) or n_point > len(point_subjects):
                continue

            test_g = Graph()
            for triple in base_g:
                test_g.add(triple)

            for subj in scale_subjects[:n_scale]:
                for triple in triples_by_subject[subj]:
                    test_g.add(triple)
            for subj in point_subjects[:n_point]:
                for triple in triples_by_subject[subj]:
                    test_g.add(triple)

            print(f"  {n_scale} Scale + {n_point} Point...", end=" ", flush=True)
            result, elapsed = quick_test(test_g)
            if result:
                print(f"CONSISTENT ({elapsed:.1f}s)", flush=True)
            else:
                print(f"INCONSISTENT ({elapsed:.1f}s)", flush=True)
                if elapsed < 10:
                    print(f"    ^^^ FAST INCONSISTENCY!", flush=True)
                    break
        else:
            continue
        break


if __name__ == "__main__":
    main()
