#!/usr/bin/env python3
"""
Find redundant restrictions in the GSO ontology where the same restriction
appears in both rdfs:subClassOf and owl:equivalentClass for a class.

This script identifies cases where rdfs:subClassOf assertions are logically
redundant because they're already implied by owl:equivalentClass.
"""

import os
from collections import defaultdict
from rdflib import Graph, Namespace, URIRef, BNode, Literal, RDF, RDFS, OWL


# Define namespaces
GSOG = Namespace("https://w3id.org/gso/1.0/geology/")
GSOC = Namespace("https://w3id.org/gso/1.0/common/")
GSRM = Namespace("https://w3id.org/gso/1.0/rockmaterial/")
GSGM = Namespace("https://w3id.org/gso/1.0/granularmaterial/")
GSMIN = Namespace("https://w3id.org/gso/1.0/mineral/")


class RestrictionAnalyzer:
    """Analyzes OWL restrictions for redundancy"""

    def __init__(self):
        self.graph = Graph()

    def load_ontology(self, base_path):
        """Load GSO ontology files"""
        print("Loading ontology files...")

        files_to_load = [
            "GSO-Common.ttl",
            "GSO-Geology.ttl",
            "Modules/GSO-Geologic_Rock_Material.ttl",
            "Modules/GSO-Geologic_Granular_Material.ttl",
            "Modules/GSO-Geologic_Mineral.ttl",
            "Modules/GSO-Geologic_Quality.ttl",
            "Modules/GSO-Geologic_Role.ttl",
            "Modules/GSO-Geologic_Structure.ttl",
            "Modules/GSO-Geologic_Unit.ttl",
            "Modules/GSO-Geologic_Feature.ttl",
            "Modules/GSO-Geologic_Time.ttl",
            "Modules/GSO-Geologic_Contact.ttl",
            "Modules/GSO-Geologic_Fault.ttl",
            "Modules/GSO-Geologic_Fold.ttl",
            "Modules/GSO-Geologic_Foliation.ttl",
            "Modules/GSO-Geologic_Lineation.ttl",
            "Modules/GSO-Geologic_Event.ttl",
            "Modules/GSO-Geologic_Process.ttl",
            "Modules/GSO-Geologic_Relation.ttl",
            "Modules/GSO-Geologic_Setting.ttl",
        ]

        for filename in files_to_load:
            filepath = os.path.join(base_path, filename)
            if os.path.exists(filepath):
                print(f"  Loading {filename}...")
                try:
                    self.graph.parse(filepath, format="turtle")
                except Exception as e:
                    print(f"  Warning: Could not load {filename}: {e}")

        print(f"Loaded {len(self.graph)} triples\n")

    def get_label(self, uri):
        """Get rdfs:label for a URI"""
        if isinstance(uri, BNode):
            return "_:blank"
        if isinstance(uri, Literal):
            return str(uri)
        for label in self.graph.objects(uri, RDFS.label):
            return str(label)
        s = str(uri)
        if "#" in s:
            return s.split("#")[-1]
        return s.split("/")[-1]

    def serialize_node(self, node, depth=0, max_depth=10):
        """
        Serialize a node (URI, BNode, or Literal) to a canonical string
        for comparison purposes.
        """
        if depth > max_depth:
            return "[max depth]"

        if isinstance(node, URIRef):
            return f"<{str(node)}>"

        if isinstance(node, Literal):
            return f'"{str(node)}"'

        if isinstance(node, BNode):
            # Serialize the BNode by its properties
            props = []

            # Get all properties of this BNode
            for pred, obj in self.graph.predicate_objects(node):
                pred_str = f"<{str(pred)}>"
                obj_str = self.serialize_node(obj, depth + 1, max_depth)
                props.append((pred_str, obj_str))

            # Sort for canonical form
            props.sort()
            return "[" + ", ".join(f"{p}: {o}" for p, o in props) + "]"

        return str(node)

    def get_restrictions_from_subclassof(self, class_uri):
        """Get all restriction BNodes from rdfs:subClassOf"""
        restrictions = []
        for superclass in self.graph.objects(class_uri, RDFS.subClassOf):
            if isinstance(superclass, BNode):
                # Check if it's a restriction or class expression
                serialized = self.serialize_node(superclass)
                restrictions.append({
                    'node': superclass,
                    'serialized': serialized,
                    'source': 'subClassOf'
                })
        return restrictions

    def get_restrictions_from_equivalentclass(self, class_uri):
        """Get all restriction BNodes from owl:equivalentClass, including nested ones"""
        restrictions = []

        for equiv in self.graph.objects(class_uri, OWL.equivalentClass):
            if isinstance(equiv, BNode):
                # The equivalentClass itself
                serialized = self.serialize_node(equiv)
                restrictions.append({
                    'node': equiv,
                    'serialized': serialized,
                    'source': 'equivalentClass'
                })

                # Also extract restrictions from within intersections
                nested = self.extract_nested_restrictions(equiv)
                for n in nested:
                    restrictions.append({
                        'node': n['node'],
                        'serialized': n['serialized'],
                        'source': 'equivalentClass (nested)'
                    })

        return restrictions

    def extract_nested_restrictions(self, node):
        """Extract restrictions nested within intersections/unions"""
        restrictions = []

        if not isinstance(node, BNode):
            return restrictions

        # Check for intersection
        for intersection in self.graph.objects(node, OWL.intersectionOf):
            members = self.parse_rdf_list(intersection)
            for member in members:
                if isinstance(member, BNode):
                    # Check if it's a restriction
                    if (member, RDF.type, OWL.Restriction) in self.graph:
                        serialized = self.serialize_node(member)
                        restrictions.append({
                            'node': member,
                            'serialized': serialized
                        })
                    # Recurse for nested structures
                    restrictions.extend(self.extract_nested_restrictions(member))

        # Check for union
        for union in self.graph.objects(node, OWL.unionOf):
            members = self.parse_rdf_list(union)
            for member in members:
                if isinstance(member, BNode):
                    if (member, RDF.type, OWL.Restriction) in self.graph:
                        serialized = self.serialize_node(member)
                        restrictions.append({
                            'node': member,
                            'serialized': serialized
                        })
                    restrictions.extend(self.extract_nested_restrictions(member))

        return restrictions

    def parse_rdf_list(self, node):
        """Parse an RDF list into a Python list"""
        items = []
        current = node
        while current and current != RDF.nil:
            first = list(self.graph.objects(current, RDF.first))
            if first:
                items.append(first[0])
            rest = list(self.graph.objects(current, RDF.rest))
            current = rest[0] if rest else None
        return items

    def describe_restriction(self, node):
        """Generate a human-readable description of a restriction"""
        if not isinstance(node, BNode):
            return self.get_label(node)

        # Check if it's a restriction
        if (node, RDF.type, OWL.Restriction) in self.graph:
            on_prop = list(self.graph.objects(node, OWL.onProperty))
            prop_name = self.get_label(on_prop[0]) if on_prop else "?"

            # someValuesFrom
            some = list(self.graph.objects(node, OWL.someValuesFrom))
            if some:
                filler = self.describe_restriction(some[0])
                return f"{prop_name} some {filler}"

            # allValuesFrom
            all_v = list(self.graph.objects(node, OWL.allValuesFrom))
            if all_v:
                filler = self.describe_restriction(all_v[0])
                return f"{prop_name} only {filler}"

            # hasValue
            has_v = list(self.graph.objects(node, OWL.hasValue))
            if has_v:
                return f"{prop_name} value {self.get_label(has_v[0])}"

            # cardinality
            for card_pred, card_name in [(OWL.minCardinality, 'min'),
                                          (OWL.maxCardinality, 'max'),
                                          (OWL.cardinality, 'exactly')]:
                card = list(self.graph.objects(node, card_pred))
                if card:
                    return f"{prop_name} {card_name} {card[0]}"

            return f"{prop_name} [restriction]"

        # Check for intersection
        intersection = list(self.graph.objects(node, OWL.intersectionOf))
        if intersection:
            members = self.parse_rdf_list(intersection[0])
            parts = [self.describe_restriction(m) for m in members[:3]]
            if len(members) > 3:
                parts.append("...")
            return "(" + " AND ".join(parts) + ")"

        # Check for union
        union = list(self.graph.objects(node, OWL.unionOf))
        if union:
            members = self.parse_rdf_list(union[0])
            parts = [self.describe_restriction(m) for m in members[:3]]
            if len(members) > 3:
                parts.append("...")
            return "(" + " OR ".join(parts) + ")"

        return "[complex]"

    def find_redundant_restrictions(self):
        """Find all classes with redundant restrictions"""
        print("Analyzing classes for redundant restrictions...\n")

        redundant_classes = []

        # Get all OWL classes
        all_classes = set()
        for s in self.graph.subjects(RDF.type, OWL.Class):
            if isinstance(s, URIRef):
                all_classes.add(s)

        print(f"Checking {len(all_classes)} classes...\n")

        for class_uri in sorted(all_classes, key=lambda x: self.get_label(x)):
            subclass_restrictions = self.get_restrictions_from_subclassof(class_uri)
            equiv_restrictions = self.get_restrictions_from_equivalentclass(class_uri)

            if not subclass_restrictions or not equiv_restrictions:
                continue

            # Find matches
            equiv_serialized = {r['serialized'] for r in equiv_restrictions}
            matches = []

            for sub_r in subclass_restrictions:
                if sub_r['serialized'] in equiv_serialized:
                    matches.append(sub_r)

            if matches:
                redundant_classes.append({
                    'class': class_uri,
                    'label': self.get_label(class_uri),
                    'redundant_count': len(matches),
                    'total_subclass': len(subclass_restrictions),
                    'total_equiv': len(equiv_restrictions),
                    'matches': matches
                })

        return redundant_classes

    def generate_report(self, output_path):
        """Generate a report of redundant restrictions"""
        redundant = self.find_redundant_restrictions()

        with open(output_path, 'w', encoding='utf-8') as f:
            f.write("=" * 80 + "\n")
            f.write("REDUNDANT RESTRICTIONS REPORT\n")
            f.write("=" * 80 + "\n\n")

            f.write("This report identifies classes where the same restriction appears in both\n")
            f.write("rdfs:subClassOf and owl:equivalentClass. The rdfs:subClassOf assertion is\n")
            f.write("logically redundant because owl:equivalentClass implies rdfs:subClassOf.\n\n")

            f.write("-" * 80 + "\n")
            f.write(f"SUMMARY: Found {len(redundant)} classes with redundant restrictions\n")
            f.write("-" * 80 + "\n\n")

            total_redundant = sum(r['redundant_count'] for r in redundant)
            f.write(f"Total redundant restriction assertions: {total_redundant}\n\n")

            # Group by namespace
            by_namespace = defaultdict(list)
            for r in redundant:
                uri = str(r['class'])
                if '/geology/' in uri:
                    ns = 'geology'
                elif '/rockmaterial/' in uri:
                    ns = 'rockmaterial'
                elif '/granularmaterial/' in uri:
                    ns = 'granularmaterial'
                elif '/common/' in uri:
                    ns = 'common'
                elif '/mineral/' in uri:
                    ns = 'mineral'
                else:
                    ns = 'other'
                by_namespace[ns].append(r)

            f.write("By namespace:\n")
            for ns, items in sorted(by_namespace.items()):
                f.write(f"  {ns}: {len(items)} classes\n")
            f.write("\n")

            f.write("=" * 80 + "\n")
            f.write("DETAILED FINDINGS\n")
            f.write("=" * 80 + "\n\n")

            for r in redundant:
                f.write(f"CLASS: {r['label']}\n")
                f.write(f"URI: {r['class']}\n")
                f.write(f"Redundant restrictions: {r['redundant_count']} of {r['total_subclass']} subClassOf restrictions\n")
                f.write("\nRedundant restriction(s):\n")

                for match in r['matches']:
                    desc = self.describe_restriction(match['node'])
                    f.write(f"  - {desc}\n")

                f.write("\n" + "-" * 40 + "\n\n")

            # Generate removal suggestions
            f.write("=" * 80 + "\n")
            f.write("SUGGESTED REMOVALS\n")
            f.write("=" * 80 + "\n\n")

            f.write("The following rdfs:subClassOf statements could be removed:\n\n")

            for r in redundant:
                f.write(f"# {r['label']}\n")
                for match in r['matches']:
                    desc = self.describe_restriction(match['node'])
                    f.write(f"#   Remove: rdfs:subClassOf [ {desc} ]\n")
                f.write("\n")

        print(f"Report written to: {output_path}")
        return redundant


def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))

    analyzer = RestrictionAnalyzer()
    analyzer.load_ontology(script_dir)

    output_path = os.path.join(script_dir, "redundant_restrictions_report.txt")
    redundant = analyzer.generate_report(output_path)

    print(f"\n{'='*60}")
    print(f"Found {len(redundant)} classes with redundant restrictions")
    print(f"Report saved to: {output_path}")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
