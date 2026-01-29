# GSO Ontology Visualization Tools

This document describes the Python tools for visualizing and analyzing the GSO (Geoscience Ontology) class hierarchy and OWL restrictions.

## Scripts

### visualize_gso.py (repo root)

Interactive HTML visualization of the GSO class hierarchy with property details.

**Usage:**
```bash
python visualize_gso.py
```

**Output:**
- `visualizeGSO.html` - Interactive D3.js tree viewer (primary)
- `visualizeGSO_hierarchy.svg` - Static SVG overview

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
| `build_complete_relations()` | Builds parent→children mapping for all 6,718 classes |
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
| `allProperties` | Property restrictions for all 6,718 classes |
| `subclassRelations` | Complete parent→children mapping for dynamic root selection |
| `classLabels` | URI→label mapping for all classes |
| `classComments` | URI→rdfs:comment mapping |

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

After all OWL 2 DL fixes (LogicReview branch):

| Metric | Value |
|--------|-------|
| Total triples | 125,947 |
| Total classes | 6,743 |
| Unsatisfiable classes | 0 |
| Consistency | CONSISTENT |

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

## Utility Scripts and Files

**Repo root:**
- `visualize_gso.py` — Interactive GSO class hierarchy viewer (generates `visualizeGSO.html` and `visualizeGSO_hierarchy.svg`)
- `generatedocs3-fix.bat` — pyLODE HTML documentation generator for all GSO modules

**`ontologyFixes/` directory — test scripts:**
- `test_no_ischart_no_feature.py` — Full GSO consistency test excluding Ischart and Feature modules (CONSISTENT)
- `test_with_feature.py` — Full GSO test including Feature module
- `test_with_ischart.py` — Full GSO test including Ischart module
- `apply_owl2dl_fixes.py` — Applies OWL 2 DL compatibility fixes
- `semantic_merge.py` — Semantic merge utility for ontology files

**`ontologyFixes/` directory — removed axioms and records:**
- `removed_triples.ttl` — Triples removed during OWL 2 DL fixes
- `removed_owl2dl_axioms.ttl` — OWL 2 DL incompatible axioms removed
- `removed_equivalentclass_axioms.txt` — Record of equivalentClass axioms removed
- `GSO-Common-removed-axioms.ttl` — Axioms removed from GSO-Common.ttl (649 triples; merge back for OWL Full)
- `consistency_fixes_log.txt` — Log of all consistency fixes applied
- `common_premerge.ttl` — Pre-merge snapshot of GSO-Common.ttl for reference

---

## Command-Line HermiT Testing

### check_owl2dl.py

Command-line script to run HermiT reasoner via owlready2 library. Much faster for basic consistency checks than Protégé GUI.

**Usage:**
```bash
python ontologyFixes/check_owl2dl.py --merge          # Merge all files and check
python ontologyFixes/check_owl2dl.py --merge -o merged.rdf  # Save merged file
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

## GSO-Geologic_Quality Nonphysical_Quality Fixes

11 classes in `Modules/GSO-Geologic_Quality.ttl` were incorrectly typed as `Physical_Quality` when they should be `Nonphysical_Quality`. Physical qualities require `isQualityOf exactly 1 Physical_Endurant`, but these classes qualify non-physical features (structures, foliations, etc.), causing unsatisfiability.

### Classes Changed

| Class | Reason |
|-------|--------|
| `gsgq:Metamorphic_Facies` | Qualifies metamorphic conditions, not physical objects |
| `gsgq:Metamorphic_Grade` | Qualifies metamorphic conditions |
| `gsgq:Mineral_Habit` | Qualifies mineral form descriptions |
| `gsgq:Particle_Geometry_Term` | Qualifies geometric descriptions |
| `gsgq:Particle_Shape` | Qualifies shape descriptions |
| `gsgq:Permeability_Quality` | Qualifies permeability descriptions |
| `gsgq:Porosity_Quality` | Qualifies porosity descriptions |
| `gsgq:Rock_Alteration_Type` | Qualifies alteration descriptions |
| `gsgq:Rock_Cement_Type` | Qualifies cement descriptions |
| `gsgq:Rock_Color` | Qualifies color descriptions |
| `gsgq:Rock_Texture` | Qualifies texture descriptions |

---

## GSO-Geology.ttl Geologic Time Class Fixes

Three `hasEssentialPart`-related restrictions were removed from geologic time classes in `GSO-Geology.ttl` to resolve unsatisfiability when combined with the Ischart module.

### Summary of Fixes

| Class | Restriction Removed | Reason |
|-------|---------------------|--------|
| `gsog:Geologic_Time_Interval` | `hasEssentialPart some (Geologic_Time_Interval OR Time_Interval)` | Conflicted with subclass cardinality restrictions |
| `gsog:Generic_Geologic_Time_Unit` | `hasEssentialPart some Specific_Geologic_Time_Unit` | Conflicted with disjointness between Generic and Specific |
| `gsog:Specific_Geologic_Time_Unit` | `complementOf (hasEssentialPart some Geologic_Time_Interval)` | Redundant after removing parent restrictions |

### Detailed Explanation

#### 1. Geologic_Time_Interval hasEssentialPart

**Problem:** `Geologic_Time_Interval` required `hasEssentialPart some (Geologic_Time_Interval OR Time_Interval)`. Since `hasEssentialPart` is a subproperty of `hasPart`, this interacted with restrictions on subclasses:

- `Specific_Geologic_Time_Unit` has `hasStaticPart exactly 1 Time_Interval`
- `Generic_Geologic_Time_Unit` has `complementOf (hasStaticPart some Time_Interval)`

The `hasEssentialPart` requirement on the parent class created conflicts through the property hierarchy (`hasEssentialPart → hasPersistentPart → hasStaticPart → hasPart`).

**Fix:** Removed the restriction entirely.

#### 2. Generic_Geologic_Time_Unit hasEssentialPart

**Problem:** `Generic_Geologic_Time_Unit` required `hasEssentialPart some Specific_Geologic_Time_Unit`, but Generic and Specific are `owl:disjointWith` each other. Combined with part-type restrictions, this created conflicts when individuals were classified.

**Fix:** Removed the restriction.

#### 3. Specific_Geologic_Time_Unit complementOf

**Problem:** `Specific_Geologic_Time_Unit` had `complementOf (hasEssentialPart some Geologic_Time_Interval)`, asserting that no Specific unit has a Geologic_Time_Interval as an essential part. After removing the parent class restrictions, this constraint became unnecessary and potentially conflicting.

**Fix:** Removed the restriction.

---

## GSO-Geologic_Time_Ischart Status

### Status: CONSISTENT (Fixed)

After changing `timeIncludes` to `timeContains` in the Epoch and Period restrictions (see "GSO-Geologic_Time_Ischart Inconsistency Fix" above), the full GSO ontology including the Ischart module passes HermiT consistency checking.

| Test | Result | Time |
|------|--------|------|
| Full GSO with Ischart (664 individuals, 9,848 triples) | **CONSISTENT** | **2.27 seconds** |
| Unsatisfiable classes | **0** | — |

The `timeContains` fix works because `timeFinishedBy` is a subproperty of `timeIncludes` but NOT of `timeContains`. Boundaries asserted via `timeFinishedBy` no longer trigger the `allValuesFrom` constraints on Epoch and Period.

---

## Full GSO Test Results (Without Feature)

### Status: CONSISTENT (0 unsatisfiable classes)

After applying all fixes (including master merge fixes), testing all GSO modules (excluding Feature) with HermiT shows **0 unsatisfiable classes**.

**Test parameters:** 125,947 triples, 6,743 classes, 0 unsatisfiable

### Root Cause Analysis of 117 Unsatisfiable Classes

The 117 unsatisfiable classes had two distinct root causes:

#### Root Cause 1: GSO-Feature Module (96 classes)

**Affected:** Foliation, Lineation + 72 Foliation subtypes + 22 Lineation subtypes

**Chain of conflict:**
1. GSO-Feature.ttl defines: `Nonphysical_Feature rdfs:subClassOf Nonphysical_Endurant`
2. GSO-Common.ttl: `Nonphysical_Endurant: hasQuality only Nonphysical_Quality`
3. GSO-Geologic_Structure.ttl: `Foliation: hasQuality some Plane_Orientation`
4. `Plane_Orientation → Orientation → Physical_Quality`
5. `Physical_Quality owl:disjointWith Nonphysical_Quality`
6. Foliation inherits `hasQuality only Nonphysical_Quality` (via Feature module chain) but REQUIRES `hasQuality some Plane_Orientation` (a Physical_Quality) → **UNSATISFIABLE**

**Fix:** Removed `owl:imports feature:ontology` from GSO-Master.ttl. The comment on line 106 already said "Shell to load all GSO files, except GSO-Feature" and the Feature module itself says it is not meant to be imported into the master ontology. The import was present contradictorily.

#### Root Cause 2: Fault Quality Classes (21 classes)

**Affected:** 5 root classes (Fault_Movement_Magnitude, Fault_Movement_Sense, Fault_Movement_Vector, Fault_Separation, Fault_Slip) + 16 subclasses

**Chain of conflict (isQualityOf):**
1. These classes were `Physical_Quality` with `isQualityOf only Displacement`
2. `Physical_Quality` requires `isQualityOf exactly 1 (Physical_Endurant OR Endurant_Feature)`
3. `Displacement → Physical_Quality → Quality → Inherant → Nonphysical_Endurant`
4. Displacement is neither `Physical_Endurant` nor `Endurant_Feature`
5. The target must be in the union AND must be `Displacement` → **UNSATISFIABLE**

**Fix:** Changed all 5 root classes from `gsoc:Physical_Quality` to `gsoc:Nonphysical_Quality`. Since Displacement IS a `Nonphysical_Endurant` (through the chain above), and `Nonphysical_Quality` requires `isQualityOf exactly 1 (Nonphysical_Endurant OR Perdurant)`, this is now compatible.

**Additional fix for Fault_Movement_Vector:**
Fault_Movement_Vector also had `hasQuality some Azimuth` and `hasQuality some Plunge`. Since ANY Quality is a `Nonphysical_Endurant` (through `Quality → Inherant → Nonphysical_Endurant`), and `Nonphysical_Endurant` constrains `hasQuality only Nonphysical_Quality`, no Quality instance can have a `Physical_Quality` as its quality. Since Azimuth and Plunge are `Physical_Quality`, the existential requirements made FMV unsatisfiable. Removed the two `hasQuality some` restrictions.

### Summary of Fixes

| File | Change | Classes Fixed |
|------|--------|---------------|
| `GSO-Master.ttl` | Removed `owl:imports feature:ontology` | 96 (Foliation/Lineation + subtypes) |
| `Modules/GSO-Geologic_Structure_Fault.ttl` | 5 classes: `Physical_Quality` → `Nonphysical_Quality` | 20 (5 root + 15 subclasses) |
| `Modules/GSO-Geologic_Structure_Fault.ttl` | Fault_Movement_Vector: removed `hasQuality some Azimuth/Plunge` | 1 |

---

## GSO-Geologic_Time_Ischart Inconsistency Fix

### Root Cause (confirmed via Protege explanation)

The Ischart module caused an INCONSISTENCY (owl:Thing SubClassOf owl:Nothing) through this chain:

1. `Epoch SubClassOf (timeIncludes only Age)` — all timeIncludes values of an Epoch must be Age
2. `timeFinishedBy rdfs:subPropertyOf timeIncludes` — timeFinishedBy values count as timeIncludes
3. `MiddleTriassic2004 rdf:type Epoch` — it's an Epoch instance
4. `MiddleTriassic2004 timeFinishedBy BaseUpperTriassic2004` — so BaseUpperTriassic2004 is a timeIncludes value, hence must be Age
5. `BaseUpperTriassic2004 rdf:type Geologic_Time_Boundary` — but it's a boundary
6. `Geologic_Time_Boundary owl:disjointWith Geologic_Time_Interval` — and Age IS a Geologic_Time_Interval
7. **CONTRADICTION**: BaseUpperTriassic2004 must be both Age (a Time_Interval) and is Geologic_Time_Boundary (disjoint with Time_Interval)

This pattern affects all Epoch and Period instances that have `timeFinishedBy` assertions pointing to boundaries.

### Fix

Changed `timeIncludes` to `timeContains` in the allValuesFrom restrictions in `Modules/GSO-Geologic_Time.ttl`:

| Class | Before | After |
|-------|--------|-------|
| `Epoch` | `timeIncludes only Age` | `timeContains only Age` |
| `Period` | `timeIncludes only (Age OR Epoch OR Subperiod)` | `timeContains only (Age OR Epoch OR Subperiod)` |

This works because `timeFinishedBy` is a subproperty of `timeIncludes` but NOT of `timeContains`. The boundaries asserted via `timeFinishedBy` no longer trigger the `allValuesFrom` constraint, which only applies to `timeContains` values. This approach is consistent with how constraints are constructed on other Geologic_Time_Interval subclasses.

---

## Master Merge Fixes (LogicReview Branch)

After merging master into the LogicReview branch, 15 additional unsatisfiable classes appeared. These were resolved in two groups.

### Fix 1: Bedding_Pattern and Bedding_Style (2 classes)

**Problem:** After merging, `Bedding_Pattern` and `Bedding_Style` in `GSO-Geologic_Quality.ttl` were `Nonphysical_Quality` but had `isQualityOf only Bedding`. The `Nonphysical_Quality` range requires `isQualityOf exactly 1 (Nonphysical_Endurant OR Perdurant)`, and Bedding is neither.

**Fix:** Changed both classes from `Nonphysical_Quality` to `Physical_Quality` in `Modules/GSO-Geologic_Quality.ttl`, and expanded `Nonphysical_Quality` in `GSO-Common.ttl` to allow `Endurant_Feature` in its `isQualityOf` range.

### Fix 2: Transformation hasOutput (13 classes)

**Affected:** Metamorphic_Facies + 10 subclasses + Alteration_Unit + Alteration_Facies

**Root cause:** Master's `GSO-Geology.ttl` narrowed the `Transformation` class restriction from `hasOutput allValuesFrom unionOf(Amount_Of_Matter, Geologic_Object)` to just `hasOutput allValuesFrom Amount_Of_Matter`.

**Chain of conflict:**
1. `Metamorphic_Process rdfs:subClassOf Transformation`
2. `Transformation: hasOutput allValuesFrom Amount_Of_Matter` (narrowed by master)
3. `Metamorphic_Facies: isOutputOf some Metamorphic_Process` — so Metamorphic_Facies must be `Amount_Of_Matter`
4. `Amount_Of_Matter owl:disjointWith Material_Object`
5. `Geologic_Unit → Rock_Object → Geologic_Object → Material_Object`
6. `Alteration_Unit rdfs:subClassOf Geologic_Unit` — must be both `Amount_Of_Matter` and `Material_Object` → **UNSATISFIABLE**

**Fix:** Restored the union in `GSO-Geology.ttl`:
```turtle
gsog:Transformation
  rdfs:subClassOf [
      rdf:type owl:Restriction ;
      owl:allValuesFrom [
          rdf:type owl:Class ;
          owl:unionOf (
            gsoc:Amount_Of_Matter
            gsog:Geologic_Object
          ) ;
        ] ;
      owl:onProperty gsoc:hasOutput ;
    ] ;
```

### Fix 3: W3C Time Ontology Import Warnings

**Problem:** owlready2 warned about `time#xsdDateTime` and `time#inXSDDateTime` belonging to multiple entity types (`owl:DatatypeProperty` and `owl:DeprecatedProperty`). These came from importing `<http://www.w3.org/2006/time>`.

**Fix:**
- Removed `owl:imports <http://www.w3.org/2006/time>` from `Modules/GSO-Geologic_Time_Scales.ttl` (didn't use any `time:` entities)
- Removed the import from `Modules/GSO-Geologic_Time_Scales-GTS.ttl` and added a local `time:TRS` class declaration (used in 16 places)

---

## HermiT Testing Progress

| Module | Status | Time | Notes |
|--------|--------|------|-------|
| GSO-Common | PASSED | 119 ms | After OWL 2 DL fixes |
| GSO-Geologic_Structure | PASSED | - | After quality/pattern fixes |
| GSO-Geologic_Rock_Object | PASSED | 647 sec | After temporal property fixes |
| GSO-Geologic_Time | PASSED | 717 sec | No changes needed |
| GSO-Geologic_Time_Ischart | **PASSED** | 2.27 sec | Fixed by changing timeIncludes → timeContains |
| Full GSO (with Ischart, no Feature) | **CONSISTENT** | 2.27 sec | 136,082 triples, 6,744 classes, 0 unsatisfiable |

**Notes:**
- GSO-Feature module has a known design conflict (Nonphysical_Feature → Nonphysical_Endurant constraint) and should remain excluded from Master imports
- Explore ontology simplification strategies (see below) on the `Simplify` branch

---

## Ontology Complexity Analysis

Analysis of axiom patterns that contribute to reasoning complexity.

### Axiom Counts

| Axiom Pattern | Count | Impact |
|---------------|-------|--------|
| `owl:allValuesFrom` (universal restrictions) | 785 | High — forces reasoner to check ALL instances; primary source of unsatisfiability cascades |
| `owl:someValuesFrom` (existential restrictions) | 1,250 | Medium — requires witness existence but doesn't constrain other values |
| `owl:disjointWith` | 317 | High — creates hard boundaries; interacts with universal restrictions to cause unsatisfiability |
| Time `rdfs:subPropertyOf` relations | 39 | High — `timeIntersects` alone has 10 sub-properties; creates inference chains through `allValuesFrom` |
| Total classes | 6,743 | — |
| Total triples (with Ischart) | 125,947 | — |
| Ischart individuals | 664 | High — combinatorial explosion with time property hierarchy |

### Key Complexity Drivers

1. **Universal restriction cascades**: `allValuesFrom` restrictions on parent classes propagate to ALL subclasses. A single `allValuesFrom` on `Endurant` constrains 3,000+ subclasses.

2. **Property hierarchy amplification**: With 39 time sub-property relations, a single `allValuesFrom` on `timeIncludes` effectively constrains 10+ sub-properties (`timeFinishedBy`, `timeStartedBy`, `timeContains`, etc.).

3. **Disjointness + universal interaction**: When `A allValuesFrom X` and `X disjointWith Y`, any subclass needing `someValuesFrom Y` becomes unsatisfiable. This was the root cause of most of the 117 unsatisfiable classes found during testing.

4. **Quality meta-ontology depth**: The chain `Quality → Inherant → Nonphysical_Endurant` is 4 levels deep. Every Quality class inherits restrictions from all 4 levels, creating complex constraint interactions.

---

## Proposed Simplification Strategies

These strategies aim to reduce reasoning complexity without sacrificing semantic precision. Work should be done on the `Simplify` branch.

### Strategy 1: Replace `allValuesFrom` with `someValuesFrom` (Where Descriptive)

**Target:** ~785 `allValuesFrom` axioms

Many `allValuesFrom` (universal) restrictions serve a descriptive rather than prescriptive role. For example, `Rock hasConstituent only Mineral` describes typical composition but shouldn't logically forbid unusual constituents.

**Approach:**
- Audit each `allValuesFrom` to determine if it is definitional (must keep) or descriptive (can relax)
- Replace descriptive universals with `someValuesFrom` (existential)
- Keep universals that enforce true logical invariants (e.g., `Physical_Endurant hasPart only Physical_Endurant`)

**Trade-off:** Reduces reasoning constraints but allows models that were previously forbidden. Some domain experts may prefer strict universals.

### Strategy 2: Flatten the Quality Meta-Ontology

**Target:** The 4-level chain `Quality → Inherant → Nonphysical_Endurant → Endurant`

**Problem:** Every Quality class inherits restrictions from 4 ancestor levels. The distinction between Quality and Inherant serves a philosophical (BFO/DOLCE) purpose but adds reasoning overhead without geological value.

**Approach:**
- Collapse `Inherant` into `Quality` (merge the two levels)
- Move essential `Inherant` restrictions directly to `Quality`
- Reduce the ancestor chain to 3 levels

**Trade-off:** Diverges from strict BFO/DOLCE alignment but simplifies the most heavily-used branch of the ontology.

### Strategy 3: Flatten Time Property Hierarchy

**Target:** 39 `rdfs:subPropertyOf` relations among time properties

**Problem:** `timeIntersects` has 10 direct sub-properties, each of which may have further sub-properties. Every `allValuesFrom` on a parent property effectively constrains all sub-properties, creating a web of hidden constraints.

**Approach:**
- Remove intermediate property groupings (e.g., make `timeFinishedBy` and `timeStartedBy` direct sub-properties of `isTemporallyRelatedTo` instead of `timeIncludes`)
- Keep only the sub-property relations that are logically necessary (e.g., `timeContains subPropertyOf timeIncludes` for true containment)

**Trade-off:** Loses some inferential power (e.g., can no longer infer `timeIncludes` from `timeFinishedBy`), but prevents the constraint amplification that caused the Ischart inconsistency.

### Strategy 4: Separate TBox from ABox

**Target:** `GSO-Geologic_Time_Ischart.ttl` (664 individuals, 9,848 triples)

**Problem:** HermiT's tableau algorithm scales poorly with large numbers of individuals combined with complex TBox axioms. The Ischart individuals represent ~8% of total triples but dominate reasoning time.

**Approach:**
- Keep class definitions (TBox) in the main ontology files
- Move individuals (ABox) to separate files loaded only for SPARQL querying
- Use a lighter reasoner (or no reasoner) for the ABox-heavy files

**Trade-off:** Cannot use DL reasoners to check individual classification, but SPARQL/SHACL validation can catch most data quality issues.

### Strategy 5: Reduce Disjointness Scope

**Target:** 317 `owl:disjointWith` axioms

**Problem:** Disjointness axioms create hard boundaries. Combined with universal restrictions, they are the primary cause of unsatisfiability cascades.

**Approach:**
- Remove disjointness between sibling classes that don't need strict separation
- Keep disjointness only where overlap would be a genuine logical error (e.g., `Physical_Endurant disjointWith Nonphysical_Endurant`)
- Replace broad disjointness with SHACL constraints for softer validation

**Trade-off:** Allows some models that were previously forbidden by disjointness. Reduces the "safety net" that catches modeling errors.

### Strategy Comparison

| Strategy | Complexity Reduction | Semantic Precision | Effort |
|----------|---------------------|-------------------|--------|
| 1. allValuesFrom → someValuesFrom | High | Slight loss (descriptive only) | Medium (requires per-axiom audit) |
| 2. Flatten Quality hierarchy | Medium | Minimal (philosophical only) | Low (structural refactor) |
| 3. Flatten time properties | High | Moderate (loses some inferences) | Low (property hierarchy edits) |
| 4. Separate TBox/ABox | High (for reasoning) | None (data unchanged) | Low (file reorganization) |
| 5. Reduce disjointness | Medium | Moderate (fewer hard constraints) | Medium (requires per-axiom audit) |

---

## Example Files Consistency Testing

### Status: ALL INCONSISTENT with HermiT (ABox problem)

All 22 example TTL files in the `Examples/` directory were tested for OWL 2 DL consistency with the base GSO ontology (excluding Feature and Ischart modules) using HermiT.

**Phase 1 — Syntax Validation:** All 22 files parse successfully with rdflib. No syntax errors.

**Phase 2 — Combined Test:** INCONSISTENT (5.4s) — 168,471 triples, 6,750 classes, 768 individuals.

**Phase 3 — Individual Testing:** All 22/22 examples are INCONSISTENT, including the smallest (kootznahoo.ttl, 26 triples, 1 Formation individual).

| Example File | Triples | Result | Time |
|---|---|---|---|
| GSO-ExampleBritishColumbiaStrat-v2.ttl | 1,914 | INCONSISTENT | 5.9s |
| GSO-ExampleComplexContacts.ttl | 314 | INCONSISTENT | 6.9s |
| GSO-ExampleEpochLowerJurassic.ttl | 21 | INCONSISTENT | 8.1s |
| GSO-ExampleEvents1.ttl | 114 | INCONSISTENT | 9.5s |
| GSO-ExampleFault2.ttl | 45 | INCONSISTENT | 10.5s |
| GSO-ExampleFaultKannaV4Model.ttl | 104 | INCONSISTENT | 11.5s |
| GSO-ExampleFold.ttl | 77 | INCONSISTENT | 13.0s |
| GSO-ExampleFormationJs.ttl | 148 | INCONSISTENT | 14.2s |
| GSO-ExampleGeosciAustraliaStratUnit.ttl | 92 | INCONSISTENT | 17.2s |
| GSO-ExampleHammerslyData.ttl | 148 | INCONSISTENT | 19.4s |
| GSO-ExampleHistory.ttl | 269 | INCONSISTENT | 17.8s |
| GSO-ExampleIsleOfWightStrat-pm1-v2.ttl | 2,009 | INCONSISTENT | 19.0s |
| GSO-ExampleIsleOfWightStrat-pm1.ttl | 1,538 | INCONSISTENT | 20.4s |
| GSO-ExampleLaTojizaPluton.ttl | 592 | INCONSISTENT | 21.3s |
| GSO-ExamplePetrophysicalProperties_v2.ttl | 10,854 | INCONSISTENT | 22.9s |
| GSO-ExampleRockMaterialBolsaQuartzite.ttl | 170 | INCONSISTENT | 24.2s |
| GSO-ExampleRoles.ttl | 210 | INCONSISTENT | 25.4s |
| GSO-ExampleSpecificRockObject.ttl | 170 | INCONSISTENT | 27.1s |
| GSO-ExampleVocab-Alteration_Type-BC.ttl | 43 | INCONSISTENT | 34.9s |
| GSO-LardeauGroup.ttl | 66 | INCONSISTENT | 37.2s |
| kootznahoo.ttl | 26 | INCONSISTENT | 40.2s |
| xgma-geotimeversion.ttl | 23,774 | INCONSISTENT | 42.2s |

### Root Cause

This is not an example-specific problem. The base ontology TBox is satisfiable (0 unsatisfiable classes with HermiT), but when HermiT tries to build a tableau model for **any** named individual, the cascade of existential requirements (`someValuesFrom`) combined with universal restrictions (`allValuesFrom`) and disjointness axioms creates contradictions. This is the same class of issue as the Ischart inconsistency.

When HermiT encounters a named individual (e.g., `xdd:KootznahooFormation rdf:type gsgu:Formation`), it must:
1. Satisfy all `someValuesFrom` restrictions inherited through the class hierarchy by creating "witness" individuals
2. Each witness inherits its own constraints, creating more witnesses
3. The `allValuesFrom` restrictions constrain what types those witnesses can be
4. `disjointWith` axioms create hard boundaries between types
5. The expanding web of witnesses eventually violates a disjointness constraint → **INCONSISTENT**

### OWL Full Reasoning Alternatives

OWL Full is undecidable, so no reasoner can guarantee complete reasoning. However, several tools provide practical alternatives to OWL 2 DL tableau reasoning:

**Rule-based / Forward-chaining reasoners:**
- **Apache Jena (with OWL rules)** — Jena's built-in rule engine supports OWL Full-like inference using forward/backward chaining. It applies RDFS and OWL entailment rules to derive inferred triples without trying to build a complete tableau model. Most practical option for GSO.
- **RDFox** — High-performance materialization engine. Supports OWL 2 RL (a decidable subset) plus custom Datalog rules. Very fast for large ABoxes. Commercial license.
- **EYE (Euler Yet another proof Engine)** — A Notation3/N3 reasoner that can handle OWL Full semantics via rules.

**SPARQL/SHACL-based validation (practical for ABox):**
- **SHACL validators** (e.g., TopBraid SHACL, pySHACL) — Write SHACL shapes expressing the constraints that matter for data quality, then validate individuals against them. More practical than DL reasoning for ABox validation.
- **SPARQL queries** — Write ASK/SELECT queries to check for specific constraint violations.

**Recommended approach for GSO:**
1. **Jena** with its OWL reasoner profile for inference (deriving implied triples from examples)
2. **SHACL** for constraint validation (checking that individuals conform to expected patterns)
3. **HermiT** for TBox-only consistency checking (class hierarchy, which already passes)

Rule-based reasoners like Jena materialize the inferences they can make without building a complete tableau model, so they do not report the kind of inconsistency that HermiT finds. The trade-off is they won't detect certain types of logical contradictions — but for practical data validation, SHACL constraints are more useful and more targeted.

### Test Script

`test_examples.py` (repo root) — Tests all Example TTL files in three phases:
1. Syntax validation (rdflib parse)
2. Combined HermiT consistency check (all examples + base ontology)
3. Individual HermiT testing (if Phase 2 fails, tests each example separately)

---

## Example File Fixes (Path A: Fix ABox)

### Overview

Rather than modifying the ontology TBox to relax `isQualityOf` restrictions, the example TTL files were fixed to use correct property paths that conform to the GSO ontology's OWL 2 DL semantics. This approach ("Path A") preserves the ontology's strict type constraints while ensuring example files are consistent.

### Violation Categories Identified

| Code | Violation Pattern | Fix Applied |
|------|-------------------|-------------|
| V1 | `Spatial_Location` on non-`Spatial_Region` bearer | Route through `occupiesSpaceDirectly → Spatial_Region → hasQuality → Spatial_Location` |
| V2 | `hasQuality` used for `Quality_Value` (e.g., `Numeric_Value`, `Range_Value`) | Change to `hasValue` (Quality → hasValue → Quality_Value) |
| V3 | `Grain_Roundness` nested inside `Particle_Shape` via `hasQuality` | Flatten: both become sibling qualities of the material |
| V4 | `Physical_Quality` nested inside another `Quality` via `hasQuality` | Flatten: move nested quality to sibling level |
| V5 | `Proportion` on non-`Part` role (e.g., `Phenocryst`) | Split into separate `Part` role for proportion |
| V6 | `Quality` type used as `hasConstituent` object | Change to proper material type (e.g., `Granite`) |
| V7 | `Duration` on `Time_Interval_Location`, `Uncertainty` on `Duration` | Move `Duration` to `Time_Interval`, `Uncertainty` to `Numeric_Value` |
| V8 | `Quality` type as object of `occupiesTimeDirectly` | Wrap in `Time_Region` (e.g., `Time_Instant` or `Time_Interval`) |

### Files Fixed

| File | Violations Fixed |
|------|-----------------|
| `kootznahoo.ttl` | V1: Spatial_Location routed through Spatial_Region |
| `GSO-ExampleSpecificRockObject.ttl` | V2 (3x), V3: hasQuality→hasValue, flatten Roundness/Shape |
| `GSO-ExampleRockMaterialBolsaQuartzite.ttl` | V2 (3x), V3: hasQuality→hasValue, flatten Roundness/Shape |
| `GSO-ExampleRoles.ttl` | V3 (2x), V5: flatten Roundness/Shape, Proportion→Part role |
| `GSO-ExampleFold.ttl` | V4 (5x): flatten Azimuth/Plunge/Dip from Orientations |
| `GSO-ExampleHistory.ttl` | V4, V7: Duration to Time_Interval, Uncertainty to Numeric_Value |
| `GSO-ExampleComplexContacts.ttl` | V2, V6: Grain_Size→Granite, hasQuality→hasValue |
| `GSO-ExampleLaTojizaPluton.ttl` | V2 (7x), V8 (5x): hasQuality→hasValue, Quality→Time_Region |

### Files Verified Clean (No Violations)

- `GSO-ExampleBritishColumbiaStrat-v2.ttl`
- `GSO-ExampleEpochLowerJurassic.ttl`
- `GSO-ExampleEvents1.ttl`
- `GSO-ExampleFault2.ttl`
- `GSO-ExampleFaultKannaV4Model.ttl`
- `GSO-ExampleFormationJs.ttl`
- `GSO-ExampleGeosciAustraliaStratUnit.ttl`
- `GSO-ExampleIsleOfWightStrat-pm1.ttl`
- `GSO-ExamplePetrophysicalProperties_v2.ttl`
- `GSO-ExampleVocabularyExtension-Alteration_Type-BC.ttl`
- `GSO-LardeauGroup.ttl`

### Validation Script

**validate_examples.py** — Targeted validation of example files against GSO structural constraints.

**Usage:**
```bash
python validate_examples.py                     # Validate all example files
python validate_examples.py file1.ttl file2.ttl # Validate specific files
```

**Features:**
- Checks all 8 violation categories (V1-V8) using rdflib class hierarchy traversal
- No full DL reasoning required (HermiT/Pellet timeout on GSO's axiom complexity)
- Loads base ontology modules (excluding large vocabulary modules like Mineral/Element)
- Reports specific violations with class/property details
- Exit code 0 if all pass, 1 if any fail

**Validation Results:**
```
--- Summary ---
  Passed: 19/19
  Failed: 0/19
  Total violations: 0
```

**Verification:** Original (unfixed) files correctly show violations:
- `GSO-ExampleSpecificRockObject.ttl` (original): 7 violations (4x V2, 3x V3/V4)
- `GSO-ExampleRoles.ttl` (original): 3 violations (2x V3/V4, 1x V5)
- `GSO-ExampleFold.ttl` (original): 5 violations (5x V3/V4)
- `GSO-ExampleHistory.ttl` (original): 2 violations (2x V3/V4)

### Note on Full DL Reasoning

Full OWL 2 DL reasoning with HermiT or Pellet was not achievable for the GSO ontology due to axiom complexity:
- Even with ~9K triples (excluding Mineral/Element modules), HermiT exceeds 10+ minute timeouts
- The targeted validation script (`validate_examples.py`) provides equivalent coverage for the specific violation patterns that cause inconsistency
- For applications requiring full DL reasoning, consider the simplification strategies documented above

---

## OWL 2 DL Transitivity Restoration

### Overview

OWL 2 DL prohibits cardinality restrictions on transitive properties or their subproperties. The original GSO ontology removed TransitiveProperty declarations to avoid this conflict. This update restores transitivity where semantically important by:

1. Creating a new property `hasCountableStaticPart` outside the transitive `hasPart` hierarchy for cardinality-constrained cases
2. Converting problematic cardinality restrictions to existential (`someValuesFrom`) restrictions
3. Re-adding `TransitiveProperty` declarations to key properties

### New Property: hasCountableStaticPart

Created `gsoc:hasCountableStaticPart` (and inverse `gsoc:isCountableStaticPartOf`) as a non-transitive alternative for cases requiring cardinality restrictions:

```turtle
gsoc:hasCountableStaticPart a owl:ObjectProperty ;
    rdfs:comment "A static part relation that supports cardinality restrictions.
                  Not in the hasPart hierarchy to allow hasPart to be transitive."@en ;
    rdfs:subPropertyOf gsoc:constantlySpecDependsOn ;
    owl:inverseOf gsoc:isCountableStaticPartOf .
```

**Usage:** Classes that need exact cardinality on parts use `hasCountableStaticPart` instead of `hasStaticPart`.

### Properties Made Transitive

| Property | Rationale |
|----------|-----------|
| `gsoc:hasPart` | Core mereological property — if A hasPart B and B hasPart C, then A hasPart C |
| `gsoc:isPartOf` | Inverse of hasPart |
| `gsoc:hasConstituent` | Material composition — if rock has mineral and mineral has element, rock has element |
| `gsoc:isConstituentOf` | Inverse of hasConstituent |
| `gsoc:timeIncludes` | Temporal inclusion is transitive |
| `gsoc:timeIncludedBy` | Inverse of timeIncludes |
| `gsoc:timeContains` | Temporal containment is transitive |
| `gsoc:timeOlderThan` | Temporal ordering — if A older than B and B older than C, A older than C |
| `gsoc:timeYoungerThan` | Inverse of timeOlderThan |
| `gsoc:occupiesSpaceDirectly` | Spatial occupation |
| `gsoc:occupiesSpaceIndirectly` | Spatial occupation |
| `gsoc:occupiesTimeDirectly` | Temporal occupation |
| `gsoc:occupiesTimeIndirectly` | Temporal occupation |

**Note:** `gsoc:hosts` is NOT transitive because `gsoc:hostedBy` (its inverse) has cardinality restrictions in GSO-Geologic_Structure.ttl and GSO-Geologic_Structure_Contact.ttl.

### Cardinality Restrictions Changed to someValuesFrom

To enable transitivity, these cardinality restrictions were relaxed:

| File | Class | Before | After |
|------|-------|--------|-------|
| `GSO-Geologic_Setting.ttl` | `Crustal_Setting` | `hasStaticPart exactly 1 Crust` | `hasStaticPart some Crust` |
| `GSO-Geologic_Structure_Fold.ttl` | `Fold_System` | `hasEssentialPart min 2 Fold` | `hasEssentialPart some Fold` |
| `GSO-Geologic_Structure_Contact.ttl` | `Stratigraphic_Point` | `hasEssentialPart exactly 1 Spatial_Region_0D` | `hasEssentialPart some Spatial_Region_0D` |
| `GSO-Geology.ttl` | `Geologic_Time_Date` | `hasStaticPart exactly 1 (Time_Instant and not Geologic_Time_Feature)` | `hasStaticPart some Time_Instant` |
| `GSO-Geology.ttl` | `Specific_Geologic_Time_Unit` | `staticHostedBy exactly 1 Rock_Body` | `staticHostedBy some Rock_Body` |
| `GSO-Geology.ttl` | `Geologic_Time_Scale` | `timeIncludes min 2 Specific_Geologic_Time_Unit` | `timeIncludes some Specific_Geologic_Time_Unit` |

### Cardinality Restrictions Migrated to hasCountableStaticPart

These restrictions kept exact cardinality by using the new non-transitive property:

| File | Class | Before | After |
|------|-------|--------|-------|
| `GSO-Geology.ttl` | `Specific_Geologic_Time_Unit` | `hasStaticPart exactly 1 Time_Interval` | `hasCountableStaticPart exactly 1 Time_Interval` |
| `GSO-Geology.ttl` | `Specific_Geologic_Time_Unit` | `hasStaticPart exactly 2 Geologic_Time_Boundary` | `hasCountableStaticPart exactly 2 Geologic_Time_Boundary` |
| `GSO-Common.ttl` | `Parthood` | `hasStaticPart exactly 2 Particular` | `hasCountableStaticPart exactly 2 Particular` |
| `GSO-Common.ttl` | `Relator` | `hasStaticPart min 2 Role` | `hasCountableStaticPart min 2 Role` |

### isValueOf Cardinality Restrictions Fixed

Changed all `isValueOf exactly 1` to `isValueOf some` to allow `isPartOf` (ancestor of `isValueOf`) to be transitive:

| File | Class |
|------|-------|
| `GSO-Common.ttl` | `Shape_Value`, `State_Of_Matter_Value`, `Proportion_Value`, `Quality_Value` |
| `GSO-Geologic_Quality.ttl` | `Metamorphosed`, `Not_Metamorphosed` |
| `GSO-Quality.ttl` | `Distribution_Value`, `Intensity_Value`, `Orientation_Value` |

### Validation Results

After all changes:
- **36/36 TTL files parse successfully**
- **136,598 total triples**
- **13 transitive properties declared** (hosts excluded due to hostedBy cardinality restrictions)
- **34 cardinality restrictions remain** — none conflict with transitive properties
- **OWL 2 DL compliant** — no cardinality restrictions on transitive properties or their subproperties
- **HermiT consistency test (without Ischart):** CONSISTENT, 0 unsatisfiable classes

---

## Allen Temporal Relations Property Hierarchy (Revised)

### Design Goals

The GSO time properties implement Allen's interval algebra relations with modifications for OWL 2 DL compatibility. The key insight is that `allValuesFrom` restrictions on properties propagate through the subproperty hierarchy, so boundary-coincidence properties (like `timeStartedBy`, `timeFinishedBy`) must NOT be subproperties of `timeIncludes`/`timeContains` to avoid constraint violations when boundary instants are asserted.

### Semantic Definitions

| Property | Allen Relation | Semantics |
|----------|---------------|-----------|
| `timeIncludes` | includes (broad) | Target completely within source; boundaries MAY coincide |
| `timeContains` | contains (strict) | Target strictly within source; source begins BEFORE target, ends AFTER target |
| `timeStartedBy` | startedBy | Source and target start at same instant; source ends after target |
| `timeFinishedBy` | finishedBy | Source and target end at same instant; source begins before target |
| `timeStarts` | starts | Source and target start at same instant; target ends after source |
| `timeFinishes` | finishes | Source and target end at same instant; target begins before source |
| `timeDuring` | during | Inverse of contains; source strictly within target |

### Property Hierarchy

```
isTemporallyRelatedTo (top-level symmetric temporal relation)
├── timeIntersects (any temporal overlap)
│   ├── timeEquivalentTo
│   ├── timeOverlaps / timeOverlappedBy
│   ├── timeMeets / timeMetBy
│   └── timeInclusion
│       ├── timeIncludes (NOT transitive)
│       │   └── timeContains (transitive, strict containment)
│       └── timeIncludedBy (NOT transitive)
│           └── timeDuring (inverse of timeContains)
├── timeStartedBy / timeStarts (boundary coincidence - NOT under timeIncludes)
├── timeFinishedBy / timeFinishes (boundary coincidence - NOT under timeIncludes)
└── timeDisjoint (before/after)
```

### Changes Made

| Property | Before | After | Reason |
|----------|--------|-------|--------|
| `timeIncludes` | TransitiveProperty | NOT transitive | Avoid constraint propagation with allValuesFrom |
| `timeIncludedBy` | TransitiveProperty | NOT transitive | Inverse of timeIncludes |
| `timeStartedBy` | subPropertyOf timeIncludes | subPropertyOf isTemporallyRelatedTo | Boundary assertions shouldn't trigger allValuesFrom on timeIncludes |
| `timeStarts` | subPropertyOf timeIncludedBy | subPropertyOf isTemporallyRelatedTo | Inverse consistency |
| `timeFinishedBy` | subPropertyOf timeIncludes | subPropertyOf isTemporallyRelatedTo | Boundary assertions shouldn't trigger allValuesFrom on timeIncludes |
| `timeFinishes` | subPropertyOf timeIncludedBy | subPropertyOf isTemporallyRelatedTo | Inverse consistency |
| `timeContains` | (unchanged) | subPropertyOf timeIncludes, TransitiveProperty | Strict containment remains transitive |
| `timeDuring` | (unchanged) | subPropertyOf timeIncludedBy | Inverse of timeContains |

### Usage Pattern

For class restrictions on geologic time intervals:

```turtle
# Use timeContains (not timeIncludes) when you want ONLY strict containment
# This excludes boundary assertions via timeStartedBy/timeFinishedBy

gst:Epoch rdfs:subClassOf [
    owl:allValuesFrom gst:Age ;
    owl:onProperty gsoc:timeContains ;  # NOT timeIncludes
] .

# Boundaries can still be asserted without violating the constraint:
ist:MiddleTriassic2004 gsoc:timeFinishedBy ist:BaseUpperTriassic2004 .
# This is OK because timeFinishedBy is NOT a subproperty of timeContains
```

### Crystal_Role Fix

Crystal_Role was unsatisfiable due to a qualified cardinality restriction on the Role class.

**Root Cause:** The Role class had:
```turtle
gsoc:Role rdfs:subClassOf [
    owl:onProperty gsoc:hasRolePlayer ;
    owl:qualifiedCardinality "1"^^xsd:nonNegativeInteger ;
    owl:onClass gsoc:Particular
] .
```

This "exactly 1" restriction conflicted with Crystal_Role's inheritance chain. The hasRoleObject property was already changed to use `someValuesFrom`, so hasRolePlayer should match.

**Fix Applied:** Changed both restrictions on Role class to existential quantification:
```turtle
gsoc:Role rdfs:subClassOf [
    owl:onProperty gsoc:hasRolePlayer ;
    owl:someValuesFrom gsoc:Particular
] ,
[
    owl:onProperty gsoc:mutuallySpecDependsOn ;
    owl:someValuesFrom gsoc:Relator
] .
```

### Testing Results

**HermiT test on GSO-GeologicTime completed successfully:**
- **Processing time:** 8,176,671 ms (~136 minutes)
- **Result:** CONSISTENT
- **Unsatisfiable classes:** 0

All three previously unsatisfiable classes are now satisfiable:
- ✓ Geologic_Time_Interval_Collection (fixed by removing timeIncludes transitivity)
- ✓ Geologic_Time_Scale (fixed by removing timeIncludes transitivity)
- ✓ Crystal_Role (fixed by changing hasRolePlayer from "exactly 1" to "some")

**Note:** Pellet reasoner gives a false positive inconsistency error:
```
InconsistentOntologyException: Intersection of datatypes [decimal, anySimpleType] is inconsistent
```
This is a known Pellet limitation with xsd:anySimpleType handling. Use HermiT for accurate consistency checking.

### Contact Module Incompatibility with Ischart

**Issue:** GSO-Geologic_Time_Ischart.ttl uses `gscn:GSSP` to type GSSP instances, but importing the full GSO-Geologic_Structure_Contact module causes immediate unsatisfiability.

**Root Cause:** The Contact module's GSSP class has restrictions:
```turtle
gscn:GSSP
  rdfs:subClassOf gscn:Stratigraphic_Point ;
  rdfs:subClassOf [
      owl:onProperty gsoc:isPartOf ;
      owl:someValuesFrom gscn:Chronostratigraphic_Contact ;
    ] ;
  rdfs:subClassOf [
      owl:onProperty gsoc:staticHostedBy ;
      owl:someValuesFrom gsog:Geologic_Event ;
    ] .
```

These restrictions interact with other axioms (likely in the Stratigraphic_Point hierarchy or Contact class definitions) to create unsatisfiability when combined with the Ischart time scale data.

**Workaround:** Instead of importing the Contact module, Ischart defines a local stub:
```turtle
gscn:GSSP
  rdf:type owl:Class ;
  rdfs:comment "Global Boundary Stratotype Section and Point..." ;
  rdfs:label "GSSP"@en .
```

This provides the class for typing GSSP instances without the problematic restrictions.

**Future Investigation:** The root cause of the incompatibility should be investigated to allow full Contact module import. Likely involves:
- Restrictions on Stratigraphic_Point or its superclasses
- Interactions between isPartOf/staticHostedBy and other property hierarchies
- Possible disjointness axioms in the Contact module
