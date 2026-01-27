#!/usr/bin/env python3
"""Diagnose unsatisfiable classes by testing exact module combinations."""

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
from rdflib import Graph, OWL

owlready2.reasoning.JAVA_MEMORY = 4000

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def get_all_files(base_path):
    """Get all ontology files."""
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
             'Ischart' not in f and
             'ischart' not in f.lower()]
    return sorted(set(files))


def find_file(all_files, exact_name):
    """Find a file by exact basename (without extension)."""
    for f in all_files:
        base = os.path.basename(f).replace('.ttl', '')
        if base == exact_name:
            return f
    return None


def test_files(file_list, label=""):
    """Test a set of ontology files for consistency."""
    g = Graph()
    for f in file_list:
        g.parse(f, format='turtle')

    for s, p, o in list(g.triples((None, OWL.imports, None))):
        g.remove((s, p, o))

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
            elapsed = time.time() - start
            return "INCONSISTENT", elapsed, []

        unsatisfiable = list(default_world.inconsistent_classes())
        unsatisfiable = [c for c in unsatisfiable if str(c) != 'owl.Nothing']

        elapsed = time.time() - start
        if unsatisfiable:
            return "UNSATISFIABLE", elapsed, unsatisfiable
        else:
            return "CONSISTENT", elapsed, []

    finally:
        os.remove(temp_file)


def main():
    all_files = get_all_files(BASE_DIR)

    # Base modules (exact matches)
    base_names = ['GSO-Common', 'GSO-Geology', 'GSO-Master', 'GSO-Element',
                  'GSO-Feature', 'GSO-Quality', 'GSO-Perdurant', 'GSO-QUDTvoc',
                  'GSO-skos_annotation']

    base_files = []
    for name in base_names:
        f = find_file(all_files, name)
        if f:
            base_files.append(f)

    # Test 1: Base + Quality + Structure (exact file only)
    print("=" * 70, flush=True)
    print("TEST 1: Base + Geologic_Quality + Geologic_Structure (exact)", flush=True)
    print("=" * 70, flush=True)

    gq_file = find_file(all_files, 'GSO-Geologic_Quality')
    gs_file = find_file(all_files, 'GSO-Geologic_Structure')
    gp_file = find_file(all_files, 'GSO-Geologic_Process')

    test1_files = base_files + [gq_file, gs_file]
    print(f"Files ({len(test1_files)}):", flush=True)
    for f in test1_files:
        print(f"  {os.path.basename(f)}", flush=True)

    result, elapsed, unsat = test_files(test1_files)
    print(f"\nResult: {result} ({elapsed:.1f}s)", flush=True)
    if unsat:
        unsat_names = sorted(set(str(c).split('.')[-1] for c in unsat))
        print(f"Unsatisfiable ({len(unsat)}):", flush=True)
        for name in unsat_names:
            print(f"  - {name}", flush=True)

    # Test 2: Add each structure sub-module individually
    sub_modules = [
        'GSO-Geologic_Process',
        'GSO-Geologic_Structure_Fault',
        'GSO-Geologic_Structure_Fold',
        'GSO-Geologic_Structure_Foliation',
        'GSO-Geologic_Structure_Lineation',
        'GSO-Geologic_Structure_Contact',
    ]

    print(f"\n{'=' * 70}", flush=True)
    print("TEST 2: Base+Quality+Structure + each sub-module individually", flush=True)
    print("=" * 70, flush=True)

    for mod_name in sub_modules:
        mod_file = find_file(all_files, mod_name)
        if not mod_file:
            print(f"\n  {mod_name}: NOT FOUND", flush=True)
            continue

        # Need to include process module for fault module
        if 'Fault' in mod_name:
            test_batch = test1_files + [gp_file, mod_file]
        else:
            test_batch = test1_files + [mod_file]

        print(f"\n  + {mod_name}...", end=" ", flush=True)
        result, elapsed, unsat = test_files(test_batch)
        print(f"{result} ({elapsed:.1f}s)", flush=True)
        if unsat:
            unsat_names = sorted(set(str(c).split('.')[-1] for c in unsat))
            print(f"    Unsatisfiable ({len(unsat)}):", flush=True)
            for name in unsat_names[:15]:
                print(f"      - {name}", flush=True)
            if len(unsat_names) > 15:
                print(f"      ... and {len(unsat_names) - 15} more", flush=True)

    # Test 3: If base+quality+structure has unsatisfiable classes,
    # try removing Geologic_Quality to isolate
    if test1_files:
        print(f"\n{'=' * 70}", flush=True)
        print("TEST 3: Base + Structure (no Geologic_Quality)", flush=True)
        print("=" * 70, flush=True)

        test3_files = base_files + [gs_file]
        result, elapsed, unsat = test_files(test3_files)
        print(f"Result: {result} ({elapsed:.1f}s)", flush=True)
        if unsat:
            unsat_names = sorted(set(str(c).split('.')[-1] for c in unsat))
            print(f"Unsatisfiable ({len(unsat)}):", flush=True)
            for name in unsat_names[:15]:
                print(f"  - {name}", flush=True)
            if len(unsat_names) > 15:
                print(f"  ... and {len(unsat_names) - 15} more", flush=True)


if __name__ == "__main__":
    main()
