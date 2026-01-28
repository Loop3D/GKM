#!/usr/bin/env python3
"""Test GSO Example files for consistency with GSO-Master ontology.

Phase 1: Syntax validation (rdflib parse) - fast
Phase 2: Combined HermiT consistency check - all examples merged with base ontology
Phase 3: If Phase 2 fails, test each example individually to isolate the problem
"""

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

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
EXAMPLES_DIR = os.path.join(BASE_DIR, "Examples")


def get_base_files():
    """Get GSO core + module files (excluding Feature, Ischart, examples)."""
    patterns = [
        os.path.join(BASE_DIR, "*.ttl"),
        os.path.join(BASE_DIR, "Modules", "*.ttl"),
    ]
    files = []
    for pattern in patterns:
        files.extend(glob.glob(pattern))

    files = [f for f in files if
             not f.endswith('.bak') and
             '~$' not in f and
             '-SMR-' not in f and
             '.inconsistent' not in f]

    result = []
    for f in files:
        basename = os.path.basename(f).lower()
        if 'ischart' in basename:
            continue
        if basename == 'gso-feature.ttl':
            continue
        result.append(f)

    return sorted(set(result))


def get_example_files():
    """Get all TTL files from Examples directory."""
    pattern = os.path.join(EXAMPLES_DIR, "*.ttl")
    files = sorted(glob.glob(pattern))
    return files


def build_base_graph(base_files):
    """Build the base ontology graph."""
    g = Graph()
    for f in base_files:
        g.parse(f, format='turtle')
    # Remove owl:imports
    for s, p, o in list(g.triples((None, OWL.imports, None))):
        g.remove((s, p, o))
    return g


def run_hermit(graph, label=""):
    """Run HermiT on a graph, return (consistent, unsatisfiable_classes, elapsed)."""
    fd, temp_file = tempfile.mkstemp(suffix='.rdf')
    os.close(fd)
    graph.serialize(destination=temp_file, format='xml')

    try:
        default_world.ontologies.clear()
        onto = get_ontology(f"file://{os.path.abspath(temp_file)}").load()

        classes = list(onto.classes())
        individuals = list(onto.individuals())
        print(f"  [{label}] Loaded {len(classes)} classes, {len(individuals)} individuals", flush=True)

        print(f"  [{label}] Running HermiT...", flush=True)
        start = time.time()
        try:
            sync_reasoner_hermit(onto, infer_property_values=False, debug=0,
                                ignore_unsupported_datatypes=True)
        except OwlReadyInconsistentOntologyError:
            elapsed = time.time() - start
            return False, ["INCONSISTENT"], elapsed

        unsatisfiable = list(default_world.inconsistent_classes())
        unsatisfiable = [c for c in unsatisfiable if str(c) != 'owl.Nothing']
        elapsed = time.time() - start
        return len(unsatisfiable) == 0, [str(c) for c in unsatisfiable], elapsed

    finally:
        os.remove(temp_file)


def main():
    base_files = get_base_files()
    example_files = get_example_files()

    print(f"Base ontology: {len(base_files)} files")
    print(f"Example files: {len(example_files)} files\n")

    # Phase 1: Syntax validation
    print("=" * 60)
    print("PHASE 1: Syntax Validation (rdflib parse)")
    print("=" * 60)

    parse_ok = []
    parse_fail = []

    for f in example_files:
        basename = os.path.basename(f)
        try:
            g = Graph()
            g.parse(f, format='turtle')
            triple_count = len(g)
            print(f"  OK  {basename} ({triple_count} triples)")
            parse_ok.append((f, triple_count))
        except Exception as e:
            print(f"  FAIL {basename}: {e}")
            parse_fail.append((f, str(e)))

    print(f"\nPhase 1 result: {len(parse_ok)} OK, {len(parse_fail)} FAIL")

    if parse_fail:
        print("\nFailed files:")
        for f, err in parse_fail:
            print(f"  {os.path.basename(f)}: {err}")

    # Only test files that parsed successfully
    testable = [f for f, _ in parse_ok]

    if not testable:
        print("\nNo files to test with HermiT.")
        return

    # Phase 2: Combined consistency test
    print(f"\n{'=' * 60}")
    print("PHASE 2: Combined HermiT Consistency Check")
    print(f"{'=' * 60}")
    print(f"Merging base ontology + {len(testable)} example files...", flush=True)

    base_graph = build_base_graph(base_files)
    base_triples = len(base_graph)
    print(f"  Base ontology: {base_triples} triples", flush=True)

    combined = Graph()
    # Copy base graph
    for triple in base_graph:
        combined.add(triple)

    for f in testable:
        combined.parse(f, format='turtle')

    # Remove owl:imports from examples too
    for s, p, o in list(combined.triples((None, OWL.imports, None))):
        combined.remove((s, p, o))

    total_triples = len(combined)
    print(f"  Combined: {total_triples} triples (+{total_triples - base_triples} from examples)", flush=True)

    consistent, unsat, elapsed = run_hermit(combined, "ALL")

    if consistent:
        print(f"\n  RESULT: CONSISTENT ({elapsed:.1f}s)")
        print(f"\n  All {len(testable)} example files are consistent with GSO-Master!")
        if parse_fail:
            print(f"\n  NOTE: {len(parse_fail)} files had parse errors (see Phase 1)")
        return

    print(f"\n  RESULT: {'INCONSISTENT' if 'INCONSISTENT' in unsat else f'UNSATISFIABLE ({len(unsat)} classes)'} ({elapsed:.1f}s)")
    if unsat and 'INCONSISTENT' not in unsat:
        for name in sorted(set(unsat)):
            print(f"    - {name}")

    # Phase 3: Individual testing
    print(f"\n{'=' * 60}")
    print("PHASE 3: Individual Example Testing")
    print(f"{'=' * 60}")
    print("Testing each example file individually to isolate the problem...\n", flush=True)

    results = {}
    for f in testable:
        basename = os.path.basename(f)
        print(f"\nTesting {basename}...", flush=True)

        individual = Graph()
        for triple in base_graph:
            individual.add(triple)
        individual.parse(f, format='turtle')
        for s, p, o in list(individual.triples((None, OWL.imports, None))):
            individual.remove((s, p, o))

        ok, ind_unsat, ind_elapsed = run_hermit(individual, basename)
        results[basename] = (ok, ind_unsat, ind_elapsed)

        if ok:
            print(f"  {basename}: CONSISTENT ({ind_elapsed:.1f}s)")
        else:
            status = 'INCONSISTENT' if 'INCONSISTENT' in ind_unsat else f'UNSATISFIABLE ({len(ind_unsat)})'
            print(f"  {basename}: {status} ({ind_elapsed:.1f}s)")

    # Summary
    print(f"\n{'=' * 60}")
    print("SUMMARY")
    print(f"{'=' * 60}")
    ok_count = sum(1 for v in results.values() if v[0])
    fail_count = sum(1 for v in results.values() if not v[0])
    print(f"Consistent: {ok_count}")
    print(f"Inconsistent/Unsatisfiable: {fail_count}")
    if fail_count:
        print("\nProblem files:")
        for basename, (ok, ind_unsat, _) in sorted(results.items()):
            if not ok:
                status = 'INCONSISTENT' if 'INCONSISTENT' in ind_unsat else f'UNSATISFIABLE: {", ".join(sorted(set(ind_unsat)))}'
                print(f"  {basename}: {status}")


if __name__ == "__main__":
    main()
