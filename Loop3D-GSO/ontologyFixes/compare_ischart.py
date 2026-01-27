#!/usr/bin/env python3
"""Compare what's in Ischart file vs just gstime individuals."""

import os
import glob
from rdflib import Graph, OWL, RDF, URIRef, Namespace

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
    module_files = [f for f in all_files if 'Modules' in f]

    # Find Ischart
    ischart_file = None
    for f in module_files:
        if 'Time_Ischart' in f:
            ischart_file = f
            break

    print(f"Loading Ischart: {ischart_file}")

    g = Graph()
    g.parse(ischart_file, format='turtle')

    print(f"Total triples: {len(g)}")

    # Categorize triples
    gstime_triples = []
    ontology_triples = []
    other_triples = []
    blank_node_triples = []

    for s, p, o in g:
        s_str = str(s)
        if not isinstance(s, URIRef):
            blank_node_triples.append((s, p, o))
        elif s_str.startswith(str(GSTIME)):
            if s_str == str(GSTIME) + "ontology":
                ontology_triples.append((s, p, o))
            else:
                gstime_triples.append((s, p, o))
        else:
            other_triples.append((s, p, o))

    print(f"\nTriple categories:")
    print(f"  gstime: individuals: {len(gstime_triples)}")
    print(f"  gstime: ontology: {len(ontology_triples)}")
    print(f"  Blank node triples: {len(blank_node_triples)}")
    print(f"  Other: {len(other_triples)}")

    # Look at "other" triples
    if other_triples:
        print(f"\nOther triples (not gstime:):")
        seen_subjects = set()
        for s, p, o in other_triples[:50]:
            if s not in seen_subjects:
                print(f"  Subject: {s}")
                seen_subjects.add(s)

    # Check what blank nodes are attached to
    print(f"\n\nBlank node analysis:")
    # Group blank nodes by their rdf:type
    bn_types = {}
    for s, p, o in blank_node_triples:
        if p == RDF.type:
            type_str = str(o).split('/')[-1]
            if type_str not in bn_types:
                bn_types[type_str] = []
            bn_types[type_str].append(s)

    for t, nodes in sorted(bn_types.items(), key=lambda x: -len(x[1])):
        print(f"  {t}: {len(nodes)} blank nodes")

    # Check what predicates are used with blank nodes
    print(f"\n\nPredicates used with blank nodes as subject:")
    bn_preds = {}
    for s, p, o in blank_node_triples:
        p_str = str(p).split('/')[-1]
        bn_preds[p_str] = bn_preds.get(p_str, 0) + 1

    for p, count in sorted(bn_preds.items(), key=lambda x: -x[1])[:20]:
        print(f"  {p}: {count}")

    # Check what properties gstime individuals have that involve blank nodes
    print(f"\n\nProperties where gstime individual -> blank node:")
    gstime_to_bn = {}
    for s, p, o in gstime_triples:
        if not isinstance(o, URIRef) and not isinstance(o, str):
            p_str = str(p).split('/')[-1]
            gstime_to_bn[p_str] = gstime_to_bn.get(p_str, 0) + 1

    for p, count in sorted(gstime_to_bn.items(), key=lambda x: -x[1]):
        print(f"  {p}: {count}")

    # Check types of gstime individuals
    print(f"\n\nTypes of gstime: individuals:")
    gstime_types = {}
    for s, p, o in gstime_triples:
        if p == RDF.type:
            type_str = str(o).split('/')[-1]
            gstime_types[type_str] = gstime_types.get(type_str, 0) + 1

    for t, count in sorted(gstime_types.items(), key=lambda x: -x[1]):
        print(f"  {t}: {count}")


if __name__ == "__main__":
    main()
