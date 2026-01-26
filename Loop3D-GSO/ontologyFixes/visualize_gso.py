#!/usr/bin/env python3
"""
GSO Ontology Visualizer - Generates interactive HTML visualization of the Geoscience Ontology
rooted at Solid_Geologic_Material class, with property details panel.

Requires: rdflib (pip install rdflib)
"""

import os
import json
from collections import defaultdict
from rdflib import Graph, Namespace, URIRef, BNode, Literal, RDFS, RDF, OWL

# Define namespaces
GSOG = Namespace("https://w3id.org/gso/1.0/geology/")
GSOC = Namespace("https://w3id.org/gso/1.0/common/")
GSRM = Namespace("https://w3id.org/gso/1.0/rockmaterial/")
GSGM = Namespace("https://w3id.org/gso/1.0/granularmaterial/")
GSMIN = Namespace("https://w3id.org/gso/1.0/mineral/")


class GSOVisualizer:
    """Visualizes GSO ontology as SVG"""

    def __init__(self):
        self.graph = Graph()
        self.classes = {}  # uri -> label (for initial hierarchy)
        self.subclass_relations = defaultdict(list)  # parent -> [children] (for initial hierarchy)
        self.all_classes = {}  # uri -> label (for entire ontology)
        self.all_subclass_relations = defaultdict(list)  # parent -> [children] (for entire ontology)
        self.object_properties = defaultdict(list)  # (domain, range) relationships

    def load_ontology(self, base_path):
        """Load the GSO ontology files"""
        print("Loading ontology files...")

        # Core files
        core_files = [
            "GSO-Common.ttl",
            "GSO-Geology.ttl",
        ]

        # All module files for complete ontology coverage
        module_files = [
            "Modules/GSO-Element.ttl",
            "Modules/GSO-Feature.ttl",
            "Modules/GSO-Geologic_Event.ttl",
            "Modules/GSO-Geologic_Feature.ttl",
            "Modules/GSO-Geologic_Granular_Material.ttl",
            "Modules/GSO-Geologic_Mineral.ttl",
            "Modules/GSO-Geologic_Process.ttl",
            "Modules/GSO-Geologic_Quality.ttl",
            "Modules/GSO-Geologic_Reference_System.ttl",
            "Modules/GSO-Geologic_Relation.ttl",
            "Modules/GSO-Geologic_Rock_Material.ttl",
            "Modules/GSO-Geologic_Rock_Object.ttl",
            "Modules/GSO-Geologic_Role.ttl",
            "Modules/GSO-Geologic_Setting.ttl",
            "Modules/GSO-Geologic_Structure.ttl",
            "Modules/GSO-Geologic_Structure_Contact.ttl",
            "Modules/GSO-Geologic_Structure_Fault.ttl",
            "Modules/GSO-Geologic_Structure_Fold.ttl",
            "Modules/GSO-Geologic_Structure_Foliation.ttl",
            "Modules/GSO-Geologic_Structure_Lineation.ttl",
            "Modules/GSO-Geologic_Time.ttl",
            "Modules/GSO-Geologic_Time_Ischart.ttl",
            "Modules/GSO-Geologic_Unit.ttl",
            "Modules/GSO-Hydrology.ttl",
            "Modules/GSO-Perdurant.ttl",
            "Modules/GSO-Quality.ttl",
            "Modules/GSO-skos_annotation.ttl",
        ]

        for filename in core_files + module_files:
            filepath = os.path.join(base_path, filename)
            if os.path.exists(filepath):
                print(f"  Loading {filename}...")
                try:
                    self.graph.parse(filepath, format="turtle")
                except Exception as e:
                    print(f"  Warning: Could not load {filename}: {e}")
            else:
                print(f"  Warning: File not found: {filepath}")

        print(f"Loaded {len(self.graph)} triples")

    def build_complete_relations(self):
        """Build complete subclass relations for the entire ontology"""
        print("\nBuilding complete subclass relations for all classes...")

        # Get all OWL classes
        all_classes = set()
        for s in self.graph.subjects(RDF.type, OWL.Class):
            if isinstance(s, URIRef):
                all_classes.add(s)

        # Also include classes that appear as subjects or objects of rdfs:subClassOf
        for s, o in self.graph.subject_objects(RDFS.subClassOf):
            if isinstance(s, URIRef):
                all_classes.add(s)
            if isinstance(o, URIRef):
                all_classes.add(o)

        # Build labels for all classes
        for cls in all_classes:
            label = self._get_label(cls)
            self.all_classes[cls] = label

        # Build complete parent -> children mapping
        for subclass in all_classes:
            for parent in self.graph.objects(subclass, RDFS.subClassOf):
                if isinstance(parent, URIRef):
                    self.all_subclass_relations[parent].append(subclass)

        print(f"Found {len(self.all_classes)} total classes in ontology")
        return all_classes

    def extract_hierarchy(self, root_uri):
        """Extract class hierarchy starting from root class"""
        print(f"\nExtracting hierarchy from {root_uri}...")

        # Get all subclasses recursively
        visited = set()
        to_visit = [root_uri]

        while to_visit:
            current = to_visit.pop(0)
            if current in visited:
                continue
            visited.add(current)

            # Get label for this class
            label = self._get_label(current)
            self.classes[current] = label

            # Find direct subclasses
            for subclass in self.graph.subjects(RDFS.subClassOf, current):
                if isinstance(subclass, URIRef):
                    # Check if it's a direct subclass (not a restriction)
                    self.subclass_relations[current].append(subclass)
                    if subclass not in visited:
                        to_visit.append(subclass)

        print(f"Found {len(self.classes)} classes in hierarchy")
        return visited

    def _get_label(self, uri):
        """Get rdfs:label for a URI"""
        for label in self.graph.objects(uri, RDFS.label):
            return str(label)
        # Fallback to local name
        return str(uri).split("/")[-1].split("#")[-1]

    def _get_local_name(self, uri):
        """Get local name from URI"""
        s = str(uri)
        if "#" in s:
            return s.split("#")[-1]
        return s.split("/")[-1]

    # ==================== Property Extraction Methods ====================

    def _parse_rdf_list(self, node):
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

    def _extract_classes_from_expression(self, node):
        """Extract named classes and connector type from a class expression"""
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
                result = self._extract_classes_from_expression(member)
                all_classes.extend(result['classes'])
            return {'classes': all_classes, 'connector': 'AND'}

        # Check for union (OR)
        union = list(self.graph.objects(node, OWL.unionOf))
        if union:
            members = self._parse_rdf_list(union[0])
            all_classes = []
            for member in members:
                result = self._extract_classes_from_expression(member)
                all_classes.extend(result['classes'])
            return {'classes': all_classes, 'connector': 'OR'}

        return {'classes': [], 'connector': None}

    def _format_class_expression(self, node):
        """Format a class expression with AND/OR connectors"""
        result = self._extract_classes_from_expression(node)
        classes = result['classes']
        connector = result['connector']
        if not classes:
            return None
        labels = [self._get_label(c) for c in classes]
        if connector == 'OR':
            return " OR ".join(labels)
        return " AND ".join(labels)

    def _parse_restriction(self, node):
        """Parse an OWL restriction and return structured data"""
        if not isinstance(node, BNode):
            return []

        results = []

        # Check if this is a Restriction
        if (node, RDF.type, OWL.Restriction) in self.graph:
            on_property = list(self.graph.objects(node, OWL.onProperty))
            if not on_property:
                return []
            prop = on_property[0]
            prop_label = self._get_label(prop)

            restriction = {'property': prop_label, 'property_uri': str(prop)}

            # someValuesFrom
            some_values = list(self.graph.objects(node, OWL.someValuesFrom))
            if some_values:
                filler = some_values[0]
                restriction['type'] = 'some'
                if isinstance(filler, URIRef):
                    restriction['filler'] = self._get_label(filler)
                else:
                    formatted = self._format_class_expression(filler)
                    restriction['filler'] = formatted if formatted else '[complex]'
                    # Get nested restrictions
                    nested = self._parse_restriction(filler)
                    if nested:
                        restriction['nested'] = nested
                results.append(restriction)
                return results

            # allValuesFrom
            all_values = list(self.graph.objects(node, OWL.allValuesFrom))
            if all_values:
                filler = all_values[0]
                restriction['type'] = 'only'
                if isinstance(filler, URIRef):
                    restriction['filler'] = self._get_label(filler)
                else:
                    formatted = self._format_class_expression(filler)
                    restriction['filler'] = formatted if formatted else '[complex]'
                    nested = self._parse_restriction(filler)
                    if nested:
                        restriction['nested'] = nested
                results.append(restriction)
                return results

            # hasValue
            has_value = list(self.graph.objects(node, OWL.hasValue))
            if has_value:
                restriction['type'] = 'value'
                restriction['filler'] = self._get_label(has_value[0])
                results.append(restriction)
                return results

            # Cardinality
            for card_type, card_name in [(OWL.minCardinality, 'min'),
                                          (OWL.maxCardinality, 'max'),
                                          (OWL.cardinality, 'exactly')]:
                card = list(self.graph.objects(node, card_type))
                if card:
                    restriction['type'] = card_name
                    restriction['cardinality'] = int(card[0])
                    on_class = list(self.graph.objects(node, OWL.onClass))
                    if on_class:
                        restriction['filler'] = self._get_label(on_class[0])
                    results.append(restriction)
                    return results

        # Check for intersection
        intersection = list(self.graph.objects(node, OWL.intersectionOf))
        if intersection:
            members = self._parse_rdf_list(intersection[0])
            for member in members:
                results.extend(self._parse_restriction(member))

        # Check for union
        union = list(self.graph.objects(node, OWL.unionOf))
        if union:
            members = self._parse_rdf_list(union[0])
            for member in members:
                nested = self._parse_restriction(member)
                for r in nested:
                    r['in_union'] = True
                results.extend(nested)

        return results

    def get_property_info(self, prop_uri):
        """Get domain, range, and characteristics for a property"""
        info = {
            'type': None,
            'domain': None,
            'range': None,
            'characteristics': [],
            'inverse': None
        }

        if (prop_uri, RDF.type, OWL.ObjectProperty) in self.graph:
            info['type'] = 'ObjectProperty'
        elif (prop_uri, RDF.type, OWL.DatatypeProperty) in self.graph:
            info['type'] = 'DatatypeProperty'

        # Domain
        for domain in self.graph.objects(prop_uri, RDFS.domain):
            if isinstance(domain, URIRef):
                info['domain'] = self._get_label(domain)
            else:
                info['domain'] = self._format_class_expression(domain)
            break

        # Range
        for range_val in self.graph.objects(prop_uri, RDFS.range):
            if isinstance(range_val, URIRef):
                info['range'] = self._get_label(range_val)
            else:
                info['range'] = self._format_class_expression(range_val)
            break

        # Characteristics
        if (prop_uri, RDF.type, OWL.TransitiveProperty) in self.graph:
            info['characteristics'].append('Transitive')
        if (prop_uri, RDF.type, OWL.FunctionalProperty) in self.graph:
            info['characteristics'].append('Functional')
        if (prop_uri, RDF.type, OWL.SymmetricProperty) in self.graph:
            info['characteristics'].append('Symmetric')

        # Inverse
        for inv in self.graph.objects(prop_uri, OWL.inverseOf):
            if isinstance(inv, URIRef):
                info['inverse'] = self._get_label(inv)
            break

        return info

    def get_class_restrictions(self, class_uri):
        """Get all restrictions defined directly on a class"""
        restrictions = []

        # From rdfs:subClassOf
        for superclass in self.graph.objects(class_uri, RDFS.subClassOf):
            if isinstance(superclass, BNode):
                parsed = self._parse_restriction(superclass)
                for r in parsed:
                    r['source'] = 'subClassOf'
                restrictions.extend(parsed)

        # From owl:equivalentClass
        for equiv in self.graph.objects(class_uri, OWL.equivalentClass):
            if isinstance(equiv, BNode):
                parsed = self._parse_restriction(equiv)
                for r in parsed:
                    r['source'] = 'equivalentClass'
                restrictions.extend(parsed)

        return restrictions

    def get_superclass_chain(self, class_uri):
        """Get the chain of superclasses for a class"""
        superclasses = []
        visited = set()
        to_visit = [class_uri]

        while to_visit:
            current = to_visit.pop(0)
            if current in visited:
                continue
            visited.add(current)
            if current != class_uri:
                superclasses.append(self._get_label(current))

            for superclass in self.graph.objects(current, RDFS.subClassOf):
                if isinstance(superclass, URIRef) and superclass not in visited:
                    to_visit.append(superclass)

        return superclasses

    def get_all_class_properties(self, class_uri):
        """Get all properties for a class including inherited ones"""
        all_restrictions = []
        visited = set()
        to_visit = [class_uri]

        while to_visit:
            current = to_visit.pop(0)
            if current in visited:
                continue
            visited.add(current)

            restrictions = self.get_class_restrictions(current)
            for r in restrictions:
                r['from_class'] = self._get_label(current)
            all_restrictions.extend(restrictions)

            for superclass in self.graph.objects(current, RDFS.subClassOf):
                if isinstance(superclass, URIRef) and superclass not in visited:
                    to_visit.append(superclass)

            for equiv in self.graph.objects(current, OWL.equivalentClass):
                if isinstance(equiv, URIRef) and equiv not in visited:
                    to_visit.append(equiv)

        # Group by property
        by_property = defaultdict(list)
        for r in all_restrictions:
            by_property[r['property']].append(r)

        # Build result with property info
        result = []
        for prop_name, prop_restrictions in sorted(by_property.items()):
            prop_uri = prop_restrictions[0].get('property_uri')
            prop_info = self.get_property_info(URIRef(prop_uri)) if prop_uri else {}

            result.append({
                'property': prop_name,
                'info': prop_info,
                'restrictions': prop_restrictions
            })

        return result

    def extract_properties(self, class_uris):
        """Extract relevant object properties for classes"""
        print("\nExtracting object properties...")

        # Properties of interest
        properties_of_interest = [
            GSOC["hasConstituent"],
            GSOC["hasPart"],
            GSOC["isConstituentOf"],
            GSOC["isPartOf"],
        ]

        for prop in properties_of_interest:
            # Get domain and range restrictions
            for restriction in self.graph.subjects(RDF.type, OWL.Restriction):
                on_prop = list(self.graph.objects(restriction, OWL.onProperty))
                if on_prop and on_prop[0] == prop:
                    # Get someValuesFrom or allValuesFrom
                    for pred in [OWL.someValuesFrom, OWL.allValuesFrom]:
                        for target in self.graph.objects(restriction, pred):
                            if target in class_uris:
                                # Find classes that use this restriction
                                for cls in self.graph.subjects(RDFS.subClassOf, restriction):
                                    if cls in class_uris:
                                        self.object_properties[(cls, target)].append(
                                            self._get_local_name(prop)
                                        )

        print(f"Found {len(self.object_properties)} property relationships")

    def generate_svg(self, output_path, root_uri, max_depth=4):
        """Generate SVG visualization"""
        print(f"\nGenerating SVG to {output_path}...")

        # Calculate layout
        layout = self._calculate_layout(root_uri, max_depth)

        # SVG dimensions
        margin = 50
        node_width = 180
        node_height = 30
        level_height = 80

        # Calculate canvas size
        max_nodes_per_level = max(len(nodes) for nodes in layout.values()) if layout else 1
        width = max(max_nodes_per_level * (node_width + 40) + margin * 2, 1200)
        height = (max(layout.keys()) + 1) * level_height + margin * 2 if layout else 400

        # Generate SVG
        svg_parts = []

        # SVG header with styles
        svg_parts.append(f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg"
     xmlns:xlink="http://www.w3.org/1999/xlink"
     width="{width}" height="{height}"
     viewBox="0 0 {width} {height}">
  <defs>
    <style>
      .node-rect {{
        fill: #e8f4fd;
        stroke: #2196F3;
        stroke-width: 2;
        rx: 5;
        ry: 5;
      }}
      .node-rect:hover {{
        fill: #bbdefb;
        cursor: pointer;
      }}
      .root-rect {{
        fill: #fff3e0;
        stroke: #ff9800;
        stroke-width: 3;
      }}
      .material-rect {{
        fill: #e8f5e9;
        stroke: #4caf50;
        stroke-width: 2;
      }}
      .grain-rect {{
        fill: #fce4ec;
        stroke: #e91e63;
        stroke-width: 2;
      }}
      .node-text {{
        font-family: Arial, sans-serif;
        font-size: 11px;
        fill: #333;
        text-anchor: middle;
        dominant-baseline: middle;
      }}
      .edge {{
        stroke: #999;
        stroke-width: 1.5;
        fill: none;
      }}
      .property-edge {{
        stroke: #9c27b0;
        stroke-width: 1;
        stroke-dasharray: 5,3;
        fill: none;
      }}
      .title {{
        font-family: Arial, sans-serif;
        font-size: 18px;
        font-weight: bold;
        fill: #333;
      }}
      .legend-text {{
        font-family: Arial, sans-serif;
        font-size: 12px;
        fill: #666;
      }}
    </style>
    <marker id="arrowhead" markerWidth="10" markerHeight="7"
            refX="9" refY="3.5" orient="auto">
      <polygon points="0 0, 10 3.5, 0 7" fill="#999"/>
    </marker>
  </defs>

  <!-- Title -->
  <text x="{width/2}" y="30" class="title" text-anchor="middle">
    GSO Solid_Geologic_Material Class Hierarchy
  </text>
''')

        # Calculate node positions
        node_positions = {}
        for level, nodes in layout.items():
            y = margin + 50 + level * level_height
            total_width = len(nodes) * (node_width + 20)
            start_x = (width - total_width) / 2

            for i, node_uri in enumerate(nodes):
                x = start_x + i * (node_width + 20) + node_width / 2
                node_positions[node_uri] = (x, y)

        # Draw edges first (so they appear behind nodes)
        svg_parts.append("  <!-- Edges -->")
        for parent, children in self.subclass_relations.items():
            if parent not in node_positions:
                continue
            parent_x, parent_y = node_positions[parent]

            for child in children:
                if child in node_positions:
                    child_x, child_y = node_positions[child]
                    # Draw curved edge
                    mid_y = (parent_y + child_y) / 2
                    svg_parts.append(
                        f'  <path class="edge" d="M {child_x} {child_y - node_height/2} '
                        f'Q {child_x} {mid_y} {parent_x} {parent_y + node_height/2}" '
                        f'marker-end="url(#arrowhead)"/>'
                    )

        # Draw nodes
        svg_parts.append("\n  <!-- Nodes -->")
        for node_uri, (x, y) in node_positions.items():
            label = self.classes.get(node_uri, self._get_local_name(node_uri))
            # Truncate long labels
            display_label = label[:25] + "..." if len(label) > 25 else label

            # Determine node style based on type
            rect_class = "node-rect"
            if node_uri == root_uri:
                rect_class = "root-rect"
            elif "Rock_Material" in str(node_uri) or "Rock" in label:
                rect_class = "material-rect"
            elif "Grain" in str(node_uri) or "Particle" in label:
                rect_class = "grain-rect"

            svg_parts.append(f'''  <g transform="translate({x - node_width/2}, {y - node_height/2})">
    <rect class="{rect_class}" width="{node_width}" height="{node_height}"/>
    <text x="{node_width/2}" y="{node_height/2}" class="node-text">
      <title>{label}</title>
      {display_label}
    </text>
  </g>''')

        # Legend
        legend_y = height - 80
        svg_parts.append(f'''
  <!-- Legend -->
  <g transform="translate(20, {legend_y})">
    <text x="0" y="0" class="legend-text" font-weight="bold">Legend:</text>
    <rect x="0" y="10" width="20" height="15" class="root-rect"/>
    <text x="25" y="22" class="legend-text">Root Class (Solid_Geologic_Material)</text>
    <rect x="200" y="10" width="20" height="15" class="material-rect"/>
    <text x="225" y="22" class="legend-text">Rock Material Classes</text>
    <rect x="400" y="10" width="20" height="15" class="grain-rect"/>
    <text x="425" y="22" class="legend-text">Grain/Particle Classes</text>
    <rect x="600" y="10" width="20" height="15" class="node-rect"/>
    <text x="625" y="22" class="legend-text">Other Classes</text>
  </g>
''')

        svg_parts.append("</svg>")

        # Write SVG file
        with open(output_path, "w", encoding="utf-8") as f:
            f.write("\n".join(svg_parts))

        print(f"SVG saved to {output_path}")
        print(f"  Canvas size: {width}x{height}")
        print(f"  Nodes rendered: {len(node_positions)}")

    def _calculate_layout(self, root_uri, max_depth):
        """Calculate hierarchical layout with BFS"""
        layout = defaultdict(list)
        visited = set()
        queue = [(root_uri, 0)]

        while queue:
            current, depth = queue.pop(0)

            if current in visited or depth > max_depth:
                continue

            visited.add(current)
            layout[depth].append(current)

            # Add children (subclasses)
            children = self.subclass_relations.get(current, [])
            for child in sorted(children, key=lambda x: self._get_label(x)):
                if child not in visited:
                    queue.append((child, depth + 1))

        return layout

    def generate_detailed_svg(self, output_path, root_uri, max_classes=100):
        """Generate a more detailed SVG showing all subclasses"""
        print(f"\nGenerating detailed SVG to {output_path}...")

        # Get all classes and organize by immediate parent
        all_classes = set(self.classes.keys())

        # Create a simplified tree focusing on direct subclasses of key types
        key_classes = [
            root_uri,
            GSOG["Rock_Material"],
            GSOG["Rock_Grain_Material"],
            GSOG["Mineral_Material"],
            GSOG["Mineraloid_Material"],
        ]

        # Calculate layout
        node_width = 160
        node_height = 24
        h_spacing = 10
        v_spacing = 40
        margin = 30

        # Organize classes by level
        levels = defaultdict(list)
        class_level = {}

        # Level 0: root
        levels[0] = [root_uri]
        class_level[root_uri] = 0

        # Level 1: direct subclasses of root
        direct_subs = self.subclass_relations.get(root_uri, [])
        for cls in direct_subs:
            levels[1].append(cls)
            class_level[cls] = 1

        # Level 2+: further subclasses
        for lvl1_cls in levels[1]:
            subs = self.subclass_relations.get(lvl1_cls, [])[:15]  # Limit to 15 per parent
            for cls in subs:
                if cls not in class_level:
                    levels[2].append(cls)
                    class_level[cls] = 2

        # Calculate dimensions
        max_per_level = max(len(v) for v in levels.values())
        width = max(max_per_level * (node_width + h_spacing) + margin * 2, 1400)
        height = len(levels) * (node_height + v_spacing) + margin * 2 + 100

        # Start SVG
        svg = [f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}">
  <style>
    .node {{ fill: #e3f2fd; stroke: #1976d2; stroke-width: 1.5; rx: 4; }}
    .node-root {{ fill: #fff8e1; stroke: #f57c00; stroke-width: 2; }}
    .node-material {{ fill: #e8f5e9; stroke: #388e3c; }}
    .node-grain {{ fill: #fce4ec; stroke: #c2185b; }}
    .node-mineral {{ fill: #f3e5f5; stroke: #7b1fa2; }}
    .label {{ font: 10px Arial; fill: #333; text-anchor: middle; }}
    .edge {{ stroke: #90a4ae; stroke-width: 1; fill: none; }}
    .title {{ font: bold 16px Arial; fill: #333; }}
  </style>
  <text x="{width/2}" y="25" class="title" text-anchor="middle">
    GSO Solid_Geologic_Material Hierarchy
  </text>
''']

        # Calculate positions
        positions = {}
        for level, nodes in levels.items():
            y = margin + 50 + level * (node_height + v_spacing)
            total_w = len(nodes) * (node_width + h_spacing)
            start_x = (width - total_w) / 2
            for i, node in enumerate(nodes):
                x = start_x + i * (node_width + h_spacing)
                positions[node] = (x, y)

        # Draw edges
        for parent, children in self.subclass_relations.items():
            if parent not in positions:
                continue
            px, py = positions[parent]
            for child in children:
                if child in positions:
                    cx, cy = positions[child]
                    svg.append(f'  <line class="edge" x1="{px + node_width/2}" y1="{py + node_height}" '
                              f'x2="{cx + node_width/2}" y2="{cy}"/>')

        # Draw nodes
        for node, (x, y) in positions.items():
            label = self._get_label(node)[:22]

            # Determine style
            node_class = "node"
            if node == root_uri:
                node_class = "node node-root"
            elif "Rock_Material" in str(node):
                node_class = "node node-material"
            elif "Grain" in str(node) or "Particle" in str(node):
                node_class = "node node-grain"
            elif "Mineral" in str(node):
                node_class = "node node-mineral"

            svg.append(f'  <rect class="{node_class}" x="{x}" y="{y}" '
                      f'width="{node_width}" height="{node_height}"/>')
            svg.append(f'  <text class="label" x="{x + node_width/2}" y="{y + node_height/2 + 4}">'
                      f'{label}</text>')

        # Legend
        ly = height - 50
        svg.append(f'''
  <g transform="translate(20, {ly})">
    <rect class="node node-root" x="0" y="0" width="15" height="15"/>
    <text class="label" x="80" y="12" text-anchor="start">Root</text>
    <rect class="node node-material" x="120" y="0" width="15" height="15"/>
    <text class="label" x="200" y="12" text-anchor="start">Rock Material</text>
    <rect class="node node-grain" x="280" y="0" width="15" height="15"/>
    <text class="label" x="360" y="12" text-anchor="start">Grain/Particle</text>
    <rect class="node node-mineral" x="430" y="0" width="15" height="15"/>
    <text class="label" x="510" y="12" text-anchor="start">Mineral</text>
  </g>
''')

        svg.append("</svg>")

        with open(output_path, "w", encoding="utf-8") as f:
            f.write("\n".join(svg))

        print(f"Detailed SVG saved to {output_path}")


    def generate_interactive_html(self, output_path, root_uri):
        """Generate an interactive HTML visualization with collapsible tree and property details panel"""
        print(f"\nGenerating interactive HTML to {output_path}...")
        print("  Building property data for all classes (this may take a moment)...")

        # Build property data for all classes in ontology (enables any root URI)
        all_properties = {}
        for uri in self.all_classes.keys():
            props = self.get_all_class_properties(uri)
            all_properties[str(uri)] = props

        print(f"  Extracted properties for {len(all_properties)} classes")

        # Build tree data structure
        def build_tree(uri, visited=None):
            if visited is None:
                visited = set()
            if uri in visited:
                return None
            visited.add(uri)

            label = self._get_label(uri)
            children = self.subclass_relations.get(uri, [])

            # Determine node type for styling
            node_type = "other"
            uri_str = str(uri)
            if uri == root_uri:
                node_type = "root"
            elif "Rock_Material" in uri_str or "rockmaterial" in uri_str:
                node_type = "rock"
            elif "Grain" in uri_str or "Particle" in uri_str or "granular" in uri_str:
                node_type = "grain"
            elif "Mineral" in uri_str or "mineral" in uri_str:
                node_type = "mineral"

            return {
                "name": label,
                "uri": uri_str,
                "type": node_type,
                "children": [build_tree(c, visited.copy()) for c in sorted(children, key=self._get_label)
                            if c not in visited]
            }

        tree_data = build_tree(root_uri)

        # Build subclass relations data for dynamic tree building
        subclass_data = {}
        # Use all_subclass_relations for complete ontology coverage (enables any root URI)
        for parent, children in self.all_subclass_relations.items():
            subclass_data[str(parent)] = [str(c) for c in children]

        # Build class labels from all classes in ontology
        class_labels = {str(uri): label for uri, label in self.all_classes.items()}

        # Build class comments (rdfs:comment) for all classes
        class_comments = {}
        for uri in self.all_classes.keys():
            comments = list(self.graph.objects(uri, RDFS.comment))
            if comments:
                # Join multiple comments with newlines
                class_comments[str(uri)] = " | ".join(str(c) for c in comments)

        print(f"  Found comments for {len(class_comments)} classes")

        # Convert to JSON
        tree_json = json.dumps(tree_data, indent=2)
        properties_json = json.dumps(all_properties)
        subclass_json = json.dumps(subclass_data)
        labels_json = json.dumps(class_labels)
        comments_json = json.dumps(class_comments)
        default_root = str(root_uri)

        # Generate HTML with D3.js collapsible tree and details panel
        html = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>GSO Class Hierarchy Viewer</title>
    <script src="https://d3js.org/d3.v7.min.js"></script>
    <style>
        * {{ box-sizing: border-box; }}
        body {{
            font-family: Arial, sans-serif;
            margin: 0;
            padding: 10px;
            background: #f5f5f5;
            height: 100vh;
            overflow: hidden;
        }}
        h1 {{
            text-align: center;
            color: #333;
            margin: 5px 0;
            font-size: 1.4em;
        }}
        .info {{
            text-align: center;
            color: #666;
            margin-bottom: 5px;
            font-size: 0.9em;
        }}
        .uri-input-container {{
            display: flex;
            justify-content: center;
            align-items: center;
            gap: 10px;
            margin-bottom: 10px;
            flex-wrap: wrap;
        }}
        #uri-input {{
            width: 500px;
            padding: 8px 12px;
            font-size: 0.9em;
            border: 1px solid #ddd;
            border-radius: 4px;
        }}
        #uri-input:focus {{
            outline: none;
            border-color: #2196f3;
            box-shadow: 0 0 3px rgba(33, 150, 243, 0.3);
        }}
        .load-btn {{
            padding: 8px 20px;
            background: #2196f3;
            color: white;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            font-size: 0.9em;
        }}
        .load-btn:hover {{
            background: #1976d2;
        }}
        .current-root {{
            font-size: 0.85em;
            color: #666;
            text-align: center;
            margin-bottom: 5px;
        }}
        .current-root strong {{
            color: #333;
        }}
        .main-container {{
            display: flex;
            height: calc(100vh - 180px);
            gap: 10px;
        }}
        #tree-container {{
            flex: 1;
            background: white;
            border: 1px solid #ddd;
            border-radius: 8px;
            overflow: auto;
            min-width: 400px;
        }}
        #details-panel {{
            width: 450px;
            background: white;
            border: 1px solid #ddd;
            border-radius: 8px;
            overflow: auto;
            padding: 15px;
        }}
        #details-panel h2 {{
            margin: 0 0 10px 0;
            font-size: 1.1em;
            color: #333;
            border-bottom: 2px solid #2196f3;
            padding-bottom: 5px;
        }}
        #details-panel h3 {{
            margin: 15px 0 5px 0;
            font-size: 0.95em;
            color: #555;
        }}
        .class-uri {{
            font-size: 0.8em;
            color: #666;
            word-break: break-all;
            margin-bottom: 10px;
        }}
        .class-comment {{
            font-size: 0.9em;
            color: #444;
            background: #f0f7ff;
            padding: 10px;
            border-radius: 4px;
            border-left: 3px solid #2196f3;
            margin-bottom: 15px;
            line-height: 1.4;
            font-style: italic;
        }}
        .superclasses {{
            font-size: 0.85em;
            color: #666;
            margin-bottom: 15px;
        }}
        .property-item {{
            margin-bottom: 15px;
            padding: 10px;
            background: #f8f9fa;
            border-radius: 4px;
            border-left: 3px solid #2196f3;
        }}
        .property-name {{
            font-weight: bold;
            color: #1976d2;
            font-size: 0.95em;
        }}
        .property-info {{
            font-size: 0.8em;
            color: #666;
            margin: 3px 0;
        }}
        .restriction {{
            font-size: 0.85em;
            margin: 5px 0 5px 10px;
            padding: 5px;
            background: white;
            border-radius: 3px;
        }}
        .restriction-type {{
            color: #e91e63;
            font-weight: bold;
        }}
        .restriction-filler {{
            color: #4caf50;
        }}
        .restriction-source {{
            color: #999;
            font-size: 0.8em;
        }}
        .no-selection {{
            color: #999;
            text-align: center;
            margin-top: 50px;
        }}
        .node circle {{
            stroke-width: 2px;
            cursor: pointer;
        }}
        .node text {{
            font-size: 11px;
        }}
        .node--root circle {{ fill: #fff3e0; stroke: #ff9800; }}
        .node--rock circle {{ fill: #e8f5e9; stroke: #4caf50; }}
        .node--grain circle {{ fill: #fce4ec; stroke: #e91e63; }}
        .node--mineral circle {{ fill: #f3e5f5; stroke: #9c27b0; }}
        .node--other circle {{ fill: #e3f2fd; stroke: #2196f3; }}
        .node--collapsed circle {{ fill: #999 !important; }}
        .node--selected circle {{ stroke-width: 4px; stroke: #ff5722 !important; }}
        .link {{
            fill: none;
            stroke: #ccc;
            stroke-width: 1.5px;
        }}
        .legend {{
            display: flex;
            justify-content: center;
            gap: 20px;
            margin-bottom: 10px;
            flex-wrap: wrap;
            font-size: 0.85em;
        }}
        .legend-item {{
            display: flex;
            align-items: center;
            gap: 5px;
        }}
        .legend-circle {{
            width: 14px;
            height: 14px;
            border-radius: 50%;
            border: 2px solid;
        }}
        .controls {{
            text-align: center;
            margin-bottom: 10px;
        }}
        .controls button {{
            padding: 5px 12px;
            margin: 0 3px;
            cursor: pointer;
            border: 1px solid #ddd;
            border-radius: 4px;
            background: white;
            font-size: 0.85em;
        }}
        .controls button:hover {{
            background: #f0f0f0;
        }}
    </style>
</head>
<body>
    <h1>GSO Class Hierarchy Viewer</h1>
    <p class="info">Enter a class URI to set as root, or click nodes to view properties. Double-click to expand/collapse.</p>

    <div class="uri-input-container">
        <input type="text" id="uri-input" placeholder="Enter class URI (e.g., https://w3id.org/gso/1.0/rockmaterial/Rock)" value="{default_root}">
        <button class="load-btn" onclick="loadFromUri()">Load as Root</button>
    </div>

    <div class="current-root">Current root: <strong id="current-root-label">Solid_Geologic_Material</strong></div>

    <div class="legend">
        <div class="legend-item">
            <div class="legend-circle" style="background: #fff3e0; border-color: #ff9800;"></div>
            <span>Root</span>
        </div>
        <div class="legend-item">
            <div class="legend-circle" style="background: #e8f5e9; border-color: #4caf50;"></div>
            <span>Rock Material</span>
        </div>
        <div class="legend-item">
            <div class="legend-circle" style="background: #fce4ec; border-color: #e91e63;"></div>
            <span>Grain/Particle</span>
        </div>
        <div class="legend-item">
            <div class="legend-circle" style="background: #f3e5f5; border-color: #9c27b0;"></div>
            <span>Mineral</span>
        </div>
        <div class="legend-item">
            <div class="legend-circle" style="background: #e3f2fd; border-color: #2196f3;"></div>
            <span>Other</span>
        </div>
    </div>

    <div class="controls">
        <button onclick="expandAll()">Expand Level 2</button>
        <button onclick="collapseAll()">Collapse All</button>
        <button onclick="resetZoom()">Reset View</button>
    </div>

    <div class="main-container">
        <div id="tree-container"></div>
        <div id="details-panel">
            <div class="no-selection">Click on a class node to view its properties</div>
        </div>
    </div>

    <script>
        let treeData = {tree_json};
        const allProperties = {properties_json};
        const subclassRelations = {subclass_json};
        const classLabels = {labels_json};
        const classComments = {comments_json};
        let currentRootUri = "{default_root}";
        let selectedNode = null;
        let root = null;

        // Function to build tree data from a URI
        function buildTreeFromUri(uri, visited = new Set()) {{
            if (visited.has(uri)) return null;
            visited.add(uri);

            const label = classLabels[uri] || uri.split('/').pop().split('#').pop();
            const children = subclassRelations[uri] || [];

            // Determine node type
            let nodeType = "other";
            if (uri === currentRootUri) {{
                nodeType = "root";
            }} else if (uri.includes("Rock_Material") || uri.includes("rockmaterial")) {{
                nodeType = "rock";
            }} else if (uri.includes("Grain") || uri.includes("Particle") || uri.includes("granular")) {{
                nodeType = "grain";
            }} else if (uri.includes("Mineral") || uri.includes("mineral")) {{
                nodeType = "mineral";
            }}

            const childNodes = children
                .filter(c => !visited.has(c))
                .map(c => buildTreeFromUri(c, new Set(visited)))
                .filter(c => c !== null)
                .sort((a, b) => a.name.localeCompare(b.name));

            return {{
                name: label,
                uri: uri,
                type: nodeType,
                children: childNodes
            }};
        }}

        // Function to load tree from URI input
        function loadFromUri() {{
            const input = document.getElementById('uri-input');
            const uri = input.value.trim();

            if (!uri) {{
                alert('Please enter a URI');
                return;
            }}

            // Check if URI exists in our data
            if (!classLabels[uri] && !subclassRelations[uri]) {{
                alert('URI not found in the ontology. Make sure you enter a complete URI like:\\nhttps://w3id.org/gso/1.0/rockmaterial/Rock');
                return;
            }}

            currentRootUri = uri;
            treeData = buildTreeFromUri(uri);

            if (!treeData) {{
                alert('Could not build tree from this URI');
                return;
            }}

            // Update root label display
            document.getElementById('current-root-label').textContent = treeData.name;

            // Clear existing visualization
            g.selectAll("*").remove();

            // Rebuild hierarchy
            root = d3.hierarchy(treeData);

            // Collapse appropriately
            root.descendants().forEach((d, i) => {{
                if (d.depth > 1 || (d.depth === 1 && d.data.name === "Mineral")) {{
                    d._children = d.children;
                    d.children = null;
                }}
            }});

            selectedNode = null;
            document.getElementById('details-panel').innerHTML = '<div class="no-selection">Click on a class node to view its properties</div>';

            root.x0 = 50;
            root.y0 = 0;
            svg.call(zoom.transform, d3.zoomIdentity.translate(margin.left, margin.top));
            update(root);
        }}

        // Handle Enter key in input
        document.getElementById('uri-input').addEventListener('keypress', function(e) {{
            if (e.key === 'Enter') {{
                loadFromUri();
            }}
        }});

        // Set up dimensions
        const container = document.getElementById('tree-container');
        const margin = {{top: 50, right: 150, bottom: 80, left: 100}};
        const containerWidth = container.clientWidth;
        const containerHeight = container.clientHeight || 600;

        // Create SVG
        const svg = d3.select("#tree-container")
            .append("svg")
            .attr("width", containerWidth)
            .attr("height", containerHeight);

        const g = svg.append("g");

        // Add zoom behavior
        const zoom = d3.zoom()
            .scaleExtent([0.1, 5])
            .on("zoom", (event) => {{
                g.attr("transform", event.transform);
            }});

        svg.call(zoom);

        // Create hierarchy
        root = d3.hierarchy(treeData);

        // Initially collapse Mineral node and deeper levels
        root.descendants().forEach((d, i) => {{
            if (d.depth > 1 || (d.depth === 1 && d.data.name === "Mineral")) {{
                d._children = d.children;
                d.children = null;
            }}
        }});

        function showProperties(d) {{
            selectedNode = d;
            const panel = document.getElementById('details-panel');
            const props = allProperties[d.data.uri] || [];
            const comment = classComments[d.data.uri];

            let html = `<h2>${{d.data.name}}</h2>`;
            html += `<div class="class-uri">${{d.data.uri}}</div>`;

            if (comment) {{
                html += `<div class="class-comment">${{comment}}</div>`;
            }}

            if (props.length === 0) {{
                html += '<p style="color:#666;">No property restrictions defined for this class.</p>';
            }} else {{
                html += `<p style="font-size:0.85em;color:#666;">${{props.length}} properties with restrictions:</p>`;

                props.forEach(prop => {{
                    html += `<div class="property-item">`;
                    html += `<div class="property-name">${{prop.property}}</div>`;

                    const info = prop.info || {{}};
                    if (info.type) {{
                        html += `<div class="property-info">Type: ${{info.type}}</div>`;
                    }}
                    if (info.domain) {{
                        html += `<div class="property-info">Domain: ${{info.domain}}</div>`;
                    }}
                    if (info.range) {{
                        html += `<div class="property-info">Range: ${{info.range}}</div>`;
                    }}
                    if (info.characteristics && info.characteristics.length > 0) {{
                        html += `<div class="property-info">Characteristics: ${{info.characteristics.join(', ')}}</div>`;
                    }}
                    if (info.inverse) {{
                        html += `<div class="property-info">Inverse: ${{info.inverse}}</div>`;
                    }}

                    prop.restrictions.forEach(r => {{
                        html += `<div class="restriction">`;
                        html += `<span class="restriction-type">${{r.type || '?'}}</span> `;
                        html += `<span class="restriction-filler">${{r.filler || '[complex]'}}</span>`;
                        if (r.cardinality !== undefined) {{
                            html += ` (${{r.cardinality}})`;
                        }}
                        html += `<br><span class="restriction-source">from ${{r.from_class}} (${{r.source}})</span>`;
                        html += `</div>`;
                    }});

                    html += `</div>`;
                }});
            }}

            panel.innerHTML = html;

            // Update node selection visual
            g.selectAll(".node").classed("node--selected", false);
            g.selectAll(".node").filter(n => n === d).classed("node--selected", true);
        }}

        function update(source) {{
            const duration = 400;

            const visibleNodes = root.descendants();
            const visibleHeight = Math.max(400, visibleNodes.length * 40);
            const visibleWidth = containerWidth - margin.left - margin.right;

            const tree = d3.tree().size([visibleHeight, visibleWidth]);
            const treeLayout = tree(root);
            const nodes = treeLayout.descendants();
            const links = treeLayout.links();

            svg.attr("height", visibleHeight + margin.top + margin.bottom);

            const depthSpacing = Math.min(200, visibleWidth / 5);
            nodes.forEach(d => {{ d.y = d.depth * depthSpacing; }});

            const node = g.selectAll(".node")
                .data(nodes, d => d.data.uri);

            const nodeEnter = node.enter().append("g")
                .attr("class", d => `node node--${{d.data.type}}`)
                .attr("transform", d => `translate(${{source.y0 || 0}},${{source.x0 || 0}})`)
                .on("click", (event, d) => {{
                    showProperties(d);
                }})
                .on("dblclick", (event, d) => {{
                    if (d.children) {{
                        d._children = d.children;
                        d.children = null;
                    }} else if (d._children) {{
                        d.children = d._children;
                        d._children = null;
                    }}
                    update(d);
                }});

            nodeEnter.append("circle").attr("r", 6);

            nodeEnter.append("text")
                .attr("dy", "0.35em")
                .attr("x", d => d.children || d._children ? -10 : 10)
                .attr("text-anchor", d => d.children || d._children ? "end" : "start")
                .text(d => d.data.name.length > 30 ? d.data.name.substring(0, 30) + "..." : d.data.name);

            const nodeUpdate = nodeEnter.merge(node);

            nodeUpdate.transition()
                .duration(duration)
                .attr("transform", d => `translate(${{d.y}},${{d.x}})`);

            nodeUpdate.select("circle")
                .attr("r", 6)
                .classed("node--collapsed", d => d._children);

            if (selectedNode) {{
                nodeUpdate.classed("node--selected", d => d === selectedNode);
            }}

            node.exit().transition()
                .duration(duration)
                .attr("transform", d => `translate(${{source.y}},${{source.x}})`)
                .remove();

            const link = g.selectAll(".link")
                .data(links, d => d.target.data.uri);

            const linkEnter = link.enter().insert("path", "g")
                .attr("class", "link")
                .attr("d", d => {{
                    const o = {{x: source.x0 || 0, y: source.y0 || 0}};
                    return diagonal(o, o);
                }});

            linkEnter.merge(link).transition()
                .duration(duration)
                .attr("d", d => diagonal(d.source, d.target));

            link.exit().transition()
                .duration(duration)
                .attr("d", d => {{
                    const o = {{x: source.x, y: source.y}};
                    return diagonal(o, o);
                }})
                .remove();

            nodes.forEach(d => {{
                d.x0 = d.x;
                d.y0 = d.y;
            }});
        }}

        function diagonal(s, d) {{
            return `M ${{s.y}} ${{s.x}}
                    C ${{(s.y + d.y) / 2}} ${{s.x}},
                      ${{(s.y + d.y) / 2}} ${{d.x}},
                      ${{d.y}} ${{d.x}}`;
        }}

        function expandAll() {{
            root.descendants().forEach(d => {{
                if (d._children && d.depth < 2) {{
                    d.children = d._children;
                    d._children = null;
                }}
            }});
            update(root);
        }}

        function collapseAll() {{
            root.descendants().forEach(d => {{
                if (d.depth > 0 && d.children) {{
                    d._children = d.children;
                    d.children = null;
                }}
            }});
            update(root);
        }}

        function resetZoom() {{
            svg.transition().duration(500)
                .call(zoom.transform, d3.zoomIdentity.translate(margin.left, margin.top));
        }}

        root.x0 = 50;
        root.y0 = 0;
        svg.call(zoom.transform, d3.zoomIdentity.translate(margin.left, margin.top));
        update(root);
    </script>
</body>
</html>
'''

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(html)

        print(f"Interactive HTML saved to {output_path}")


def main():
    """Main entry point"""
    # Get the directory of this script
    script_dir = os.path.dirname(os.path.abspath(__file__))

    # Initialize visualizer
    viz = GSOVisualizer()

    # Load ontology
    viz.load_ontology(script_dir)

    # Root class to visualize (initial view)
    root_uri = GSOG["Solid_Geologic_Material"]

    # Build complete relations for entire ontology (enables any root URI in the viewer)
    viz.build_complete_relations()

    # Extract hierarchy for initial root
    class_uris = viz.extract_hierarchy(root_uri)

    # Extract object properties
    viz.extract_properties(class_uris)

    # Generate interactive HTML (primary output)
    interactive_html = os.path.join(script_dir, "solid_geologic_material_interactive.html")
    viz.generate_interactive_html(interactive_html, root_uri)

    # Generate a detailed SVG view
    detailed_svg = os.path.join(script_dir, "solid_geologic_material_detailed.svg")
    viz.generate_detailed_svg(detailed_svg, root_uri)

    print("\n" + "="*60)
    print("Visualization complete!")
    print(f"Open the following files in your browser:")
    print(f"  1. {interactive_html} (Interactive, recommended)")
    print(f"  2. {detailed_svg} (Static overview)")
    print("="*60)


if __name__ == "__main__":
    main()
