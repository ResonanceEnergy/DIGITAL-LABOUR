#!/usr/bin/env python3
"""
BIT RAGE LABOUR Operations Interface Launcher
Choose between chat interface or API server
"""

import sys
import asyncio
import subprocess

def show_menu():
    """Display the main menu"""
    print("""
🤖 BIT RAGE LABOUR Operations Interface
═══════════════════════════════════════

Choose your interface:

1. 💬 Interactive Chat
   - Talk naturally with department heads
   - Get real-time operational updates
   - Conversational AI interface

2. 🔌 API Server
   - REST API for programmatic access
   - Integrate with other systems
   - Machine-to-machine communication

3. 🧪 Test Operations
   - Run test queries
   - Validate system functionality
   - Debug interface

4. 📚 Help & Documentation
   - Interface documentation
   - Available departments
   - Usage examples

Type your choice (1-4) or 'quit' to exit:
    """.strip())

def launch_chat():
    """Launch the interactive chat interface"""
    print("🚀 Starting Operations Chat...")
    try:
        subprocess.run([sys.executable, "operations_chat.py"])
    except KeyboardInterrupt:
        print("\n👋 Chat session ended.")
    except Exception as e:
        print(f"❌ Error launching chat: {e}")

def launch_api():
    """Launch the API server"""
    print("🚀 Starting Operations API Server...")
    print("📡 API will be available at: http://localhost:5000")
    print("Press Ctrl+C to stop the server")
    try:
        subprocess.run([sys.executable, "operations_api.py"])
    except KeyboardInterrupt:
        print("\n👋 API server stopped.")
    except Exception as e:
        print(f"❌ Error launching API server: {e}")

def run_tests():
    """Run test operations"""
    print("🧪 Running Operations Interface Tests...")

    async def test_queries():
        from operations_command_interface import handle_operations_query

        test_queries = [
            "How is NCC doing?",
            "What's the status of Council 52?",
            "Give me an update on portfolio operations",
            "How is TESLA-TECH performing?",
            "What departments are available?"
        ]

        print(f"Testing {len(test_queries)} queries...\n")

        for i, query in enumerate(test_queries, 1):
            print(f"Test {i}: '{query}'")
            try:
                result = await handle_operations_query(query)
                response_type = result.get('response_type', 'unknown')
                department = result.get('department_name', 'Unknown')

                if response_type == 'operational_update':
                    print(f"  ✅ Success - {department}")
                elif response_type == 'clarification_needed':
                    print("  ℹ️  Clarification needed")
                else:
                    print(f"  ⚠️  {response_type}")

            except Exception as e:
                print(f"  ❌ Error: {e}")

            print()

    asyncio.run(test_queries())
    print("🧪 Testing complete!")

def show_help():
    """Show help and documentation"""
    print("""
📚 BIT RAGE LABOUR Operations Interface - Help
═══════════════════════════════════════════════

OVERVIEW
────────
The Operations Command Interface (OCI) enables real-time conversational access
to all BIT RAGE LABOUR departments and operations. You can talk naturally with
department heads and get immediate operational updates.

AVAILABLE INTERFACES
────────────────────
1. Interactive Chat (operations_chat.py)
   - Natural language conversation
   - Real-time responses
   - Department head simulation

2. REST API (operations_api.py)
   - Programmatic access
   - System integration
   - Machine-to-machine communication

DEPARTMENTS & DIVISIONS
───────────────────────
Core Departments:
• NCC (Neural Command Center) - Command & Control
• Council 52 - Intelligence Operations
• Portfolio Operations - Company Oversight
• AI Research - Machine Learning & NCL
• Platform Engineering - Infrastructure
• Market Intelligence - Market Analysis
• Product Development - Product Strategy
• Security Operations - Security Monitoring
• Financial Operations - Financial Management

Portfolio Companies (24 total):
• All companies from portfolio.json
• Individual company status and updates
• Development progress tracking

USAGE EXAMPLES
──────────────
Chat Interface:
• "How is NCC doing today?"
• "What's the status of Council 52?"
• "Give me an update on TESLA-TECH"
• "Any issues in portfolio operations?"
• "How is AI research progressing?"

API Usage:
POST /api/v1/operations/query
{
  "query": "How is NCC doing?",
  "user_context": {"role": "executive"}
}

SYSTEM ARCHITECTURE
───────────────────
• operations_command_interface.py - Core OCI logic
• operations_chat.py - Interactive chat interface
• operations_api.py - REST API server
• Integrated with existing BIT RAGE LABOUR systems
• Real-time data from portfolio, agents, and operations

TECHNICAL FEATURES
──────────────────
• Natural language processing
• Department recognition and routing
• Real-time operational data
• Portfolio company integration
• Executive context awareness
• Conversation history tracking

For technical support or questions, contact the BIT RAGE LABOUR operations team.
    """.strip())

def main():
    """Main launcher function"""
    while True:
        show_menu()

        try:
            choice = input().strip().lower()

            if choice in ['q', 'quit', 'exit']:
                print("👋 Goodbye!")
                break
            elif choice == '1':
                launch_chat()
            elif choice == '2':
                launch_api()
            elif choice == '3':
                run_tests()
            elif choice == '4':
                show_help()
                input("\nPress Enter to return to menu...")
            else:
                print(f"❌ Invalid choice: {choice}")
                print("Please enter 1-4 or 'quit'")

        except KeyboardInterrupt:
            print("\n👋 Goodbye!")
            break
        except Exception as e:
            print(f"❌ Error: {e}")
            print("Please try again.")

if __name__ == "__main__":
    main()
