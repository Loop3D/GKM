#!/usr/bin/env python3
"""Semantic 3-way merge for OWL/RDF Turtle files using rdflib.

Loads the merge base, ours (LogicReview), and theirs (master) as RDF graphs,
computes triple-level additions and removals from each branch, and combines
them. Conflicts (same triple modified differently by both) are reported.

Uses master's serialization format as the base, since master preserves
the original hand-written Turtle formatting.
"""

import sys
from rdflib import Graph, Namespace, URIRef, Literal, BNode
from rdflib.compare import to_isomorphic, graph_diff


def load_graph(path):
    g = Graph()
    g.parse(path, format='turtle')
    return g


def get_non_bnode_triples(g):
    """Get all triples that don't involve blank nodes."""
    return set((s, p, o) for s, p, o in g if
               not isinstance(s, BNode) and not isinstance(o, BNode))


def main():
    base_path = sys.argv[1]
    ours_path = sys.argv[2]
    master_path = sys.argv[3]
    output_path = sys.argv[4] if len(sys.argv) > 4 else None

    print(f"Loading base: {base_path}")
    base = load_graph(base_path)
    print(f"  {len(base)} triples")

    print(f"Loading ours (LogicReview): {ours_path}")
    ours = load_graph(ours_path)
    print(f"  {len(ours)} triples")

    print(f"Loading master: {master_path}")
    master = load_graph(master_path)
    print(f"  {len(master)} triples")

    # Get non-bnode triples for comparison
    base_triples = get_non_bnode_triples(base)
    ours_triples = get_non_bnode_triples(ours)
    master_triples = get_non_bnode_triples(master)

    # Compute changes
    ours_added = ours_triples - base_triples
    ours_removed = base_triples - ours_triples
    master_added = master_triples - base_triples
    master_removed = base_triples - master_triples

    print(f"\nLogicReview changes (non-bnode):")
    print(f"  Added: {len(ours_added)}")
    print(f"  Removed: {len(ours_removed)}")
    print(f"\nMaster changes (non-bnode):")
    print(f"  Added: {len(master_added)}")
    print(f"  Removed: {len(master_removed)}")

    # Check for conflicts: same triple added by one and removed by the other
    conflicts_add_remove = ours_added & master_removed
    conflicts_remove_add = ours_removed & master_added

    if conflicts_add_remove:
        print(f"\n*** CONFLICT: {len(conflicts_add_remove)} triples added by ours but removed by master:")
        for s, p, o in sorted(conflicts_add_remove, key=str):
            print(f"  {s} {p} {o}")

    if conflicts_remove_add:
        print(f"\n*** CONFLICT: {len(conflicts_remove_add)} triples removed by ours but added by master:")
        for s, p, o in sorted(conflicts_remove_add, key=str):
            print(f"  {s} {p} {o}")

    # For the merge result, start with master (preserves formatting),
    # then apply ours_added and ours_removed
    # But we need to handle blank nodes separately since they can't be compared by identity

    # Strategy: Start from master's graph, apply LogicReview's non-bnode changes
    result = Graph()
    # Copy all master triples
    for s, p, o in master:
        result.add((s, p, o))
    # Copy master's namespace bindings
    for prefix, ns in master.namespaces():
        result.bind(prefix, ns)

    # Apply LogicReview additions (that aren't already in master)
    added_count = 0
    for s, p, o in ours_added:
        if (s, p, o) not in master_triples:
            result.add((s, p, o))
            added_count += 1

    # Apply LogicReview removals (that master didn't also remove)
    removed_count = 0
    for s, p, o in ours_removed:
        if (s, p, o) not in master_removed:
            result.remove((s, p, o))
            removed_count += 1

    print(f"\nMerge result:")
    print(f"  Started with master: {len(master)} triples")
    print(f"  Applied {added_count} additions from LogicReview")
    print(f"  Applied {removed_count} removals from LogicReview")
    print(f"  Result: {len(result)} triples")

    # Now handle blank node changes
    # LogicReview made changes involving blank nodes (e.g., Physical_Quality isQualityOf expansion)
    # We need to identify these by examining the bnode-containing triples
    # For now, report bnode-related differences

    # Get bnode triples
    def get_bnode_subjects(g):
        return set(s for s in g.subjects() if isinstance(s, BNode))

    # Count bnode triples per version
    base_bnode_count = sum(1 for s, p, o in base if isinstance(s, BNode) or isinstance(o, BNode))
    ours_bnode_count = sum(1 for s, p, o in ours if isinstance(s, BNode) or isinstance(o, BNode))
    master_bnode_count = sum(1 for s, p, o in master if isinstance(s, BNode) or isinstance(o, BNode))

    print(f"\nBlank node triples:")
    print(f"  Base: {base_bnode_count}")
    print(f"  Ours: {ours_bnode_count}")
    print(f"  Master: {master_bnode_count}")
    print(f"  Result (from master): {master_bnode_count}")
    print(f"\nNote: Blank node changes from LogicReview (restrictions, equivalentClass")
    print(f"removals, etc.) must be verified manually or via reasoner testing.")

    if output_path:
        print(f"\nSerializing to: {output_path}")
        result.serialize(destination=output_path, format='turtle')
        print("Done.")
    else:
        print("\nNo output path specified, dry run only.")


if __name__ == "__main__":
    main()
