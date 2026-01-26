#!/usr/bin/env python3
"""
Remove redundant restrictions from GSO ontology files.

This script:
1. Creates backup files (.ttl.bak) before modifying
2. Removes rdfs:subClassOf restrictions that are already in owl:equivalentClass
3. Preserves all other content

Note: rdflib re-serialization will change formatting but preserve semantics.
"""

import os
import shutil
from collections import defaultdict
from rdflib import Graph, Namespace, URIRef, BNode, Literal, RDF, RDFS, OWL


# Define namespaces
GSOG = Namespace("https://w3id.org/gso/1.0/geology/")
GSOC = Namespace("https://w3id.org/gso/1.0/common/")
GSRM = Namespace("https://w3id.org/gso/1.0/rockmaterial/")
GSGM = Namespace("https://w3id.org/gso/1.0/granularmaterial/")
GSMIN = Namespace("https://w3id.org/gso/1.0/mineral/")
GSGU = Namespace("https://w3id.org/gso/1.0/geologicunit/")


class RedundancyRemover:
    """Removes redundant restrictions from ontology files"""

    def __init__(self, base_path):
        self.base_path = base_path
        self.files_to_process = [
            "GSO-Common.ttl",
            "GSO-Geology.ttl",
            "Modules/GSO-Geologic_Unit.ttl",
        ]

    def get_label(self, graph, uri):
        """Get rdfs:label for a URI"""
        if isinstance(uri, BNode):
            return "_:blank"
        if isinstance(uri, Literal):
            return str(uri)
        for label in graph.objects(uri, RDFS.label):
            return str(label)
        s = str(uri)
        if "#" in s:
            return s.split("#")[-1]
        return s.split("/")[-1]

    def serialize_node(self, graph, node, depth=0, max_depth=10):
        """Serialize a node to a canonical string for comparison"""
        if depth > max_depth:
            return "[max depth]"

        if isinstance(node, URIRef):
            return f"<{str(node)}>"

        if isinstance(node, Literal):
            return f'"{str(node)}"'

        if isinstance(node, BNode):
            props = []
            for pred, obj in graph.predicate_objects(node):
                pred_str = f"<{str(pred)}>"
                obj_str = self.serialize_node(graph, obj, depth + 1, max_depth)
                props.append((pred_str, obj_str))
            props.sort()
            return "[" + ", ".join(f"{p}: {o}" for p, o in props) + "]"

        return str(node)

    def parse_rdf_list(self, graph, node):
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

    def extract_nested_restrictions(self, graph, node):
        """Extract restrictions nested within intersections/unions"""
        restrictions = []

        if not isinstance(node, BNode):
            return restrictions

        # Check for intersection
        for intersection in graph.objects(node, OWL.intersectionOf):
            members = self.parse_rdf_list(graph, intersection)
            for member in members:
                if isinstance(member, BNode):
                    if (member, RDF.type, OWL.Restriction) in graph:
                        serialized = self.serialize_node(graph, member)
                        restrictions.append({
                            'node': member,
                            'serialized': serialized
                        })
                    restrictions.extend(self.extract_nested_restrictions(graph, member))

        # Check for union
        for union in graph.objects(node, OWL.unionOf):
            members = self.parse_rdf_list(graph, union)
            for member in members:
                if isinstance(member, BNode):
                    if (member, RDF.type, OWL.Restriction) in graph:
                        serialized = self.serialize_node(graph, member)
                        restrictions.append({
                            'node': member,
                            'serialized': serialized
                        })
                    restrictions.extend(self.extract_nested_restrictions(graph, member))

        return restrictions

    def get_all_bnode_triples(self, graph, bnode):
        """Get all triples involving a BNode and its nested BNodes (for removal)"""
        triples = set()
        to_process = [bnode]
        processed = set()

        while to_process:
            current = to_process.pop()
            if current in processed:
                continue
            processed.add(current)

            # Get all triples where this BNode is subject
            for pred, obj in graph.predicate_objects(current):
                triples.add((current, pred, obj))
                if isinstance(obj, BNode):
                    to_process.append(obj)

            # Handle RDF lists
            if (current, RDF.first, None) in graph or (current, RDF.rest, None) in graph:
                for first in graph.objects(current, RDF.first):
                    triples.add((current, RDF.first, first))
                    if isinstance(first, BNode):
                        to_process.append(first)
                for rest in graph.objects(current, RDF.rest):
                    triples.add((current, RDF.rest, rest))
                    if isinstance(rest, BNode) and rest != RDF.nil:
                        to_process.append(rest)

        return triples

    def find_redundant_in_file(self, filepath):
        """Find redundant restrictions in a single file"""
        graph = Graph()
        graph.parse(filepath, format="turtle")

        redundant = []

        # Get all OWL classes in this file
        for class_uri in graph.subjects(RDF.type, OWL.Class):
            if not isinstance(class_uri, URIRef):
                continue

            # Get subClassOf restrictions (BNodes only)
            subclass_restrictions = []
            for superclass in graph.objects(class_uri, RDFS.subClassOf):
                if isinstance(superclass, BNode):
                    serialized = self.serialize_node(graph, superclass)
                    subclass_restrictions.append({
                        'node': superclass,
                        'serialized': serialized
                    })

            if not subclass_restrictions:
                continue

            # Get equivalentClass restrictions and nested ones
            equiv_serialized = set()
            for equiv in graph.objects(class_uri, OWL.equivalentClass):
                if isinstance(equiv, BNode):
                    equiv_serialized.add(self.serialize_node(graph, equiv))
                    for nested in self.extract_nested_restrictions(graph, equiv):
                        equiv_serialized.add(nested['serialized'])

            if not equiv_serialized:
                continue

            # Find matches
            for sub_r in subclass_restrictions:
                if sub_r['serialized'] in equiv_serialized:
                    redundant.append({
                        'class': class_uri,
                        'label': self.get_label(graph, class_uri),
                        'bnode': sub_r['node'],
                        'serialized': sub_r['serialized']
                    })

        return graph, redundant

    def remove_redundant_from_graph(self, graph, redundant_list):
        """Remove redundant restrictions from graph"""
        removed_count = 0

        for item in redundant_list:
            class_uri = item['class']
            bnode = item['bnode']

            # Remove the subClassOf triple
            graph.remove((class_uri, RDFS.subClassOf, bnode))

            # Remove all triples involving this BNode and nested BNodes
            bnode_triples = self.get_all_bnode_triples(graph, bnode)
            for triple in bnode_triples:
                graph.remove(triple)

            removed_count += 1
            print(f"  Removed redundant restriction from {item['label']}")

        return removed_count

    def process_file(self, filename):
        """Process a single file: backup, find redundant, remove, save"""
        filepath = os.path.join(self.base_path, filename)

        if not os.path.exists(filepath):
            print(f"  File not found: {filename}")
            return 0

        print(f"\nProcessing {filename}...")

        # Find redundant restrictions
        graph, redundant = self.find_redundant_in_file(filepath)

        if not redundant:
            print(f"  No redundant restrictions found")
            return 0

        print(f"  Found {len(redundant)} redundant restriction(s)")

        # Create backup
        backup_path = filepath + ".bak"
        shutil.copy2(filepath, backup_path)
        print(f"  Created backup: {filename}.bak")

        # Remove redundant restrictions
        removed = self.remove_redundant_from_graph(graph, redundant)

        # Bind namespaces for nice output
        graph.bind("gsoc", GSOC)
        graph.bind("gsog", GSOG)
        graph.bind("gsrm", GSRM)
        graph.bind("gsgm", GSGM)
        graph.bind("gsmin", GSMIN)
        graph.bind("gsgu", GSGU)
        graph.bind("owl", OWL)
        graph.bind("rdf", RDF)
        graph.bind("rdfs", RDFS)
        graph.bind("xsd", Namespace("http://www.w3.org/2001/XMLSchema#"))
        graph.bind("skos", Namespace("http://www.w3.org/2004/02/skos/core#"))
        graph.bind("dcterms", Namespace("http://purl.org/dc/terms/"))
        graph.bind("schema", Namespace("http://schema.org/"))

        # Save modified graph
        graph.serialize(destination=filepath, format="turtle")
        print(f"  Saved modified file: {filename}")

        return removed

    def run(self):
        """Run the removal process on all files"""
        print("=" * 60)
        print("REMOVING REDUNDANT RESTRICTIONS")
        print("=" * 60)

        total_removed = 0

        for filename in self.files_to_process:
            removed = self.process_file(filename)
            total_removed += removed

        print("\n" + "=" * 60)
        print(f"COMPLETE: Removed {total_removed} redundant restrictions")
        print("=" * 60)
        print("\nBackup files created with .bak extension")
        print("To restore: rename .ttl.bak files back to .ttl")

        return total_removed


def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))

    remover = RedundancyRemover(script_dir)
    remover.run()


if __name__ == "__main__":
    main()
