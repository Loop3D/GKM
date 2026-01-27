#!/usr/bin/env python3
"""Apply all OWL 2 DL fixes to GSO-Common.ttl.

Takes master's version and applies all documented OWL 2 DL removals/changes
to produce a version compatible with HermiT reasoner.

Changes applied:
1. Remove all owl:equivalentClass axioms
2. Remove all owl:TransitiveProperty declarations
3. Remove 7 owl:propertyDisjointWith axioms
4. Remove indirectlyYoungerThan property chain axiom
5. Remove hasUOM rdfs:subPropertyOf hasQuality
6. Remove 3 isReferenceSystemFor restrictions
7. Remove Pattern_Feature hasEssentialPart restrictions
8. Expand Physical_Quality isQualityOf range to include Endurant_Feature
9. Change constantlySpecDependsOn subPropertyOf to isTemporallyRelatedTo
10. Change timeStartedBy subPropertyOf to isTemporallyRelatedTo
11. Change timeStarts subPropertyOf to isTemporallyRelatedTo
"""

import sys
import os
from rdflib import Graph, Namespace, URIRef, Literal, BNode, RDF, RDFS, OWL, XSD
from rdflib.collection import Collection

GSOC = Namespace("https://w3id.org/gso/1.0/common/")


def remove_equivalentclass(g):
    """Remove all owl:equivalentClass axioms and their blank node structures."""
    count = 0
    for s, p, o in list(g.triples((None, OWL.equivalentClass, None))):
        g.remove((s, p, o))
        if isinstance(o, BNode):
            _remove_bnode_tree(g, o)
        count += 1
    return count


def _remove_bnode_tree(g, node):
    """Recursively remove a blank node and all triples rooted at it."""
    for s, p, o in list(g.triples((node, None, None))):
        g.remove((s, p, o))
        if isinstance(o, BNode):
            _remove_bnode_tree(g, o)


def remove_transitive_property(g):
    """Remove all owl:TransitiveProperty type declarations."""
    count = 0
    for s, p, o in list(g.triples((None, RDF.type, OWL.TransitiveProperty))):
        g.remove((s, p, o))
        count += 1
    return count


def remove_property_disjoint_with(g):
    """Remove specific propertyDisjointWith axioms involving transitive properties."""
    targets = [
        (GSOC.occupiesSpaceDirectly, GSOC.occupiesSpaceIndirectly),
        (GSOC.occupiesSpaceIndirectly, GSOC.occupiesSpaceDirectly),
        (GSOC.occupiesTimeDirectly, GSOC.occupiesTimeIndirectly),
        (GSOC['spatio-temporallyDependsOn'], GSOC.spatiallyDisjoint),
        (GSOC.externallyGenDependsOn, GSOC.hasEssentialPart),
        (GSOC.hasEssentialPart, GSOC.timeDisjoint),
        (GSOC.hasReferenceSystem, GSOC.isReferenceSystemFor),
    ]
    count = 0
    for s, o in targets:
        for triple in list(g.triples((s, OWL.propertyDisjointWith, o))):
            g.remove(triple)
            count += 1
    return count


def remove_property_chain(g):
    """Remove indirectlyYoungerThan property chain axiom."""
    count = 0
    for s, p, o in list(g.triples((GSOC.indirectlyYoungerThan, OWL.propertyChainAxiom, None))):
        g.remove((s, p, o))
        if isinstance(o, BNode):
            _remove_bnode_tree(g, o)
        count += 1
    return count


def remove_hasuom_subproperty(g):
    """Remove hasUOM rdfs:subPropertyOf hasQuality."""
    count = 0
    for triple in list(g.triples((GSOC.hasUOM, RDFS.subPropertyOf, GSOC.hasQuality))):
        g.remove(triple)
        count += 1
    return count


def remove_referencesystem_restrictions(g):
    """Remove isReferenceSystemFor restrictions from reference system classes."""
    targets = [
        GSOC.Nonphysical_Reference_System,
        GSOC.Physical_Reference_System,
        GSOC.Temporal_Reference_System,
    ]
    count = 0
    for cls in targets:
        for s, p, o in list(g.triples((cls, RDFS.subClassOf, None))):
            if isinstance(o, BNode):
                prop = list(g.triples((o, OWL.onProperty, GSOC.isReferenceSystemFor)))
                if prop:
                    g.remove((s, p, o))
                    _remove_bnode_tree(g, o)
                    count += 1
    return count


def remove_pattern_feature_restrictions(g):
    """Remove hasEssentialPart restrictions from Pattern_Feature."""
    count = 0
    for s, p, o in list(g.triples((GSOC.Pattern_Feature, RDFS.subClassOf, None))):
        if isinstance(o, BNode):
            prop = list(g.triples((o, OWL.onProperty, GSOC.hasEssentialPart)))
            if prop:
                g.remove((s, p, o))
                _remove_bnode_tree(g, o)
                count += 1
    return count


def expand_physical_quality_range(g):
    """Expand Physical_Quality isQualityOf to include Endurant_Feature in union."""
    # Find the existing restriction on Physical_Quality with isQualityOf
    for s, p, o in list(g.triples((GSOC.Physical_Quality, RDFS.subClassOf, None))):
        if isinstance(o, BNode):
            # Check if this is a qualified cardinality restriction on isQualityOf
            prop = list(g.triples((o, OWL.onProperty, GSOC.isQualityOf)))
            card = list(g.triples((o, OWL.qualifiedCardinality, None)))
            if prop and card:
                # Find the onClass
                for _, _, cls_node in list(g.triples((o, OWL.onClass, None))):
                    if cls_node == GSOC.Physical_Endurant:
                        # Replace with union
                        g.remove((o, OWL.onClass, cls_node))
                        union_node = BNode()
                        union_list = BNode()
                        g.add((o, OWL.onClass, union_node))
                        g.add((union_node, RDF.type, OWL.Class))
                        # Build the union list
                        Collection(g, union_list, [GSOC.Physical_Endurant, GSOC.Endurant_Feature])
                        g.add((union_node, OWL.unionOf, union_list))
                        print("  Expanded Physical_Quality isQualityOf to include Endurant_Feature")
                        return 1
                    elif isinstance(cls_node, BNode):
                        # Already a union? Check
                        union = list(g.triples((cls_node, OWL.unionOf, None)))
                        if union:
                            print("  Physical_Quality isQualityOf already has a union, checking...")
                            # Check if Endurant_Feature is already in the union
                            items = list(Collection(g, union[0][2]))
                            if GSOC.Endurant_Feature in items:
                                print("  Endurant_Feature already present, skipping")
                                return 0
                            else:
                                # Add Endurant_Feature to existing union
                                items.append(GSOC.Endurant_Feature)
                                # Remove old list
                                old_list = union[0][2]
                                g.remove((cls_node, OWL.unionOf, old_list))
                                _remove_bnode_tree(g, old_list)
                                # Create new list
                                new_list = BNode()
                                Collection(g, new_list, items)
                                g.add((cls_node, OWL.unionOf, new_list))
                                print("  Added Endurant_Feature to existing union")
                                return 1
    print("  WARNING: Could not find Physical_Quality isQualityOf restriction")
    return 0


def change_subproperty(g, prop, old_super, new_super):
    """Change a subPropertyOf relation."""
    count = 0
    for triple in list(g.triples((prop, RDFS.subPropertyOf, old_super))):
        g.remove(triple)
        g.add((prop, RDFS.subPropertyOf, new_super))
        count += 1
    return count


def main():
    input_path = sys.argv[1] if len(sys.argv) > 1 else None
    output_path = sys.argv[2] if len(sys.argv) > 2 else None

    if not input_path:
        print("Usage: apply_owl2dl_fixes.py <input.ttl> <output.ttl>")
        sys.exit(1)

    print(f"Loading: {input_path}")
    g = Graph()
    g.parse(input_path, format='turtle')
    print(f"  {len(g)} triples")

    print("\nApplying OWL 2 DL fixes:")

    n = remove_equivalentclass(g)
    print(f"  1. Removed {n} equivalentClass axioms")

    n = remove_transitive_property(g)
    print(f"  2. Removed {n} TransitiveProperty declarations")

    n = remove_property_disjoint_with(g)
    print(f"  3. Removed {n} propertyDisjointWith axioms")

    n = remove_property_chain(g)
    print(f"  4. Removed {n} property chain axioms")

    n = remove_hasuom_subproperty(g)
    print(f"  5. Removed {n} hasUOM subPropertyOf hasQuality")

    n = remove_referencesystem_restrictions(g)
    print(f"  6. Removed {n} isReferenceSystemFor restrictions")

    n = remove_pattern_feature_restrictions(g)
    print(f"  7. Removed {n} Pattern_Feature hasEssentialPart restrictions")

    n = expand_physical_quality_range(g)
    print(f"  8. Physical_Quality isQualityOf expansion: {n} changes")

    n = change_subproperty(g, GSOC.constantlySpecDependsOn,
                           GSOC.timeIncludedBy, GSOC.isTemporallyRelatedTo)
    print(f"  9. constantlySpecDependsOn subPropertyOf change: {n}")

    n = change_subproperty(g, GSOC.timeStartedBy,
                           GSOC.timeIncludes, GSOC.isTemporallyRelatedTo)
    print(f"  10. timeStartedBy subPropertyOf change: {n}")

    n = change_subproperty(g, GSOC.timeStarts,
                           GSOC.timeIncludedBy, GSOC.isTemporallyRelatedTo)
    print(f"  11. timeStarts subPropertyOf change: {n}")

    print(f"\nResult: {len(g)} triples")

    # Verify
    equiv = list(g.triples((None, OWL.equivalentClass, None)))
    trans = list(g.triples((None, RDF.type, OWL.TransitiveProperty)))
    print(f"\nVerification:")
    print(f"  equivalentClass axioms remaining: {len(equiv)}")
    print(f"  TransitiveProperty declarations remaining: {len(trans)}")

    if output_path:
        print(f"\nSerializing to: {output_path}")
        g.serialize(destination=output_path, format='turtle')
        print("Done.")


if __name__ == "__main__":
    main()
