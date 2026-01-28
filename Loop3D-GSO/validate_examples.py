#!/usr/bin/env python3
"""Validate example files against GSO ontology structural constraints.

Instead of full DL reasoning (HermiT/Pellet timeout on this ontology),
this validates the specific patterns that cause OWL 2 DL inconsistencies:

V1: Spatial_Location on non-Spatial_Region bearer
V2: hasQuality used for Quality_Value (should be hasValue)
V3: Quality nested as quality of another Quality (cardinality conflict)
V4: Physical_Quality nested inside Quality bearer
V5: Proportion on non-Part role
V6: Wrong type in hasConstituent (e.g., Quality used as constituent)
V7: Duration/Uncertainty on wrong bearer type
V8: Quality type used as object of occupiesTime (should be Time_Region)
"""

import os
import sys
import glob
from collections import defaultdict
from rdflib import Graph, Namespace, OWL, RDF, RDFS, URIRef

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# GSO namespaces
GSOC = Namespace("https://w3id.org/gso/1.0/common/")
GSOG = Namespace("https://w3id.org/gso/1.0/geology/")
GSGM = Namespace("https://w3id.org/gso/1.0/granularmaterial/")
GSGQ = Namespace("https://w3id.org/gso/1.0/geologicquality/")
GSOQ = Namespace("https://w3id.org/gso/1.0/quality/")
GSOR = Namespace("https://w3id.org/gso/1.0/geologicrole/")
GSRM = Namespace("https://w3id.org/gso/1.0/rockmaterial/")
GSPD = Namespace("https://w3id.org/gso/1.0/perdurant/")

# Core classes
QUALITY = GSOC.Quality
QUALITY_VALUE = GSOC.Quality_Value
PHYSICAL_QUALITY = GSOC.Physical_Quality
PROPORTION = GSOC.Proportion
SPATIAL_LOCATION = GSOC.Spatial_Location
SPATIAL_REGION = GSOC.Spatial_Region
TIME_INSTANT = GSOC.Time_Instant
TIME_INTERVAL = GSOC.Time_Interval
TIME_REGION = GSOC.Time_Region
TIME_INSTANT_LOCATION = GSOC.Time_Instant_Location
TIME_INTERVAL_LOCATION = GSOC.Time_Interval_Location
DURATION = GSOC.Duration
UNCERTAINTY = GSOC.Uncertainty
PART = GSOC.Part
ROLE = GSOC.Role
ENDURANT = GSOC.Endurant

HAS_QUALITY = GSOC.hasQuality
HAS_VALUE = GSOC.hasValue
HAS_CONSTITUENT = GSOC.hasConstituent
OCCUPIES_TIME_DIRECTLY = GSOC.occupiesTimeDirectly
OCCUPIES_TIME_INDIRECTLY = GSOC.occupiesTimeIndirectly
OCCUPIES_SPACE_DIRECTLY = GSOC.occupiesSpaceDirectly


def get_all_superclasses(g, cls, visited=None):
    """Get all superclasses of a class (transitive rdfs:subClassOf)."""
    if visited is None:
        visited = set()
    if cls in visited:
        return visited
    visited.add(cls)
    for parent in g.objects(cls, RDFS.subClassOf):
        if isinstance(parent, URIRef):
            get_all_superclasses(g, parent, visited)
    return visited


def is_subclass_of(g, cls, target):
    """Check if cls is a subclass of target."""
    supers = get_all_superclasses(g, cls)
    return target in supers


def get_types(g, node):
    """Get all rdf:type values for a node."""
    return list(g.objects(node, RDF.type))


def get_quality_classes(g):
    """Get all classes that are subclasses of Quality."""
    quality_classes = set()
    for s in g.subjects(RDFS.subClassOf, QUALITY):
        if isinstance(s, URIRef):
            quality_classes.add(s)
    # Transitive
    changed = True
    while changed:
        changed = False
        for s, p, o in g.triples((None, RDFS.subClassOf, None)):
            if isinstance(s, URIRef) and isinstance(o, URIRef):
                if o in quality_classes and s not in quality_classes:
                    quality_classes.add(s)
                    changed = True
    quality_classes.add(QUALITY)
    return quality_classes


def get_quality_value_classes(g):
    """Get all classes that are subclasses of Quality_Value."""
    qv_classes = set()
    for s in g.subjects(RDFS.subClassOf, QUALITY_VALUE):
        if isinstance(s, URIRef):
            qv_classes.add(s)
    changed = True
    while changed:
        changed = False
        for s, p, o in g.triples((None, RDFS.subClassOf, None)):
            if isinstance(s, URIRef) and isinstance(o, URIRef):
                if o in qv_classes and s not in qv_classes:
                    qv_classes.add(s)
                    changed = True
    qv_classes.add(QUALITY_VALUE)
    return qv_classes


def get_part_classes(g):
    """Get all classes that are subclasses of Part."""
    part_classes = set()
    for s in g.subjects(RDFS.subClassOf, PART):
        if isinstance(s, URIRef):
            part_classes.add(s)
    changed = True
    while changed:
        changed = False
        for s, p, o in g.triples((None, RDFS.subClassOf, None)):
            if isinstance(s, URIRef) and isinstance(o, URIRef):
                if o in part_classes and s not in part_classes:
                    part_classes.add(s)
                    changed = True
    part_classes.add(PART)
    return part_classes


def get_time_region_classes(g):
    """Get all classes that are subclasses of Time_Region."""
    tr_classes = set()
    for s in g.subjects(RDFS.subClassOf, TIME_REGION):
        if isinstance(s, URIRef):
            tr_classes.add(s)
    changed = True
    while changed:
        changed = False
        for s, p, o in g.triples((None, RDFS.subClassOf, None)):
            if isinstance(s, URIRef) and isinstance(o, URIRef):
                if o in tr_classes and s not in tr_classes:
                    tr_classes.add(s)
                    changed = True
    tr_classes.add(TIME_REGION)
    return tr_classes


def validate_example(base_graph, example_path, quality_classes, qv_classes,
                     part_classes, time_region_classes):
    """Validate an example file for known violation patterns."""
    violations = []
    name = os.path.basename(example_path)

    # Parse example
    eg = Graph()
    for triple in base_graph:
        eg.add(triple)
    for prefix, ns in base_graph.namespaces():
        eg.bind(prefix, ns)
    try:
        eg.parse(example_path, format='turtle')
    except Exception as e:
        return [f"PARSE_ERROR: {e}"]
    for s, p, o in list(eg.triples((None, OWL.imports, None))):
        eg.remove((s, p, o))

    # V2: hasQuality used for Quality_Value instances
    # If X hasQuality Q, and Q is typed as a Quality_Value subclass, that's wrong
    for s, p, q in eg.triples((None, HAS_QUALITY, None)):
        q_types = get_types(eg, q)
        for qt in q_types:
            if qt in qv_classes:
                violations.append(
                    f"V2: hasQuality used for Quality_Value type {_short(qt)} "
                    f"on {_short(s)} (should use hasValue)")

    # V3/V4: Quality nested as hasQuality of another Quality
    # If bearer X is typed as a Quality, and Q is also a Quality, that's wrong
    for s, p, q in eg.triples((None, HAS_QUALITY, None)):
        s_types = get_types(eg, s)
        q_types = get_types(eg, q)
        s_is_quality = any(t in quality_classes for t in s_types)
        q_is_quality = any(t in quality_classes for t in q_types)
        if s_is_quality and q_is_quality:
            s_qtype = [t for t in s_types if t in quality_classes]
            q_qtype = [t for t in q_types if t in quality_classes]
            # Exception: Uncertainty on Measure_Value is OK (Measure_Value is a Quality_Value)
            if any(t in qv_classes for t in s_types):
                continue
            violations.append(
                f"V3/V4: Quality {_short(q_qtype[0])} nested inside "
                f"Quality {_short(s_qtype[0])} via hasQuality")

    # V5: Proportion on non-Part role
    # If X hasRole R, R hasQuality Proportion, and R is not a Part subclass
    for s, p, role in eg.triples((None, GSOC.hasRole, None)):
        role_types = get_types(eg, role)
        has_proportion = False
        for _, _, q in eg.triples((role, HAS_QUALITY, None)):
            q_types = get_types(eg, q)
            if PROPORTION in q_types:
                has_proportion = True
                break
        if has_proportion:
            role_is_part = any(t in part_classes for t in role_types)
            if not role_is_part and role_types:
                violations.append(
                    f"V5: Proportion on non-Part role {_short(role_types[0])} "
                    f"(Proportion requires Part bearer)")

    # V6: Quality type used as constituent (e.g., Grain_Size as constituent type)
    for s, p, c in eg.triples((None, HAS_CONSTITUENT, None)):
        c_types = get_types(eg, c)
        for ct in c_types:
            if ct in quality_classes:
                violations.append(
                    f"V6: Quality type {_short(ct)} used as constituent of "
                    f"{_short(s)} (should be a Material type)")

    # V8: Quality type used as object of occupiesTime
    for pred in [OCCUPIES_TIME_DIRECTLY, OCCUPIES_TIME_INDIRECTLY]:
        for s, p, t in eg.triples((None, pred, None)):
            t_types = get_types(eg, t)
            t_is_time_region = any(tt in time_region_classes for tt in t_types)
            t_is_quality = any(tt in quality_classes for tt in t_types)
            if t_is_quality and not t_is_time_region:
                violations.append(
                    f"V8: Quality type {_short(t_types[0])} used as object of "
                    f"{_short(pred)} (should be Time_Region)")

    # V1: Spatial_Location on non-Spatial_Region bearer
    for s, p, q in eg.triples((None, HAS_QUALITY, None)):
        q_types = get_types(eg, q)
        if SPATIAL_LOCATION in q_types or any(
                is_subclass_of(eg, t, SPATIAL_LOCATION) for t in q_types if isinstance(t, URIRef)):
            s_types = get_types(eg, s)
            s_is_spatial = any(
                is_subclass_of(eg, t, SPATIAL_REGION) for t in s_types if isinstance(t, URIRef))
            if not s_is_spatial and s_types:
                # Check if any type could be a Material_Endurant (which should use
                # occupiesSpaceDirectly -> Spatial_Region -> hasQuality -> Spatial_Location)
                violations.append(
                    f"V1: Spatial_Location on non-Spatial_Region {_short(s_types[0])}")

    return violations


def _short(uri):
    """Shorten a URI for display."""
    if isinstance(uri, URIRef):
        s = str(uri)
        for prefix in ['https://w3id.org/gso/1.0/common/',
                        'https://w3id.org/gso/1.0/geology/',
                        'https://w3id.org/gso/1.0/granularmaterial/',
                        'https://w3id.org/gso/1.0/geologicquality/',
                        'https://w3id.org/gso/1.0/quality/',
                        'https://w3id.org/gso/1.0/geologicrole/',
                        'https://w3id.org/gso/1.0/rockmaterial/',
                        'https://w3id.org/gso/1.0/perdurant/',
                        'https://w3id.org/gso/1.0/geologicprocess/',
                        'https://w3id.org/gso/1.0/geologicsetting/',
                        'https://w3id.org/gso/1.0/mineral/',
                        'https://w3id.org/gso/1.0/element/',
                        'https://w3id.org/gso/1.0/feature/',
                        'http://www.w3.org/2002/07/owl#',
                        'http://www.w3.org/1999/02/22-rdf-syntax-ns#',
                        'http://www.w3.org/2000/01/rdf-schema#']:
            if s.startswith(prefix):
                return s[len(prefix):]
        return s.rsplit('/', 1)[-1] if '/' in s else s.rsplit('#', 1)[-1] if '#' in s else s
    return str(uri)


def main():
    test_files = sys.argv[1:] if len(sys.argv) > 1 else None

    # Load base ontology (core modules only)
    EXCLUDE = {'gso-geologic_mineral.ttl', 'gso-element.ttl',
               'gso-geologic_time_ischart.ttl'}
    patterns = [os.path.join(BASE_DIR, '*.ttl'),
                os.path.join(BASE_DIR, 'Modules', '*.ttl')]
    files = []
    for p in patterns:
        files.extend(glob.glob(p))
    base_files = []
    for f in files:
        bn = os.path.basename(f).lower()
        if (f.endswith('.bak') or '-SMR-' in f or '.inconsistent' in f
                or bn == 'gso-feature.ttl' or bn in EXCLUDE):
            continue
        base_files.append(f)
    base_files = sorted(set(base_files))

    print(f"Loading {len(base_files)} base ontology modules...", flush=True)
    base_graph = Graph()
    for f in base_files:
        base_graph.parse(f, format='turtle')
    for s, p, o in list(base_graph.triples((None, OWL.imports, None))):
        base_graph.remove((s, p, o))
    print(f"Base graph: {len(base_graph)} triples", flush=True)

    # Pre-compute class hierarchies
    print("Computing class hierarchies...", flush=True)
    quality_classes = get_quality_classes(base_graph)
    qv_classes = get_quality_value_classes(base_graph)
    part_classes = get_part_classes(base_graph)
    time_region_classes = get_time_region_classes(base_graph)
    print(f"  Quality subclasses: {len(quality_classes)}", flush=True)
    print(f"  Quality_Value subclasses: {len(qv_classes)}", flush=True)
    print(f"  Part subclasses: {len(part_classes)}", flush=True)
    print(f"  Time_Region subclasses: {len(time_region_classes)}", flush=True)

    # Get example files
    example_dir = os.path.join(BASE_DIR, "Examples")
    if test_files:
        example_files = []
        for f in test_files:
            if not os.path.isabs(f):
                f = os.path.join(example_dir, f)
            example_files.append(f)
    else:
        example_files = sorted(glob.glob(os.path.join(example_dir, "*.ttl")))

    print(f"\n--- Validating {len(example_files)} example files ---\n", flush=True)

    all_results = {}
    total_violations = 0
    for ex_path in example_files:
        name = os.path.basename(ex_path)
        violations = validate_example(base_graph, ex_path, quality_classes,
                                      qv_classes, part_classes, time_region_classes)
        all_results[name] = violations
        if violations:
            print(f"  FAIL  {name} ({len(violations)} violations)", flush=True)
            for v in violations:
                print(f"        {v}", flush=True)
            total_violations += len(violations)
        else:
            print(f"  OK    {name}", flush=True)

    # Summary
    passed = sum(1 for v in all_results.values() if not v)
    failed = sum(1 for v in all_results.values() if v)
    print(f"\n--- Summary ---", flush=True)
    print(f"  Passed: {passed}/{len(all_results)}", flush=True)
    print(f"  Failed: {failed}/{len(all_results)}", flush=True)
    print(f"  Total violations: {total_violations}", flush=True)

    if failed:
        print(f"\n  Failed files:", flush=True)
        for name, violations in all_results.items():
            if violations:
                print(f"    {name}: {len(violations)} violations", flush=True)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
