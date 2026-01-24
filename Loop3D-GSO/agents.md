# GSO Ontology Visualization Tools

This document describes the Python tools for visualizing and analyzing the GSO (Geoscience Ontology) class hierarchy and OWL restrictions.

## Scripts

### visualize_gso.py

Interactive HTML visualization of the GSO class hierarchy with property details.

**Usage:**
```bash
python visualize_gso.py
```

**Output:**
- `solid_geologic_material_interactive.html` - Interactive D3.js tree viewer (primary)
- `solid_geologic_material_detailed.svg` - Static SVG overview

**Features:**
- Collapsible D3.js tree visualization
- Single-click to view class properties, double-click to expand/collapse
- Property details panel showing inherited restrictions
- URI input box to change root class dynamically (supports any class in the ontology)
- Color-coded nodes (root/rock/grain/mineral/other)
- Displays rdfs:comment when available

**Class: GSOVisualizer**

| Method | Description |
|--------|-------------|
| `load_ontology(base_path)` | Loads all GSO TTL files (core + 27 modules) |
| `build_complete_relations()` | Builds parent→children mapping for all 6,692 classes |
| `extract_hierarchy(root_uri)` | BFS traversal to find subclasses from a root |
| `get_all_class_properties(uri)` | Collects restrictions from class and all superclasses |
| `get_property_info(prop_uri)` | Gets domain, range, characteristics, inverse for a property |
| `_parse_restriction(node)` | Parses owl:Restriction (someValuesFrom, allValuesFrom, cardinality) |
| `_extract_classes_from_expression(node)` | Handles owl:intersectionOf (AND) and owl:unionOf (OR) |
| `generate_interactive_html(path, root)` | Creates D3.js visualization with embedded data |
| `generate_detailed_svg(path, root)` | Creates static SVG overview |

**Data Structures in Generated HTML:**

| Variable | Description |
|----------|-------------|
| `treeData` | Initial tree JSON for D3.js hierarchy |
| `allProperties` | Property restrictions for all 6,692 classes |
| `subclassRelations` | Complete parent→children mapping for dynamic root selection |
| `classLabels` | URI→label mapping for all classes |
| `classComments` | URI→rdfs:comment mapping (1,193 classes have comments) |

---

### extract_class_properties.py

Command-line tool to extract and display all OWL properties/restrictions for a specific class.

**Usage:**
```bash
python extract_class_properties.py <class_uri_or_prefix>
```

**Examples:**
```bash
python extract_class_properties.py gsrm:Rock
python extract_class_properties.py gsog:Solid_Geologic_Material
python extract_class_properties.py https://w3id.org/gso/1.0/geologicrole/Crystal_Role
```

**Output:** Text report showing:
- Class label and URI
- Superclass chain (transitive closure)
- All restrictions grouped by property
- Property metadata (domain, range, characteristics, inverse)
- Restriction type and filler classes

---

### find_redundant_restrictions.py

Identifies classes with logically redundant restrictions (same restriction in both rdfs:subClassOf and owl:equivalentClass).

**Usage:**
```bash
python find_redundant_restrictions.py
```

**Output:** `redundant_restrictions_report.txt` containing:
- Summary of redundant classes by namespace
- Detailed findings for each class
- Suggested removals

**Background:**
- `owl:equivalentClass` implies `rdfs:subClassOf`
- Having the same restriction in both is logically redundant
- Safe to remove the `rdfs:subClassOf` assertion

---

### remove_redundant_restrictions.py

Removes redundant rdfs:subClassOf restrictions identified by `find_redundant_restrictions.py`.

**Usage:**
```bash
python remove_redundant_restrictions.py
```

**Behavior:**
1. Creates `.bak` backup files before modifying
2. Removes redundant restrictions from:
   - `GSO-Common.ttl`
   - `GSO-Geology.ttl`
   - `Modules/GSO-Geologic_Unit.ttl`
3. Re-serializes using rdflib (formatting changes but semantics preserved)

**To restore backups:**
```bash
mv GSO-Common.ttl.bak GSO-Common.ttl
mv GSO-Geology.ttl.bak GSO-Geology.ttl
mv Modules/GSO-Geologic_Unit.ttl.bak Modules/GSO-Geologic_Unit.ttl
```

---

## OWL Property Extraction Logic

The property extraction traverses the superclass hierarchy to collect all inherited restrictions:

1. **Get transitive closure of superclasses** via `rdfs:subClassOf` and `owl:equivalentClass`
2. **For each superclass, extract restrictions from:**
   - `rdfs:subClassOf` pointing to BNodes (restrictions)
   - `owl:equivalentClass` pointing to BNodes
3. **Parse restriction types:**
   - `owl:someValuesFrom` → "some"
   - `owl:allValuesFrom` → "only"
   - `owl:hasValue` → "value"
   - `owl:minCardinality`, `owl:maxCardinality`, `owl:cardinality`
4. **Handle nested expressions:**
   - `owl:intersectionOf` → displayed as "AND"
   - `owl:unionOf` → displayed as "OR"
5. **Get property definitions:**
   - `rdfs:domain`, `rdfs:range`
   - `owl:inverseOf`
   - Property characteristics (Transitive, Symmetric, Functional, etc.)

---

## Key URIs

| Prefix | Namespace |
|--------|-----------|
| gsoc | https://w3id.org/gso/1.0/common/ |
| gsog | https://w3id.org/gso/1.0/geology/ |
| gsrm | https://w3id.org/gso/1.0/rockmaterial/ |
| gsgm | https://w3id.org/gso/1.0/granularmaterial/ |
| gsmin | https://w3id.org/gso/1.0/mineral/ |
| gsor | https://w3id.org/gso/1.0/geologicrole/ |
| gsgu | https://w3id.org/gso/1.0/geologicunit/ |

**Example class URIs:**
- `https://w3id.org/gso/1.0/geology/Solid_Geologic_Material`
- `https://w3id.org/gso/1.0/rockmaterial/Rock`
- `https://w3id.org/gso/1.0/geologicrole/Crystal_Role`
- `https://w3id.org/gso/1.0/common/Endurant`

---

## Dependencies

- Python 3.x
- rdflib (`pip install rdflib`)

---

## Ontology Statistics

After removing redundant restrictions:

| Metric | Value |
|--------|-------|
| Total triples | 129,137 |
| Total classes | 6,692 |
| Classes with comments | 1,193 |
| Redundant restrictions removed | 72 |

---

## Files Modified by Redundancy Removal

| File | Redundant Restrictions Removed |
|------|-------------------------------|
| GSO-Common.ttl | 43 |
| GSO-Geology.ttl | 9 |
| Modules/GSO-Geologic_Unit.ttl | 20 |

---

## OWL 2 DL Compatibility (HermiT Reasoner)

GSO-Common.ttl was originally designed with OWL 2 Full expressivity, which caused inconsistencies when using OWL 2 DL reasoners like HermiT. The following modifications were required to achieve consistency.

### Removed Axioms Summary

| Category | Count | Issue |
|----------|-------|-------|
| TransitiveProperty declarations | 25 | OWL 2 DL prohibits cardinality restrictions on transitive properties |
| propertyDisjointWith axioms | 7 | Referenced non-simple (transitive) properties |
| Property chain axioms | 1 | Created irregular property hierarchy |
| owl:equivalentClass axioms | 48 | Caused unintended classification via complement/intersection expressions |
| hasUOM subPropertyOf hasQuality | 1 | Range conflict (Quality_Value vs Quality are disjoint) |
| isReferenceSystemFor restrictions | 3 | Property range is Quality_Value but restrictions pointed to Quality subtypes |

**Total: ~85 axioms removed**

### Detailed Explanation

#### 1. TransitiveProperty Declarations (25 removed)

OWL 2 DL does not allow cardinality restrictions on transitive properties or their superproperties. The following properties had TransitiveProperty declarations removed:

```
gsoc:hasPart, gsoc:isPartOf, gsoc:hasConstituent, gsoc:isConstituentOf,
gsoc:hasPersistentPart, gsoc:isPersistentPartOf, gsoc:hostedBy, gsoc:hosts,
gsoc:occupiesSpaceDirectly, gsoc:occupiesTimeDirectly, gsoc:timeIncludes,
gsoc:timeIncludedBy, gsoc:timeOlderThan, gsoc:timeYoungerThan, gsoc:timeContains,
gsoc:constantlyGenDependsOn, gsoc:constantlySpecDependsOn,
gsoc:externallyGenDependsOn, gsoc:externallySpecDependsOn,
gsoc:spatio-temporallyDependsOn, gsoc:specificallyDependsOn,
gsoc:genericallyDependsOn, gsoc:hasOlderHost, gsoc:hasYoungerHost,
gsoc:staticHostedBy
```

#### 2. propertyDisjointWith Axioms (7 removed)

OWL 2 DL requires simple properties for disjointness. These axioms referenced transitive properties:

```
gsoc:occupiesSpaceDirectly owl:propertyDisjointWith gsoc:occupiesSpaceIndirectly
gsoc:occupiesSpaceIndirectly owl:propertyDisjointWith gsoc:occupiesSpaceDirectly
gsoc:occupiesTimeDirectly owl:propertyDisjointWith gsoc:occupiesTimeIndirectly
gsoc:spatio-temporallyDependsOn owl:propertyDisjointWith gsoc:spatiallyDisjoint
gsoc:externallyGenDependsOn owl:propertyDisjointWith gsoc:hasEssentialPart
gsoc:hasEssentialPart owl:propertyDisjointWith gsoc:timeDisjoint
gsoc:hasReferenceSystem owl:propertyDisjointWith gsoc:isReferenceSystemFor
```

#### 3. Property Chain Axiom (1 removed)

Created an irregular property hierarchy where a subproperty appeared on the right side of its superproperty's chain:

```
gsoc:indirectlyYoungerThan owl:propertyChainAxiom ( gsoc:occupiesTime gsoc:timeYoungerThan )
```

#### 4. owl:equivalentClass Axioms (48 removed)

These defined classes using necessary-and-sufficient conditions that caused unintended classifications. Examples include:

- **Complement expressions** (owl:complementOf): Defined classes as "everything NOT satisfying X"
- **Partition definitions**: `Endurant EquivalentTo Physical_Endurant OR Nonphysical_Endurant`
- **Complex intersections**: Classes defined as intersections with restrictions

Classes affected include: Endurant, Physical_Endurant, Nonphysical_Endurant, Material_Endurant, Spatial_Region, Quality, Quality_Value, Amount_Of_Matter, Process, Event, Role, Relator, and many others.

#### 5. Subproperty Range Conflict (1 removed)

```
gsoc:hasUOM rdfs:subPropertyOf gsoc:hasQuality
```

**Problem:**
- `hasQuality` has `rdfs:range Quality`
- `hasUOM` has `rdfs:range Unit_Of_Measure_Value`
- `Unit_Of_Measure_Value` is a `Quality_Value`
- `Quality` is `owl:disjointWith Quality_Value`

As a subproperty, `hasUOM` inherits the range constraint, requiring `Unit_Of_Measure_Value` to be both a `Quality` AND a `Quality_Value` - impossible due to disjointness.

#### 6. Restrictions with Range Violations (3 removed)

These restrictions used `isReferenceSystemFor some [Quality subtype]` but the property's range is `Quality_Value`:

```
# From Nonphysical_Reference_System
rdfs:subClassOf [ owl:onProperty gsoc:isReferenceSystemFor ;
                  owl:someValuesFrom gsoc:Nonphysical_Quality ]

# From Physical_Reference_System
rdfs:subClassOf [ owl:onProperty gsoc:isReferenceSystemFor ;
                  owl:someValuesFrom gsoc:Temporal_Quality ]

# From Temporal_Reference_System
rdfs:subClassOf [ owl:onProperty gsoc:isReferenceSystemFor ;
                  owl:someValuesFrom gsoc:Perdurant ]
```

### Removed Axioms File

All removed axioms are preserved in `GSO-Common-removed-axioms.ttl` (649 triples). To restore OWL 2 Full expressivity:

```bash
# Merge removed axioms back (for OWL Full reasoners only)
python -c "
from rdflib import Graph
g = Graph()
g.parse('GSO-Common.ttl', format='turtle')
g.parse('GSO-Common-removed-axioms.ttl', format='turtle')
g.serialize('GSO-Common-Full.ttl', format='turtle')
"
```

### Testing with HermiT

After modifications, GSO-Common.ttl passes HermiT reasoning:

```
INFO  ------------------------------- Running Reasoner -------------------------------
INFO  Pre-computing inferences:
INFO      - class hierarchy
INFO      - object property hierarchy
INFO      - data property hierarchy
INFO      - class assertions
INFO      - object property assertions
INFO      - same individuals
INFO  Ontologies processed in 119 ms by HermiT
```

### Script: remove_all_equivalentclass.py

Utility script that removes all `owl:equivalentClass` statements from GSO-Common.ttl:

```bash
python remove_all_equivalentclass.py
```

This converts necessary-and-sufficient conditions to just necessary conditions (rdfs:subClassOf), which prevents unintended classification conflicts.
