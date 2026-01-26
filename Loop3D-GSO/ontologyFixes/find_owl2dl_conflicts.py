#!/usr/bin/env python3
"""
Find OWL 2 DL conflicts in GSO ontology.

OWL 2 DL Rule: Non-simple properties cannot be used with:
- Cardinality restrictions (owl:cardinality, owl:minCardinality, owl:maxCardinality, qualified variants)
- owl:propertyDisjointWith

A property is non-simple if:
1. It's declared owl:TransitiveProperty
2. It has a subproperty that is non-simple
3. It appears in a property chain axiom (owl:propertyChainAxiom)
"""

from rdflib import Graph, Namespace, RDF, RDFS, OWL, URIRef, BNode
from collections import defaultdict
import os

# Namespaces
GSOC = Namespace("https://w3id.org/gso/1.0/common/")
GSOG = Namespace("https://w3id.org/gso/1.0/geology/")

def load_ontology():
    """Load all GSO ontology files."""
    g = Graph()

    base_path = os.path.dirname(os.path.abspath(__file__))

    # Core files
    core_files = [
        "GSO-Common.ttl",
        "GSO-Geology.ttl",
    ]

    # Module files
    modules_path = os.path.join(base_path, "Modules")
    module_files = []
    if os.path.exists(modules_path):
        module_files = [os.path.join("Modules", f) for f in os.listdir(modules_path) if f.endswith('.ttl')]

    all_files = core_files + module_files

    for ttl_file in all_files:
        full_path = os.path.join(base_path, ttl_file)
        if os.path.exists(full_path):
            try:
                g.parse(full_path, format='turtle')
                print(f"Loaded: {ttl_file}")
            except Exception as e:
                print(f"Error loading {ttl_file}: {e}")

    print(f"\nTotal triples: {len(g)}")
    return g


def find_transitive_properties(g):
    """Find all properties declared as TransitiveProperty."""
    transitive = set()
    for prop in g.subjects(RDF.type, OWL.TransitiveProperty):
        if isinstance(prop, URIRef):
            transitive.add(prop)
    return transitive


def find_property_chains(g):
    """Find all properties that have property chain axioms."""
    chained = set()
    for prop in g.subjects(OWL.propertyChainAxiom, None):
        if isinstance(prop, URIRef):
            chained.add(prop)
    return chained


def build_property_hierarchy(g):
    """Build subPropertyOf hierarchy (child -> parents)."""
    hierarchy = defaultdict(set)
    for child, _, parent in g.triples((None, RDFS.subPropertyOf, None)):
        if isinstance(child, URIRef) and isinstance(parent, URIRef):
            hierarchy[child].add(parent)
    return hierarchy


def build_inverse_hierarchy(g):
    """Build inverse property mapping."""
    inverses = {}
    for p1, _, p2 in g.triples((None, OWL.inverseOf, None)):
        if isinstance(p1, URIRef) and isinstance(p2, URIRef):
            inverses[p1] = p2
            inverses[p2] = p1
    return inverses


def compute_non_simple_properties(g, transitive, chained, hierarchy, inverses):
    """
    Compute all non-simple properties.
    A property is non-simple if:
    1. It's transitive
    2. It has a property chain
    3. It has a subproperty that is non-simple
    4. Its inverse is non-simple
    """
    non_simple = set(transitive) | set(chained)

    # Get all properties
    all_props = set()
    for prop in g.subjects(RDF.type, OWL.ObjectProperty):
        if isinstance(prop, URIRef):
            all_props.add(prop)

    # Propagate non-simplicity up the hierarchy (subproperty makes parent non-simple for cardinality purposes)
    # Actually, in OWL 2 DL, non-simplicity propagates DOWN (from superproperty to subproperty)
    # But for cardinality restrictions, we need to check if the property or any of its superproperties is non-simple

    # Build reverse hierarchy (parent -> children)
    children_of = defaultdict(set)
    for child, parents in hierarchy.items():
        for parent in parents:
            children_of[parent].add(child)

    # Propagate non-simplicity down from transitive/chained properties to their subproperties
    changed = True
    while changed:
        changed = False
        for prop in list(non_simple):
            for child in children_of.get(prop, []):
                if child not in non_simple:
                    non_simple.add(child)
                    changed = True

    # Also, if a property's inverse is non-simple, so is the property
    changed = True
    while changed:
        changed = False
        for prop in list(non_simple):
            inv = inverses.get(prop)
            if inv and inv not in non_simple:
                non_simple.add(inv)
                changed = True

    return non_simple


def get_superproperties(prop, hierarchy, visited=None):
    """Get all superproperties of a property (transitive closure)."""
    if visited is None:
        visited = set()
    if prop in visited:
        return set()
    visited.add(prop)

    supers = set(hierarchy.get(prop, []))
    for parent in list(supers):
        supers |= get_superproperties(parent, hierarchy, visited)
    return supers


def find_cardinality_restrictions(g):
    """Find all cardinality restrictions and the properties they constrain."""
    restrictions = []

    cardinality_predicates = [
        OWL.cardinality,
        OWL.minCardinality,
        OWL.maxCardinality,
        OWL.qualifiedCardinality,
        URIRef("http://www.w3.org/2002/07/owl#minQualifiedCardinality"),
        URIRef("http://www.w3.org/2002/07/owl#maxQualifiedCardinality"),
    ]

    # Find all restriction nodes
    for restr in g.subjects(RDF.type, OWL.Restriction):
        prop = None
        card_type = None
        card_value = None
        used_by = []

        # Get the property
        for p in g.objects(restr, OWL.onProperty):
            prop = p
            break

        if not prop or not isinstance(prop, URIRef):
            continue

        # Check for cardinality
        for card_pred in cardinality_predicates:
            for val in g.objects(restr, card_pred):
                card_type = card_pred
                card_value = val
                break
            if card_type:
                break

        if not card_type:
            continue

        # Find what classes use this restriction
        for cls in g.subjects(RDFS.subClassOf, restr):
            if isinstance(cls, URIRef):
                used_by.append(('subClassOf', cls))
        for cls in g.subjects(OWL.equivalentClass, restr):
            if isinstance(cls, URIRef):
                used_by.append(('equivalentClass', cls))

        # Also check for nested restrictions in intersections/unions
        # This is complex, so we'll just record the restriction

        restrictions.append({
            'property': prop,
            'cardinality_type': card_type,
            'cardinality_value': card_value,
            'used_by': used_by,
            'restriction_node': restr
        })

    return restrictions


def find_disjoint_property_axioms(g):
    """Find all propertyDisjointWith axioms."""
    disjoints = []

    for p1, _, p2 in g.triples((None, OWL.propertyDisjointWith, None)):
        if isinstance(p1, URIRef):
            disjoints.append({
                'property1': p1,
                'property2': p2
            })

    return disjoints


def get_label(g, uri):
    """Get rdfs:label for a URI."""
    if not isinstance(uri, URIRef):
        return str(uri)
    for label in g.objects(uri, RDFS.label):
        return str(label)
    # Return local name
    s = str(uri)
    return s.split('/')[-1].split('#')[-1]


def main():
    print("=" * 70)
    print("OWL 2 DL Conflict Finder for GSO Ontology")
    print("=" * 70)

    g = load_ontology()

    print("\n" + "=" * 70)
    print("Step 1: Finding transitive properties...")
    print("=" * 70)
    transitive = find_transitive_properties(g)
    print(f"Found {len(transitive)} transitive properties:")
    for prop in sorted(transitive, key=str):
        print(f"  - {get_label(g, prop)}: {prop}")

    print("\n" + "=" * 70)
    print("Step 2: Finding property chain axioms...")
    print("=" * 70)
    chained = find_property_chains(g)
    print(f"Found {len(chained)} properties with chain axioms:")
    for prop in sorted(chained, key=str):
        print(f"  - {get_label(g, prop)}: {prop}")

    print("\n" + "=" * 70)
    print("Step 3: Building property hierarchy...")
    print("=" * 70)
    hierarchy = build_property_hierarchy(g)
    inverses = build_inverse_hierarchy(g)
    print(f"Found {len(hierarchy)} properties with superproperties")
    print(f"Found {len(inverses)//2} inverse property pairs")

    print("\n" + "=" * 70)
    print("Step 4: Computing non-simple properties...")
    print("=" * 70)
    non_simple = compute_non_simple_properties(g, transitive, chained, hierarchy, inverses)
    print(f"Found {len(non_simple)} non-simple properties (transitive + subproperties + inverses)")

    print("\n" + "=" * 70)
    print("Step 5: Finding cardinality restrictions...")
    print("=" * 70)
    card_restrictions = find_cardinality_restrictions(g)
    print(f"Found {len(card_restrictions)} cardinality restrictions")

    print("\n" + "=" * 70)
    print("Step 6: Finding propertyDisjointWith axioms...")
    print("=" * 70)
    disjoints = find_disjoint_property_axioms(g)
    print(f"Found {len(disjoints)} propertyDisjointWith axioms")

    print("\n" + "=" * 70)
    print("CONFLICTS: Cardinality restrictions on non-simple properties")
    print("=" * 70)

    card_conflicts = []
    for restr in card_restrictions:
        prop = restr['property']
        # Check if property or any superproperty is non-simple
        all_props = {prop} | get_superproperties(prop, hierarchy)
        inv = inverses.get(prop)
        if inv:
            all_props.add(inv)
            all_props |= get_superproperties(inv, hierarchy)

        non_simple_in_chain = all_props & non_simple
        if non_simple_in_chain:
            card_conflicts.append({
                'restriction': restr,
                'non_simple_props': non_simple_in_chain
            })

    if card_conflicts:
        print(f"\nFound {len(card_conflicts)} cardinality restriction conflicts:\n")
        for i, conflict in enumerate(card_conflicts, 1):
            restr = conflict['restriction']
            prop = restr['property']
            print(f"{i}. Property: {get_label(g, prop)}")
            print(f"   URI: {prop}")
            print(f"   Cardinality: {restr['cardinality_type'].split('#')[-1]} = {restr['cardinality_value']}")
            print(f"   Non-simple because of: {[get_label(g, p) for p in conflict['non_simple_props']]}")
            if restr['used_by']:
                print(f"   Used by classes: {[get_label(g, c) for _, c in restr['used_by'][:3]]}")
            print()
    else:
        print("No cardinality restriction conflicts found.")

    print("\n" + "=" * 70)
    print("CONFLICTS: propertyDisjointWith on non-simple properties")
    print("=" * 70)

    disjoint_conflicts = []
    for disj in disjoints:
        p1 = disj['property1']
        p2 = disj['property2']

        # Check p1
        all_props1 = {p1} | get_superproperties(p1, hierarchy)
        inv1 = inverses.get(p1)
        if inv1:
            all_props1.add(inv1)

        # Check p2 if it's a URI
        all_props2 = set()
        if isinstance(p2, URIRef):
            all_props2 = {p2} | get_superproperties(p2, hierarchy)
            inv2 = inverses.get(p2)
            if inv2:
                all_props2.add(inv2)

        non_simple1 = all_props1 & non_simple
        non_simple2 = all_props2 & non_simple

        if non_simple1 or non_simple2:
            disjoint_conflicts.append({
                'axiom': disj,
                'non_simple1': non_simple1,
                'non_simple2': non_simple2
            })

    if disjoint_conflicts:
        print(f"\nFound {len(disjoint_conflicts)} propertyDisjointWith conflicts:\n")
        for i, conflict in enumerate(disjoint_conflicts, 1):
            axiom = conflict['axiom']
            p1 = axiom['property1']
            p2 = axiom['property2']
            print(f"{i}. {get_label(g, p1)} propertyDisjointWith {get_label(g, p2) if isinstance(p2, URIRef) else p2}")
            print(f"   Property1: {p1}")
            print(f"   Property2: {p2}")
            if conflict['non_simple1']:
                print(f"   Property1 non-simple because of: {[get_label(g, p) for p in conflict['non_simple1']]}")
            if conflict['non_simple2']:
                print(f"   Property2 non-simple because of: {[get_label(g, p) for p in conflict['non_simple2']]}")
            print()
    else:
        print("No propertyDisjointWith conflicts found.")

    # Summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"Total transitive properties: {len(transitive)}")
    print(f"Total non-simple properties: {len(non_simple)}")
    print(f"Total cardinality restrictions: {len(card_restrictions)}")
    print(f"Total propertyDisjointWith axioms: {len(disjoints)}")
    print(f"Cardinality conflicts: {len(card_conflicts)}")
    print(f"Disjoint conflicts: {len(disjoint_conflicts)}")

    # Recommendations
    print("\n" + "=" * 70)
    print("RECOMMENDATIONS")
    print("=" * 70)

    # Find which transitive properties are causing the most conflicts
    conflict_sources = defaultdict(int)
    for conflict in card_conflicts:
        for prop in conflict['non_simple_props']:
            if prop in transitive:
                conflict_sources[prop] += 1

    for conflict in disjoint_conflicts:
        for prop in conflict['non_simple1'] | conflict['non_simple2']:
            if prop in transitive:
                conflict_sources[prop] += 1

    if conflict_sources:
        print("\nTransitive properties causing most conflicts:")
        for prop, count in sorted(conflict_sources.items(), key=lambda x: -x[1])[:20]:
            print(f"  {count:3d} conflicts: {get_label(g, prop)}")
            print(f"                {prop}")

        print("\nTo fix: Remove 'rdf:type owl:TransitiveProperty' from these properties,")
        print("OR remove the cardinality restrictions that use them.")

    # Write detailed report
    report_file = "owl2dl_conflicts_report.txt"
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write("OWL 2 DL Conflict Report for GSO Ontology\n")
        f.write("=" * 70 + "\n\n")

        f.write("TRANSITIVE PROPERTIES\n")
        f.write("-" * 40 + "\n")
        for prop in sorted(transitive, key=str):
            f.write(f"{get_label(g, prop)}: {prop}\n")

        f.write(f"\n\nNON-SIMPLE PROPERTIES ({len(non_simple)} total)\n")
        f.write("-" * 40 + "\n")
        for prop in sorted(non_simple, key=str):
            reasons = []
            if prop in transitive:
                reasons.append("transitive")
            if prop in chained:
                reasons.append("has chain")
            # Check if non-simple due to superproperty
            supers = get_superproperties(prop, hierarchy)
            non_simple_supers = supers & non_simple
            if non_simple_supers and prop not in transitive and prop not in chained:
                reasons.append(f"subproperty of {[get_label(g, p) for p in non_simple_supers]}")
            f.write(f"{get_label(g, prop)}: {prop}\n")
            f.write(f"  Reason: {', '.join(reasons) if reasons else 'inverse of non-simple'}\n")

        f.write(f"\n\nCARDINALITY CONFLICTS ({len(card_conflicts)} total)\n")
        f.write("-" * 40 + "\n")
        for i, conflict in enumerate(card_conflicts, 1):
            restr = conflict['restriction']
            prop = restr['property']
            f.write(f"\n{i}. Property: {get_label(g, prop)}\n")
            f.write(f"   URI: {prop}\n")
            f.write(f"   Cardinality: {restr['cardinality_type'].split('#')[-1]} = {restr['cardinality_value']}\n")
            f.write(f"   Non-simple because: {[get_label(g, p) for p in conflict['non_simple_props']]}\n")

        f.write(f"\n\nDISJOINT CONFLICTS ({len(disjoint_conflicts)} total)\n")
        f.write("-" * 40 + "\n")
        for i, conflict in enumerate(disjoint_conflicts, 1):
            axiom = conflict['axiom']
            p1 = axiom['property1']
            p2 = axiom['property2']
            f.write(f"\n{i}. {get_label(g, p1)} propertyDisjointWith {get_label(g, p2) if isinstance(p2, URIRef) else p2}\n")
            f.write(f"   {p1}\n")
            f.write(f"   {p2}\n")

    print(f"\nDetailed report written to: {report_file}")


if __name__ == "__main__":
    main()
