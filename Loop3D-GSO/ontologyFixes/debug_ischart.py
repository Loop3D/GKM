#!/usr/bin/env python3
"""
Debug script to find the exact cause of GSO-Geologic_Time_Ischart inconsistency.
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


def merge_and_load(files, apply_fixes=True):
    """Merge files with rdflib and load into owlready2."""
    g = Graph()
    for f in files:
        filepath = os.path.join(BASE_DIR, f)
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


def test_consistency(world, desc=""):
    """Test ontology consistency."""
    print(f"\nTesting: {desc}")
    try:
        with world:
            sync_reasoner_hermit(infer_property_values=False, debug=0)
        print("Result: CONSISTENT")
        return True
    except owlready2.OwlReadyInconsistentOntologyError as e:
        print(f"Result: INCONSISTENT - {e}")
        return False


def main():
    # Base files always needed
    base_files = [
        "GSO-Common.ttl",
        "GSO-Geology.ttl",
        "Modules/GSO-Perdurant.ttl",
    ]

    time_file = "Modules/GSO-Geologic_Time.ttl"
    ischart_file = "Modules/GSO-Geologic_Time_Ischart.ttl"

    # Test 1: Base + Time (should pass)
    print("=" * 60)
    print("TEST 1: Base + Time only")
    world1, onto1 = merge_and_load(base_files + [time_file])
    result1 = test_consistency(world1, "Base + Time")

    # Test 2: Base + Time + Ischart (should fail)
    print("\n" + "=" * 60)
    print("TEST 2: Base + Time + Ischart")
    world2, onto2 = merge_and_load(base_files + [time_file, ischart_file])
    result2 = test_consistency(world2, "Base + Time + Ischart")

    if result2:
        print("\nNo inconsistency found with fixes applied!")
        return

    # Analyze the classes and restrictions
    print("\n" + "=" * 60)
    print("ANALYSIS: Class hierarchy and restrictions")

    GSOC = world2.get_namespace("https://w3id.org/gso/1.0/common/")
    GSOG = world2.get_namespace("https://w3id.org/gso/1.0/geology/")
    GST = world2.get_namespace("https://w3id.org/gso/1.0/geologictime/")
    GSTIME = world2.get_namespace("https://w3id.org/gso/1.0/ischart/")

    print("\n1. Geologic_Time_Interval restrictions:")
    gti = GSOG.Geologic_Time_Interval
    if gti:
        for r in gti.is_a:
            print(f"   {r}")

    print("\n2. Specific_Geologic_Time_Unit restrictions:")
    stgu = GSOG.Specific_Geologic_Time_Unit
    if stgu:
        for r in stgu.is_a:
            print(f"   {r}")

    print("\n3. gst:Age restrictions:")
    age = GST.Age
    if age:
        for r in age.is_a:
            print(f"   {r}")

    print("\n4. Sample dual-typed individuals (Age + Specific_Geologic_Time_Unit):")
    count = 0
    for ind in world2.individuals():
        types = list(ind.is_a)
        is_age = GST.Age in types
        is_specific = GSOG.Specific_Geologic_Time_Unit in types

        if is_age and is_specific:
            count += 1
            if count <= 3:
                print(f"   {ind.name}:")
                print(f"      Types: {[str(t) for t in types]}")
                # Check hasEssentialPart
                if hasattr(ind, 'hasEssentialPart'):
                    print(f"      hasEssentialPart: {list(ind.hasEssentialPart)}")
                if hasattr(GSOC, 'hasEssentialPart') and hasattr(ind, GSOC.hasEssentialPart.python_name):
                    ep = getattr(ind, GSOC.hasEssentialPart.python_name, [])
                    print(f"      hasEssentialPart (via GSOC): {list(ep)}")

    print(f"\n   Total dual-typed individuals: {count}")

    # Try removing the complementOf restriction to see if that's the issue
    print("\n" + "=" * 60)
    print("TEST 3: Removing complementOf restriction from Specific_Geologic_Time_Unit")

    world3, onto3 = merge_and_load(base_files + [time_file, ischart_file])
    GSOG3 = world3.get_namespace("https://w3id.org/gso/1.0/geology/")
    GSOC3 = world3.get_namespace("https://w3id.org/gso/1.0/common/")

    stgu3 = GSOG3.Specific_Geologic_Time_Unit
    if stgu3:
        # Find and remove the complementOf restriction
        removed = []
        for r in list(stgu3.is_a):
            r_str = str(r)
            if 'complementOf' in r_str and 'hasEssentialPart' in r_str:
                stgu3.is_a.remove(r)
                removed.append(r)
                print(f"   Removed: {r}")

        if not removed:
            print("   No complementOf restriction found to remove")

    result3 = test_consistency(world3, "Without complementOf restriction")

    if result3:
        print("\n>>> The complementOf restriction on Specific_Geologic_Time_Unit is causing the inconsistency!")


if __name__ == "__main__":
    main()
