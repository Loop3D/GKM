#!/usr/bin/env python3
"""
Fix OWL 2 DL violations: non-simple properties in disjoint property axioms.

In OWL 2 DL, only "simple" properties can appear in:
- owl:propertyDisjointWith
- owl:AllDisjointProperties
- owl:IrreflexiveObjectProperty
- owl:AsymmetricObjectProperty

A property PE is NON-SIMPLE (composite) if ANY of these apply:
1. PE is transitive
2. PE has a property chain axiom
3. PE has a non-simple SUBproperty (transitivity propagates UP!)
4. PE has a non-simple superproperty (transitivity propagates DOWN)
5. PE's inverse is non-simple

Solution: Remove owl:TransitiveProperty from all properties that cause
non-simplicity in properties with disjoint axioms.
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


def compute_non_simple_properties(graph):
    """
    Compute all non-simple properties using OWL 2 DL rules.
    Non-simplicity propagates both up and down the subproperty hierarchy.
    """
    non_simple = set()

    # Step 1: Direct transitive properties
    for prop in graph.subjects(RDF.type, OWL.TransitiveProperty):
        if isinstance(prop, URIRef):
            non_simple.add(prop)

    # Step 2: Properties with chain axioms
    for prop in graph.subjects(OWL.propertyChainAxiom, None):
        if isinstance(prop, URIRef):
            non_simple.add(prop)

    # Step 3: Propagate non-simplicity through property hierarchy
    # This needs to iterate until fixpoint because of complex hierarchies
    changed = True
    while changed:
        changed = False
        for prop in list(graph.subjects(RDF.type, OWL.ObjectProperty)):
            if not isinstance(prop, URIRef):
                continue
            if prop in non_simple:
                continue

            # Check superproperties (non-simplicity propagates DOWN)
            for superprop in graph.objects(prop, RDFS.subPropertyOf):
                if superprop in non_simple:
                    non_simple.add(prop)
                    changed = True
                    break

            if prop in non_simple:
                continue

            # Check subproperties (non-simplicity propagates UP!)
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


def find_transitive_causing_nonsimple(graph, prop, non_simple):
    """
    Find all transitive properties that cause a given property to be non-simple.
    This includes transitive subproperties, superproperties, and inverses.
    """
    transitive_causes = set()

    # Check if directly transitive
    if (prop, RDF.type, OWL.TransitiveProperty) in graph:
        transitive_causes.add(prop)

    # Check superproperties
    superprops = get_all_superproperties(graph, prop)
    for sp in superprops:
        if (sp, RDF.type, OWL.TransitiveProperty) in graph:
            transitive_causes.add(sp)

    # Check subproperties (non-simplicity propagates UP!)
    subprops = get_all_subproperties(graph, prop)
    for sub in subprops:
        if (sub, RDF.type, OWL.TransitiveProperty) in graph:
            transitive_causes.add(sub)

    # Check inverse and its hierarchy
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


def find_all_violations(graph):
    """Find all properties with disjoint axioms that are non-simple."""
    non_simple = compute_non_simple_properties(graph)
    violations = []

    # Find all properties involved in disjoint axioms
    props_with_disjoint = set()
    for subj in graph.subjects(OWL.propertyDisjointWith, None):
        if isinstance(subj, URIRef):
            props_with_disjoint.add(subj)
    for obj in graph.objects(None, OWL.propertyDisjointWith):
        if isinstance(obj, URIRef):
            props_with_disjoint.add(obj)

    for prop in props_with_disjoint:
        if prop in non_simple:
            transitive_causes = find_transitive_causing_nonsimple(graph, prop, non_simple)
            disjoint_with = [get_label(graph, d) for d in graph.objects(prop, OWL.propertyDisjointWith)]
            disjoint_from = [get_label(graph, d) for d in graph.subjects(OWL.propertyDisjointWith, prop)]

            violations.append({
                'property': prop,
                'label': get_label(graph, prop),
                'transitive_causes': transitive_causes,
                'disjoint_with': disjoint_with,
                'disjoint_from': disjoint_from
            })

    return violations


def fix_violations(filepath):
    """Fix by removing TransitiveProperty declarations that cause violations"""
    print(f"\nAnalyzing {filepath}...")

    graph = Graph()
    graph.parse(filepath, format="turtle")
    print(f"Loaded {len(graph)} triples")

    # Count transitive properties
    all_transitive = set()
    for prop in graph.subjects(RDF.type, OWL.TransitiveProperty):
        if isinstance(prop, URIRef):
            all_transitive.add(prop)
    print(f"Found {len(all_transitive)} transitive properties")

    violations = find_all_violations(graph)

    if not violations:
        print("No non-simple property disjoint axiom violations found!")
        return False

    print(f"\nFound {len(violations)} properties with disjoint axioms that are non-simple:")

    transitive_to_remove = set()

    for v in violations:
        print(f"\n  {v['label']}:")
        if v['disjoint_with']:
            print(f"    disjointWith: {', '.join(v['disjoint_with'])}")
        if v['disjoint_from']:
            print(f"    disjointFrom: {', '.join(v['disjoint_from'])}")

        if v['transitive_causes']:
            cause_labels = [get_label(graph, c) for c in v['transitive_causes']]
            print(f"    -> Non-simple due to transitive: {', '.join(cause_labels)}")
            transitive_to_remove.update(v['transitive_causes'])

    if not transitive_to_remove:
        print("\nNo transitive properties to remove!")
        return False

    print(f"\n\nWill remove transitivity from {len(transitive_to_remove)} properties:")
    for prop in sorted(transitive_to_remove, key=lambda p: get_label(graph, p)):
        print(f"  - {get_label(graph, prop)}")

    # Create backup
    backup_path = filepath + ".nonsimple.bak"
    shutil.copy2(filepath, backup_path)
    print(f"\nCreated backup: {backup_path}")

    # Remove TransitiveProperty declarations
    fixes_made = 0
    for prop in transitive_to_remove:
        triple = (prop, RDF.type, OWL.TransitiveProperty)
        if triple in graph:
            graph.remove(triple)
            print(f"Removed: {get_label(graph, prop)} rdf:type owl:TransitiveProperty")
            fixes_made += 1

    if fixes_made > 0:
        graph.bind("gsoc", GSOC)
        graph.bind("owl", OWL)
        graph.bind("rdf", RDF)
        graph.bind("rdfs", RDFS)
        graph.bind("xsd", Namespace("http://www.w3.org/2001/XMLSchema#"))
        graph.bind("skos", Namespace("http://www.w3.org/2004/02/skos/core#"))
        graph.bind("dcterms", Namespace("http://purl.org/dc/terms/"))

        graph.serialize(destination=filepath, format="turtle")
        print(f"\nSaved fixed ontology: {filepath}")
        print(f"Removed transitivity from {fixes_made} properties")
        return True

    return False


def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))

    print("=" * 70)
    print("FIX NON-SIMPLE PROPERTY DISJOINT AXIOM VIOLATIONS")
    print("(Handles transitivity propagating both UP and DOWN hierarchy)")
    print("=" * 70)

    common_path = os.path.join(script_dir, "GSO-Common.ttl")

    # Run iteratively until no more violations
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
            print("\nWARNING: Too many iterations, stopping.")
            break

    print("\n" + "=" * 70)
    print("COMPLETE")
    print("=" * 70)


if __name__ == "__main__":
    main()
