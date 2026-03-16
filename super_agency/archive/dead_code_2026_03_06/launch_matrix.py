#!/usr/bin/env python3
"""
Quick launch script for Matrix Maximizer
"""

import sys
import os

# Add the current directory to Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

def main():
    from matrix_maximizer import MatrixMaximizer
    print("[LAUNCH] Launching Matrix Maximizer...")
    matrix = MatrixMaximizer()
    print("[OK] Matrix Maximizer initialized successfully")
    print("[NET] Starting on http://0.0.0.0:3000")
    matrix.run(host='0.0.0.0', port=3000, debug=False)


if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        print(f"[ERROR] Error launching Matrix Maximizer: {e}")
        import traceback
        traceback.print_exc()