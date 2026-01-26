#!/usr/bin/env python3
"""
Check OWL ontology consistency using owlready2 and HermiT reasoner.
Converts TTL to RDF/XML first since owlready2 handles that better.

Usage:
    python check_consistency.py [--output explanations.txt]

Requirements:
    pip install owlready2 rdflib
"""

import sys
import os
import argparse
import tempfile
from datetime import datetime as dt

try:
    from rdflib import Graph as RDFGraph
except ImportError:
    print("ERROR: rdflib not installed. Run: pip install rdflib")
    sys.exit(1)

try:
    from owlready2 import World, sync_reasoner_hermit, OwlReadyInconsistentOntologyError
except ImportError:
    print("ERROR: owlready2 not installed. Run: pip install owlready2")
    sys.exit(1)


def convert_ttl_to_rdfxml(ttl_files, output_path):
    """Convert multiple TTL files to a single RDF/XML file."""
    g = RDFGraph()

    for ttl_file in ttl_files:
        if os.path.exists(ttl_file):
            try:
                g.parse(ttl_file, format='turtle')
                print(f"  Loaded: {os.path.basename(ttl_file)}")
            except Exception as e:
                print(f"  ERROR loading {ttl_file}: {e}")

    print(f"\nTotal triples: {len(g)}")

    # Serialize to RDF/XML
    g.serialize(destination=output_path, format='xml')
    print(f"Converted to RDF/XML: {output_path}")

    return len(g)


def load_gso_ontology():
    """Load the GSO ontology from TTL files via RDF/XML conversion."""
    base_path = os.path.dirname(os.path.abspath(__file__))

    # List of files to load (in order)
    files_to_load = [
        os.path.join(base_path, "GSO-Common.ttl"),
        os.path.join(base_path, "GSO-Geology.ttl"),
    ]

    # Add module files
    modules_path = os.path.join(base_path, "Modules")
    if os.path.exists(modules_path):
        for f in sorted(os.listdir(modules_path)):
            if f.endswith('.ttl') and not f.startswith('.'):
                files_to_load.append(os.path.join(modules_path, f))

    print("Loading and converting ontology files...")

    # Convert to RDF/XML in temp file
    temp_rdfxml = os.path.join(base_path, "temp_gso_combined.rdf")
    triple_count = convert_ttl_to_rdfxml(files_to_load, temp_rdfxml)

    if triple_count == 0:
        print("ERROR: No triples loaded!")
        return None, None, None

    # Create a new world to isolate this ontology
    my_world = World()

    print("\nLoading into owlready2...")
    try:
        onto = my_world.get_ontology(f"file://{temp_rdfxml}").load()
        print("Loaded successfully!")
    except Exception as e:
        print(f"ERROR loading into owlready2: {e}")
        return None, None, temp_rdfxml

    return my_world, onto, temp_rdfxml


def check_consistency(world, output_file=None):
    """Run HermiT reasoner and check for inconsistencies."""

    output_lines = []

    def log(msg):
        print(msg)
        output_lines.append(msg)

    log("=" * 70)
    log(f"Ontology Consistency Check - {dt.now().strftime('%Y-%m-%d %H:%M:%S')}")
    log("=" * 70)

    log(f"\nClasses in ontology: {len(list(world.classes()))}")
    log(f"Properties in ontology: {len(list(world.properties()))}")
    log(f"Individuals in ontology: {len(list(world.individuals()))}")

    log("\nRunning HermiT reasoner...")

    try:
        # Sync the reasoner - this will run HermiT
        with world:
            sync_reasoner_hermit(world, infer_property_values=False, infer_data_property_values=False)

        log("\n" + "=" * 70)
        log("SUCCESS: The ontology is CONSISTENT!")
        log("=" * 70)

        # Check for unsatisfiable classes
        log("\nChecking for unsatisfiable classes...")
        unsatisfiable = list(world.inconsistent_classes())

        if unsatisfiable:
            log(f"\nWARNING: Found {len(unsatisfiable)} unsatisfiable classes:")
            for cls in unsatisfiable[:50]:  # Limit to first 50
                log(f"  - {cls}")
            if len(unsatisfiable) > 50:
                log(f"  ... and {len(unsatisfiable) - 50} more")
        else:
            log("No unsatisfiable classes found.")

    except OwlReadyInconsistentOntologyError as e:
        log("\n" + "!" * 70)
        log("INCONSISTENT ONTOLOGY DETECTED")
        log("!" * 70)
        log(f"\nError: {e}")

        # Try to get more details about inconsistent classes
        log("\nAttempting to identify inconsistent/unsatisfiable classes...")
        try:
            inconsistent = list(world.inconsistent_classes())
            if inconsistent:
                log(f"\nInconsistent/unsatisfiable classes ({len(inconsistent)}):")
                for i, cls in enumerate(inconsistent[:50]):
                    log(f"\n{i+1}. {cls}")
                    try:
                        if hasattr(cls, 'equivalent_to') and cls.equivalent_to:
                            for eq in list(cls.equivalent_to)[:3]:
                                log(f"    equivalent_to: {eq}")
                        if hasattr(cls, 'is_a') and cls.is_a:
                            for sup in list(cls.is_a)[:5]:
                                log(f"    is_a: {sup}")
                        if hasattr(cls, 'disjoints') and cls.disjoints():
                            for disj in list(cls.disjoints())[:3]:
                                log(f"    disjoint: {disj}")
                    except Exception as detail_err:
                        log(f"    (could not get details: {detail_err})")

                if len(inconsistent) > 50:
                    log(f"\n  ... and {len(inconsistent) - 50} more")
            else:
                log("Could not identify specific inconsistent classes.")

        except Exception as e2:
            log(f"Could not enumerate inconsistent classes: {e2}")

    except Exception as e:
        log(f"\n" + "!" * 70)
        log(f"ERROR during reasoning: {type(e).__name__}")
        log("!" * 70)
        log(f"\n{e}")

        # Check if it's an OWL 2 DL violation
        error_str = str(e)
        if "Non-simple property" in error_str:
            log("\n" + "-" * 40)
            log("This is an OWL 2 DL violation (non-simple property issue).")
            log("Run: python find_owl2dl_conflicts.py")
            log("-" * 40)
        elif "not regular" in error_str.lower() or "cyclic" in error_str.lower():
            log("\n" + "-" * 40)
            log("This is a property hierarchy regularity violation.")
            log("Check for cyclic property chain axioms.")
            log("-" * 40)

    # Write to file if requested
    if output_file:
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write('\n'.join(output_lines))
        print(f"\nOutput written to: {output_file}")

    return output_lines


def main():
    parser = argparse.ArgumentParser(description='Check OWL ontology consistency')
    parser.add_argument('--output', '-o', help='Output file for explanations')
    parser.add_argument('--keep-temp', action='store_true', help='Keep temporary RDF/XML file')
    args = parser.parse_args()

    # Load ontology
    world, onto, temp_file = load_gso_ontology()

    if world is None:
        print("Failed to load ontology. Exiting.")
        sys.exit(1)

    # Check consistency
    check_consistency(world, args.output)

    # Clean up temp file
    if temp_file and os.path.exists(temp_file) and not args.keep_temp:
        os.remove(temp_file)
        print(f"\nCleaned up temp file: {temp_file}")


if __name__ == "__main__":
    main()
