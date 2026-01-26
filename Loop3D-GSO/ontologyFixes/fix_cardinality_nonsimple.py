#!/usr/bin/env python3
"""
Fix OWL 2 DL violations: non-simple properties in cardinality restrictions.

In OWL 2 DL, only simple properties can appear in:
- owl:minCardinality / owl:minQualifiedCardinality
- owl:maxCardinality / owl:maxQualifiedCardinality
- owl:cardinality / owl:qualifiedCardinality

Solution: Remove owl:TransitiveProperty from properties used in cardinality restrictions.
"""

import os
import shutil
from rdflib import Graph, Namespace, URIRef, BNode, RDF, RDFS, OWL


GSOC = Namespace("https://w3id.org/gso/1.0/common/")


def get_label(graph, uri):
    """Get rdfs:label for a URI"""
    if isinstance(uri, BNode):
        return "_:blank"
    for label in graph.objects(uri, RDFS.label):
        return str(label)
    s = str(uri)
    if "#" in s:
        return s.split("#")[-1]
    return s.split("/")[-1]


def get_all_superproperties(graph, prop, visited=None):
    """Get transitive closure of superproperties"""
    if visited is None:
        visited = set()
    if prop in visited:
        return visited
    for superprop in graph.objects(prop, RDFS.subPropertyOf):
        if isinstance(superprop, URIRef):
            visited.add(superprop)
            get_all_superproperties(graph, superprop, visited)
    return visited


def get_all_subproperties(graph, prop, visited=None):
    """Get transitive closure of subproperties"""
    if visited is None:
        visited = set()
    if prop in visited:
        return visited
    for subprop in graph.subjects(RDFS.subPropertyOf, prop):
        if isinstance(subprop, URIRef):
            visited.add(subprop)
            get_all_subproperties(graph, subprop, visited)
    return visited


def get_inverse(graph, prop):
    """Get inverse property if defined"""
    for inv in graph.objects(prop, OWL.inverseOf):
        if isinstance(inv, URIRef):
            return inv
    for inv in graph.subjects(OWL.inverseOf, prop):
        if isinstance(inv, URIRef):
            return inv
    return None


def find_properties_in_cardinality_restrictions(graph):
    """Find all properties used in cardinality restrictions"""
    cardinality_predicates = [
        OWL.cardinality,
        OWL.qualifiedCardinality,
        OWL.minCardinality,
        OWL.minQualifiedCardinality,
        OWL.maxCardinality,
        OWL.maxQualifiedCardinality,
    ]

    props_in_cardinality = set()

    # Find all restrictions with cardinality
    for card_pred in cardinality_predicates:
        for restriction in graph.subjects(card_pred, None):
            # Get the property used in this restriction
            for prop in graph.objects(restriction, OWL.onProperty):
                if isinstance(prop, URIRef):
                    props_in_cardinality.add(prop)

    return props_in_cardinality


def compute_non_simple_properties(graph):
    """Compute all non-simple properties"""
    non_simple = set()

    # Transitive properties
    for prop in graph.subjects(RDF.type, OWL.TransitiveProperty):
        if isinstance(prop, URIRef):
            non_simple.add(prop)

    # Properties with chain axioms
    for prop in graph.subjects(OWL.propertyChainAxiom, None):
        if isinstance(prop, URIRef):
            non_simple.add(prop)

    # Properties appearing in chains
    for chain_list in graph.objects(None, OWL.propertyChainAxiom):
        current = chain_list
        while current and current != RDF.nil:
            first = list(graph.objects(current, RDF.first))
            if first and isinstance(first[0], URIRef):
                non_simple.add(first[0])
            rest = list(graph.objects(current, RDF.rest))
            current = rest[0] if rest else None

    # Propagate through hierarchy
    changed = True
    while changed:
        changed = False
        for prop in list(graph.subjects(RDF.type, OWL.ObjectProperty)):
            if not isinstance(prop, URIRef) or prop in non_simple:
                continue

            # Check superproperties
            for superprop in graph.objects(prop, RDFS.subPropertyOf):
                if superprop in non_simple:
                    non_simple.add(prop)
                    changed = True
                    break

            if prop in non_simple:
                continue

            # Check subproperties
            for subprop in graph.subjects(RDFS.subPropertyOf, prop):
                if subprop in non_simple:
                    non_simple.add(prop)
                    changed = True
                    break

            if prop in non_simple:
                continue

            # Check inverse
            inv = get_inverse(graph, prop)
            if inv and inv in non_simple:
                non_simple.add(prop)
                changed = True

    return non_simple


def find_transitive_causing_nonsimple(graph, prop):
    """Find all transitive properties causing a property to be non-simple"""
    transitive_causes = set()

    # Check if directly transitive
    if (prop, RDF.type, OWL.TransitiveProperty) in graph:
        transitive_causes.add(prop)

    # Check superproperties
    for sp in get_all_superproperties(graph, prop):
        if (sp, RDF.type, OWL.TransitiveProperty) in graph:
            transitive_causes.add(sp)

    # Check subproperties
    for sub in get_all_subproperties(graph, prop):
        if (sub, RDF.type, OWL.TransitiveProperty) in graph:
            transitive_causes.add(sub)

    # Check inverse
    inv = get_inverse(graph, prop)
    if inv:
        if (inv, RDF.type, OWL.TransitiveProperty) in graph:
            transitive_causes.add(inv)
        for sp in get_all_superproperties(graph, inv):
            if (sp, RDF.type, OWL.TransitiveProperty) in graph:
                transitive_causes.add(sp)
        for sub in get_all_subproperties(graph, inv):
            if (sub, RDF.type, OWL.TransitiveProperty) in graph:
                transitive_causes.add(sub)

    return transitive_causes


def fix_violations(filepath):
    """Fix by removing transitivity from properties used in cardinality restrictions"""
    print(f"\nAnalyzing {filepath}...")

    graph = Graph()
    graph.parse(filepath, format="turtle")
    print(f"Loaded {len(graph)} triples")

    # Find properties in cardinality restrictions
    props_in_cardinality = find_properties_in_cardinality_restrictions(graph)
    print(f"Found {len(props_in_cardinality)} properties in cardinality restrictions")

    # Find non-simple properties
    non_simple = compute_non_simple_properties(graph)
    print(f"Found {len(non_simple)} non-simple properties")

    # Find violations
    violations = props_in_cardinality & non_simple
    if not violations:
        print("No cardinality restriction violations found!")
        return False

    print(f"\nFound {len(violations)} non-simple properties in cardinality restrictions:")

    transitive_to_remove = set()
    for prop in violations:
        causes = find_transitive_causing_nonsimple(graph, prop)
        cause_labels = [get_label(graph, c) for c in causes]
        print(f"  - {get_label(graph, prop)}")
        if causes:
            print(f"    -> Non-simple due to: {', '.join(cause_labels)}")
            transitive_to_remove.update(causes)

    if not transitive_to_remove:
        print("\nNo transitive properties to remove (may be due to property chains)")
        return False

    print(f"\n\nWill remove transitivity from {len(transitive_to_remove)} properties:")
    for prop in sorted(transitive_to_remove, key=lambda p: get_label(graph, p)):
        print(f"  - {get_label(graph, prop)}")

    # Create backup
    backup_path = filepath + ".cardinality.bak"
    shutil.copy2(filepath, backup_path)
    print(f"\nCreated backup: {backup_path}")

    # Remove TransitiveProperty declarations
    removed = 0
    for prop in transitive_to_remove:
        triple = (prop, RDF.type, OWL.TransitiveProperty)
        if triple in graph:
            graph.remove(triple)
            print(f"Removed: {get_label(graph, prop)} rdf:type owl:TransitiveProperty")
            removed += 1

    if removed > 0:
        graph.bind("gsoc", GSOC)
        graph.bind("owl", OWL)
        graph.bind("rdf", RDF)
        graph.bind("rdfs", RDFS)
        graph.bind("xsd", Namespace("http://www.w3.org/2001/XMLSchema#"))
        graph.bind("skos", Namespace("http://www.w3.org/2004/02/skos/core#"))
        graph.bind("dcterms", Namespace("http://purl.org/dc/terms/"))

        graph.serialize(destination=filepath, format="turtle")
        print(f"\nSaved fixed ontology: {filepath}")
        print(f"Removed transitivity from {removed} properties")
        return True

    return False


def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))

    print("=" * 70)
    print("FIX NON-SIMPLE PROPERTIES IN CARDINALITY RESTRICTIONS")
    print("(Removes transitivity to preserve cardinality constraints)")
    print("=" * 70)

    common_path = os.path.join(script_dir, "GSO-Common.ttl")

    # Run iteratively
    iteration = 1
    while True:
        print(f"\n{'='*70}")
        print(f"ITERATION {iteration}")
        print("=" * 70)

        fixed = fix_violations(common_path)
        if not fixed:
            break
        iteration += 1
        if iteration > 10:
            print("\nWARNING: Too many iterations")
            break

    print("\n" + "=" * 70)
    print("COMPLETE")
    print("=" * 70)


if __name__ == "__main__":
    main()
