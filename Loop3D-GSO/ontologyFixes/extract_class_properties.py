#!/usr/bin/env python3
"""
Extract all properties and associations allowed/required for a given OWL class
by traversing the class hierarchy and collecting restrictions.

This handles:
- rdfs:subClassOf restrictions
- owl:equivalentClass restrictions
- Nested restrictions (intersections, unions)
- Different restriction types (someValuesFrom, allValuesFrom, hasValue, cardinality)
"""

import os
import sys
from collections import defaultdict
from rdflib import Graph, Namespace, URIRef, BNode, RDF, RDFS, OWL, Literal


# Define namespaces
GSOG = Namespace("https://w3id.org/gso/1.0/geology/")
GSOC = Namespace("https://w3id.org/gso/1.0/common/")
GSRM = Namespace("https://w3id.org/gso/1.0/rockmaterial/")
GSGM = Namespace("https://w3id.org/gso/1.0/granularmaterial/")
GSMIN = Namespace("https://w3id.org/gso/1.0/mineral/")
GSOR = Namespace("https://w3id.org/gso/1.0/geologicrole/")
GSOQ = Namespace("https://w3id.org/gso/1.0/quality/")


class OWLPropertyExtractor:
    """Extracts all properties/restrictions for a given OWL class"""

    def __init__(self):
        self.graph = Graph()
        self.restrictions = []  # List of (source_class, restriction_type, property, filler, nested_restrictions)
        self.property_info = {}  # Cache of property domain/range info

    def load_ontology(self, base_path):
        """Load relevant GSO ontology files"""
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
        """Get rdfs:label for a URI, or extract local name"""
        if isinstance(uri, BNode):
            return f"_:blank"
        if isinstance(uri, Literal):
            return str(uri)
        for label in self.graph.objects(uri, RDFS.label):
            return str(label)
        # Fallback to local name
        s = str(uri)
        if "#" in s:
            return s.split("#")[-1]
        return s.split("/")[-1]

    def get_property_info(self, prop_uri):
        """Get domain, range, and other info for a property"""
        if prop_uri in self.property_info:
            return self.property_info[prop_uri]

        info = {
            'uri': prop_uri,
            'label': self.get_label(prop_uri),
            'domains': [],
            'ranges': [],
            'type': None,
            'super_properties': [],
            'characteristics': []
        }

        # Get property type
        if (prop_uri, RDF.type, OWL.ObjectProperty) in self.graph:
            info['type'] = 'ObjectProperty'
        elif (prop_uri, RDF.type, OWL.DatatypeProperty) in self.graph:
            info['type'] = 'DatatypeProperty'
        elif (prop_uri, RDF.type, OWL.AnnotationProperty) in self.graph:
            info['type'] = 'AnnotationProperty'

        # Get domains
        for domain in self.graph.objects(prop_uri, RDFS.domain):
            if isinstance(domain, URIRef):
                info['domains'].append(self.get_label(domain))
            elif isinstance(domain, BNode):
                # Complex domain (union/intersection)
                info['domains'].append(self._format_class_expression(domain))

        # Get ranges
        for range_val in self.graph.objects(prop_uri, RDFS.range):
            if isinstance(range_val, URIRef):
                info['ranges'].append(self.get_label(range_val))
            elif isinstance(range_val, BNode):
                info['ranges'].append(self._format_class_expression(range_val))

        # Get super properties
        for super_prop in self.graph.objects(prop_uri, RDFS.subPropertyOf):
            if isinstance(super_prop, URIRef):
                info['super_properties'].append(self.get_label(super_prop))

        # Get property characteristics
        if (prop_uri, RDF.type, OWL.FunctionalProperty) in self.graph:
            info['characteristics'].append('Functional')
        if (prop_uri, RDF.type, OWL.InverseFunctionalProperty) in self.graph:
            info['characteristics'].append('InverseFunctional')
        if (prop_uri, RDF.type, OWL.TransitiveProperty) in self.graph:
            info['characteristics'].append('Transitive')
        if (prop_uri, RDF.type, OWL.SymmetricProperty) in self.graph:
            info['characteristics'].append('Symmetric')
        if (prop_uri, RDF.type, OWL.AsymmetricProperty) in self.graph:
            info['characteristics'].append('Asymmetric')
        if (prop_uri, RDF.type, OWL.ReflexiveProperty) in self.graph:
            info['characteristics'].append('Reflexive')
        if (prop_uri, RDF.type, OWL.IrreflexiveProperty) in self.graph:
            info['characteristics'].append('Irreflexive')

        # Get inverse property
        for inv in self.graph.objects(prop_uri, OWL.inverseOf):
            if isinstance(inv, URIRef):
                info['inverse'] = self.get_label(inv)

        self.property_info[prop_uri] = info
        return info

    def get_superclasses(self, class_uri, include_self=True):
        """Get transitive closure of superclasses for a given class"""
        superclasses = set()
        if include_self:
            superclasses.add(class_uri)

        visited = set()
        to_visit = [class_uri]

        while to_visit:
            current = to_visit.pop(0)
            if current in visited:
                continue
            visited.add(current)

            # Find direct superclasses (only named classes, not restrictions)
            for superclass in self.graph.objects(current, RDFS.subClassOf):
                if isinstance(superclass, URIRef):
                    superclasses.add(superclass)
                    if superclass not in visited:
                        to_visit.append(superclass)

            # Also check equivalent classes for named class equivalents
            for equiv in self.graph.objects(current, OWL.equivalentClass):
                if isinstance(equiv, URIRef):
                    superclasses.add(equiv)
                    if equiv not in visited:
                        to_visit.append(equiv)

        return superclasses

    def parse_restriction(self, node, depth=0):
        """
        Parse an OWL restriction or class expression.
        Returns a list of restriction dicts with structure:
        {
            'type': 'some' | 'only' | 'value' | 'min' | 'max' | 'exact',
            'property': URIRef,
            'filler': URIRef or nested structure,
            'nested': list of nested restrictions
        }
        """
        results = []

        if isinstance(node, URIRef):
            # Named class - no restrictions to extract here
            return results

        if not isinstance(node, BNode):
            return results

        # Check if this is a Restriction
        if (node, RDF.type, OWL.Restriction) in self.graph:
            restriction = self._parse_single_restriction(node, depth)
            if restriction:
                results.append(restriction)

        # Check for intersection (AND)
        intersection = list(self.graph.objects(node, OWL.intersectionOf))
        if intersection:
            members = self._parse_rdf_list(intersection[0])
            for member in members:
                results.extend(self.parse_restriction(member, depth + 1))

        # Check for union (OR)
        union = list(self.graph.objects(node, OWL.unionOf))
        if union:
            # For unions, we note them but still extract the restrictions
            members = self._parse_rdf_list(union[0])
            for member in members:
                nested = self.parse_restriction(member, depth + 1)
                for r in nested:
                    r['in_union'] = True
                results.extend(nested)

        return results

    def _extract_named_classes_from_expression(self, node, connector=None):
        """
        Extract all named classes from a complex class expression.
        Returns a dict with 'classes' list and 'connector' ('AND' or 'OR')
        """
        if isinstance(node, URIRef):
            return {'classes': [node], 'connector': None}

        if not isinstance(node, BNode):
            return {'classes': [], 'connector': None}

        # Check for intersection (AND)
        intersection = list(self.graph.objects(node, OWL.intersectionOf))
        if intersection:
            members = self._parse_rdf_list(intersection[0])
            all_classes = []
            for member in members:
                result = self._extract_named_classes_from_expression(member, 'AND')
                all_classes.extend(result['classes'])
            return {'classes': all_classes, 'connector': 'AND'}

        # Check for union (OR)
        union = list(self.graph.objects(node, OWL.unionOf))
        if union:
            members = self._parse_rdf_list(union[0])
            all_classes = []
            for member in members:
                result = self._extract_named_classes_from_expression(member, 'OR')
                all_classes.extend(result['classes'])
            return {'classes': all_classes, 'connector': 'OR'}

        return {'classes': [], 'connector': connector}

    def _format_class_expression(self, node):
        """Format a class expression with proper AND/OR connectors"""
        result = self._extract_named_classes_from_expression(node)
        classes = result['classes']
        connector = result['connector']

        if not classes:
            return "[complex]"

        labels = [self.get_label(c) for c in classes]
        if connector == 'OR':
            return " OR ".join(labels)
        else:
            return " AND ".join(labels)

    def _parse_single_restriction(self, node, depth=0):
        """Parse a single owl:Restriction node"""
        # Get the property
        on_property = list(self.graph.objects(node, OWL.onProperty))
        if not on_property:
            return None
        prop = on_property[0]

        restriction = {
            'property': prop,
            'property_label': self.get_label(prop),
            'nested': [],
            'depth': depth
        }

        # Check restriction type
        # someValuesFrom (existential - "some")
        some_values = list(self.graph.objects(node, OWL.someValuesFrom))
        if some_values:
            restriction['type'] = 'some'
            filler = some_values[0]
            restriction['filler'] = filler
            if isinstance(filler, URIRef):
                restriction['filler_label'] = self.get_label(filler)
            else:
                # Extract named classes from complex expression with proper connector
                restriction['filler_label'] = self._format_class_expression(filler)
            # Parse nested restrictions in the filler
            if isinstance(filler, BNode):
                restriction['nested'] = self.parse_restriction(filler, depth + 1)
            return restriction

        # allValuesFrom (universal - "only")
        all_values = list(self.graph.objects(node, OWL.allValuesFrom))
        if all_values:
            restriction['type'] = 'only'
            filler = all_values[0]
            restriction['filler'] = filler
            if isinstance(filler, URIRef):
                restriction['filler_label'] = self.get_label(filler)
            else:
                restriction['filler_label'] = self._format_class_expression(filler)
            if isinstance(filler, BNode):
                restriction['nested'] = self.parse_restriction(filler, depth + 1)
            return restriction

        # hasValue
        has_value = list(self.graph.objects(node, OWL.hasValue))
        if has_value:
            restriction['type'] = 'value'
            restriction['filler'] = has_value[0]
            restriction['filler_label'] = self.get_label(has_value[0])
            return restriction

        # Cardinality restrictions
        min_card = list(self.graph.objects(node, OWL.minCardinality))
        if min_card:
            restriction['type'] = 'min'
            restriction['cardinality'] = int(min_card[0])
            on_class = list(self.graph.objects(node, OWL.onClass))
            if on_class:
                restriction['filler'] = on_class[0]
                restriction['filler_label'] = self.get_label(on_class[0])
            return restriction

        max_card = list(self.graph.objects(node, OWL.maxCardinality))
        if max_card:
            restriction['type'] = 'max'
            restriction['cardinality'] = int(max_card[0])
            on_class = list(self.graph.objects(node, OWL.onClass))
            if on_class:
                restriction['filler'] = on_class[0]
                restriction['filler_label'] = self.get_label(on_class[0])
            return restriction

        exact_card = list(self.graph.objects(node, OWL.cardinality))
        if exact_card:
            restriction['type'] = 'exact'
            restriction['cardinality'] = int(exact_card[0])
            on_class = list(self.graph.objects(node, OWL.onClass))
            if on_class:
                restriction['filler'] = on_class[0]
                restriction['filler_label'] = self.get_label(on_class[0])
            return restriction

        # Qualified cardinality
        min_qcard = list(self.graph.objects(node, OWL.minQualifiedCardinality))
        if min_qcard:
            restriction['type'] = 'min'
            restriction['cardinality'] = int(min_qcard[0])
            on_class = list(self.graph.objects(node, OWL.onClass))
            if on_class:
                restriction['filler'] = on_class[0]
                restriction['filler_label'] = self.get_label(on_class[0])
            return restriction

        max_qcard = list(self.graph.objects(node, OWL.maxQualifiedCardinality))
        if max_qcard:
            restriction['type'] = 'max'
            restriction['cardinality'] = int(max_qcard[0])
            on_class = list(self.graph.objects(node, OWL.onClass))
            if on_class:
                restriction['filler'] = on_class[0]
                restriction['filler_label'] = self.get_label(on_class[0])
            return restriction

        return None

    def _parse_rdf_list(self, node):
        """Parse an RDF list (rdf:first/rdf:rest) into a Python list"""
        items = []
        current = node
        while current and current != RDF.nil:
            first = list(self.graph.objects(current, RDF.first))
            if first:
                items.append(first[0])
            rest = list(self.graph.objects(current, RDF.rest))
            current = rest[0] if rest else None
        return items

    def extract_class_restrictions(self, class_uri):
        """Extract all restrictions for a class from subClassOf and equivalentClass"""
        restrictions = []

        # Get restrictions from rdfs:subClassOf
        for superclass in self.graph.objects(class_uri, RDFS.subClassOf):
            if isinstance(superclass, BNode):
                parsed = self.parse_restriction(superclass)
                for r in parsed:
                    r['source'] = 'subClassOf'
                    r['from_class'] = class_uri
                    r['from_class_label'] = self.get_label(class_uri)
                restrictions.extend(parsed)

        # Get restrictions from owl:equivalentClass
        for equiv in self.graph.objects(class_uri, OWL.equivalentClass):
            if isinstance(equiv, BNode):
                parsed = self.parse_restriction(equiv)
                for r in parsed:
                    r['source'] = 'equivalentClass'
                    r['from_class'] = class_uri
                    r['from_class_label'] = self.get_label(class_uri)
                restrictions.extend(parsed)

        return restrictions

    def get_all_properties_for_class(self, target_class):
        """
        Get all properties allowed/required for a class by traversing
        the entire superclass hierarchy and collecting restrictions.
        """
        print(f"Analyzing class: {self.get_label(target_class)}")
        print(f"URI: {target_class}\n")

        # Get all superclasses
        superclasses = self.get_superclasses(target_class)
        print(f"Found {len(superclasses)} classes in hierarchy\n")

        # Collect all restrictions from all classes in hierarchy
        all_restrictions = []
        for cls in superclasses:
            restrictions = self.extract_class_restrictions(cls)
            all_restrictions.extend(restrictions)

        return superclasses, all_restrictions

    def restriction_to_manchester(self, r, depth=0):
        """Convert a restriction to Manchester syntax-like string"""
        rtype = r.get('type', '?')
        prop_label = r.get('property_label', '?')

        if rtype in ('some', 'only'):
            filler_label = r.get('filler_label', '')
            nested = r.get('nested', [])

            if filler_label and not nested:
                return f"{prop_label} {rtype} {filler_label}"
            elif filler_label and nested:
                # Has both named class and nested restrictions (intersection)
                nested_parts = [self.restriction_to_manchester(n, depth+1) for n in nested]
                nested_str = " AND ".join(f"({p})" for p in nested_parts if p)
                return f"{prop_label} {rtype} ({filler_label} AND {nested_str})"
            elif nested:
                # Only nested restrictions
                nested_parts = [self.restriction_to_manchester(n, depth+1) for n in nested]
                nested_str = " AND ".join(f"({p})" for p in nested_parts if p)
                return f"{prop_label} {rtype} ({nested_str})"
            else:
                return f"{prop_label} {rtype} [?]"
        elif rtype == 'value':
            return f"{prop_label} value {r.get('filler_label', '?')}"
        elif rtype in ('min', 'max', 'exact'):
            card = r.get('cardinality', '?')
            filler_label = r.get('filler_label', '')
            if filler_label:
                return f"{prop_label} {rtype} {card} {filler_label}"
            return f"{prop_label} {rtype} {card}"
        return f"{prop_label} [?]"

    def format_restriction(self, r, indent=0):
        """Format a single restriction for output"""
        prefix = "  " * indent

        # Build the restriction string
        rtype = r.get('type', '?')
        prop_label = r.get('property_label', str(r.get('property', '?')))

        if rtype in ('some', 'only'):
            filler_label = r.get('filler_label')
            if filler_label:
                line = f"{prefix}{prop_label} {rtype} {filler_label}"
            else:
                line = f"{prefix}{prop_label} {rtype} [complex expression]"
        elif rtype == 'value':
            line = f"{prefix}{prop_label} value {r.get('filler_label', '?')}"
        elif rtype in ('min', 'max', 'exact'):
            card = r.get('cardinality', '?')
            filler_label = r.get('filler_label', '')
            if filler_label:
                line = f"{prefix}{prop_label} {rtype} {card} {filler_label}"
            else:
                line = f"{prefix}{prop_label} {rtype} {card}"
        else:
            line = f"{prefix}{prop_label} [unknown restriction type]"

        # Add source info
        if r.get('in_union'):
            line += " [in union]"

        return line

    def format_nested_restrictions(self, restrictions, indent=0):
        """Recursively format restrictions including nested ones"""
        lines = []
        for r in restrictions:
            lines.append(self.format_restriction(r, indent))
            if r.get('nested'):
                lines.extend(self.format_nested_restrictions(r['nested'], indent + 1))
        return lines

    def write_report(self, target_class, output_path):
        """Generate a text report of all properties for a class"""
        superclasses, restrictions = self.get_all_properties_for_class(target_class)

        with open(output_path, 'w', encoding='utf-8') as f:
            # Header
            f.write("=" * 80 + "\n")
            f.write(f"OWL Class Property Report\n")
            f.write("=" * 80 + "\n\n")

            f.write(f"Target Class: {self.get_label(target_class)}\n")
            f.write(f"URI: {target_class}\n\n")

            # List superclass hierarchy
            f.write("-" * 40 + "\n")
            f.write("Superclass Hierarchy:\n")
            f.write("-" * 40 + "\n")
            for cls in sorted(superclasses, key=lambda x: self.get_label(x)):
                f.write(f"  {self.get_label(cls)}\n")
            f.write(f"\nTotal: {len(superclasses)} classes\n\n")

            # Group restrictions by property
            by_property = defaultdict(list)
            for r in restrictions:
                prop = r.get('property_label', str(r.get('property')))
                by_property[prop].append(r)

            # Write restrictions grouped by property
            f.write("-" * 40 + "\n")
            f.write("Properties and Restrictions:\n")
            f.write("-" * 40 + "\n\n")

            for prop in sorted(by_property.keys()):
                f.write(f"PROPERTY: {prop}\n")
                prop_restrictions = by_property[prop]

                # Get property definition info (domain/range)
                if prop_restrictions:
                    prop_uri = prop_restrictions[0].get('property')
                    if prop_uri:
                        prop_info = self.get_property_info(prop_uri)
                        if prop_info['type']:
                            f.write(f"  Type: {prop_info['type']}\n")
                        if prop_info['domains']:
                            f.write(f"  Domain: {', '.join(prop_info['domains'])}\n")
                        if prop_info['ranges']:
                            f.write(f"  Range: {', '.join(prop_info['ranges'])}\n")
                        if prop_info['characteristics']:
                            f.write(f"  Characteristics: {', '.join(prop_info['characteristics'])}\n")
                        if prop_info.get('inverse'):
                            f.write(f"  Inverse: {prop_info['inverse']}\n")
                        if prop_info['super_properties']:
                            f.write(f"  SubPropertyOf: {', '.join(prop_info['super_properties'])}\n")

                f.write("  Restrictions:\n")
                for r in prop_restrictions:
                    from_class = r.get('from_class_label', '?')
                    source = r.get('source', '?')
                    rtype = r.get('type', '?')

                    # Format the restriction
                    if rtype in ('some', 'only'):
                        filler = r.get('filler_label', '[complex]')
                        f.write(f"    [{source} from {from_class}]\n")
                        f.write(f"      {rtype} {filler}\n")
                    elif rtype == 'value':
                        f.write(f"    [{source} from {from_class}]\n")
                        f.write(f"      value {r.get('filler_label', '?')}\n")
                    elif rtype in ('min', 'max', 'exact'):
                        card = r.get('cardinality', '?')
                        filler = r.get('filler_label', '')
                        f.write(f"    [{source} from {from_class}]\n")
                        f.write(f"      {rtype} {card} {filler}\n")

                    # Handle nested restrictions - show Manchester syntax
                    if r.get('nested'):
                        manchester = self.restriction_to_manchester(r)
                        f.write(f"      Full expression: {manchester}\n")

                f.write("\n")

            # Summary
            f.write("-" * 40 + "\n")
            f.write("Summary:\n")
            f.write("-" * 40 + "\n")
            f.write(f"Total restrictions found: {len(restrictions)}\n")
            f.write(f"Unique properties: {len(by_property)}\n")

            # Count by type
            by_type = defaultdict(int)
            for r in restrictions:
                by_type[r.get('type', 'unknown')] += 1
            f.write("\nBy restriction type:\n")
            for rtype, count in sorted(by_type.items()):
                f.write(f"  {rtype}: {count}\n")

        print(f"\nReport written to: {output_path}")
        return restrictions


def main():
    """Main entry point"""
    # Get the directory of this script
    script_dir = os.path.dirname(os.path.abspath(__file__))

    # Default target class
    target_class = GSRM["Rock"]

    # Allow command line override
    if len(sys.argv) > 1:
        arg = sys.argv[1]
        # Handle common prefixes
        prefix_map = {
            'gsrm:': str(GSRM),
            'gsog:': str(GSOG),
            'gsoc:': str(GSOC),
            'gsgm:': str(GSGM),
            'gsmin:': str(GSMIN),
        }
        for prefix, ns in prefix_map.items():
            if arg.lower().startswith(prefix):
                target_class = URIRef(ns + arg[len(prefix):])
                break
        else:
            # Assume it's a full URI or local name
            if arg.startswith('http'):
                target_class = URIRef(arg)
            else:
                # Try to find it in rockmaterial namespace
                target_class = GSRM[arg]

    # Initialize extractor
    extractor = OWLPropertyExtractor()

    # Load ontology
    extractor.load_ontology(script_dir)

    # Generate report
    class_name = extractor.get_label(target_class)
    output_path = os.path.join(script_dir, f"{class_name}_properties.txt")
    extractor.write_report(target_class, output_path)


if __name__ == "__main__":
    main()
