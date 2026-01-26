#!/usr/bin/env python3
"""
Run the exact same test as check_owl2dl.py incremental, but print more debug info.
"""

import sys
import os
import tempfile
import glob
import time

# Check for 64-bit Java
java_home = os.environ.get('JAVA_HOME_64', r'C:\Program Files\OpenJDK\jdk-25')
if os.path.exists(java_home):
    os.environ['JAVA_HOME'] = java_home
    os.environ['PATH'] = os.path.join(java_home, 'bin') + os.pathsep + os.environ.get('PATH', '')
    print(f"Using 64-bit Java: {os.path.join(java_home, 'bin', 'java.exe')}")

import owlready2
from owlready2 import get_ontology, sync_reasoner_hermit, World, OwlReadyInconsistentOntologyError
from rdflib import Graph, OWL

owlready2.JAVA_MEMORY = 8000

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def get_all_ontology_files(base_path):
    """Get list of all ontology files - EXACT same as check_owl2dl.py"""
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


def merge_ontologies(base_path, file_list, quiet=True):
    """Merge TTL files - EXACT same as check_owl2dl.py"""
    g = Graph()
    for f in file_list:
        try:
            if not quiet:
                print(f"  Loading: {os.path.basename(f)}")
            g.parse(f, format='turtle')
        except Exception as e:
            print(f"  WARNING: Failed to parse {f}: {e}")

    # Remove owl:imports
    for s, p, o in list(g.triples((None, OWL.imports, None))):
        g.remove((s, p, o))

    fd, target_file = tempfile.mkstemp(suffix='.rdf')
    os.close(fd)
    g.serialize(destination=target_file, format='xml')

    return target_file


def check_merged_ontology(rdfxml_path, verbose=False):
    """Check ontology - EXACT same as check_owl2dl.py"""
    result = {
        'status': 'unknown',
        'time': 0,
        'unsatisfiable': [],
    }

    start = time.time()

    try:
        world = World()
        onto = world.get_ontology(f"file://{rdfxml_path}").load()

        all_classes = list(onto.classes())

        with world:
            sync_reasoner_hermit(infer_property_values=False, debug=0)

        # Check for unsatisfiable classes
        unsatisfiable = []
        for cls in all_classes:
            if cls is owlready2.Nothing:
                continue
            if len(list(cls.equivalent_to)) > 0:
                for eq in cls.equivalent_to:
                    if eq is owlready2.Nothing:
                        unsatisfiable.append(str(cls))
                        break

        result['time'] = time.time() - start
        result['unsatisfiable'] = unsatisfiable

        if unsatisfiable:
            result['status'] = 'has_unsatisfiable'
        else:
            result['status'] = 'consistent'

    except OwlReadyInconsistentOntologyError:
        result['status'] = 'inconsistent'
        result['time'] = time.time() - start
    except Exception as e:
        result['status'] = 'error'
        result['time'] = time.time() - start
        if verbose:
            print(f"Error: {e}")

    return result


def main():
    all_files = get_all_ontology_files(BASE_DIR)

    # EXACT same categorization as check_owl2dl.py
    base_files = [f for f in all_files if 'Modules' not in f]
    module_files = [f for f in all_files if 'Modules' in f]

    print(f"Base files ({len(base_files)}): {[os.path.basename(f) for f in base_files]}")
    print(f"Module files ({len(module_files)}): {[os.path.basename(f) for f in module_files]}")

    # Find Time_Ischart index
    ischart_idx = None
    for i, f in enumerate(module_files):
        if 'Time_Ischart' in f:
            ischart_idx = i
            break

    print(f"\nTime_Ischart index: {ischart_idx}")

    # Start with base files only - EXACT same as check_owl2dl.py
    current_files = base_files.copy()

    print("\n" + "=" * 70)
    print("PHASE 1: Testing base files only")
    print("=" * 70)

    temp_file = merge_ontologies(BASE_DIR, current_files)
    try:
        result = check_merged_ontology(temp_file)
        print(f"Base files: {result['status'].upper()} ({result['time']:.1f}s)")
    finally:
        os.remove(temp_file)

    print("\n" + "=" * 70)
    print("PHASE 2: Adding modules one at a time")
    print("=" * 70)

    for i, module in enumerate(module_files):
        module_name = os.path.basename(module)
        test_files = current_files + [module]

        print(f"{i}: Testing + {module_name}... ({len(test_files)} total files)", end=" ", flush=True)

        temp_file = merge_ontologies(BASE_DIR, test_files)
        try:
            result = check_merged_ontology(temp_file)

            if result['status'] == 'inconsistent':
                print(f"*** INCONSISTENT *** ({result['time']:.1f}s)")
                print(f"\n  >>> Failed at module {i}: {module_name}")
                print(f"  >>> Current files before failure ({len(current_files)}):")
                for cf in current_files:
                    print(f"        {os.path.basename(cf)}")
                break
            elif result['status'] == 'has_unsatisfiable':
                print(f"UNSATISFIABLE ({len(result['unsatisfiable'])}) ({result['time']:.1f}s)")
                # DON'T add failed modules
            else:
                print(f"OK ({result['time']:.1f}s)")
                current_files.append(module)
        finally:
            os.remove(temp_file)


if __name__ == "__main__":
    main()
