#!/usr/bin/env python3
"""
Test Audio Processor
Basic functionality tests for the audio processing pipeline
"""

import sys
import os
from pathlib import Path

# Add the project root to Python path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from ncl_second_brain.engine.audio_processor import AudioProcessor

def test_initialization():
    """Test that AudioProcessor initializes correctly"""
    print("Testing AudioProcessor initialization...")

    try:
        processor = AudioProcessor()
        print("✓ AudioProcessor initialized successfully")
        print(f"  Base directory: {processor.base_dir}")
        print(f"  Audio directory: {processor.audio_dir}")
        print(f"  Fingerprints directory: {processor.fingerprints_dir}")
        return True
    except Exception as e:
        print(f"✗ Initialization failed: {e}")
        return False

def test_directory_creation():
    """Test that required directories are created"""
    print("\nTesting directory creation...")

    try:
        processor = AudioProcessor()

        # Check if directories exist
        dirs_to_check = [
            processor.base_dir,
            processor.audio_dir,
            processor.fingerprints_dir
        ]

        for dir_path in dirs_to_check:
            if dir_path.exists():
                print(f"✓ Directory exists: {dir_path}")
            else:
                print(f"✗ Directory missing: {dir_path}")
                return False

        return True
    except Exception as e:
        print(f"✗ Directory creation test failed: {e}")
        return False

def test_dependency_check():
    """Test dependency checking"""
    print("\nTesting dependency checking...")

    try:
        processor = AudioProcessor()
        # The _check_dependencies method is called in __init__
        print("✓ Dependencies checked (no exceptions raised)")
        print(f"  Diarization available: {processor.diarization_available}")
        return True
    except Exception as e:
        print(f"✗ Dependency check failed: {e}")
        return False

def test_fingerprint_generation():
    """Test fingerprint generation with a dummy file"""
    print("\nTesting fingerprint generation...")

    try:
        processor = AudioProcessor()

        # Create a dummy audio file for testing
        test_file = processor.audio_dir / "test_dummy.txt"
        test_file.write_text("This is dummy audio content for testing")

        # Test fingerprint generation (will fall back to file hash)
        fingerprint = processor._generate_fingerprint(test_file)
        print(f"✓ Fingerprint generated: {fingerprint[:16]}...")

        # Clean up
        test_file.unlink()

        return True
    except Exception as e:
        print(f"✗ Fingerprint generation failed: {e}")
        return False

def test_duplicate_detection():
    """Test duplicate detection logic"""
    print("\nTesting duplicate detection...")

    try:
        processor = AudioProcessor()

        # Test with a known fingerprint
        test_fp = "test_fingerprint_12345"

        # First check should not be duplicate
        is_dup1 = processor._is_duplicate(test_fp)
        print(f"✓ First check (should not be duplicate): {is_dup1}")

        # Second check should be duplicate
        is_dup2 = processor._is_duplicate(test_fp)
        print(f"✓ Second check (should be duplicate): {is_dup2}")

        if not is_dup1 and is_dup2:
            print("✓ Duplicate detection working correctly")
            return True
        else:
            print("✗ Duplicate detection logic incorrect")
            return False

    except Exception as e:
        print(f"✗ Duplicate detection test failed: {e}")
        return False

def run_all_tests():
    """Run all tests and report results"""
    print("🧪 Running Audio Processor Tests")
    print("=" * 50)

    tests = [
        test_initialization,
        test_directory_creation,
        test_dependency_check,
        test_fingerprint_generation,
        test_duplicate_detection
    ]

    passed = 0
    total = len(tests)

    for test in tests:
        try:
            if test():
                passed += 1
            else:
                print(f"❌ Test failed: {test.__name__}")
        except Exception as e:
            print(f"❌ Test crashed: {test.__name__} - {e}")

    print("\n" + "=" * 50)
    print(f"📊 Test Results: {passed}/{total} passed")

    if passed == total:
        print("🎉 All tests passed!")
        return True
    else:
        print("⚠️ Some tests failed. Check output above.")
        return False

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)