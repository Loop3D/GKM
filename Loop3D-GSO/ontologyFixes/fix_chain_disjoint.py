#!/usr/bin/env python3
"""
Fix OWL 2 DL violations where property chains make properties non-simple,
and those non-simple properties have disjoint axioms.

Solution: Remove the disjoint axioms (since we want to keep the property chains).
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


def get_properties_in_chains(graph):
    """Find all properties that appear in property chain axioms"""
    props_in_chains = set()

    for chain_list in graph.objects(None, OWL.propertyChainAxiom):
        # Parse the RDF list
        current = chain_list
        while current and current != RDF.nil:
            first = list(graph.objects(current, RDF.first))
            if first and isinstance(first[0], URIRef):
                props_in_chains.add(first[0])
            rest = list(graph.objects(current, RDF.rest))
            current = rest[0] if rest else None

    return props_in_chains


def compute_non_simple_properties(graph):
    """
    Compute all non-simple properties using OWL 2 DL rules.
    """
    non_simple = set()

    # Properties that appear in chains are non-simple
    props_in_chains = get_properties_in_chains(graph)
    non_simple.update(props_in_chains)

    # Transitive properties
    for prop in graph.subjects(RDF.type, OWL.TransitiveProperty):
        if isinstance(prop, URIRef):
            non_simple.add(prop)

    # Properties with chain axioms
    for prop in graph.subjects(OWL.propertyChainAxiom, None):
        if isinstance(prop, URIRef):
            non_simple.add(prop)

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


def find_disjoint_violations(graph, non_simple):
    """Find all disjoint axioms involving non-simple properties"""
    violations = []

    for subj, obj in graph.subject_objects(OWL.propertyDisjointWith):
        if isinstance(subj, URIRef) and isinstance(obj, URIRef):
            if subj in non_simple or obj in non_simple:
                violations.append({
                    'subject': subj,
                    'subject_label': get_label(graph, subj),
                    'object': obj,
                    'object_label': get_label(graph, obj),
                    'subject_nonsimple': subj in non_simple,
                    'object_nonsimple': obj in non_simple
                })

    return violations


def fix_violations(filepath):
    """Fix by removing disjoint axioms involving non-simple properties"""
    print(f"\nAnalyzing {filepath}...")

    graph = Graph()
    graph.parse(filepath, format="turtle")
    print(f"Loaded {len(graph)} triples")

    # Find properties in chains
    props_in_chains = get_properties_in_chains(graph)
    print(f"Found {len(props_in_chains)} properties appearing in chains")
    for p in props_in_chains:
        print(f"  - {get_label(graph, p)}")

    # Compute non-simple properties
    non_simple = compute_non_simple_properties(graph)
    print(f"\nFound {len(non_simple)} non-simple properties total")

    # Find violations
    violations = find_disjoint_violations(graph, non_simple)

    if not violations:
        print("No disjoint axiom violations found!")
        return False

    print(f"\nFound {len(violations)} disjoint axioms involving non-simple properties:")
    for v in violations:
        ns1 = " (non-simple)" if v['subject_nonsimple'] else ""
        ns2 = " (non-simple)" if v['object_nonsimple'] else ""
        print(f"  - {v['subject_label']}{ns1} disjointWith {v['object_label']}{ns2}")

    # Create backup
    backup_path = filepath + ".chaindisjoint.bak"
    shutil.copy2(filepath, backup_path)
    print(f"\nCreated backup: {backup_path}")

    # Remove disjoint axioms
    removed = 0
    for v in violations:
        triple = (v['subject'], OWL.propertyDisjointWith, v['object'])
        if triple in graph:
            graph.remove(triple)
            print(f"Removed: {v['subject_label']} propertyDisjointWith {v['object_label']}")
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
        print(f"Removed {removed} disjoint axioms")
        return True

    return False


def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))

    print("=" * 70)
    print("FIX PROPERTY CHAIN + DISJOINT AXIOM VIOLATIONS")
    print("(Removes disjoint axioms to preserve property chains)")
    print("=" * 70)

    common_path = os.path.join(script_dir, "GSO-Common.ttl")
    fix_violations(common_path)

    print("\n" + "=" * 70)
    print("COMPLETE")
    print("=" * 70)


if __name__ == "__main__":
    main()
