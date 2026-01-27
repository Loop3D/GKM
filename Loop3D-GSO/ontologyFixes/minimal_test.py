#!/usr/bin/env python3
"""Build minimal ontology to isolate Foliation unsatisfiability."""

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
from rdflib import Graph, OWL, RDF, RDFS, URIRef, BNode, Namespace, XSD, Literal

owlready2.reasoning.JAVA_MEMORY = 4000

EX = Namespace("http://example.org/test/")


def build_ontology(exclude=None):
    """Build minimal ontology. Exclude is a set of axiom labels to skip."""
    if exclude is None:
        exclude = set()

    g = Graph()
    g.bind("ex", EX)
    g.bind("owl", OWL)
    g.bind("rdfs", RDFS)

    # Ontology declaration
    onto_uri = URIRef("http://example.org/test/ontology")
    g.add((onto_uri, RDF.type, OWL.Ontology))

    # Declare all classes
    classes = [
        "Particular", "Endurant", "Feature",
        "Physical_Endurant", "Nonphysical_Endurant",
        "Endurant_Feature", "Nonphysical_Feature", "Inherant_Feature", "Pattern_Feature",
        "Inherant", "Quality", "Physical_Quality", "Nonphysical_Quality",
        "Orientation", "Plane_Orientation",
        "Fabric", "Geologic_Structure", "Foliation",
    ]
    for c in classes:
        g.add((EX[c], RDF.type, OWL.Class))

    # Declare all properties
    obj_props = [
        "hasQuality", "isQualityOf", "hasInherant", "inheresIn",
        "hasEssentialPart", "hasPart", "isPartOf", "parthood",
        "hasDependent", "dependsOn", "dependance",
    ]
    for p in obj_props:
        g.add((EX[p], RDF.type, OWL.ObjectProperty))

    # Helper functions
    def add_axiom(label, triples):
        if label not in exclude:
            for t in triples:
                g.add(t)

    def subclass(child, parent, label=None):
        lbl = label or f"{child}_sub_{parent}"
        add_axiom(lbl, [(EX[child], RDFS.subClassOf, EX[parent])])

    def only_restriction(cls, prop, filler, label):
        if label not in exclude:
            bn = BNode()
            g.add((EX[cls], RDFS.subClassOf, bn))
            g.add((bn, RDF.type, OWL.Restriction))
            g.add((bn, OWL.onProperty, EX[prop]))
            g.add((bn, OWL.allValuesFrom, EX[filler]))

    def some_restriction(cls, prop, filler, label):
        if label not in exclude:
            bn = BNode()
            g.add((EX[cls], RDFS.subClassOf, bn))
            g.add((bn, RDF.type, OWL.Restriction))
            g.add((bn, OWL.onProperty, EX[prop]))
            g.add((bn, OWL.someValuesFrom, EX[filler]))

    def exactly1_union_restriction(cls, prop, fillers, label):
        """Add: cls subClassOf (prop exactly 1 (filler1 OR filler2))"""
        if label not in exclude:
            bn = BNode()
            union_bn = BNode()
            g.add((EX[cls], RDFS.subClassOf, bn))
            g.add((bn, RDF.type, OWL.Restriction))
            g.add((bn, OWL.onProperty, EX[prop]))
            g.add((bn, OWL.qualifiedCardinality, Literal(1, datatype=XSD.nonNegativeInteger)))
            g.add((bn, OWL.onClass, union_bn))
            g.add((union_bn, RDF.type, OWL.Class))
            # Build RDF list for union
            curr = BNode()
            g.add((union_bn, OWL.unionOf, curr))
            for i, filler in enumerate(fillers):
                g.add((curr, RDF.first, EX[filler]))
                if i < len(fillers) - 1:
                    next_bn = BNode()
                    g.add((curr, RDF.rest, next_bn))
                    curr = next_bn
                else:
                    g.add((curr, RDF.rest, RDF.nil))

    def exactly1_restriction(cls, prop, filler, label):
        """Add: cls subClassOf (prop exactly 1 filler)"""
        if label not in exclude:
            bn = BNode()
            g.add((EX[cls], RDFS.subClassOf, bn))
            g.add((bn, RDF.type, OWL.Restriction))
            g.add((bn, OWL.onProperty, EX[prop]))
            g.add((bn, OWL.qualifiedCardinality, Literal(1, datatype=XSD.nonNegativeInteger)))
            g.add((bn, OWL.onClass, EX[filler]))

    # === CLASS HIERARCHY ===
    subclass("Endurant", "Particular")
    subclass("Feature", "Particular")
    subclass("Physical_Endurant", "Endurant")
    subclass("Nonphysical_Endurant", "Endurant")
    subclass("Endurant_Feature", "Feature")
    subclass("Nonphysical_Feature", "Endurant_Feature")
    subclass("Inherant_Feature", "Nonphysical_Feature")
    subclass("Pattern_Feature", "Inherant_Feature")
    subclass("Inherant", "Nonphysical_Endurant")
    subclass("Quality", "Inherant")
    subclass("Physical_Quality", "Quality")
    subclass("Nonphysical_Quality", "Quality")
    subclass("Orientation", "Physical_Quality")
    subclass("Plane_Orientation", "Orientation")
    subclass("Fabric", "Pattern_Feature")
    subclass("Geologic_Structure", "Endurant_Feature")
    subclass("Fabric", "Geologic_Structure", "Fabric_sub_GeoStruct")
    subclass("Foliation", "Fabric")

    # === DISJOINTNESS ===
    add_axiom("PE_disjoint_NE", [(EX.Physical_Endurant, OWL.disjointWith, EX.Nonphysical_Endurant)])
    add_axiom("PQ_disjoint_NQ", [(EX.Physical_Quality, OWL.disjointWith, EX.Nonphysical_Quality)])

    # === CLASS RESTRICTIONS ===
    only_restriction("Nonphysical_Endurant", "hasPart", "Nonphysical_Endurant", "NE_hasPart_only_NE")
    only_restriction("Nonphysical_Endurant", "hasQuality", "Nonphysical_Quality", "NE_hasQuality_only_NQ")
    only_restriction("Physical_Endurant", "hasPart", "Physical_Endurant", "PE_hasPart_only_PE")
    only_restriction("Physical_Endurant", "hasQuality", "Physical_Quality", "PE_hasQuality_only_PQ")
    only_restriction("Nonphysical_Feature", "hasEssentialPart", "Nonphysical_Endurant", "NF_hasEP_only_NE")
    some_restriction("Nonphysical_Feature", "hasEssentialPart", "Nonphysical_Endurant", "NF_hasEP_some_NE")
    only_restriction("Inherant_Feature", "hasEssentialPart", "Inherant", "IF_hasEP_only_Inh")
    some_restriction("Inherant_Feature", "hasEssentialPart", "Inherant", "IF_hasEP_some_Inh")
    only_restriction("Inherant", "hasPart", "Inherant", "Inh_hasPart_only_Inh")
    exactly1_restriction("Inherant", "inheresIn", "Particular", "Inh_inheresIn_1_Part")
    exactly1_restriction("Quality", "isQualityOf", "Particular", "Q_isQualityOf_1_Part")
    exactly1_union_restriction("Physical_Quality", "isQualityOf",
                               ["Physical_Endurant", "Endurant_Feature"], "PQ_isQualityOf")

    # Foliation hasQuality
    some_restriction("Foliation", "hasQuality", "Plane_Orientation", "Fol_hasQ_PO")

    # === PROPERTY HIERARCHY ===
    add_axiom("hQ_sub_hInh", [(EX.hasQuality, RDFS.subPropertyOf, EX.hasInherant)])
    add_axiom("hQ_range_Q", [(EX.hasQuality, RDFS.range, EX.Quality)])
    add_axiom("hQ_inv_iQO", [(EX.hasQuality, OWL.inverseOf, EX.isQualityOf)])
    add_axiom("iQO_dom_Q", [(EX.isQualityOf, RDFS.domain, EX.Quality)])
    add_axiom("iQO_sub_iIn", [(EX.isQualityOf, RDFS.subPropertyOf, EX.inheresIn)])
    add_axiom("iIn_dom_Inh", [(EX.inheresIn, RDFS.domain, EX.Inherant)])
    add_axiom("iIn_func", [(EX.inheresIn, RDF.type, OWL.FunctionalProperty)])
    add_axiom("hInh_range_Inh", [(EX.hasInherant, RDFS.range, EX.Inherant)])
    add_axiom("hInh_inv_iIn", [(EX.hasInherant, OWL.inverseOf, EX.inheresIn)])
    add_axiom("hInh_sub_hDep", [(EX.hasInherant, RDFS.subPropertyOf, EX.hasDependent)])
    add_axiom("hEP_sub_hP", [(EX.hasEssentialPart, RDFS.subPropertyOf, EX.hasPart)])
    add_axiom("hP_sub_part", [(EX.hasPart, RDFS.subPropertyOf, EX.parthood)])
    add_axiom("hP_inv_iPO", [(EX.hasPart, OWL.inverseOf, EX.isPartOf)])
    add_axiom("part_sym", [(EX.parthood, RDF.type, OWL.SymmetricProperty)])
    add_axiom("hDep_inv_dOn", [(EX.hasDependent, OWL.inverseOf, EX.dependsOn)])
    add_axiom("dOn_sub_dep", [(EX.dependsOn, RDFS.subPropertyOf, EX.dependance)])
    add_axiom("hDep_sub_dep", [(EX.hasDependent, RDFS.subPropertyOf, EX.dependance)])
    add_axiom("dep_sym", [(EX.dependance, RDF.type, OWL.SymmetricProperty)])

    return g


def test_graph(g, label=""):
    """Test a graph for consistency."""
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


def main():
    # Test 1: Full minimal ontology
    print("=" * 70, flush=True)
    print("TEST 1: Full minimal ontology", flush=True)
    g = build_ontology()
    result, elapsed, unsat = test_graph(g)
    print(f"Result: {result} ({elapsed:.1f}s) - {unsat}", flush=True)

    if result == "CONSISTENT":
        print("\nMinimal ontology is CONSISTENT - more axioms needed.", flush=True)
        return

    # Test 2: Remove each axiom one at a time to find which ones fix the issue
    print(f"\n{'='*70}", flush=True)
    print("TEST 2: Remove axioms one at a time", flush=True)
    print("=" * 70, flush=True)

    axioms_to_test = [
        # Class restrictions
        "NE_hasQuality_only_NQ",
        "PE_hasQuality_only_PQ",
        "NE_hasPart_only_NE",
        "PE_hasPart_only_PE",
        "NF_hasEP_only_NE",
        "NF_hasEP_some_NE",
        "IF_hasEP_only_Inh",
        "IF_hasEP_some_Inh",
        "Inh_hasPart_only_Inh",
        "Inh_inheresIn_1_Part",
        "Q_isQualityOf_1_Part",
        "PQ_isQualityOf",
        "Fol_hasQ_PO",
        # Disjointness
        "PE_disjoint_NE",
        "PQ_disjoint_NQ",
        # Property axioms
        "hQ_sub_hInh",
        "hQ_range_Q",
        "hQ_inv_iQO",
        "iQO_dom_Q",
        "iQO_sub_iIn",
        "iIn_dom_Inh",
        "iIn_func",
        "hInh_range_Inh",
        "hInh_inv_iIn",
        "hInh_sub_hDep",
        "hEP_sub_hP",
        "hP_sub_part",
        "hP_inv_iPO",
        "part_sym",
        "hDep_inv_dOn",
        "dOn_sub_dep",
        "hDep_sub_dep",
        "dep_sym",
        # Hierarchy
        "Fabric_sub_GeoStruct",
    ]

    fixes = []
    for axiom in axioms_to_test:
        g = build_ontology(exclude={axiom})
        result, elapsed, unsat = test_graph(g)
        if result == "CONSISTENT":
            print(f"  Without {axiom}: *** FIXES *** ({elapsed:.1f}s)", flush=True)
            fixes.append(axiom)
        else:
            print(f"  Without {axiom}: still {result} ({elapsed:.1f}s)", flush=True)

    if fixes:
        print(f"\n{'='*70}", flush=True)
        print(f"AXIOMS THAT FIX WHEN REMOVED:", flush=True)
        for f in fixes:
            print(f"  - {f}", flush=True)


if __name__ == "__main__":
    main()
