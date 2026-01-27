#!/usr/bin/env python3
"""Check what becomes unsatisfiable when Scale + Point are added."""

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

    # Get Scale and Point subjects
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

    # Get triples for Scale + Point
    triples = []
    for subj in scale_subjects + point_subjects:
        triples.extend(triples_by_subject[subj])

    print(f"\nTriples for Scale + Point: {len(triples)}", flush=True)

    # Show the triples
    print(f"\nScale triples:", flush=True)
    for subj in scale_subjects[:3]:
        print(f"  {subj}:", flush=True)
        for s, p, o in triples_by_subject[subj]:
            p_short = str(p).split('/')[-1]
            o_short = str(o).split('/')[-1]
            print(f"    {p_short}: {o_short}", flush=True)

    print(f"\nPoint triples:", flush=True)
    for subj in point_subjects[:3]:
        print(f"  {subj}:", flush=True)
        for s, p, o in triples_by_subject[subj]:
            p_short = str(p).split('/')[-1]
            o_short = str(o).split('/')[-1]
            print(f"    {p_short}: {o_short}", flush=True)

    # Test with just one Scale and one Point
    print(f"\n{'='*70}", flush=True)
    print(f"Testing minimal Scale + Point:", flush=True)
    print(f"{'='*70}", flush=True)

    test_g = Graph()
    for triple in base_g:
        test_g.add(triple)

    # Add just first Scale
    for triple in triples_by_subject[scale_subjects[0]]:
        test_g.add(triple)

    print(f"  1 Scale subject...", end=" ", flush=True)
    fd, temp_file = tempfile.mkstemp(suffix='.rdf')
    os.close(fd)
    test_g.serialize(destination=temp_file, format='xml')
    default_world.ontologies.clear()
    onto = get_ontology(f"file://{os.path.abspath(temp_file)}").load()
    start = time.time()
    try:
        sync_reasoner_hermit(onto, infer_property_values=False, debug=0,
                           ignore_unsupported_datatypes=True)
        unsatisfiable = list(default_world.inconsistent_classes())
        unsatisfiable = [c for c in unsatisfiable if str(c) != 'owl.Nothing']
        if unsatisfiable:
            print(f"UNSATISFIABLE: {unsatisfiable}", flush=True)
        else:
            print(f"CONSISTENT ({time.time()-start:.1f}s)", flush=True)
    except OwlReadyInconsistentOntologyError:
        print(f"INCONSISTENT ({time.time()-start:.1f}s)", flush=True)
    os.remove(temp_file)

    # Add just first Point
    test_g2 = Graph()
    for triple in base_g:
        test_g2.add(triple)
    for triple in triples_by_subject[point_subjects[0]]:
        test_g2.add(triple)

    print(f"  1 Point subject...", end=" ", flush=True)
    fd, temp_file = tempfile.mkstemp(suffix='.rdf')
    os.close(fd)
    test_g2.serialize(destination=temp_file, format='xml')
    default_world.ontologies.clear()
    onto = get_ontology(f"file://{os.path.abspath(temp_file)}").load()
    start = time.time()
    try:
        sync_reasoner_hermit(onto, infer_property_values=False, debug=0,
                           ignore_unsupported_datatypes=True)
        unsatisfiable = list(default_world.inconsistent_classes())
        unsatisfiable = [c for c in unsatisfiable if str(c) != 'owl.Nothing']
        if unsatisfiable:
            print(f"UNSATISFIABLE: {unsatisfiable}", flush=True)
        else:
            print(f"CONSISTENT ({time.time()-start:.1f}s)", flush=True)
    except OwlReadyInconsistentOntologyError:
        print(f"INCONSISTENT ({time.time()-start:.1f}s)", flush=True)
    os.remove(temp_file)

    # Add both
    test_g3 = Graph()
    for triple in base_g:
        test_g3.add(triple)
    for triple in triples_by_subject[scale_subjects[0]]:
        test_g3.add(triple)
    for triple in triples_by_subject[point_subjects[0]]:
        test_g3.add(triple)

    print(f"  1 Scale + 1 Point...", end=" ", flush=True)
    fd, temp_file = tempfile.mkstemp(suffix='.rdf')
    os.close(fd)
    test_g3.serialize(destination=temp_file, format='xml')
    default_world.ontologies.clear()
    onto = get_ontology(f"file://{os.path.abspath(temp_file)}").load()
    start = time.time()
    try:
        sync_reasoner_hermit(onto, infer_property_values=False, debug=0,
                           ignore_unsupported_datatypes=True)
        unsatisfiable = list(default_world.inconsistent_classes())
        unsatisfiable = [c for c in unsatisfiable if str(c) != 'owl.Nothing']
        if unsatisfiable:
            print(f"UNSATISFIABLE: {unsatisfiable}", flush=True)
        else:
            print(f"CONSISTENT ({time.time()-start:.1f}s)", flush=True)
    except OwlReadyInconsistentOntologyError:
        print(f"INCONSISTENT ({time.time()-start:.1f}s)", flush=True)
    os.remove(temp_file)


if __name__ == "__main__":
    main()
