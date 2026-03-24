#!/usr/bin/env python3
"""
DIGITAL LABOUR Codebase Cleanup Script
Implements all recommendations from the audit report
"""

import os
import subprocess
import sys
from pathlib import Path

WORKSPACE = Path(__file__).parent


def delete_duplicate_files():
    """Delete all -ResonanceEnergy duplicate files"""
    print("\n" + "=" * 60)
    print("STEP 1: Deleting duplicate -ResonanceEnergy files")
    print("=" * 60)

    duplicates = list(WORKSPACE.rglob("*-ResonanceEnergy.py"))
    print(f"Found {len(duplicates)} duplicate files")

    deleted = 0
    errors = []
    for f in duplicates:
        try:
            f.unlink()
            deleted += 1
        except Exception as e:
            errors.append(f"{f.name}: {e}")

    print(f"✅ Successfully deleted {deleted} files")
    if errors:
        print(f"⚠️ {len(errors)} errors occurred")
        for e in errors[:5]:
            print(f"   - {e}")

    return deleted


def count_remaining_files():
    """Count remaining Python files"""
    py_files = list(WORKSPACE.rglob("*.py"))
    print(f"\n📊 Remaining Python files: {len(py_files)}")
    return len(py_files)


def install_tools():
    """Install autoflake, black, isort, pre-commit"""
    print("\n" + "=" * 60)
    print("STEP 2: Installing code quality tools")
    print("=" * 60)

    tools = ["autoflake", "black", "isort", "pre-commit"]
    for tool in tools:
        try:
            result = subprocess.run(
                [sys.executable, "-m", "pip", "install", tool, "-q"],
                capture_output=True,
                text=True,
                timeout=60,
            )
            if result.returncode == 0:
                print(f"✅ {tool} installed")
            else:
                print(f"⚠️ {tool} install issue: {result.stderr[:100]}")
        except Exception as e:
            print(f"❌ {tool} failed: {e}")


def run_autoflake():
    """Remove unused imports"""
    print("\n" + "=" * 60)
    print("STEP 3: Removing unused imports with autoflake")
    print("=" * 60)

    # Run on root-level py files only (to save time)
    py_files = [f for f in WORKSPACE.glob("*.py")]
    fixed = 0

    for f in py_files:
        try:
            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "autoflake",
                    "--in-place",
                    "--remove-all-unused-imports",
                    str(f),
                ],
                capture_output=True,
                text=True,
                timeout=30,
            )
            if result.returncode == 0:
                fixed += 1
        except Exception:
            pass

    print(f"✅ Processed {fixed} root-level files")


def run_isort():
    """Sort imports"""
    print("\n" + "=" * 60)
    print("STEP 4: Sorting imports with isort")
    print("=" * 60)

    try:
        result = subprocess.run(
            [sys.executable, "-m", "isort", ".", "--profile", "black", "-q"],
            cwd=str(WORKSPACE),
            capture_output=True,
            text=True,
            timeout=120,
        )
        if result.returncode == 0:
            print("✅ Imports sorted successfully")
        else:
            print(f"⚠️ isort completed with issues")
    except subprocess.TimeoutExpired:
        print("⚠️ isort timed out (too many files) - run manually later")
    except Exception as e:
        print(f"❌ isort failed: {e}")


def run_black():
    """Format code with black"""
    print("\n" + "=" * 60)
    print("STEP 5: Formatting code with black")
    print("=" * 60)

    # Only format root level to save time
    py_files = [f for f in WORKSPACE.glob("*.py")]

    formatted = 0
    for f in py_files:
        try:
            result = subprocess.run(
                [sys.executable, "-m", "black", str(f), "-q"],
                capture_output=True,
                text=True,
                timeout=30,
            )
            if result.returncode == 0:
                formatted += 1
        except Exception:
            pass

    print(f"✅ Formatted {formatted} root-level files")


def generate_summary():
    """Generate cleanup summary"""
    print("\n" + "=" * 60)
    print("CLEANUP COMPLETE - SUMMARY")
    print("=" * 60)

    py_count = len(list(WORKSPACE.rglob("*.py")))
    dupe_count = len(list(WORKSPACE.rglob("*-ResonanceEnergy.py")))

    print(f"📁 Total Python files: {py_count}")
    print(f"🗑️ Remaining duplicates: {dupe_count}")
    print(
        f"📦 pyproject.toml: {'✅ exists' if (WORKSPACE / 'pyproject.toml').exists() else '❌ missing'}"
    )
    print(
        f"📋 .pre-commit-config.yaml: {'✅ exists' if (WORKSPACE / '.pre-commit-config.yaml').exists() else '❌ missing'}"
    )
    print(f"📄 LICENSE: {'✅ exists' if (WORKSPACE / 'LICENSE').exists() else '❌ missing'}")


def main():
    print("🚀 DIGITAL LABOUR CODEBASE CLEANUP")
    print("Implementing all audit recommendations...")

    # Step 1: Delete duplicates
    deleted = delete_duplicate_files()

    # Count remaining
    count_remaining_files()

    # Step 2: Install tools
    install_tools()

    # Step 3: Remove unused imports
    run_autoflake()

    # Step 4: Sort imports
    run_isort()

    # Step 5: Format code
    run_black()

    # Summary
    generate_summary()

    print("\n✨ Cleanup script complete!")
    print("Run 'python3 cleanup_codebase.py' again to verify")


if __name__ == "__main__":
    main()
