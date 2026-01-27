#!/usr/bin/env python3
"""Diagnose which module(s) trigger unsatisfiability when added to base+quality+structure."""

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


def find_file(base_path, exact_name):
    """Find a file by exact basename (without extension)."""
    patterns = [
        os.path.join(base_path, "*.ttl"),
        os.path.join(base_path, "Modules", "*.ttl"),
    ]
    for pattern in patterns:
        for f in glob.glob(pattern):
            base = os.path.basename(f).replace('.ttl', '')
            if base == exact_name:
                return f
    return None


def test_files(file_list):
    """Test a set of ontology files for consistency. Returns fresh each time."""
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
    # Core modules that form the consistent baseline
    core_names = [
        'GSO-Common', 'GSO-Geology', 'GSO-Master', 'GSO-Element',
        'GSO-Feature', 'GSO-Quality', 'GSO-Perdurant', 'GSO-QUDTvoc',
        'GSO-skos_annotation', 'GSO-Geologic_Quality', 'GSO-Geologic_Structure'
    ]

    core_files = []
    for name in core_names:
        f = find_file(BASE_DIR, name)
        if f:
            core_files.append(f)
        else:
            print(f"WARNING: {name} not found!", flush=True)

    # Test 0: Verify baseline is consistent
    print("=" * 70, flush=True)
    print("TEST 0: Baseline (core modules)", flush=True)
    print("=" * 70, flush=True)
    print(f"Files ({len(core_files)}):", flush=True)
    for f in core_files:
        print(f"  {os.path.basename(f)}", flush=True)

    result, elapsed, unsat = test_files(core_files)
    print(f"Result: {result} ({elapsed:.1f}s)", flush=True)
    if unsat:
        unsat_names = sorted(set(str(c).split('.')[-1] for c in unsat))
        print(f"  Unsatisfiable: {unsat_names}", flush=True)

    # Modules to test individually
    test_modules = [
        'GSO-Geologic_Process',
        'GSO-Geologic_Structure_Fault',
        'GSO-Geologic_Structure_Fold',
        'GSO-Geologic_Structure_Foliation',
        'GSO-Geologic_Structure_Lineation',
        'GSO-Geologic_Structure_Contact',
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

    # Test each module individually added to core
    print(f"\n{'=' * 70}", flush=True)
    print("TEST 1: Adding each module individually to core", flush=True)
    print("=" * 70, flush=True)

    problem_modules = []

    for mod_name in test_modules:
        mod_file = find_file(BASE_DIR, mod_name)
        if not mod_file:
            print(f"\n  {mod_name}: NOT FOUND", flush=True)
            continue

        # Some modules depend on others
        extra_deps = []
        if 'Fault' in mod_name:
            dep = find_file(BASE_DIR, 'GSO-Geologic_Process')
            if dep:
                extra_deps.append(dep)

        test_batch = core_files + extra_deps + [mod_file]
        print(f"\n  + {mod_name}...", end=" ", flush=True)
        result, elapsed, unsat = test_files(test_batch)
        print(f"{result} ({elapsed:.1f}s)", flush=True)
        if unsat:
            unsat_names = sorted(set(str(c).split('.')[-1] for c in unsat))
            print(f"    Unsatisfiable ({len(unsat)}): {', '.join(unsat_names[:10])}", flush=True)
            if len(unsat_names) > 10:
                print(f"    ... and {len(unsat_names) - 10} more", flush=True)
            problem_modules.append(mod_name)

    if problem_modules:
        print(f"\n{'=' * 70}", flush=True)
        print(f"PROBLEM MODULES: {problem_modules}", flush=True)
        print("=" * 70, flush=True)
    else:
        # If no single module causes the problem, test pairs
        print(f"\n{'=' * 70}", flush=True)
        print("No single module causes issues. Testing pairs...", flush=True)
        print("=" * 70, flush=True)

        for i, mod1 in enumerate(test_modules):
            f1 = find_file(BASE_DIR, mod1)
            if not f1:
                continue
            for mod2 in test_modules[i+1:]:
                f2 = find_file(BASE_DIR, mod2)
                if not f2:
                    continue
                test_batch = core_files + [f1, f2]
                print(f"\n  + {mod1} + {mod2}...", end=" ", flush=True)
                result, elapsed, unsat = test_files(test_batch)
                if unsat or result == "INCONSISTENT":
                    print(f"{result} ({elapsed:.1f}s)", flush=True)
                    if unsat:
                        unsat_names = sorted(set(str(c).split('.')[-1] for c in unsat))
                        print(f"    Unsatisfiable ({len(unsat)}): {', '.join(unsat_names[:5])}", flush=True)
                else:
                    print(f"OK ({elapsed:.1f}s)", flush=True)


if __name__ == "__main__":
    main()
