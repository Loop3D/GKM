#!/usr/bin/env python3
"""
Analyze ontology for potential sources of inconsistency.

Common causes:
1. Disjoint classes with overlapping definitions
2. Unsatisfiable classes (contradictory restrictions)
3. Property domain/range conflicts
4. Individual membership in disjoint classes
"""

import os
from rdflib import Graph, Namespace, URIRef, BNode, RDF, RDFS, OWL


GSOC = Namespace("https://w3id.org/gso/1.0/common/")


def get_label(graph, uri):
    """Get rdfs:label for a URI"""
    if isinstance(uri, BNode):
        return "_:blank"
    if isinstance(uri, URIRef):
        for label in graph.objects(uri, RDFS.label):
            return str(label)
        s = str(uri)
        if "#" in s:
            return s.split("#")[-1]
        return s.split("/")[-1]
    return str(uri)


def find_disjoint_classes(graph):
    """Find all disjoint class declarations"""
    disjoint_pairs = []

    # owl:disjointWith
    for c1, c2 in graph.subject_objects(OWL.disjointWith):
        if isinstance(c1, URIRef) and isinstance(c2, URIRef):
            disjoint_pairs.append((c1, c2))

    # owl:AllDisjointClasses
    for disjoint_node in graph.subjects(RDF.type, OWL.AllDisjointClasses):
        members_list = list(graph.objects(disjoint_node, OWL.members))
        if members_list:
            members = parse_rdf_list(graph, members_list[0])
            for i, m1 in enumerate(members):
                for m2 in members[i+1:]:
                    if isinstance(m1, URIRef) and isinstance(m2, URIRef):
                        disjoint_pairs.append((m1, m2))

    return disjoint_pairs


def parse_rdf_list(graph, node):
    """Parse an RDF list"""
    items = []
    current = node
    while current and current != RDF.nil:
        first = list(graph.objects(current, RDF.first))
        if first:
            items.append(first[0])
        rest = list(graph.objects(current, RDF.rest))
        current = rest[0] if rest else None
    return items


def find_equivalent_class_issues(graph):
    """Find classes with potentially contradictory equivalentClass definitions"""
    issues = []

    for cls in graph.subjects(RDF.type, OWL.Class):
        if not isinstance(cls, URIRef):
            continue

        equiv_classes = list(graph.objects(cls, OWL.equivalentClass))
        if len(equiv_classes) > 1:
            issues.append({
                'class': cls,
                'label': get_label(graph, cls),
                'issue': f'Multiple equivalentClass definitions ({len(equiv_classes)})',
                'details': equiv_classes
            })

    return issues


def find_nothing_subclasses(graph):
    """Find classes that are subclasses of owl:Nothing (unsatisfiable)"""
    unsatisfiable = []

    for cls in graph.subjects(RDFS.subClassOf, OWL.Nothing):
        if isinstance(cls, URIRef):
            unsatisfiable.append(cls)

    return unsatisfiable


def find_complement_issues(graph):
    """Find classes defined as both X and complementOf X"""
    issues = []

    for cls in graph.subjects(RDF.type, OWL.Class):
        if not isinstance(cls, URIRef):
            continue

        # Get all superclasses and equivalent classes
        supers = set(graph.objects(cls, RDFS.subClassOf))
        equivs = set(graph.objects(cls, OWL.equivalentClass))
        all_related = supers | equivs

        # Check for complement conflicts
        for related in all_related:
            if isinstance(related, BNode):
                complement = list(graph.objects(related, OWL.complementOf))
                if complement:
                    comp_class = complement[0]
                    # Check if cls is also related to comp_class
                    if comp_class in all_related:
                        issues.append({
                            'class': cls,
                            'label': get_label(graph, cls),
                            'issue': f'Related to both a class and its complement',
                            'complement_of': get_label(graph, comp_class)
                        })

    return issues


def find_domain_range_conflicts(graph):
    """Find potential domain/range conflicts"""
    issues = []

    for prop in graph.subjects(RDF.type, OWL.ObjectProperty):
        if not isinstance(prop, URIRef):
            continue

        domains = list(graph.objects(prop, RDFS.domain))
        ranges = list(graph.objects(prop, RDFS.range))

        # Check if domain and range are disjoint
        for d in domains:
            for r in ranges:
                if isinstance(d, URIRef) and isinstance(r, URIRef):
                    if (d, OWL.disjointWith, r) in graph or (r, OWL.disjointWith, d) in graph:
                        issues.append({
                            'property': prop,
                            'label': get_label(graph, prop),
                            'issue': 'Domain and range are disjoint classes',
                            'domain': get_label(graph, d),
                            'range': get_label(graph, r)
                        })

    return issues


def find_intersection_with_complement(graph):
    """Find intersections that include a class and its complement"""
    issues = []

    for intersection_list in graph.objects(None, OWL.intersectionOf):
        members = parse_rdf_list(graph, intersection_list)

        # Look for complement patterns
        named_classes = set()
        complement_of = set()

        for m in members:
            if isinstance(m, URIRef):
                named_classes.add(m)
            elif isinstance(m, BNode):
                comp = list(graph.objects(m, OWL.complementOf))
                if comp and isinstance(comp[0], URIRef):
                    complement_of.add(comp[0])

        # Check for conflicts
        conflict = named_classes & complement_of
        if conflict:
            issues.append({
                'issue': 'Intersection contains class and its complement',
                'conflicting_classes': [get_label(graph, c) for c in conflict]
            })

    return issues


def analyze_recent_changes(graph):
    """Look for issues related to recent changes (someValuesFrom conversions)"""
    issues = []

    # Find restrictions that might have been converted
    for restriction in graph.subjects(RDF.type, OWL.Restriction):
        some_values = list(graph.objects(restriction, OWL.someValuesFrom))
        on_prop = list(graph.objects(restriction, OWL.onProperty))

        if some_values and on_prop:
            prop = on_prop[0]
            filler = some_values[0]

            # Check if filler is owl:Nothing or unsatisfiable
            if filler == OWL.Nothing:
                issues.append({
                    'issue': 'someValuesFrom owl:Nothing (unsatisfiable)',
                    'property': get_label(graph, prop)
                })

    return issues


def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    filepath = os.path.join(script_dir, "GSO-Common.ttl")

    print("=" * 70)
    print("INCONSISTENCY ANALYSIS")
    print("=" * 70)

    print(f"\nLoading {filepath}...")
    graph = Graph()
    graph.parse(filepath, format="turtle")
    print(f"Loaded {len(graph)} triples")

    # Run analyses
    print("\n" + "-" * 70)
    print("1. Checking for classes subclassOf owl:Nothing...")
    unsatisfiable = find_nothing_subclasses(graph)
    if unsatisfiable:
        print(f"   FOUND {len(unsatisfiable)} unsatisfiable classes:")
        for cls in unsatisfiable:
            print(f"     - {get_label(graph, cls)}")
    else:
        print("   None found")

    print("\n" + "-" * 70)
    print("2. Checking for complement conflicts...")
    complement_issues = find_complement_issues(graph)
    if complement_issues:
        print(f"   FOUND {len(complement_issues)} potential issues:")
        for issue in complement_issues:
            print(f"     - {issue['label']}: {issue['issue']}")
    else:
        print("   None found")

    print("\n" + "-" * 70)
    print("3. Checking for intersection with complement...")
    intersection_issues = find_intersection_with_complement(graph)
    if intersection_issues:
        print(f"   FOUND {len(intersection_issues)} potential issues:")
        for issue in intersection_issues:
            print(f"     - {issue['issue']}: {issue['conflicting_classes']}")
    else:
        print("   None found")

    print("\n" + "-" * 70)
    print("4. Checking for domain/range conflicts...")
    dr_issues = find_domain_range_conflicts(graph)
    if dr_issues:
        print(f"   FOUND {len(dr_issues)} potential issues:")
        for issue in dr_issues:
            print(f"     - {issue['label']}: domain={issue['domain']}, range={issue['range']}")
    else:
        print("   None found")

    print("\n" + "-" * 70)
    print("5. Checking for multiple equivalentClass definitions...")
    equiv_issues = find_equivalent_class_issues(graph)
    if equiv_issues:
        print(f"   FOUND {len(equiv_issues)} classes with multiple equivalentClass:")
        for issue in equiv_issues[:10]:  # Limit output
            print(f"     - {issue['label']}: {issue['issue']}")
        if len(equiv_issues) > 10:
            print(f"     ... and {len(equiv_issues) - 10} more")
    else:
        print("   None found")

    print("\n" + "-" * 70)
    print("6. Checking disjoint class pairs...")
    disjoint_pairs = find_disjoint_classes(graph)
    print(f"   Found {len(disjoint_pairs)} disjoint class pairs")

    print("\n" + "-" * 70)
    print("7. Checking recent someValuesFrom conversions...")
    recent_issues = analyze_recent_changes(graph)
    if recent_issues:
        print(f"   FOUND {len(recent_issues)} potential issues:")
        for issue in recent_issues:
            print(f"     - {issue}")
    else:
        print("   None found")

    print("\n" + "=" * 70)
    print("ANALYSIS COMPLETE")
    print("=" * 70)
    print("\nIf no obvious issues found, the inconsistency may be due to")
    print("complex interactions between class definitions. Try using")
    print("Protege's 'Explain' feature on the inconsistency.")


if __name__ == "__main__":
    main()
