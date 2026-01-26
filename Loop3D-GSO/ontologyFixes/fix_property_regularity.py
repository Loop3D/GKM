#!/usr/bin/env python3
"""
Fix OWL 2 DL property hierarchy regularity violations in GSO ontology.

The HermiT reasoner reports:
  "The given property hierarchy is not regular.
   There is a cyclic dependency involving property timeYoungerThan"

The Problem:
-----------
gsoc:indirectlyYoungerThan has:
  1. rdfs:subPropertyOf gsoc:timeYoungerThan
  2. owl:propertyChainAxiom ( gsoc:occupiesTime gsoc:timeYoungerThan )

Combined with gsoc:timeYoungerThan being owl:TransitiveProperty, this violates
OWL 2 DL regularity because the property chain creates a cycle with the
transitive superproperty.

OWL 2 Regularity Rule:
  If property P has a chain axiom R1 o R2 o ... o Rn ⊑ P, and P ⊑ S where
  S is transitive (or appears in another chain), then S cannot appear in
  the chain Ri. Here, timeYoungerThan appears both as a superproperty of
  indirectlyYoungerThan AND in its property chain.

Solution:
--------
Remove the rdfs:subPropertyOf assertion. The property chain already captures
the intended inference pattern. The subproperty relationship is not strictly
necessary and causes the regularity violation.

"""

import os
import shutil
from rdflib import Graph, Namespace, URIRef, RDF, RDFS, OWL


GSOC = Namespace("https://w3id.org/gso/1.0/common/")


def analyze_property_chains(graph):
    """Analyze property chains and subproperty relationships for regularity issues"""
    issues = []

    # Find all transitive properties
    transitive_props = set()
    for prop in graph.subjects(RDF.type, OWL.TransitiveProperty):
        transitive_props.add(prop)

    print(f"Found {len(transitive_props)} transitive properties")

    # Find all properties with property chain axioms
    props_with_chains = {}
    for prop in graph.subjects(OWL.propertyChainAxiom, None):
        chains = list(graph.objects(prop, OWL.propertyChainAxiom))
        props_with_chains[prop] = chains

    print(f"Found {len(props_with_chains)} properties with chain axioms")

    # For each property with a chain, check for regularity issues
    for prop, chains in props_with_chains.items():
        prop_label = get_label(graph, prop)

        # Get all superproperties (transitive closure)
        superprops = get_all_superproperties(graph, prop)

        # Check if any superproperty is transitive
        transitive_superprops = superprops & transitive_props

        if transitive_superprops:
            # Parse the chain to get properties in it
            for chain in chains:
                chain_props = parse_rdf_list(graph, chain)
                chain_prop_set = set()
                for cp in chain_props:
                    if isinstance(cp, URIRef):
                        chain_prop_set.add(cp)
                        # Also add superproperties of chain members
                        chain_prop_set.update(get_all_superproperties(graph, cp))

                # Check for overlap between transitive superprops and chain props
                overlap = transitive_superprops & chain_prop_set
                if overlap:
                    for overlapping_prop in overlap:
                        issues.append({
                            'property': prop,
                            'property_label': prop_label,
                            'transitive_superprop': overlapping_prop,
                            'transitive_label': get_label(graph, overlapping_prop),
                            'chain': chain_props,
                            'issue': f'{prop_label} has chain containing {get_label(graph, overlapping_prop)} '
                                    f'which is also a transitive superproperty'
                        })

    return issues


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


def parse_rdf_list(graph, node):
    """Parse an RDF list into a Python list"""
    items = []
    current = node
    while current and current != RDF.nil:
        first = list(graph.objects(current, RDF.first))
        if first:
            items.append(first[0])
        rest = list(graph.objects(current, RDF.rest))
        current = rest[0] if rest else None
    return items


def get_label(graph, uri):
    """Get rdfs:label for a URI"""
    for label in graph.objects(uri, RDFS.label):
        return str(label)
    s = str(uri)
    if "#" in s:
        return s.split("#")[-1]
    return s.split("/")[-1]


def fix_regularity_issues(filepath):
    """Fix regularity issues in an ontology file"""
    print(f"\nAnalyzing {filepath}...")

    # Load the graph
    graph = Graph()
    graph.parse(filepath, format="turtle")
    print(f"Loaded {len(graph)} triples")

    # Analyze for issues
    issues = analyze_property_chains(graph)

    if not issues:
        print("No regularity issues found!")
        return False

    print(f"\nFound {len(issues)} regularity issue(s):")
    for issue in issues:
        print(f"  - {issue['issue']}")

    # Create backup
    backup_path = filepath + ".regularity.bak"
    if not os.path.exists(backup_path):
        shutil.copy2(filepath, backup_path)
        print(f"\nCreated backup: {backup_path}")

    # Fix each issue by removing the problematic subPropertyOf
    fixes_made = 0
    for issue in issues:
        prop = issue['property']
        superprop = issue['transitive_superprop']

        # Check if this specific subPropertyOf triple exists
        if (prop, RDFS.subPropertyOf, superprop) in graph:
            graph.remove((prop, RDFS.subPropertyOf, superprop))
            print(f"\nRemoved: {issue['property_label']} rdfs:subPropertyOf {issue['transitive_label']}")
            fixes_made += 1

    if fixes_made > 0:
        # Bind namespaces for nice output
        graph.bind("gsoc", GSOC)
        graph.bind("owl", OWL)
        graph.bind("rdf", RDF)
        graph.bind("rdfs", RDFS)
        graph.bind("xsd", Namespace("http://www.w3.org/2001/XMLSchema#"))
        graph.bind("skos", Namespace("http://www.w3.org/2004/02/skos/core#"))
        graph.bind("dcterms", Namespace("http://purl.org/dc/terms/"))

        # Save the fixed graph
        graph.serialize(destination=filepath, format="turtle")
        print(f"\nSaved fixed ontology to: {filepath}")
        print(f"Made {fixes_made} fix(es)")
        return True

    return False


def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))

    print("=" * 60)
    print("OWL 2 DL PROPERTY REGULARITY CHECKER AND FIXER")
    print("=" * 60)

    # Fix GSO-Common.ttl
    common_path = os.path.join(script_dir, "GSO-Common.ttl")
    fixed = fix_regularity_issues(common_path)

    if fixed:
        print("\n" + "=" * 60)
        print("REGULARITY ISSUES FIXED")
        print("=" * 60)
        print("\nThe fix removed the rdfs:subPropertyOf assertion that caused")
        print("the cycle. The property chain axiom is preserved, which still")
        print("allows the reasoner to infer the intended relationships.")
        print("\nTo restore the original file:")
        print(f"  mv {common_path}.regularity.bak {common_path}")
    else:
        print("\n" + "=" * 60)
        print("NO FIXES NEEDED")
        print("=" * 60)


if __name__ == "__main__":
    main()
