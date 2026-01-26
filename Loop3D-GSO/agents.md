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

---

## GSO-Geologic_Structure HermiT Fixes

Additional fixes required for GSO-Geologic_Structure module to pass HermiT reasoning.

### Summary of Fixes

| File | Change | Reason |
|------|--------|--------|
| `Modules/GSO-Geologic_Quality.ttl` | Dip: `hasQuality` → `hasValue` | Range mismatch: `hasQuality` range is `Quality`, but values were `Quality_Value` subclasses |
| `Modules/GSO-Geologic_Quality.ttl` | Plunge: `hasQuality` → `hasValue` | Same range mismatch as Dip |
| `Modules/GSO-Geologic_Quality.ttl` | Removed duplicate `gsgq:Bedding_Pattern` | Canonical definition is in GSO-Geologic_Structure.ttl |
| `Modules/GSO-Geologic_Quality.ttl` | Removed duplicate `gsgq:Bedding_Style` | Canonical definition is in GSO-Geologic_Structure.ttl |
| `GSO-Common.ttl` | Pattern_Feature: removed `hasEssentialPart some Relator` | Forced nonphysical Relator part on physical Fabrics |
| `GSO-Common.ttl` | Pattern_Feature: removed `hasEssentialPart only Relator` | Combined with inherited `some Inherant` from Inherant_Feature, forced Relator existence |
| `GSO-Common.ttl` | Physical_Quality: expanded `isQualityOf` range | Changed from `exactly 1 Physical_Endurant` to `exactly 1 (Physical_Endurant OR Endurant_Feature)` |

### Detailed Explanations

#### 1. Dip and Plunge Property Mismatch

**Problem:** Both classes used `gsoc:hasQuality` with `someValuesFrom` pointing to `Quality_Value` subclasses:

```turtle
gsgq:Dip
  rdfs:subClassOf [
      owl:onProperty gsoc:hasQuality ;  # WRONG
      owl:someValuesFrom [ owl:unionOf (Numeric_Value Named_Value Range_Value) ] ;
    ] ;
```

- `hasQuality` has range `Quality`
- `Numeric_Value`, `Named_Value`, `Range_Value` are `Quality_Value` subclasses
- `Quality` is `owl:disjointWith Quality_Value`
- This created an impossible constraint

**Fix:** Changed to `gsoc:hasValue` (which has domain `Quality` and range `Quality_Value`), matching the pattern used by `gsgq:Azimuth`.

#### 2. Pattern_Feature Relator Restrictions

**Problem:** Pattern_Feature had two restrictions:
- `hasEssentialPart only Relator`
- `hasEssentialPart some Relator` (removed in first pass)

Combined with inherited restrictions from Inherant_Feature (`hasEssentialPart some Inherant`) and Feature (`hasEssentialPart some Particular`), this forced Pattern_Feature to have a Relator as an essential part.

But Fabric (a Pattern_Feature subclass) is physical and hosted by Rock_Body. The conflict:
- Relator is a `Nonphysical_Endurant`
- Physical_Endurant has `hasPart only Physical_Endurant`
- `hasEssentialPart` is subPropertyOf `hasPart`
- Fabric cannot have both physical-only parts AND a nonphysical Relator

**Fix:** Removed both `hasEssentialPart` restrictions from Pattern_Feature, allowing physical patterns like Fabric to satisfy inherited constraints with physical parts.

#### 3. Physical_Quality isQualityOf Range

**Problem:** The conflict chain:
1. `gsos:Bedding_Pattern` is a `Physical_Quality`
2. `Physical_Quality` requires `isQualityOf exactly 1 Physical_Endurant`
3. `Bedding_Pattern` has `isQualityOf only Bedding`
4. Therefore Bedding must be a `Physical_Endurant`
5. But Bedding → Fabric → Pattern_Feature → Inherant_Feature → Nonphysical_Feature
6. `Nonphysical_Feature` has restrictions requiring nonphysical essential parts
7. `Physical_Endurant` has `hasPart only Physical_Endurant`
8. Contradiction: Bedding cannot be both physical (parts-only-physical) and have nonphysical parts

**Fix:** Expanded Physical_Quality to allow qualities of Endurant_Features:

```turtle
gsoc:Physical_Quality
  rdfs:subClassOf [
      owl:onClass [
          owl:unionOf (
              gsoc:Physical_Endurant
              gsoc:Endurant_Feature
            ) ;
        ] ;
      owl:onProperty gsoc:isQualityOf ;
      owl:qualifiedCardinality "1"^^xsd:nonNegativeInteger ;
    ] ;
```

This allows Bedding_Pattern to be a Physical_Quality of Bedding (an Endurant_Feature) without forcing Bedding to be a Physical_Endurant.

#### 4. Duplicate Class Removal

Removed `gsgq:Bedding_Pattern` and `gsgq:Bedding_Style` from GSO-Geologic_Quality.ttl. The canonical definitions with `isQualityOf only Bedding` remain in GSO-Geologic_Structure.ttl.

### Classes Fixed

These classes were previously unsatisfiable and should now be satisfiable:

- Bedding_Pattern, Bedding_Style
- Dip, Dip_Value, Inclined, Gently_Inclined, Moderately_Inclined, Steeply_Inclined, Horizontal_Inclination, Vertical_Inclination
- Plunge, Plunge_Value, Plunging_Line, Gently_Plunging_Line, Moderately_Plunging_Line, Steeply_Plunging_Line, Horizontal_Line, Vertical_Line
- Foliation, Lineation

---

## GSO-Geologic_Rock_Object HermiT Fixes

Additional fixes required for GSO-Geologic_Rock_Object module to pass HermiT reasoning.

### Summary of Fixes

| File | Property | Before | After | Reason |
|------|----------|--------|-------|--------|
| `GSO-Common.ttl` | `constantlySpecDependsOn` | `subPropertyOf timeIncludedBy` | `subPropertyOf isTemporallyRelatedTo` | Broke unintended inference chain |
| `GSO-Common.ttl` | `timeStartedBy` | `subPropertyOf timeIncludes` | `subPropertyOf isTemporallyRelatedTo` | Prevented instant/interval conflict |
| `GSO-Common.ttl` | `timeStarts` | `subPropertyOf timeIncludedBy` | `subPropertyOf isTemporallyRelatedTo` | Same (inverse property) |

### Detailed Explanations

#### 1. constantlySpecDependsOn Subproperty Chain

**Problem:** The property hierarchy created an unintended inference chain:

```
isQualityOf → inheresIn → constantlySpecDependsOn → timeIncludedBy
```

This meant if `quality isQualityOf subject`, it inferred `quality timeIncludedBy subject`, which means `subject timeIncludes quality`.

For Epoch with `timeIncludes only Age`, any quality of an Epoch would need to be an Age - impossible for Temporal_Location qualities.

**Fix:** Changed `constantlySpecDependsOn` from `subPropertyOf timeIncludedBy` to `subPropertyOf isTemporallyRelatedTo`. This preserves the semantic meaning (constant dependence implies temporal relatedness) without the specific inclusion inference.

#### 2. timeStartedBy / timeStarts Subproperty Issue

**Problem:** These Allen interval algebra properties had:
- `timeStartedBy subPropertyOf timeIncludes`
- `timeStarts subPropertyOf timeIncludedBy`

When epochs "start at" geologic time boundaries (instants), this created conflicts:

1. `Upper_Jurassic_Epoch timeStarts Base_of_Upper_Jurassic`
2. Via inverse: `Base_of_Upper_Jurassic timeStartedBy Upper_Jurassic_Epoch`
3. Via subproperty: `Base_of_Upper_Jurassic timeIncludes Upper_Jurassic_Epoch`
4. Via inverse: `Upper_Jurassic_Epoch timeIncludedBy Base_of_Upper_Jurassic`
5. But Epoch has `timeIncludedBy only (Eon or Era or Period or Subperiod or Supereon)`
6. So `Base_of_Upper_Jurassic` must be one of those ranks
7. But it's a `Geologic_Time_Boundary` → `Temporal_Boundary` → `Time_Instant_Feature`
8. `Time_Instant_Feature` is disjoint with `Time_Interval_Feature` (which the ranks are)
9. **Contradiction!**

**Fix:** Changed both properties to `subPropertyOf isTemporallyRelatedTo`. This allows boundaries to be temporally related to intervals without implying inclusion relationships that only make sense for interval-to-interval relations.

### Testing Results

GSO-Geologic_Rock_Object passes HermiT reasoning:
- Processing time: 646,998 ms (~11 minutes)
- No unsatisfiable classes

---

## Utility Scripts Location

All Python scripts and reports have been moved to the `ontologyFixes/` subdirectory:

**Scripts:**
- `check_consistency.py`, `extract_class_properties.py`, `find_inconsistency.py`
- `find_owl2dl_conflicts.py`, `find_redundant_restrictions.py`
- `fix_cardinality_nonsimple.py`, `fix_cardinality_to_some.py`, `fix_chain_disjoint.py`
- `fix_nonsimple_disjoint.py`, `fix_owl2dl_conflicts.py`, `fix_property_regularity.py`
- `remove_all_equivalentclass.py`, `remove_redundant_restrictions.py`, `visualize_gso.py`
- `check_owl2dl.py` - Command-line HermiT reasoner (via owlready2)
- `run_hermit.py` - Direct HermiT JAR runner (requires separate download)

**Reports & Removed Axioms:**
- `consistency_fixes_log.txt`, `owl2dl_conflicts_report.txt`, `redundant_restrictions_report.txt`
- `removed_equivalentclass_axioms.txt`, `rock_properties.txt`, `Solid_Geologic_Material_properties.txt`
- `GSO-Common-removed-axioms.ttl`, `removed_owl2dl_axioms.ttl`, `removed_triples.ttl`

---

## Command-Line HermiT Testing

### check_owl2dl.py

Command-line script to run HermiT reasoner via owlready2 library. Much faster for basic consistency checks than Protégé GUI.

**Usage:**
```bash
cd ontologyFixes
python check_owl2dl.py --merge          # Merge all files and check
python check_owl2dl.py --merge -o merged.rdf  # Save merged file
```

**Features:**
- Merges all TTL files using rdflib (handles multiple ontology modules)
- Removes owl:imports statements (content already merged locally)
- Runs HermiT via owlready2's bundled reasoner
- Reports consistency/inconsistency and unsatisfiable classes
- Uses 500MB Java heap (configurable via `owlready2.reasoning.JAVA_MEMORY`)

**Dependencies:**
```bash
pip install owlready2 rdflib
```

---

## HermiT Testing Progress

| Module | Status | Time | Notes |
|--------|--------|------|-------|
| GSO-Common | PASSED | 119 ms | After OWL 2 DL fixes |
| GSO-Geologic_Structure | PASSED | - | After quality/pattern fixes |
| GSO-Geologic_Rock_Object | PASSED | 647 sec | After temporal property fixes |
| GSO-Geologic_Time | PASSED | 717 sec | No changes needed |
| GSO-Master (all merged) | INCONSISTENT | 6 sec | Using check_owl2dl.py |

**Remaining modules to test individually:**
- GSO-Geology, GSO-Feature, GSO-Element
- GSO-Geologic_Event, GSO-Geologic_Feature, GSO-Geologic_Granular_Material
- GSO-Geologic_Mineral, GSO-Geologic_Process, GSO-Geologic_Quality
- GSO-Geologic_Reference_System, GSO-Geologic_Relation, GSO-Geologic_Role
- GSO-Geologic_Setting, GSO-Geologic_Time_Ischart, GSO-Geologic_Unit
- GSO-Geologic_Structure_* (Contact, Fault, Fold, Foliation, Lineation)
- GSO-Hydrology, GSO-Perdurant, GSO-QUDTvoc, GSO-Quality, GSO-skos_annotation
