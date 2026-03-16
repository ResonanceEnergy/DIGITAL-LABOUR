#!/usr/bin/env python3
"""
Quick launch script for Matrix Maximizer
"""

import sys
import os

# Add the current directory to Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

try:
    from matrix_maximizer import MatrixMaximizer
    print("🚀 Launching Matrix Maximizer...")
    matrix = MatrixMaximizer()
    print("✅ Matrix Maximizer initialized successfully")
    print("🌐 Starting on http://0.0.0.0:3000")
    matrix.run(host='0.0.0.0', port=3000, debug=False)
except Exception as e:
    print(f"❌ Error launching Matrix Maximizer: {e}")
    import traceback
    traceback.print_exc()