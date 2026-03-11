#!/usr/bin/env python3
"""L9 Contract Verification Script.

Confirms all 20 contract files exist, checks SHA-256 integrity,
and verifies each is referenced in .cursorrules and CLAUDE.md.

Exit codes:
  0 = all checks pass
  1 = one or more FAIL conditions
"""
import hashlib
import sys
import yaml
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
MANIFEST_PATH = REPO_ROOT / "tools" / "l9_template_manifest.yaml"


def compute_sha256(filepath: Path) -> str:
    return hashlib.sha256(filepath.read_bytes()).hexdigest()


def load_manifest() -> dict:
    if not MANIFEST_PATH.exists():
        print(f"FAIL: Manifest not found at {MANIFEST_PATH}")
        sys.exit(1)
    with open(MANIFEST_PATH) as f:
        return yaml.safe_load(f)


def check_file_referenced(contract_path: str, ref_file: Path) -> bool:
    if not ref_file.exists():
        return False
    content = ref_file.read_text()
    # Check for the contract path (with or without leading ./)
    clean_path = contract_path.lstrip("./")
    return clean_path in content


def main():
    manifest = load_manifest()
    fails = []
    warns = []
    passes = []

    all_contracts = []
    for level in ["engine_level", "constellation_level"]:
        contracts = manifest.get("contracts", {}).get(level, [])
        all_contracts.extend(contracts)

    total = len(all_contracts)
    present = 0
    referenced_cursorrules = 0
    referenced_claude = 0

    for entry in all_contracts:
        path = entry["path"]
        full_path = REPO_ROOT / path
        sha_expected = entry.get("sha256", "")
        required_refs = entry.get("required_refs", [".cursorrules", "CLAUDE.md"])

        # Check 1: File exists
        if not full_path.exists():
            fails.append(f"FAIL: MISSING {path}")
            continue

        present += 1

        # Check 2: SHA-256 integrity (WARN only -- engines may extend)
        if sha_expected and sha_expected != "<computed>" and not sha_expected.startswith("<"):
            actual_sha = compute_sha256(full_path)
            if actual_sha != sha_expected:
                warns.append(f"WARN: MODIFIED {path} (sha256 mismatch)")

        # Check 3: Referenced in required files
        for ref in required_refs:
            ref_path = REPO_ROOT / ref
            if ref == ".cursorrules":
                if check_file_referenced(path, ref_path):
                    referenced_cursorrules += 1
                else:
                    fails.append(f"FAIL: {path} NOT referenced in {ref}")
            elif ref == "CLAUDE.md":
                if check_file_referenced(path, ref_path):
                    referenced_claude += 1
                else:
                    fails.append(f"FAIL: {path} NOT referenced in {ref}")

        passes.append(f"PASS: {path}")

    # Print results
    print("=" * 60)
    print("L9 Contract Verification Report")
    print("=" * 60)

    for p in passes:
        print(f"  {p}")
    for w in warns:
        print(f"  {w}")
    for f_msg in fails:
        print(f"  {f_msg}")

    print()
    print(f"Contracts present:               {present}/{total}")
    print(f"Referenced in .cursorrules:       {referenced_cursorrules}/{total}")
    print(f"Referenced in CLAUDE.md:          {referenced_claude}/{total}")
    print(f"Warnings (modified):             {len(warns)}")
    print(f"Failures (missing/unreferenced): {len(fails)}")

    if fails:
        print()
        print("RESULT: FAIL -- contract verification failed")
        sys.exit(1)
    else:
        print()
        print("RESULT: PASS -- all contracts verified")
        sys.exit(0)


if __name__ == "__main__":
    main()
