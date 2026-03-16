#!/usr/bin/env python3
"""
Modern Matrix Maximizer Dashboard Launcher
Launches the enhanced Streamlit dashboard with modern UI/UX features
"""

import subprocess
import sys
import os

def launch_modern_dashboard():
    """Launch the modernized Matrix Maximizer dashboard"""

    print("🚀 Launching Modern Matrix Maximizer Dashboard...")
    print("=" * 60)
    print("✨ NEW FEATURES:")
    print("  • Modern gradient backgrounds with animations")
    print("  • Glassmorphism metric cards with hover effects")
    print("  • 3D interactive charts (pie, scatter, network)")
    print("  • Tabbed interface for better organization")
    print("  • Enhanced loading animations and transitions")
    print("  • Neural network activity indicators")
    print("  • Modern color schemes and typography")
    print("=" * 60)

    # Set environment variables for optimal performance
    env = os.environ.copy()
    env['STREAMLIT_SERVER_HEADLESS'] = 'true'
    env['STREAMLIT_BROWSER_GATHER_USAGE_STATS'] = 'false'

    try:
        # Launch Streamlit with the modernized dashboard
        cmd = [
            sys.executable, '-m', 'streamlit', 'run',
            'streamlit_matrix_maximizer.py',
            '--server.port', '8501',
            '--server.address', '0.0.0.0',
            '--theme.base', 'dark',
            '--theme.primaryColor', '#00d4ff',
            '--theme.secondaryBackgroundColor', '#1a1a2e',
            '--theme.backgroundColor', '#0a0a0a'
        ]

        print("🌐 Starting dashboard on http://localhost:8501")
        print("📱 Access from any device on your network")
        print("🛑 Press Ctrl+C to stop the dashboard")
        print("=" * 60)

        subprocess.run(cmd, env=env, cwd=os.path.dirname(os.path.abspath(__file__)))

    except KeyboardInterrupt:
        print("\n👋 Dashboard stopped. Goodbye!")
    except Exception as e:
        print(f"❌ Error launching dashboard: {e}")
        return False

    return True

if __name__ == "__main__":
    launch_modern_dashboard()
