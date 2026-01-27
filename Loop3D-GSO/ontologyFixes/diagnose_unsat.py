#!/usr/bin/env python3
"""Diagnose unsatisfiable classes by testing module combinations."""

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


def get_files(base_path, include_patterns=None, exclude_patterns=None):
    """Get ontology files matching criteria."""
    all_patterns = [
        os.path.join(base_path, "*.ttl"),
        os.path.join(base_path, "Modules", "*.ttl"),
    ]

    files = []
    for pattern in all_patterns:
        files.extend(glob.glob(pattern))

    files = [f for f in files if
             not f.endswith('.bak') and
             '~$' not in f and
             '-SMR-' not in f and
             '.inconsistent' not in f and
             'Ischart' not in f and
             'ischart' not in f.lower()]

    if include_patterns:
        files = [f for f in files if any(p in os.path.basename(f) for p in include_patterns)]
    if exclude_patterns:
        files = [f for f in files if not any(p in os.path.basename(f) for p in exclude_patterns)]

    return sorted(set(files))


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

        classes = list(onto.classes())
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
    # Define module groups for incremental testing
    # Base = Common + Geology + Master + Element + Feature + Quality + Perdurant + QUDT + skos
    base_names = ['GSO-Common', 'GSO-Geology', 'GSO-Master', 'GSO-Element',
                  'GSO-Feature', 'GSO-Quality', 'GSO-Perdurant', 'GSO-QUDTvoc',
                  'GSO-skos_annotation']

    # Structure-related modules to test incrementally
    structure_modules = [
        'GSO-Geologic_Quality',
        'GSO-Geologic_Structure',
        'GSO-Geologic_Process',
        'GSO-Geologic_Structure_Fault',
        'GSO-Geologic_Structure_Fold',
        'GSO-Geologic_Structure_Foliation',
        'GSO-Geologic_Structure_Lineation',
        'GSO-Geologic_Structure_Contact',
    ]

    # Other modules
    other_modules = [
        'GSO-Geologic_Event',
        'GSO-Geologic_Feature',
        'GSO-Geologic_Granular_Material',
        'GSO-Geologic_Mineral',
        'GSO-Geologic_Reference_System',
        'GSO-Geologic_Relation',
        'GSO-Geologic_Rock_Material',
        'GSO-Geologic_Rock_Object',
        'GSO-Geologic_Role',
        'GSO-Geologic_Setting',
        'GSO-Geologic_Time',
        'GSO-Geologic_Unit',
        'GSO-Hydrology',
    ]

    all_files = get_files(BASE_DIR)
    print(f"Total available files: {len(all_files)}", flush=True)
    for f in all_files:
        print(f"  {os.path.basename(f)}", flush=True)

    # Test 1: Base only
    print(f"\n{'='*70}", flush=True)
    print(f"TEST 1: Base modules only", flush=True)
    print(f"{'='*70}", flush=True)
    base_files = [f for f in all_files if any(
        os.path.basename(f).startswith(n) for n in base_names)]
    print(f"Files: {[os.path.basename(f) for f in base_files]}", flush=True)
    result, elapsed, unsat = test_files(base_files, "base")
    print(f"Result: {result} ({elapsed:.1f}s)", flush=True)
    if unsat:
        for c in unsat[:10]:
            print(f"  - {c}", flush=True)
        if len(unsat) > 10:
            print(f"  ... and {len(unsat) - 10} more", flush=True)

    # Test 2: Base + structure modules incrementally
    print(f"\n{'='*70}", flush=True)
    print(f"TEST 2: Adding structure modules one by one", flush=True)
    print(f"{'='*70}", flush=True)
    current_files = list(base_files)
    for mod_name in structure_modules:
        mod_files = [f for f in all_files if os.path.basename(f).startswith(mod_name)]
        if not mod_files:
            print(f"\n  {mod_name}: NOT FOUND", flush=True)
            continue
        current_files.extend(mod_files)
        print(f"\n  + {mod_name}...", end=" ", flush=True)
        result, elapsed, unsat = test_files(current_files)
        print(f"{result} ({elapsed:.1f}s)", flush=True)
        if unsat:
            # Show first few unsatisfiable classes
            unsat_names = [str(c).split('.')[-1] for c in unsat]
            print(f"    Unsatisfiable ({len(unsat)}): {', '.join(unsat_names[:10])}", flush=True)
            if len(unsat) > 10:
                print(f"    ... and {len(unsat) - 10} more", flush=True)

    # Test 3: If structure modules alone are fine, add other modules one by one
    struct_files = list(current_files)
    if result == "CONSISTENT":
        print(f"\n{'='*70}", flush=True)
        print(f"TEST 3: Structure OK, adding other modules one by one", flush=True)
        print(f"{'='*70}", flush=True)
        for mod_name in other_modules:
            mod_files = [f for f in all_files if os.path.basename(f).startswith(mod_name)]
            if not mod_files:
                continue
            test_batch = struct_files + mod_files
            print(f"\n  + {mod_name}...", end=" ", flush=True)
            result, elapsed, unsat = test_files(test_batch)
            print(f"{result} ({elapsed:.1f}s)", flush=True)
            if unsat:
                unsat_names = [str(c).split('.')[-1] for c in unsat]
                print(f"    Unsatisfiable ({len(unsat)}): {', '.join(unsat_names[:10])}", flush=True)


if __name__ == "__main__":
    main()
