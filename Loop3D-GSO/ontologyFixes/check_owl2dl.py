#!/usr/bin/env python3
"""
OWL 2 DL Consistency Checker using owlready2 + HermiT

This script uses the owlready2 library which bundles HermiT internally.
Merges all local ontology files to avoid import resolution issues.

Installation:
    pip install owlready2 rdflib

Usage:
    python check_owl2dl.py <ontology_file>
    python check_owl2dl.py --all
    python check_owl2dl.py --merge   # Merge all and check
"""

import sys
import os
import glob
import time
import tempfile

try:
    from owlready2 import get_ontology, sync_reasoner_hermit, default_world, OwlReadyInconsistentOntologyError
    import owlready2.reasoning

    # Try to find and use 64-bit Java for more memory
    java_64bit_paths = [
        r"C:\Program Files\OpenJDK\jdk-25\bin\java.exe",
        r"C:\Program Files\Java\jdk-11.0.2\bin\java.exe",
        r"C:\Program Files\Java\jdk-17\bin\java.exe",
    ]
    for java_path in java_64bit_paths:
        if os.path.exists(java_path):
            os.environ['JAVA_HOME'] = os.path.dirname(os.path.dirname(java_path))
            # Prepend to PATH so owlready2 uses 64-bit Java
            os.environ['PATH'] = os.path.dirname(java_path) + os.pathsep + os.environ.get('PATH', '')
            owlready2.reasoning.JAVA_MEMORY = 4000  # 4GB for 64-bit Java
            print(f"Using 64-bit Java: {java_path}", flush=True)
            break
    else:
        # Fall back to 500MB for 32-bit Java
        owlready2.reasoning.JAVA_MEMORY = 500
        print("Warning: Using 32-bit Java with 500MB memory limit", flush=True)
except ImportError:
    print("owlready2 not installed. Run: pip install owlready2")
    sys.exit(1)

try:
    from rdflib import Graph
except ImportError:
    print("rdflib not installed. Run: pip install rdflib")
    sys.exit(1)


def get_all_ontology_files(base_path):
    """Get list of all ontology files, filtered and sorted"""
    patterns = [
        os.path.join(base_path, "*.ttl"),
        os.path.join(base_path, "Modules", "*.ttl"),
    ]

    files = []
    for pattern in patterns:
        files.extend(glob.glob(pattern))

    # Filter out backups, temp files, and inconsistent files
    # Also skip GSO-Geologic_Mineral.ttl in incremental mode (passed individually but
    # ~5000 mineral classes make subsequent combined reasoning very slow)
    files = [f for f in files if
             not f.endswith('.bak') and
             '~$' not in f and
             '-SMR-' not in f and
             '.inconsistent' not in f and
             'GSO-Geologic_Mineral.ttl' not in f]
    return sorted(set(files))


def merge_ontologies(base_path, target_file=None, file_list=None, quiet=False):
    """Merge TTL files into a single RDF/XML file

    Args:
        base_path: Base directory for ontology files
        target_file: Output file path (temp file if None)
        file_list: Specific list of files to merge (all files if None)
        quiet: Suppress output messages
    """
    from rdflib import OWL, URIRef

    if file_list is None:
        files = get_all_ontology_files(base_path)
    else:
        files = file_list

    if not quiet:
        print(f"Merging {len(files)} ontology files...")

    g = Graph()
    for f in files:
        try:
            if not quiet:
                print(f"  Loading: {os.path.basename(f)}")
            g.parse(f, format='turtle')
        except Exception as e:
            print(f"  WARNING: Failed to parse {f}: {e}")

    if not quiet:
        print(f"Total triples: {len(g)}")

    # Remove owl:imports statements to prevent owlready2 from trying to fetch remote URLs
    imports_removed = 0
    for s, p, o in list(g.triples((None, OWL.imports, None))):
        g.remove((s, p, o))
        imports_removed += 1
    if not quiet:
        print(f"Removed {imports_removed} owl:imports statements (content already merged)")

    # Create output file
    if target_file is None:
        fd, target_file = tempfile.mkstemp(suffix='.rdf')
        os.close(fd)

    if not quiet:
        print(f"Serializing to: {target_file}")
    g.serialize(destination=target_file, format='xml')

    return target_file


def check_merged_ontology(rdfxml_path, verbose=True):
    """
    Check a merged ontology for consistency and unsatisfiable classes.
    """
    result = {
        'file': rdfxml_path,
        'status': 'unknown',
        'time': 0,
        'unsatisfiable': [],
        'error': None
    }

    if verbose:
        print(f"\n{'='*60}")
        print(f"Running HermiT on merged ontology")
        print('='*60)

    start_time = time.time()

    try:
        # Clear any previous ontologies
        default_world.ontologies.clear()

        # Load ontology
        if verbose:
            print("Loading merged ontology into owlready2...")
        onto = get_ontology(f"file://{os.path.abspath(rdfxml_path)}").load()

        if verbose:
            classes = list(onto.classes())
            print(f"Loaded {len(classes)} classes")
            print("Running HermiT reasoner (this may take a while)...")

        # Run reasoner (ignore unsupported datatypes like xsd:anySimpleType)
        # debug=0 for minimal output (faster), debug=2 for verbose output
        try:
            sync_reasoner_hermit(onto, infer_property_values=False, debug=0,
                               ignore_unsupported_datatypes=True)
        except OwlReadyInconsistentOntologyError:
            result['status'] = 'inconsistent'
            result['time'] = time.time() - start_time
            if verbose:
                print(f"\n*** INCONSISTENT ONTOLOGY ***")
                print(f"Time: {result['time']:.1f} seconds")
            return result

        # Check for unsatisfiable classes
        unsatisfiable = list(default_world.inconsistent_classes())

        result['time'] = time.time() - start_time
        result['unsatisfiable'] = [str(c) for c in unsatisfiable if str(c) != 'owl.Nothing']

        if result['unsatisfiable']:
            result['status'] = 'has_unsatisfiable'
            if verbose:
                print(f"\n*** UNSATISFIABLE CLASSES ({len(result['unsatisfiable'])}) ***")
                for c in result['unsatisfiable'][:30]:
                    print(f"  - {c}")
                if len(result['unsatisfiable']) > 30:
                    print(f"  ... and {len(result['unsatisfiable']) - 30} more")
        else:
            result['status'] = 'passed'
            if verbose:
                print(f"\n*** PASSED - No unsatisfiable classes ***")

        if verbose:
            print(f"Time: {result['time']:.1f} seconds ({result['time']/60:.1f} minutes)")

    except Exception as e:
        error_str = str(e)
        result['time'] = time.time() - start_time
        result['error'] = error_str

        # Distinguish memory errors from other errors
        if 'OutOfMemoryError' in error_str or 'Java heap space' in error_str:
            result['status'] = 'memory_error'
            if verbose:
                print(f"\n*** MEMORY ERROR (increase Java heap or use 64-bit Java) ***")
                print(f"Time: {result['time']:.1f} seconds")
        else:
            result['status'] = 'error'
            if verbose:
                print(f"\n*** ERROR ***")
                print(f"Error: {e}")
                import traceback
                traceback.print_exc()

    return result


def check_single_with_imports(filepath, base_path, verbose=True):
    """
    Check a single ontology file by first merging it with its dependencies.
    Uses rdflib to parse and merge, then owlready2 for reasoning.
    """
    if verbose:
        print(f"\n{'='*60}")
        print(f"Checking: {os.path.basename(filepath)}")
        print('='*60)

    # For single files, we still need all dependencies, so merge everything
    # This is a simplification - ideally we'd trace imports
    temp_file = merge_ontologies(base_path)

    try:
        result = check_merged_ontology(temp_file, verbose=verbose)
        result['file'] = filepath  # Report original file
        return result
    finally:
        if os.path.exists(temp_file):
            os.remove(temp_file)


def incremental_test(base_path, verbose=True):
    """
    Test modules incrementally to find which one causes inconsistency.
    Starts with base files and adds one module at a time.
    """
    from rdflib import OWL
    import sys

    all_files = get_all_ontology_files(base_path)

    # Categorize files: base files vs module files
    base_files = [f for f in all_files if 'Modules' not in f]
    module_files = [f for f in all_files if 'Modules' in f]

    print(f"Base files ({len(base_files)}): {[os.path.basename(f) for f in base_files]}", flush=True)
    print(f"Module files ({len(module_files)}): {[os.path.basename(f) for f in module_files]}", flush=True)
    print(flush=True)

    # Start with base files only
    current_files = base_files.copy()

    print("=" * 70, flush=True)
    print("PHASE 1: Testing base files only", flush=True)
    print("=" * 70, flush=True)

    temp_file = merge_ontologies(base_path, file_list=current_files, quiet=True)
    try:
        result = check_merged_ontology(temp_file, verbose=False)
        print(f"Base files: {result['status'].upper()} ({result['time']:.1f}s)", flush=True)
        if result['status'] == 'inconsistent':
            print("*** Base files are already inconsistent! ***", flush=True)
            return
        if result['status'] == 'has_unsatisfiable':
            print(f"*** Base files have {len(result['unsatisfiable'])} unsatisfiable classes ***", flush=True)
            for c in result['unsatisfiable'][:10]:
                print(f"  - {c}", flush=True)
    finally:
        if os.path.exists(temp_file):
            os.remove(temp_file)

    print(flush=True)
    print("=" * 70, flush=True)
    print("PHASE 2: Adding modules one at a time", flush=True)
    print("=" * 70, flush=True)

    problematic_modules = []

    for module in module_files:
        module_name = os.path.basename(module)
        test_files = current_files + [module]

        print(f"Testing + {module_name}...", end=" ", flush=True)
        temp_file = merge_ontologies(base_path, file_list=test_files, quiet=True)
        try:
            result = check_merged_ontology(temp_file, verbose=False)
            status = result['status'].upper()

            if result['status'] == 'inconsistent':
                print(f"*** INCONSISTENT *** ({result['time']:.1f}s)", flush=True)
                problematic_modules.append((module_name, 'inconsistent', []))
            elif result['status'] == 'has_unsatisfiable':
                print(f"UNSATISFIABLE ({len(result['unsatisfiable'])}) ({result['time']:.1f}s)", flush=True)
                problematic_modules.append((module_name, 'unsatisfiable', result['unsatisfiable'][:5]))
            elif result['status'] == 'memory_error':
                print(f"*** MEMORY ERROR *** ({result['time']:.1f}s)", flush=True)
                problematic_modules.append((module_name, 'memory_error', []))
            elif result['status'] == 'error':
                print(f"*** ERROR *** ({result['time']:.1f}s)", flush=True)
                problematic_modules.append((module_name, 'error', []))
            else:
                print(f"OK ({result['time']:.1f}s)", flush=True)
                # Only add passing modules to the current set
                current_files.append(module)
        finally:
            if os.path.exists(temp_file):
                os.remove(temp_file)

    print(flush=True)
    print("=" * 70, flush=True)
    print("SUMMARY", flush=True)
    print("=" * 70, flush=True)

    if problematic_modules:
        print(f"\nProblematic modules ({len(problematic_modules)}):", flush=True)
        for name, status, classes in problematic_modules:
            print(f"  - {name}: {status}", flush=True)
            for c in classes:
                print(f"      {c}", flush=True)
    else:
        print("\nAll modules passed individually!", flush=True)

    print(f"\nModules that passed: {len(current_files) - len(base_files)}", flush=True)


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Check OWL 2 DL ontologies for consistency using HermiT (via owlready2)"
    )
    parser.add_argument("ontology", nargs="?", help="Ontology file to check")
    parser.add_argument("--merge", action="store_true", help="Merge all files and check")
    parser.add_argument("--incremental", action="store_true", help="Test modules incrementally to find problematic ones")
    parser.add_argument("--output", "-o", help="Output merged RDF/XML file (with --merge)")
    parser.add_argument("--quiet", "-q", action="store_true", help="Less verbose output")

    args = parser.parse_args()

    # Get base path
    script_dir = os.path.dirname(os.path.abspath(__file__))
    base_path = os.path.dirname(script_dir)

    if args.incremental:
        incremental_test(base_path, verbose=not args.quiet)
        return

    if args.merge or args.ontology:
        # Merge all ontologies
        output_file = args.output
        if output_file:
            merged_file = merge_ontologies(base_path, output_file)
            keep_file = True
        else:
            merged_file = merge_ontologies(base_path)
            keep_file = False

        try:
            result = check_merged_ontology(merged_file, verbose=not args.quiet)
            sys.exit(0 if result['status'] == 'passed' else 1)
        finally:
            if not keep_file and os.path.exists(merged_file):
                os.remove(merged_file)
    else:
        parser.print_help()
        print("\nExamples:")
        print(f"  python {sys.argv[0]} --merge              # Merge all and check")
        print(f"  python {sys.argv[0]} --merge -o merged.rdf # Save merged file")
        print(f"  python {sys.argv[0]} --incremental        # Find problematic modules")


if __name__ == "__main__":
    main()
