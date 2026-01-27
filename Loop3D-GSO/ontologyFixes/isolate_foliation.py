#!/usr/bin/env python3
"""Isolate the exact cause of Foliation unsatisfiability."""

import sys
import os
import tempfile
import time

java_home = os.environ.get('JAVA_HOME_64', r'C:\Program Files\OpenJDK\jdk-25')
if os.path.exists(java_home):
    os.environ['JAVA_HOME'] = java_home
    os.environ['PATH'] = os.path.join(java_home, 'bin') + os.pathsep + os.environ.get('PATH', '')

import owlready2
from owlready2 import get_ontology, sync_reasoner_hermit, default_world, OwlReadyInconsistentOntologyError
from rdflib import Graph, OWL, RDF, RDFS, URIRef, BNode, Namespace

owlready2.reasoning.JAVA_MEMORY = 4000

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

GSOC = Namespace("https://w3id.org/gso/1.0/common/")
GSOG = Namespace("https://w3id.org/gso/1.0/geology/")
GSOS = Namespace("https://w3id.org/gso/1.0/geologicstructure/")
GSGQ = Namespace("https://w3id.org/gso/1.0/geologicquality/")
GSOQ = Namespace("https://w3id.org/gso/1.0/quality/")


def test_graph(g, label=""):
    """Test a graph for consistency."""
    # Remove imports
    for s, p, o in list(g.triples((None, OWL.imports, None))):
        g.remove((s, p, o))

    fd, temp_file = tempfile.mkstemp(suffix='.rdf')
    os.close(fd)
    g.serialize(destination=temp_file, format='xml')

    try:
        default_world.ontologies.clear()
        onto = get_ontology(f"file://{os.path.abspath(temp_file)}").load()

        start = time.time()
        try:
            sync_reasoner_hermit(onto, infer_property_values=False, debug=0,
                               ignore_unsupported_datatypes=True)
        except OwlReadyInconsistentOntologyError:
            elapsed = time.time() - start
            return "INCONSISTENT", elapsed, []

        unsatisfiable = list(default_world.inconsistent_classes())
        unsatisfiable = [c for c in unsatisfiable if str(c) != 'owl.Nothing']

        elapsed = time.time() - start
        if unsatisfiable:
            unsat_names = sorted(set(str(c).split('.')[-1] for c in unsatisfiable))
            return "UNSATISFIABLE", elapsed, unsat_names
        else:
            return "CONSISTENT", elapsed, []

    finally:
        os.remove(temp_file)


def load_base():
    """Load base ontology files."""
    import glob
    patterns = [
        os.path.join(BASE_DIR, "GSO-Common.ttl"),
        os.path.join(BASE_DIR, "GSO-Geology.ttl"),
        os.path.join(BASE_DIR, "GSO-Master.ttl"),
        os.path.join(BASE_DIR, "GSO-Element.ttl"),
        os.path.join(BASE_DIR, "GSO-Feature.ttl"),
        os.path.join(BASE_DIR, "Modules", "GSO-Quality.ttl"),
        os.path.join(BASE_DIR, "Modules", "GSO-Perdurant.ttl"),
        os.path.join(BASE_DIR, "Modules", "GSO-QUDTvoc.ttl"),
        os.path.join(BASE_DIR, "Modules", "GSO-skos_annotation.ttl"),
        os.path.join(BASE_DIR, "Modules", "GSO-Geologic_Quality.ttl"),
        os.path.join(BASE_DIR, "Modules", "GSO-Geologic_Structure.ttl"),
    ]

    g = Graph()
    for f in patterns:
        if os.path.exists(f):
            g.parse(f, format='turtle')
    return g


def remove_restriction(g, class_uri, prop_uri, restriction_type=None, filler_uri=None):
    """Remove a specific restriction from a class."""
    removed = 0
    for s, p, o in list(g.triples((class_uri, RDFS.subClassOf, None))):
        if isinstance(o, BNode):
            # Check if it's a restriction
            if (o, RDF.type, OWL.Restriction) in g:
                prop = None
                for _, _, prop_val in g.triples((o, OWL.onProperty, None)):
                    prop = prop_val
                if prop == prop_uri:
                    if restriction_type and filler_uri:
                        if (o, restriction_type, filler_uri) in g:
                            # Remove this restriction
                            g.remove((s, p, o))
                            # Remove all triples about the bnode
                            for t in list(g.triples((o, None, None))):
                                g.remove(t)
                            removed += 1
                    elif restriction_type is None:
                        # Remove any restriction on this property
                        g.remove((s, p, o))
                        for t in list(g.triples((o, None, None))):
                            g.remove(t)
                        removed += 1
    return removed


def main():
    print("Loading base ontology...", flush=True)
    base_g = load_base()
    print(f"Loaded {len(base_g)} triples", flush=True)

    # Test 1: Baseline (should show Foliation, Lineation unsatisfiable)
    print(f"\n{'='*70}", flush=True)
    print("TEST 1: Baseline", flush=True)
    g = Graph()
    for t in base_g:
        g.add(t)
    result, elapsed, unsat = test_graph(g)
    print(f"Result: {result} ({elapsed:.1f}s) - {unsat}", flush=True)

    # Test 2: Remove hasQuality restriction from Foliation
    print(f"\n{'='*70}", flush=True)
    print("TEST 2: Remove hasQuality from Foliation", flush=True)
    g = Graph()
    for t in base_g:
        g.add(t)
    n = remove_restriction(g, GSOS.Foliation, GSOC.hasQuality)
    print(f"  Removed {n} restrictions", flush=True)
    result, elapsed, unsat = test_graph(g)
    print(f"Result: {result} ({elapsed:.1f}s) - {unsat}", flush=True)

    # Test 3: Remove hasQuality from both Foliation and Lineation
    print(f"\n{'='*70}", flush=True)
    print("TEST 3: Remove hasQuality from both Foliation and Lineation", flush=True)
    g = Graph()
    for t in base_g:
        g.add(t)
    n1 = remove_restriction(g, GSOS.Foliation, GSOC.hasQuality)
    n2 = remove_restriction(g, GSOS.Lineation, GSOC.hasQuality)
    print(f"  Removed {n1 + n2} restrictions", flush=True)
    result, elapsed, unsat = test_graph(g)
    print(f"Result: {result} ({elapsed:.1f}s) - {unsat}", flush=True)

    # Test 4: Change Foliation's hasQuality to use Nonphysical_Quality instead
    # (keep hasQuality but point to a quality that's NOT Physical_Quality)
    print(f"\n{'='*70}", flush=True)
    print("TEST 4: Change Foliation hasQuality to some Quality (not Physical_Quality)", flush=True)
    g = Graph()
    for t in base_g:
        g.add(t)
    remove_restriction(g, GSOS.Foliation, GSOC.hasQuality)
    # Add hasQuality some Quality (generic)
    bn = BNode()
    g.add((GSOS.Foliation, RDFS.subClassOf, bn))
    g.add((bn, RDF.type, OWL.Restriction))
    g.add((bn, OWL.onProperty, GSOC.hasQuality))
    g.add((bn, OWL.someValuesFrom, GSOC.Quality))
    result, elapsed, unsat = test_graph(g)
    print(f"Result: {result} ({elapsed:.1f}s) - {unsat}", flush=True)

    # Test 5: Change Physical_Quality isQualityOf back to just Physical_Endurant
    print(f"\n{'='*70}", flush=True)
    print("TEST 5: Revert Physical_Quality isQualityOf to just Physical_Endurant", flush=True)
    g = Graph()
    for t in base_g:
        g.add(t)
    # Find and modify the Physical_Quality restriction
    for s, p, o in list(g.triples((GSOC.Physical_Quality, RDFS.subClassOf, None))):
        if isinstance(o, BNode):
            if (o, OWL.onProperty, GSOC.isQualityOf) in g:
                # Check for qualifiedCardinality
                if (o, OWL.qualifiedCardinality, None) in g:
                    # Remove the union class and replace with just Physical_Endurant
                    for _, _, onclass in list(g.triples((o, OWL.onClass, None))):
                        if isinstance(onclass, BNode):
                            # Remove the union
                            for t in list(g.triples((onclass, None, None))):
                                g.remove(t)
                            g.remove((o, OWL.onClass, onclass))
                    g.add((o, OWL.onClass, GSOC.Physical_Endurant))
                    print("  Reverted Physical_Quality isQualityOf to Physical_Endurant only", flush=True)
    result, elapsed, unsat = test_graph(g)
    print(f"Result: {result} ({elapsed:.1f}s) - {unsat}", flush=True)

    # Test 6: Check if Nonphysical_Feature restrictions cause the issue
    print(f"\n{'='*70}", flush=True)
    print("TEST 6: Remove hasEssentialPart restrictions from Nonphysical_Feature", flush=True)
    g = Graph()
    for t in base_g:
        g.add(t)
    n1 = remove_restriction(g, GSOC.Nonphysical_Feature, GSOC.hasEssentialPart)
    print(f"  Removed {n1} restrictions from Nonphysical_Feature", flush=True)
    result, elapsed, unsat = test_graph(g)
    print(f"Result: {result} ({elapsed:.1f}s) - {unsat}", flush=True)

    # Test 7: Remove hasEssentialPart from Inherant_Feature
    print(f"\n{'='*70}", flush=True)
    print("TEST 7: Remove hasEssentialPart restrictions from Inherant_Feature", flush=True)
    g = Graph()
    for t in base_g:
        g.add(t)
    n1 = remove_restriction(g, GSOC.Inherant_Feature, GSOC.hasEssentialPart)
    print(f"  Removed {n1} restrictions from Inherant_Feature", flush=True)
    result, elapsed, unsat = test_graph(g)
    print(f"Result: {result} ({elapsed:.1f}s) - {unsat}", flush=True)


if __name__ == "__main__":
    main()
