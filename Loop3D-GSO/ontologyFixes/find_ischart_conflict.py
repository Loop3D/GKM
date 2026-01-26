#!/usr/bin/env python3
"""
Find which module combination causes Time_Ischart to become inconsistent.
"""

import sys
import os
import tempfile

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

# Base files
BASE_FILES = [
    "GSO-Common.ttl",
    "GSO-Geology.ttl",
    "Modules/GSO-Perdurant.ttl",
]

# Modules in incremental order (same as check_owl2dl.py)
MODULES = [
    "Modules/GSO-Element.ttl",
    "Modules/GSO-Feature.ttl",
    "Modules/GSO-Geologic_Event.ttl",
    "Modules/GSO-Geologic_Feature.ttl",
    "Modules/GSO-Geologic_Granular_Material.ttl",
    "Modules/GSO-Geologic_Process.ttl",
    "Modules/GSO-Geologic_Quality.ttl",
    "Modules/GSO-Geologic_Reference_System.ttl",
    "Modules/GSO-Geologic_Relation.ttl",
    "Modules/GSO-Geologic_Rock_Material.ttl",
    "Modules/GSO-Geologic_Rock_Object.ttl",
    "Modules/GSO-Geologic_Role.ttl",
    "Modules/GSO-Geologic_Setting.ttl",
    "Modules/GSO-Geologic_Structure.ttl",
    "Modules/GSO-Geologic_Structure_Contact.ttl",
    "Modules/GSO-Geologic_Structure_Fault.ttl",
    "Modules/GSO-Geologic_Structure_Fold.ttl",
    "Modules/GSO-Geologic_Structure_Foliation.ttl",
    "Modules/GSO-Geologic_Structure_Lineation.ttl",
    "Modules/GSO-Geologic_Time.ttl",
]

ISCHART = "Modules/GSO-Geologic_Time_Ischart.ttl"


def merge_and_load(files, apply_fixes=True, quiet=True):
    """Merge files with rdflib and load into owlready2."""
    g = Graph()
    for f in files:
        filepath = os.path.join(BASE_DIR, f)
        if not quiet:
            print(f"  Loading: {f}")
        g.parse(filepath, format="turtle")

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

    if apply_fixes:
        # Apply the 11 Physical_Quality -> Nonphysical_Quality fixes
        GSOC = world.get_namespace("https://w3id.org/gso/1.0/common/")
        GSOS = world.get_namespace("https://w3id.org/gso/1.0/geologicstructure/")
        GSFD = world.get_namespace("https://w3id.org/gso/1.0/geologicstructurefold/")

        classes_to_fix = [
            (GSOS, "Bedding_Pattern", GSOC.Physical_Quality, GSOC.Nonphysical_Quality),
            (GSOS, "Bedding_Style", GSOC.Physical_Quality, GSOC.Nonphysical_Quality),
            (GSFD, "Fold_Amplitude", GSOC.Physical_Quality, GSOC.Nonphysical_Quality),
            (GSFD, "Fold_InterLimb_Angle", GSOC.Physical_Quality, GSOC.Nonphysical_Quality),
            (GSFD, "Fold_Span", GSOC.Physical_Quality, GSOC.Nonphysical_Quality),
            (GSFD, "Fold_Symmetry", GSOC.Physical_Quality, GSOC.Nonphysical_Quality),
            (GSFD, "Hinge_Line_Curvature", GSOC.Physical_Quality, GSOC.Nonphysical_Quality),
            (GSFD, "Is_Periodic", GSOC.Physical_Quality, GSOC.Nonphysical_Quality),
            (GSFD, "Fold_Limb_Shape", GSOC.Shape, GSOC.Nonphysical_Quality),
            (GSFD, "Hinge_Shape", GSOC.Shape, GSOC.Nonphysical_Quality),
            (GSFD, "Fold_Wavelength", GSOC.Physical_Quality, GSOC.Nonphysical_Quality),
        ]

        for ns, class_name, old_parent, new_parent in classes_to_fix:
            cls = getattr(ns, class_name, None)
            if cls and old_parent in cls.is_a:
                cls.is_a.remove(old_parent)
                cls.is_a.append(new_parent)

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
    print("Testing Time_Ischart with different module combinations...")
    print("=" * 70)

    # Test 1: Base + Time + Ischart (minimal, should pass)
    print("\nTest 1: Base + Time + Ischart only...")
    files1 = BASE_FILES + ["Modules/GSO-Geologic_Time.ttl", ISCHART]
    world1, _ = merge_and_load(files1)
    result1 = test_consistency(world1)
    print(f"  Result: {'PASS' if result1 else 'INCONSISTENT'}")

    # Test 2: All modules + Time + Ischart
    print("\nTest 2: All modules + Time + Ischart...")
    files2 = BASE_FILES + MODULES + [ISCHART]
    world2, _ = merge_and_load(files2)
    result2 = test_consistency(world2)
    print(f"  Result: {'PASS' if result2 else 'INCONSISTENT'}")

    if result2:
        print("\n>>> Full ontology is consistent! Time_Ischart works.")
        return

    # Binary search to find the problematic module
    print("\n" + "=" * 70)
    print("Binary search to find conflicting module...")

    # Start with just Time + Ischart passing, add modules until it fails
    working_files = BASE_FILES + ["Modules/GSO-Geologic_Time.ttl"]

    for i, module in enumerate(MODULES[:-1]):  # Exclude Time itself
        test_files = working_files + [module, ISCHART]
        world, _ = merge_and_load(test_files, quiet=True)
        result = test_consistency(world)

        status = "PASS" if result else "FAIL"
        print(f"  + {os.path.basename(module)}: {status}")

        if not result:
            print(f"\n>>> Found conflict! Adding {module} makes Time_Ischart inconsistent!")

            # Verify the conflict
            print("\nVerifying: Without this module...")
            verify_files = working_files + [ISCHART]
            world_v, _ = merge_and_load(verify_files)
            result_v = test_consistency(world_v)
            print(f"  Time + Ischart (no {os.path.basename(module)}): {'PASS' if result_v else 'FAIL'}")

            break

        working_files.append(module)

    else:
        print("\n>>> All modules added individually pass. Issue might be cumulative.")


if __name__ == "__main__":
    main()
