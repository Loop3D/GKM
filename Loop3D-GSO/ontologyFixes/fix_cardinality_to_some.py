#!/usr/bin/env python3
"""
Fix OWL 2 DL violations: convert cardinality restrictions on non-simple properties
to someValuesFrom restrictions.

Non-simple properties cannot have cardinality restrictions. This script converts:
- owl:qualifiedCardinality -> owl:someValuesFrom
- owl:minQualifiedCardinality -> owl:someValuesFrom
- owl:maxQualifiedCardinality -> (removed, no equivalent)
- owl:cardinality -> owl:someValuesFrom owl:Thing
- owl:minCardinality -> owl:someValuesFrom owl:Thing
- owl:maxCardinality -> (removed)
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

            for superprop in graph.objects(prop, RDFS.subPropertyOf):
                if superprop in non_simple:
                    non_simple.add(prop)
                    changed = True
                    break

            if prop in non_simple:
                continue

            for subprop in graph.subjects(RDFS.subPropertyOf, prop):
                if subprop in non_simple:
                    non_simple.add(prop)
                    changed = True
                    break

            if prop in non_simple:
                continue

            inv = get_inverse(graph, prop)
            if inv and inv in non_simple:
                non_simple.add(prop)
                changed = True

    return non_simple


def find_cardinality_restrictions_to_fix(graph, non_simple):
    """Find all cardinality restrictions using non-simple properties"""
    cardinality_predicates = [
        (OWL.cardinality, False),
        (OWL.qualifiedCardinality, True),
        (OWL.minCardinality, False),
        (OWL.minQualifiedCardinality, True),
        (OWL.maxCardinality, False),
        (OWL.maxQualifiedCardinality, True),
    ]

    restrictions_to_fix = []

    for card_pred, is_qualified in cardinality_predicates:
        for restriction in graph.subjects(card_pred, None):
            prop = list(graph.objects(restriction, OWL.onProperty))
            if not prop:
                continue
            prop = prop[0]

            if prop not in non_simple:
                continue

            # Get the class (for qualified) or use owl:Thing
            if is_qualified:
                on_class = list(graph.objects(restriction, OWL.onClass))
                if on_class:
                    filler = on_class[0]
                else:
                    filler = OWL.Thing
            else:
                filler = OWL.Thing

            card_value = list(graph.objects(restriction, card_pred))

            restrictions_to_fix.append({
                'restriction': restriction,
                'property': prop,
                'property_label': get_label(graph, prop),
                'cardinality_pred': card_pred,
                'cardinality_value': card_value[0] if card_value else None,
                'is_qualified': is_qualified,
                'filler': filler,
                'filler_label': get_label(graph, filler) if isinstance(filler, URIRef) else "_:blank",
                'is_max': 'max' in str(card_pred).lower(),
            })

    return restrictions_to_fix


def fix_violations(filepath):
    """Convert cardinality restrictions to someValuesFrom"""
    print(f"\nAnalyzing {filepath}...")

    graph = Graph()
    graph.parse(filepath, format="turtle")
    print(f"Loaded {len(graph)} triples")

    non_simple = compute_non_simple_properties(graph)
    print(f"Found {len(non_simple)} non-simple properties")

    restrictions = find_cardinality_restrictions_to_fix(graph, non_simple)

    if not restrictions:
        print("No cardinality restrictions on non-simple properties found!")
        return False

    print(f"\nFound {len(restrictions)} cardinality restrictions to convert:")
    for r in restrictions:
        print(f"  - {r['property_label']} {str(r['cardinality_pred']).split('#')[-1]} {r['cardinality_value']} on {r['filler_label']}")

    # Create backup
    backup_path = filepath + ".cardtosome.bak"
    shutil.copy2(filepath, backup_path)
    print(f"\nCreated backup: {backup_path}")

    # Convert restrictions
    converted = 0
    removed = 0

    for r in restrictions:
        restriction = r['restriction']
        prop = r['property']
        filler = r['filler']
        card_pred = r['cardinality_pred']
        card_value = r['cardinality_value']

        if r['is_max']:
            # Max cardinality has no someValuesFrom equivalent - just remove
            graph.remove((restriction, card_pred, card_value))
            if r['is_qualified']:
                graph.remove((restriction, OWL.onClass, filler))
            print(f"Removed: {r['property_label']} {str(card_pred).split('#')[-1]} (no equivalent)")
            removed += 1
        else:
            # Convert to someValuesFrom
            graph.remove((restriction, card_pred, card_value))
            if r['is_qualified']:
                graph.remove((restriction, OWL.onClass, filler))
            graph.add((restriction, OWL.someValuesFrom, filler))
            print(f"Converted: {r['property_label']} -> someValuesFrom {r['filler_label']}")
            converted += 1

    if converted > 0 or removed > 0:
        graph.bind("gsoc", GSOC)
        graph.bind("owl", OWL)
        graph.bind("rdf", RDF)
        graph.bind("rdfs", RDFS)
        graph.bind("xsd", Namespace("http://www.w3.org/2001/XMLSchema#"))
        graph.bind("skos", Namespace("http://www.w3.org/2004/02/skos/core#"))
        graph.bind("dcterms", Namespace("http://purl.org/dc/terms/"))

        graph.serialize(destination=filepath, format="turtle")
        print(f"\nSaved fixed ontology: {filepath}")
        print(f"Converted {converted} restrictions, removed {removed} max restrictions")
        return True

    return False


def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))

    print("=" * 70)
    print("CONVERT CARDINALITY RESTRICTIONS TO SOMEVALUESFROM")
    print("(For non-simple properties that can't have cardinality)")
    print("=" * 70)

    common_path = os.path.join(script_dir, "GSO-Common.ttl")
    fix_violations(common_path)

    print("\n" + "=" * 70)
    print("COMPLETE")
    print("=" * 70)


if __name__ == "__main__":
    main()
