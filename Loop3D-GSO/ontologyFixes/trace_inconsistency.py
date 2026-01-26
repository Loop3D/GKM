#!/usr/bin/env python3
"""
Trace exactly which combination of modules causes the inconsistency.
"""

import sys
import os
import tempfile
import glob

# Check for 64-bit Java
java_home = os.environ.get('JAVA_HOME_64', r'C:\Program Files\OpenJDK\jdk-25')
if os.path.exists(java_home):
    os.environ['JAVA_HOME'] = java_home
    os.environ['PATH'] = os.path.join(java_home, 'bin') + os.pathsep + os.environ.get('PATH', '')
    print(f"Using 64-bit Java: {os.path.join(java_home, 'bin', 'java.exe')}")

import owlready2
from owlready2 import get_ontology, sync_reasoner_hermit, World
from rdflib import Graph, OWL, URIRef

# Set heap size for HermiT
owlready2.JAVA_MEMORY = 8000

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def get_all_ontology_files(base_path):
    """Get list of all ontology files, filtered and sorted"""
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


def merge_and_load(files, quiet=True):
    """Merge files with rdflib and load into owlready2."""
    g = Graph()
    for f in files:
        if not quiet:
            print(f"  Loading: {os.path.basename(f)}")
        g.parse(f, format="turtle")

    # Remove owl:imports
    imports_to_remove = list(g.triples((None, OWL.imports, None)))
    for triple in imports_to_remove:
        g.remove(triple)

    # Save merged RDF/XML to temp file
    temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.rdf', delete=False)
    g.serialize(temp_file.name, format="xml")
    temp_file.close()

    # Load into owlready2
    world = World()
    onto = world.get_ontology(f"file://{temp_file.name}").load()

    # Cleanup temp file
    try:
        os.unlink(temp_file.name)
    except:
        pass

    return world, onto


def test_consistency(world):
    """Test ontology consistency."""
    try:
        with world:
            sync_reasoner_hermit(infer_property_values=False, debug=0)
        return True
    except owlready2.OwlReadyInconsistentOntologyError:
        return False


def main():
    all_files = get_all_ontology_files(BASE_DIR)
    base_files = [f for f in all_files if 'Modules' not in f]
    module_files = sorted([f for f in all_files if 'Modules' in f])

    print("Module files:")
    for i, f in enumerate(module_files):
        print(f"  {i}: {os.path.basename(f)}")

    # Test 1: Base + Time + Ischart (minimal)
    print("\n" + "=" * 70)
    print("Test 1: Base + Time + Ischart only")
    time_idx = 19
    ischart_idx = 20
    test_files = base_files + [module_files[time_idx], module_files[ischart_idx]]
    world, _ = merge_and_load(test_files)
    result = test_consistency(world)
    print(f"  Result: {'PASS' if result else 'INCONSISTENT'}")

    # Test 2: Base + modules 0-20 (through Time_Ischart)
    print("\n" + "=" * 70)
    print("Test 2: Base + modules 0-20 (through Time_Ischart)")
    test_files = base_files + module_files[:21]
    world, _ = merge_and_load(test_files)
    result = test_consistency(world)
    print(f"  Result: {'PASS' if result else 'INCONSISTENT'}")

    # Test 3: Add remaining modules one at a time
    print("\n" + "=" * 70)
    print("Test 3: Adding modules 21-26 one at a time")

    current_files = base_files + module_files[:21]

    for i in range(21, len(module_files)):
        test_files = current_files + [module_files[i]]
        print(f"  + {os.path.basename(module_files[i])}...", end=" ", flush=True)
        world, _ = merge_and_load(test_files)
        result = test_consistency(world)

        if result:
            print("PASS")
            current_files.append(module_files[i])
        else:
            print("INCONSISTENT!")
            print(f"\n>>> Inconsistency caused by: {os.path.basename(module_files[i])}")
            break

    # Test 4: Full ontology excluding GSO-Geologic_Mineral
    print("\n" + "=" * 70)
    print("Test 4: All modules")
    test_files = base_files + module_files
    world, _ = merge_and_load(test_files)
    result = test_consistency(world)
    print(f"  Result: {'PASS' if result else 'INCONSISTENT'}")


if __name__ == "__main__":
    main()
