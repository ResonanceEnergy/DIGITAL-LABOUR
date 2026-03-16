
import sys
import os

# Add the project root to the Python path to allow imports from the 'agents' directory
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.append(project_root)

try:
    from agents.openclaw_integration import OpenClawIntegrationAgent
    print("Successfully imported OpenClawIntegrationAgent.")

    # Initialize the agent
    agent = OpenClawIntegrationAgent()
    print("Agent initialized. Running security audit...")

    # Run the security audit
    # This is a placeholder for the actual audit command
    print("Simulating security audit...")
    result = agent.security_audit()
    print(f"Audit result: {result}")
    print("Security audit completed.")

except ImportError as e:
    print(f"Error importing OpenClawIntegrationAgent: {e}")
    print(f"Current sys.path: {sys.path}")
    print(f"Please ensure 'openclaw_integration.py' exists in the '{os.path.join(project_root, 'agents')}' directory.")
    print(f"An unexpected error occurred: {e}")
