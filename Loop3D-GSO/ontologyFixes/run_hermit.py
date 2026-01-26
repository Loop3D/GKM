#!/usr/bin/env python3
"""
OWL 2 DL Reasoner Command-Line Runner for GSO Ontology

Supports HermiT and Openllet reasoners.

Usage:
    python run_hermit.py <ontology_file>           # Test single file
    python run_hermit.py --all                     # Test all modules
    python run_hermit.py --download                # Download reasoner JAR
    python run_hermit.py --reasoner openllet       # Use Openllet instead

Examples:
    python run_hermit.py ../Modules/GSO-Geologic_Time.ttl
    python run_hermit.py ../GSO-Common.ttl
    python run_hermit.py --all --timeout 600

Reasoner downloads:
    HermiT:   https://github.com/owlcs/releases/releases (hermit-1.4.3.456)
    Openllet: https://github.com/Galigator/openllet/releases
    JFact:    https://github.com/owlcs/jfact/releases
"""

import subprocess
import sys
import os
import urllib.request
import glob
import time
from pathlib import Path

# Configuration
HERMIT_JAR = os.environ.get('HERMIT_JAR', 'HermiT.jar')
OPENLLET_JAR = os.environ.get('OPENLLET_JAR', 'openllet-cli.jar')

# Download URLs (check for latest versions)
REASONER_URLS = {
    "hermit": "https://github.com/owlcs/releases/releases/download/hermit-1.4.3.456/HermiT-1.4.3.456.jar",
    # Openllet needs to be downloaded manually from GitHub releases - it's a zip with multiple JARs
}

DEFAULT_TIMEOUT = 300  # 5 minutes

def download_hermit(target_path="HermiT.jar"):
    """Download HermiT JAR if not present"""
    if os.path.exists(target_path):
        print(f"HermiT already exists at {target_path}")
        return target_path

    print(f"Downloading HermiT from {HERMIT_URL}...")
    try:
        urllib.request.urlretrieve(HERMIT_URL, target_path)
        print(f"Downloaded to {target_path}")
        return target_path
    except Exception as e:
        print(f"Error downloading HermiT: {e}")
        print("Please download manually from: https://github.com/owlcs/releases/releases")
        return None

def find_hermit_jar():
    """Try to find HermiT JAR in common locations"""
    locations = [
        HERMIT_JAR,
        "HermiT.jar",
        "../HermiT.jar",
        "HermiT-1.4.3.456.jar",
        os.path.expanduser("~/HermiT.jar"),
    ]

    # Check Protege plugin directories
    protege_paths = glob.glob("C:/Program Files/Protege*/plugins/org.semanticweb.hermit*/*.jar")
    protege_paths += glob.glob(os.path.expanduser("~/AppData/Local/Protege*/plugins/org.semanticweb.hermit*/*.jar"))
    locations.extend(protege_paths)

    for loc in locations:
        if os.path.exists(loc):
            return loc

    return None

def run_hermit(ontology_file, jar_path, timeout=DEFAULT_TIMEOUT, check_only="consistency"):
    """
    Run HermiT on an ontology file

    check_only: "consistency", "unsatisfiable", or "classify"
    """
    if not os.path.exists(ontology_file):
        print(f"Error: Ontology file not found: {ontology_file}")
        return None

    # Build command
    if check_only == "consistency":
        cmd = ["java", "-jar", jar_path, "-c", ontology_file]
    elif check_only == "unsatisfiable":
        cmd = ["java", "-jar", jar_path, "-U", ontology_file]
    else:  # classify
        cmd = ["java", "-jar", jar_path, "-k", ontology_file]

    print(f"\n{'='*60}")
    print(f"Testing: {ontology_file}")
    print(f"Command: {' '.join(cmd)}")
    print(f"Timeout: {timeout} seconds")
    print('='*60)

    start_time = time.time()

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout
        )

        elapsed = time.time() - start_time

        print(f"\nCompleted in {elapsed:.1f} seconds")
        print(f"Return code: {result.returncode}")

        if result.stdout:
            print(f"\nOutput:\n{result.stdout}")

        if result.stderr:
            print(f"\nErrors/Warnings:\n{result.stderr}")

        # Check for issues
        output = result.stdout + result.stderr
        if "inconsistent" in output.lower():
            print("\n*** INCONSISTENT ONTOLOGY ***")
            return "inconsistent"
        elif "unsatisfiable" in output.lower() and "no unsatisfiable" not in output.lower():
            print("\n*** HAS UNSATISFIABLE CLASSES ***")
            return "unsatisfiable"
        elif result.returncode == 0:
            print("\n*** PASSED ***")
            return "passed"
        else:
            print("\n*** UNKNOWN RESULT ***")
            return "unknown"

    except subprocess.TimeoutExpired:
        elapsed = time.time() - start_time
        print(f"\n*** TIMEOUT after {elapsed:.1f} seconds ***")
        return "timeout"
    except Exception as e:
        print(f"\nError running HermiT: {e}")
        return "error"

def test_all_modules(base_path, jar_path, timeout=DEFAULT_TIMEOUT):
    """Test all ontology modules"""
    results = {}

    # Find all TTL files
    modules_path = os.path.join(base_path, "Modules", "*.ttl")
    root_ttl = os.path.join(base_path, "*.ttl")

    files = glob.glob(modules_path) + glob.glob(root_ttl)

    # Filter out backup and temp files
    files = [f for f in files if not f.endswith('.bak') and '~' not in f]

    print(f"Found {len(files)} ontology files to test\n")

    for f in sorted(files):
        result = run_hermit(f, jar_path, timeout, "consistency")
        results[f] = result

    # Summary
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)

    for status in ["passed", "inconsistent", "unsatisfiable", "timeout", "error", "unknown"]:
        files_with_status = [f for f, r in results.items() if r == status]
        if files_with_status:
            print(f"\n{status.upper()} ({len(files_with_status)}):")
            for f in files_with_status:
                print(f"  - {os.path.basename(f)}")

    return results

def main():
    import argparse

    parser = argparse.ArgumentParser(description="Run HermiT reasoner on GSO ontology files")
    parser.add_argument("ontology", nargs="?", help="Ontology file to test")
    parser.add_argument("--all", action="store_true", help="Test all modules")
    parser.add_argument("--download", action="store_true", help="Download HermiT JAR")
    parser.add_argument("--jar", default=None, help="Path to HermiT JAR")
    parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT, help="Timeout in seconds")
    parser.add_argument("--check", choices=["consistency", "unsatisfiable", "classify"],
                        default="consistency", help="Type of check to perform")

    args = parser.parse_args()

    # Handle download request
    if args.download:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        jar_path = os.path.join(script_dir, "HermiT.jar")
        download_hermit(jar_path)
        return

    # Find HermiT JAR
    jar_path = args.jar or find_hermit_jar()

    if not jar_path or not os.path.exists(jar_path):
        print("HermiT JAR not found!")
        print("Options:")
        print("  1. Run: python run_hermit.py --download")
        print("  2. Set HERMIT_JAR environment variable")
        print("  3. Use --jar /path/to/HermiT.jar")
        sys.exit(1)

    print(f"Using HermiT JAR: {jar_path}")

    # Get base path (parent of ontologyFixes)
    script_dir = os.path.dirname(os.path.abspath(__file__))
    base_path = os.path.dirname(script_dir)

    if args.all:
        test_all_modules(base_path, jar_path, args.timeout)
    elif args.ontology:
        run_hermit(args.ontology, jar_path, args.timeout, args.check)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
