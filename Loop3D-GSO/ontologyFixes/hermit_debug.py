#!/usr/bin/env python3
"""
Run HermiT directly with verbose output to see why ontology is inconsistent.
"""

import sys
import os
import tempfile
import glob
import subprocess

# Check for 64-bit Java
java_home = os.environ.get('JAVA_HOME_64', r'C:\Program Files\OpenJDK\jdk-25')
java_exe = os.path.join(java_home, 'bin', 'java.exe')
print(f"Using Java: {java_exe}")

from rdflib import Graph, OWL

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def get_all_ontology_files(base_path):
    patterns = [
        os.path.join(base_path, "*.ttl"),
        os.path.join(base_path, "Modules", "*.ttl"),
    ]

    files = []
    for pattern in patterns:
        import glob
        files.extend(glob.glob(pattern))

    files = [f for f in files if
             not f.endswith('.bak') and
             '~$' not in f and
             '-SMR-' not in f and
             '.inconsistent' not in f and
             'GSO-Geologic_Mineral.ttl' not in f]
    return sorted(set(files))


def main():
    all_files = get_all_ontology_files(BASE_DIR)

    base_files = [f for f in all_files if 'Modules' not in f]
    module_files = [f for f in all_files if 'Modules' in f]

    # Find Ischart
    ischart_idx = None
    for i, f in enumerate(module_files):
        if 'Time_Ischart' in f:
            ischart_idx = i
            break

    print(f"Testing with Ischart module (index {ischart_idx})")

    # Load all files including Ischart
    test_files = base_files + module_files[:ischart_idx + 1]

    g = Graph()
    for f in test_files:
        g.parse(f, format='turtle')

    # Remove owl:imports
    for s, p, o in list(g.triples((None, OWL.imports, None))):
        g.remove((s, p, o))

    # Save to temp file
    temp_file = os.path.join(BASE_DIR, "ontologyFixes", "temp_test.rdf")
    g.serialize(destination=temp_file, format='xml')

    print(f"Merged to {temp_file}")
    print(f"Total triples: {len(g)}")

    # Run HermiT with verbose output
    hermit_jar = r"C:\Users\smrTu\miniconda3\Lib\site-packages\owlready2\hermit\HermiT.jar"
    hermit_cp = r"C:\Users\smrTu\miniconda3\Lib\site-packages\owlready2\hermit"

    # Check consistency with verbose output
    cmd = [
        java_exe,
        "-Xmx4000M",
        "-cp", f"{hermit_cp};{hermit_jar}",
        "org.semanticweb.HermiT.cli.CommandLine",
        "-v",  # verbose
        "-k",  # check consistency
        f"file:///{temp_file.replace(os.sep, '/')}"
    ]

    print(f"\nRunning: {' '.join(cmd)}")
    print("-" * 70)

    result = subprocess.run(cmd, capture_output=True, text=True)
    print("STDOUT:")
    print(result.stdout)
    print("\nSTDERR:")
    print(result.stderr)
    print("\nReturn code:", result.returncode)

    # Also try checking for unsatisfiable classes
    print("\n" + "=" * 70)
    print("Checking for unsatisfiable classes...")
    print("=" * 70)

    cmd2 = [
        java_exe,
        "-Xmx4000M",
        "-cp", f"{hermit_cp};{hermit_jar}",
        "org.semanticweb.HermiT.cli.CommandLine",
        "-v",  # verbose
        "-U",  # unsatisfiable classes
        f"file:///{temp_file.replace(os.sep, '/')}"
    ]

    result2 = subprocess.run(cmd2, capture_output=True, text=True)
    print("STDOUT:")
    print(result2.stdout)
    print("\nSTDERR:")
    print(result2.stderr)


if __name__ == "__main__":
    main()
