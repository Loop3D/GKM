#!/usr/bin/env python3
"""
Check what triples from Ischart module remain after removing individuals.
"""

import os
import glob
from rdflib import Graph, OWL, RDF, RDFS, URIRef, Namespace

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

    # Group triples by subject type
    subjects = {}
    for s, p, o in g:
        s_str = str(s)
        if s_str not in subjects:
            subjects[s_str] = []
        subjects[s_str].append((p, o))

    # Count by prefix
    prefix_counts = {}
    for s in subjects:
        # Extract prefix
        if '#' in s:
            prefix = s.rsplit('#', 1)[0] + '#'
        elif '/' in s:
            prefix = s.rsplit('/', 1)[0] + '/'
        else:
            prefix = s
        prefix_counts[prefix] = prefix_counts.get(prefix, 0) + 1

    print("\nSubject prefixes:")
    for prefix, count in sorted(prefix_counts.items(), key=lambda x: -x[1]):
        print(f"  {prefix}: {count}")

    # Check types
    GSOG = Namespace("https://w3id.org/gso/1.0/geology/")
    GST = Namespace("https://w3id.org/gso/1.0/geologictime/")
    GSOC = Namespace("https://w3id.org/gso/1.0/common/")
    GSTIME = Namespace("https://w3id.org/gso/1.0/ischart/")

    print("\nTypes in Ischart:")
    types_count = {}
    for s, p, o in g.triples((None, RDF.type, None)):
        o_str = str(o)
        types_count[o_str] = types_count.get(o_str, 0) + 1

    for t, count in sorted(types_count.items(), key=lambda x: -x[1])[:20]:
        t_short = t.split('/')[-1]
        print(f"  {t_short}: {count}")

    # Check which subjects are typed as BOTH Age and Specific_Geologic_Time_Unit
    print("\n" + "=" * 70)
    print("Subjects typed as BOTH gst:Age AND gsog:Specific_Geologic_Time_Unit:")
    print("=" * 70)

    age_individuals = set()
    specific_individuals = set()

    for s, p, o in g.triples((None, RDF.type, GST["Age"])):
        age_individuals.add(s)
    for s, p, o in g.triples((None, RDF.type, GSOG["Specific_Geologic_Time_Unit"])):
        specific_individuals.add(s)

    both = age_individuals & specific_individuals
    print(f"Found {len(both)} subjects typed as both Age and Specific_Geologic_Time_Unit")
    for s in list(both)[:5]:
        print(f"  {s}")

    # Check what relationships they have
    print("\n" + "=" * 70)
    print("Sample relationships for first such individual:")
    print("=" * 70)

    if both:
        sample = list(both)[0]
        for p, o in subjects[str(sample)]:
            p_short = str(p).split('/')[-1]
            o_short = str(o).split('/')[-1] if '#' not in str(o) else str(o).split('#')[-1]
            print(f"  {p_short}: {o_short}")


if __name__ == "__main__":
    main()
