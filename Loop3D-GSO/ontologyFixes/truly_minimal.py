#!/usr/bin/env python3
"""
Create a truly minimal ontology to test the isPartOf inconsistency.
"""

import sys
import os
import tempfile
import time

# Check for 64-bit Java
java_home = os.environ.get('JAVA_HOME_64', r'C:\Program Files\OpenJDK\jdk-25')
if os.path.exists(java_home):
    os.environ['JAVA_HOME'] = java_home
    os.environ['PATH'] = os.path.join(java_home, 'bin') + os.pathsep + os.environ.get('PATH', '')
    print(f"Using 64-bit Java: {os.path.join(java_home, 'bin', 'java.exe')}")

import owlready2
from owlready2 import get_ontology, sync_reasoner_hermit, default_world, OwlReadyInconsistentOntologyError

owlready2.reasoning.JAVA_MEMORY = 4000


def test_ontology_string(turtle_content, test_name):
    """Test a minimal turtle ontology."""
    from rdflib import Graph

    print(f"\n{test_name}")
    print("=" * 70)

    # Parse turtle with rdflib and convert to RDF/XML
    g = Graph()
    g.parse(data=turtle_content, format='turtle')

    fd, temp_file = tempfile.mkstemp(suffix='.rdf')
    os.close(fd)
    g.serialize(destination=temp_file, format='xml')

    try:
        default_world.ontologies.clear()
        onto = get_ontology(f"file://{os.path.abspath(temp_file)}").load()

        classes = list(onto.classes())
        individuals = list(onto.individuals())
        print(f"  Loaded {len(classes)} classes, {len(individuals)} individuals")

        start = time.time()
        try:
            sync_reasoner_hermit(onto, infer_property_values=False, debug=0,
                               ignore_unsupported_datatypes=True)
        except OwlReadyInconsistentOntologyError:
            elapsed = time.time() - start
            print(f"  Result: INCONSISTENT ({elapsed:.1f}s)")
            return "INCONSISTENT"

        unsatisfiable = list(default_world.inconsistent_classes())
        unsatisfiable = [str(c) for c in unsatisfiable if str(c) != 'owl.Nothing']

        elapsed = time.time() - start
        if unsatisfiable:
            print(f"  Result: UNSATISFIABLE ({len(unsatisfiable)}) ({elapsed:.1f}s)")
            for u in unsatisfiable[:5]:
                print(f"    - {u}")
            return "UNSATISFIABLE"
        else:
            print(f"  Result: CONSISTENT ({elapsed:.1f}s)")
            return "CONSISTENT"

    finally:
        os.remove(temp_file)


def main():
    # Base prefixes
    prefixes = """
@prefix : <http://test.org/> .
@prefix owl: <http://www.w3.org/2002/07/owl#> .
@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .

<http://test.org/> rdf:type owl:Ontology .
"""

    # Test 1: Just Generic and Specific classes, disjoint
    test1 = prefixes + """
:Generic rdf:type owl:Class .
:Specific rdf:type owl:Class ;
    owl:disjointWith :Generic .
"""
    test_ontology_string(test1, "Test 1: Basic disjoint classes")

    # Test 2: Add hasPart and isPartOf
    test2 = prefixes + """
:hasPart rdf:type owl:ObjectProperty ;
    owl:inverseOf :isPartOf .
:isPartOf rdf:type owl:ObjectProperty .

:Generic rdf:type owl:Class .
:Specific rdf:type owl:Class ;
    owl:disjointWith :Generic .
"""
    test_ontology_string(test2, "Test 2: Add hasPart/isPartOf")

    # Test 3: Add hasEssentialPart as subPropertyOf hasPart
    test3 = prefixes + """
:hasPart rdf:type owl:ObjectProperty ;
    owl:inverseOf :isPartOf .
:isPartOf rdf:type owl:ObjectProperty .
:hasEssentialPart rdf:type owl:ObjectProperty ;
    rdfs:subPropertyOf :hasPart .

:Generic rdf:type owl:Class .
:Specific rdf:type owl:Class ;
    owl:disjointWith :Generic .
"""
    test_ontology_string(test3, "Test 3: Add hasEssentialPart")

    # Test 4: Generic requires hasEssentialPart some Specific
    test4 = prefixes + """
:hasPart rdf:type owl:ObjectProperty ;
    owl:inverseOf :isPartOf .
:isPartOf rdf:type owl:ObjectProperty .
:hasEssentialPart rdf:type owl:ObjectProperty ;
    rdfs:subPropertyOf :hasPart .

:Generic rdf:type owl:Class ;
    rdfs:subClassOf [
        rdf:type owl:Restriction ;
        owl:onProperty :hasEssentialPart ;
        owl:someValuesFrom :Specific
    ] .
:Specific rdf:type owl:Class ;
    owl:disjointWith :Generic .
"""
    test_ontology_string(test4, "Test 4: Generic requires hasEssentialPart some Specific")

    # Test 5: Add individual typed as Generic
    test5 = prefixes + """
:hasPart rdf:type owl:ObjectProperty ;
    owl:inverseOf :isPartOf .
:isPartOf rdf:type owl:ObjectProperty .
:hasEssentialPart rdf:type owl:ObjectProperty ;
    rdfs:subPropertyOf :hasPart .

:Generic rdf:type owl:Class ;
    rdfs:subClassOf [
        rdf:type owl:Restriction ;
        owl:onProperty :hasEssentialPart ;
        owl:someValuesFrom :Specific
    ] .
:Specific rdf:type owl:Class ;
    owl:disjointWith :Generic .

:genInd rdf:type :Generic .
"""
    test_ontology_string(test5, "Test 5: Add Generic individual")

    # Test 6: Add individual typed as Specific
    test6 = prefixes + """
:hasPart rdf:type owl:ObjectProperty ;
    owl:inverseOf :isPartOf .
:isPartOf rdf:type owl:ObjectProperty .
:hasEssentialPart rdf:type owl:ObjectProperty ;
    rdfs:subPropertyOf :hasPart .

:Generic rdf:type owl:Class ;
    rdfs:subClassOf [
        rdf:type owl:Restriction ;
        owl:onProperty :hasEssentialPart ;
        owl:someValuesFrom :Specific
    ] .
:Specific rdf:type owl:Class ;
    owl:disjointWith :Generic .

:genInd rdf:type :Generic .
:specInd rdf:type :Specific .
"""
    test_ontology_string(test6, "Test 6: Add Specific individual")

    # Test 7: Link specInd isPartOf genInd
    test7 = prefixes + """
:hasPart rdf:type owl:ObjectProperty ;
    owl:inverseOf :isPartOf .
:isPartOf rdf:type owl:ObjectProperty .
:hasEssentialPart rdf:type owl:ObjectProperty ;
    rdfs:subPropertyOf :hasPart .

:Generic rdf:type owl:Class ;
    rdfs:subClassOf [
        rdf:type owl:Restriction ;
        owl:onProperty :hasEssentialPart ;
        owl:someValuesFrom :Specific
    ] .
:Specific rdf:type owl:Class ;
    owl:disjointWith :Generic .

:genInd rdf:type :Generic .
:specInd rdf:type :Specific ;
    :isPartOf :genInd .
"""
    test_ontology_string(test7, "Test 7: specInd isPartOf genInd")

    # Test 8: Add isEssentialPartOf as inverse of hasEssentialPart
    test8 = prefixes + """
:hasPart rdf:type owl:ObjectProperty ;
    owl:inverseOf :isPartOf .
:isPartOf rdf:type owl:ObjectProperty .
:hasEssentialPart rdf:type owl:ObjectProperty ;
    rdfs:subPropertyOf :hasPart ;
    owl:inverseOf :isEssentialPartOf .
:isEssentialPartOf rdf:type owl:ObjectProperty ;
    rdfs:subPropertyOf :isPartOf .

:Generic rdf:type owl:Class ;
    rdfs:subClassOf [
        rdf:type owl:Restriction ;
        owl:onProperty :hasEssentialPart ;
        owl:someValuesFrom :Specific
    ] .
:Specific rdf:type owl:Class ;
    owl:disjointWith :Generic .

:genInd rdf:type :Generic .
:specInd rdf:type :Specific ;
    :isPartOf :genInd .
"""
    test_ontology_string(test8, "Test 8: Add isEssentialPartOf as subPropertyOf isPartOf")


def main2():
    """More tests mimicking GSO structure."""

    # Base prefixes
    prefixes = """
@prefix : <http://test.org/> .
@prefix owl: <http://www.w3.org/2002/07/owl#> .
@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .

<http://test.org/> rdf:type owl:Ontology .
"""

    # Test 13: With union (like GSO) - should be satisfiable
    test13 = prefixes + """
:hasPart rdf:type owl:ObjectProperty ;
    owl:inverseOf :isPartOf .
:isPartOf rdf:type owl:ObjectProperty .
:hasEssentialPart rdf:type owl:ObjectProperty ;
    rdfs:subPropertyOf :hasPart .

# PureTimeInterval is disjoint from Geologic, so Specific can use it
:TimeInterval rdf:type owl:Class .
:PureTimeInterval rdf:type owl:Class ;
    owl:disjointWith :GeologicTimeInterval .

:GeologicTimeInterval rdf:type owl:Class ;
    rdfs:subClassOf [
        rdf:type owl:Restriction ;
        owl:onProperty :hasEssentialPart ;
        owl:someValuesFrom [
            rdf:type owl:Class ;
            owl:unionOf ( :GeologicTimeInterval :PureTimeInterval )
        ]
    ] .

:Specific rdf:type owl:Class ;
    rdfs:subClassOf :GeologicTimeInterval ;
    rdfs:subClassOf [
        rdf:type owl:Class ;
        owl:complementOf [
            rdf:type owl:Restriction ;
            owl:onProperty :hasEssentialPart ;
            owl:someValuesFrom :GeologicTimeInterval
        ]
    ] .
"""
    test_ontology_string(test13, "Test 13: With union (GeologicTimeInterval OR PureTimeInterval)")

    # Test 14: Add individuals
    test14 = prefixes + """
:hasPart rdf:type owl:ObjectProperty ;
    owl:inverseOf :isPartOf .
:isPartOf rdf:type owl:ObjectProperty .
:hasEssentialPart rdf:type owl:ObjectProperty ;
    rdfs:subPropertyOf :hasPart .
:hasStaticPart rdf:type owl:ObjectProperty ;
    rdfs:subPropertyOf :hasEssentialPart .

:PureTimeInterval rdf:type owl:Class ;
    owl:disjointWith :GeologicTimeInterval .

:GeologicTimeInterval rdf:type owl:Class ;
    rdfs:subClassOf [
        rdf:type owl:Restriction ;
        owl:onProperty :hasEssentialPart ;
        owl:someValuesFrom [
            rdf:type owl:Class ;
            owl:unionOf ( :GeologicTimeInterval :PureTimeInterval )
        ]
    ] .

:Generic rdf:type owl:Class ;
    rdfs:subClassOf :GeologicTimeInterval ;
    rdfs:subClassOf [
        rdf:type owl:Restriction ;
        owl:onProperty :hasEssentialPart ;
        owl:someValuesFrom :Specific
    ] ;
    owl:disjointWith :Specific .

:Specific rdf:type owl:Class ;
    rdfs:subClassOf :GeologicTimeInterval ;
    rdfs:subClassOf [
        rdf:type owl:Class ;
        owl:complementOf [
            rdf:type owl:Restriction ;
            owl:onProperty :hasEssentialPart ;
            owl:someValuesFrom :GeologicTimeInterval
        ]
    ] ;
    rdfs:subClassOf [
        rdf:type owl:Restriction ;
        owl:onProperty :hasStaticPart ;
        owl:someValuesFrom :PureTimeInterval
    ] .

:genInd rdf:type :Generic .
:specInd rdf:type :Specific ;
    :isPartOf :genInd .
"""
    test_ontology_string(test14, "Test 14: Full GSO-like structure with individuals")

    # Test 9: Mimic GSO - TimeInterval, Generic, Specific
    test9 = prefixes + """
:hasPart rdf:type owl:ObjectProperty ;
    owl:inverseOf :isPartOf .
:isPartOf rdf:type owl:ObjectProperty .
:hasEssentialPart rdf:type owl:ObjectProperty ;
    rdfs:subPropertyOf :hasPart .
:isEssentialPartOf rdf:type owl:ObjectProperty ;
    rdfs:subPropertyOf :isPartOf ;
    owl:inverseOf :hasEssentialPart .

# Base class that Generic and Specific both inherit from
:TimeInterval rdf:type owl:Class .

:Generic rdf:type owl:Class ;
    rdfs:subClassOf :TimeInterval ;
    rdfs:subClassOf [
        rdf:type owl:Restriction ;
        owl:onProperty :hasEssentialPart ;
        owl:someValuesFrom :Specific
    ] .

:Specific rdf:type owl:Class ;
    rdfs:subClassOf :TimeInterval ;
    owl:disjointWith :Generic .

:genInd rdf:type :Generic .
:specInd rdf:type :Specific ;
    :isPartOf :genInd .
"""
    test_ontology_string(test9, "Test 9: TimeInterval base class with Generic/Specific subclasses")

    # Test 10: Add TimeInterval restriction hasEssentialPart some TimeInterval
    test10 = prefixes + """
:hasPart rdf:type owl:ObjectProperty ;
    owl:inverseOf :isPartOf .
:isPartOf rdf:type owl:ObjectProperty .
:hasEssentialPart rdf:type owl:ObjectProperty ;
    rdfs:subPropertyOf :hasPart .
:isEssentialPartOf rdf:type owl:ObjectProperty ;
    rdfs:subPropertyOf :isPartOf ;
    owl:inverseOf :hasEssentialPart .

:TimeInterval rdf:type owl:Class ;
    rdfs:subClassOf [
        rdf:type owl:Restriction ;
        owl:onProperty :hasEssentialPart ;
        owl:someValuesFrom :TimeInterval
    ] .

:Generic rdf:type owl:Class ;
    rdfs:subClassOf :TimeInterval ;
    rdfs:subClassOf [
        rdf:type owl:Restriction ;
        owl:onProperty :hasEssentialPart ;
        owl:someValuesFrom :Specific
    ] .

:Specific rdf:type owl:Class ;
    rdfs:subClassOf :TimeInterval ;
    owl:disjointWith :Generic .

:genInd rdf:type :Generic .
:specInd rdf:type :Specific ;
    :isPartOf :genInd .
"""
    test_ontology_string(test10, "Test 10: TimeInterval requires hasEssentialPart some TimeInterval")

    # Test 11: Add Specific complementOf hasEssentialPart some TimeInterval
    test11 = prefixes + """
:hasPart rdf:type owl:ObjectProperty ;
    owl:inverseOf :isPartOf .
:isPartOf rdf:type owl:ObjectProperty .
:hasEssentialPart rdf:type owl:ObjectProperty ;
    rdfs:subPropertyOf :hasPart .
:isEssentialPartOf rdf:type owl:ObjectProperty ;
    rdfs:subPropertyOf :isPartOf ;
    owl:inverseOf :hasEssentialPart .

:TimeInterval rdf:type owl:Class ;
    rdfs:subClassOf [
        rdf:type owl:Restriction ;
        owl:onProperty :hasEssentialPart ;
        owl:someValuesFrom :TimeInterval
    ] .

:Generic rdf:type owl:Class ;
    rdfs:subClassOf :TimeInterval ;
    rdfs:subClassOf [
        rdf:type owl:Restriction ;
        owl:onProperty :hasEssentialPart ;
        owl:someValuesFrom :Specific
    ] .

:Specific rdf:type owl:Class ;
    rdfs:subClassOf :TimeInterval ;
    rdfs:subClassOf [
        rdf:type owl:Class ;
        owl:complementOf [
            rdf:type owl:Restriction ;
            owl:onProperty :hasEssentialPart ;
            owl:someValuesFrom :TimeInterval
        ]
    ] ;
    owl:disjointWith :Generic .

:genInd rdf:type :Generic .
:specInd rdf:type :Specific ;
    :isPartOf :genInd .
"""
    test_ontology_string(test11, "Test 11: Specific complementOf hasEssentialPart some TimeInterval")

    # Test 12: Just Specific class (no individuals)
    test12 = prefixes + """
:hasPart rdf:type owl:ObjectProperty ;
    owl:inverseOf :isPartOf .
:isPartOf rdf:type owl:ObjectProperty .
:hasEssentialPart rdf:type owl:ObjectProperty ;
    rdfs:subPropertyOf :hasPart .

:TimeInterval rdf:type owl:Class ;
    rdfs:subClassOf [
        rdf:type owl:Restriction ;
        owl:onProperty :hasEssentialPart ;
        owl:someValuesFrom :TimeInterval
    ] .

:Specific rdf:type owl:Class ;
    rdfs:subClassOf :TimeInterval ;
    rdfs:subClassOf [
        rdf:type owl:Class ;
        owl:complementOf [
            rdf:type owl:Restriction ;
            owl:onProperty :hasEssentialPart ;
            owl:someValuesFrom :TimeInterval
        ]
    ] .
"""
    test_ontology_string(test12, "Test 12: Specific class (should be UNSATISFIABLE)")


if __name__ == "__main__":
    main()
    print("\n\n*** Running additional GSO-specific tests ***")
    main2()
