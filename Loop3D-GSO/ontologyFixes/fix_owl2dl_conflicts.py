#!/usr/bin/env python3
"""
Fix OWL 2 DL conflicts in GSO ontology by removing TransitiveProperty
declarations from properties that have cardinality restrictions.

Outputs:
1. Modified GSO-Common.ttl (in place)
2. removed_axioms.ttl - All removed triples for documentation
"""

from rdflib import Graph, Namespace, RDF, RDFS, OWL, URIRef, BNode, Literal
from collections import defaultdict
import os
import re

# Namespaces
GSOC = Namespace("https://w3id.org/gso/1.0/common/")

def load_gso_common():
    """Load just GSO-Common.ttl."""
    g = Graph()
    base_path = os.path.dirname(os.path.abspath(__file__))
    path = os.path.join(base_path, "GSO-Common.ttl")
    g.parse(path, format='turtle')
    return g, path


def find_transitive_properties(g):
    """Find all properties declared as TransitiveProperty."""
    transitive = set()
    for prop in g.subjects(RDF.type, OWL.TransitiveProperty):
        if isinstance(prop, URIRef):
            transitive.add(prop)
    return transitive


def find_property_disjoint_axioms(g):
    """Find all propertyDisjointWith axioms."""
    disjoints = []
    for p1, _, p2 in g.triples((None, OWL.propertyDisjointWith, None)):
        if isinstance(p1, URIRef):
            disjoints.append((p1, p2))
    return disjoints


def get_label(g, uri):
    """Get rdfs:label for a URI."""
    if not isinstance(uri, URIRef):
        return str(uri)
    for label in g.objects(uri, RDFS.label):
        return str(label)
    s = str(uri)
    return s.split('/')[-1].split('#')[-1]


def main():
    print("=" * 70)
    print("Fixing OWL 2 DL Conflicts in GSO-Common.ttl")
    print("=" * 70)

    # Properties that need TransitiveProperty removed (from analysis)
    # These are properties with cardinality restrictions or whose subproperties have them
    properties_to_make_simple = [
        # Core transitive properties causing most conflicts
        GSOC.constantlyGenDependsOn,
        GSOC.constantlySpecDependsOn,
        GSOC.timeIncludedBy,
        GSOC.timeIncludes,
        GSOC.hasPart,
        GSOC.isPartOf,
        GSOC.hasPersistentPart,
        GSOC.isPersistentPartOf,
        GSOC.hasConstituent,
        GSOC.isConstituentOf,
        GSOC.hasEssentialPart,  # This one we already removed the disjoint from
        # Properties in the dependency chain
        GSOC.externallyGenDependsOn,
        GSOC.externallySpecDependsOn,
        GSOC['spatio-temporallyDependsOn'],
        GSOC.specificallyDependsOn,
        GSOC.genericallyDependsOn,
        # Time properties
        GSOC.timeOlderThan,
        GSOC.timeYoungerThan,
        GSOC.timeContains,
        # Space properties
        GSOC.occupiesSpaceDirectly,
        GSOC.occupiesTimeDirectly,
        # Hosting properties (have cardinality restrictions via subproperties)
        GSOC.hostedBy,
        GSOC.hosts,
        GSOC.hasOlderHost,
        GSOC.hasYoungerHost,
        GSOC.staticHostedBy,
    ]

    # Property disjoint axioms to remove (non-simple properties can't have these)
    disjoint_axioms_to_remove = [
        (GSOC.occupiesSpaceDirectly, GSOC.occupiesSpaceIndirectly),
        (GSOC.occupiesSpaceIndirectly, GSOC.occupiesSpaceDirectly),
        (GSOC.occupiesTimeDirectly, GSOC.occupiesTimeIndirectly),
        (GSOC['spatio-temporallyDependsOn'], GSOC.spatiallyDisjoint),
        (GSOC.externallyGenDependsOn, GSOC.hasEssentialPart),
        (GSOC.hasEssentialPart, GSOC.timeDisjoint),
        (GSOC.hasReferenceSystem, GSOC.isReferenceSystemFor),  # This one might be ok but let's check
    ]

    # Read the file as text to do precise edits
    base_path = os.path.dirname(os.path.abspath(__file__))
    common_path = os.path.join(base_path, "GSO-Common.ttl")

    with open(common_path, 'r', encoding='utf-8') as f:
        content = f.read()

    original_content = content

    # Track removed axioms
    removed_axioms = []

    # Remove TransitiveProperty declarations
    print("\nRemoving TransitiveProperty declarations...")
    for prop in properties_to_make_simple:
        prop_local = str(prop).split('/')[-1]

        # Pattern: "  rdf:type owl:TransitiveProperty ;\n" or similar
        # Need to handle various formats
        patterns = [
            # After ObjectProperty declaration
            (rf'(gsoc:{re.escape(prop_local)}\s+rdf:type owl:ObjectProperty\s*;)\s*\n\s*rdf:type owl:TransitiveProperty\s*;',
             r'\1'),
            # Before ObjectProperty declaration
            (rf'(gsoc:{re.escape(prop_local)})\s+rdf:type owl:TransitiveProperty\s*;\s*\n(\s*rdf:type owl:ObjectProperty)',
             r'\1\n  \2'),
        ]

        for pattern, replacement in patterns:
            new_content = re.sub(pattern, replacement, content)
            if new_content != content:
                print(f"  Removed TransitiveProperty from {prop_local}")
                removed_axioms.append(f"gsoc:{prop_local} rdf:type owl:TransitiveProperty .")
                content = new_content

    # Remove propertyDisjointWith axioms
    print("\nRemoving propertyDisjointWith axioms...")
    for p1, p2 in disjoint_axioms_to_remove:
        p1_local = str(p1).split('/')[-1]
        p2_local = str(p2).split('/')[-1]

        # Pattern: "  owl:propertyDisjointWith gsoc:xxx ;\n" or ending with "."
        patterns = [
            # With semicolon (more properties follow)
            rf'(\s*)owl:propertyDisjointWith gsoc:{re.escape(p2_local)}\s*;\n',
            # With period (end of property definition)
            rf';\s*\n(\s*)owl:propertyDisjointWith gsoc:{re.escape(p2_local)}\s*\.',
        ]

        for i, pattern in enumerate(patterns):
            if i == 0:
                new_content = re.sub(pattern, '', content)
            else:
                new_content = re.sub(pattern, '.', content)

            if new_content != content:
                print(f"  Removed {p1_local} propertyDisjointWith {p2_local}")
                removed_axioms.append(f"gsoc:{p1_local} owl:propertyDisjointWith gsoc:{p2_local} .")
                content = new_content

    # Write the modified file
    if content != original_content:
        with open(common_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"\nModified: {common_path}")
    else:
        print("\nNo changes needed in file.")

    # Write the removed axioms to a separate file
    removed_file = os.path.join(base_path, "removed_owl2dl_axioms.ttl")
    with open(removed_file, 'w', encoding='utf-8') as f:
        f.write("""@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix owl: <http://www.w3.org/2002/07/owl#> .
@prefix gsoc: <https://w3id.org/gso/1.0/common/> .

# ============================================================================
# Axioms removed from GSO-Common.ttl for OWL 2 DL compatibility
# ============================================================================
#
# These axioms were removed because OWL 2 DL does not allow:
# 1. TransitiveProperty declarations on properties used in cardinality restrictions
# 2. propertyDisjointWith axioms on non-simple (transitive) properties
#
# To restore full expressivity (for OWL Full reasoners), add these back.
# ============================================================================

""")
        for axiom in removed_axioms:
            f.write(axiom + "\n")

    print(f"\nRemoved axioms saved to: {removed_file}")
    print(f"Total axioms removed: {len(removed_axioms)}")

    # Summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"TransitiveProperty declarations removed: {sum(1 for a in removed_axioms if 'TransitiveProperty' in a)}")
    print(f"propertyDisjointWith axioms removed: {sum(1 for a in removed_axioms if 'propertyDisjointWith' in a)}")


if __name__ == "__main__":
    main()
