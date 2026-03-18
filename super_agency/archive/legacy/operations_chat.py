#!/usr/bin/env python3
"""
BIT RAGE LABOUR Operations Chat
Conversational interface for real-time operational updates
"""

import asyncio
import json
from datetime import datetime
from operations_command_interface import handle_operations_query

class OperationsChat:
    """Conversational interface for BIT RAGE LABOUR operations"""

    def __init__(self):
        """Initialize."""
        self.session_start = datetime.now()
        self.conversation_log = []
        self.user_context = {
            "role": "executive",
            "clearance_level": "supreme_command",
            "preferred_format": "concise"
        }

    def display_welcome(self):
        """Display welcome message and available commands"""
        print("""
🤖 BIT RAGE LABOUR Operations Command Interface (OCI)
═════════════════════════════════════════════════════

Welcome to the BIT RAGE LABOUR Operations Chat!

You can now talk to any department head and get real-time operational updates.

📋 Available Departments:
• NCC (Neural Command Center) - Command & Control
• Council 52 - Intelligence Operations
• Portfolio Operations - Company Oversight
• AI Research - Machine Learning & NCL
• Platform Engineering - Infrastructure & DevOps
• Market Intelligence - Market Analysis
• Product Development - Product Strategy
• Security Operations - Security Monitoring
• Financial Operations - Financial Management
• [Any Portfolio Company Name]

💬 Example Queries:
• "How is NCC doing today?"
• "What's the status of Council 52?"
• "Give me an update on TESLA-TECH"
• "Any issues in portfolio operations?"
• "How is AI research progressing?"

Commands:
• /help - Show this help
• /departments - List all departments
• /history - Show conversation history
• /quit - Exit the chat

Type your question or command:
        """.strip())

    def display_departments(self):
        """Display all available departments"""
        print("\n📋 All Available Departments:")
        print("═══════════════════════════════")

        # Core departments
        core_depts = [
            ("NCC", "Neural Command Center - Command & Control"),
            ("Council 52", "Intelligence Operations - CIO Leadership"),
            ("Portfolio Operations", "Company Oversight - Portfolio Management"),
            ("AI Research", "Machine Learning & NCL - AI Development"),
            ("Platform Engineering", "Infrastructure & DevOps - CTO Leadership"),
            ("Market Intelligence", "Market Analysis - CMO Leadership"),
            ("Product Development", "Product Strategy - CPO Leadership"),
            ("Security Operations", "Security Monitoring - CSO Leadership"),
            ("Financial Operations", "Financial Management - CFO Leadership")
        ]

        for dept, desc in core_depts:
            print(f"• {dept:<20} - {desc}")

        try:
            with open('portfolio.json', 'r') as pf:
                portfolio = json.load(pf)
        except (FileNotFoundError, json.JSONDecodeError):
            portfolio = {"repositories": []}
        repo_count = len(portfolio.get('repositories', []))
        print(f"\nPortfolio Companies ({repo_count} total):")
        for repo in portfolio['repositories'][:10]:  # Show first 10
            print(f"• {repo['name']:<20} - Portfolio Company (Tier: {repo.get('tier', 'TBD')})")

        if len(portfolio['repositories']) > 10:
            print(f"• ... and {len(portfolio['repositories']) - 10} more companies")

        print("\n💡 Tip: You can ask about any department by name or describe what you're looking for!")

    def format_response(self, response: dict) -> str:
        """Format the OCI response for display"""

        if response["response_type"] == "clarification_needed":
            return f"""
🤔 Clarification Needed
{response["message"]}

Available departments: {", ".join(response.get("available_departments", []))}
            """.strip()

        elif response["response_type"] == "department_not_found":
            return f"""
❌ Department Not Found
{response["message"]}
            """.strip()

        elif response["response_type"] == "operational_update":
            dept_name = response.get("department_name", "Unknown")
            head = response.get("head", "Unknown Department Head")
            data = response.get("data", {})

            # Format based on department type
            if "portfolio_company" in str(data):
                # Portfolio company response
                return f"""
📊 {dept_name} Operations Update
══════════════════════════════════════════
Department Head: {head}
Autonomy Level: {data.get('autonomy_level', 'Unknown')}
Operational Health: {data.get('operational_health', 'Unknown')}

Recent Activity:
• Repository Status: {data.get('repo_status', {}).get('status', 'Unknown')}
• Recent Commits: {data.get('recent_activity', {}).get('commits', 0)}
• Last Update: {data.get('recent_activity', {}).get('today', 'Unknown')}

{self._format_portfolio_details(data)}
                """.strip()
            else:
                # Core department response
                return f"""
🏢 {dept_name} Operations Update
══════════════════════════════════════════
Department Head: {head}

{self._format_core_department_details(data)}
                """.strip()

        return f"⚠️  Unexpected response type: {response.get('response_type', 'unknown')}"

    def _format_portfolio_details(self, data: dict) -> str:
        """Format portfolio company specific details"""
        details = []

        if data.get("tier") and data["tier"] != "TBD":
            details.append(f"Business Tier: {data['tier']}")

        if data.get("repo_status"):
            status = data["repo_status"]
            if status.get("last_check"):
                details.append(f"Last Checked: {status['last_check']}")

        if data.get("recent_activity", {}).get("delta"):
            delta = data["recent_activity"]["delta"]
            summary = delta.get("summary", {})
            if summary:
                details.append("Activity Summary:")
                if summary.get("code", 0) > 0:
                    details.append(f"  • Code changes: {summary['code']}")
                if summary.get("tests", 0) > 0:
                    details.append(f"  • Test updates: {summary['tests']}")
                if summary.get("docs", 0) > 0:
                    details.append(f"  • Documentation: {summary['docs']}")
                if summary.get("ncl", 0) > 0:
                    details.append(f"  • NCL updates: {summary['ncl']}")

        return "\n".join(details) if details else "No additional details available."

    def _format_core_department_details(self, data: dict) -> str:
        """Format core department specific details"""
        details = []

        # Add department-specific formatting
        if "command_queue_depth" in data:
            details.append(f"Command Queue: {data['command_queue_depth']} pending")
            details.append(f"Active Operations: {data['active_operations']}")
            details.append(f"System Health: {data['system_health']}")
            details.append(f"Resource Utilization: {data['resource_utilization']}%")

        elif "active_intelligence_streams" in data:
            details.append(f"Active Intelligence Streams: {data['active_intelligence_streams']}")
            details.append(f"Pending Analyses: {data['pending_analyses']}")
            details.append(f"Intelligence Quality Score: {data['intelligence_quality_score']}/10")
            details.append(f"Last Major Insight: {data['last_major_insight']}")

        elif "total_companies" in data:
            details.append(f"Total Companies: {data['total_companies']}")
            details.append(f"Active Companies: {data['active_companies']}")
            details.append(f"Integration Progress: {data['integration_progress']}")

        else:
            # Generic formatting for other departments
            for key, value in data.items():
                if isinstance(value, (int, float)):
                    details.append(f"{key.replace('_', ' ').title()}: {value}")
                elif isinstance(value, str):
                    details.append(f"{key.replace('_', ' ').title()}: {value}")

        return "\n".join(details) if details else "Operational data collection in progress..."

    async def run_chat_session(self):
        """Run the interactive chat session"""
        self.display_welcome()

        while True:
            try:
                user_input = input("\n❓ Your query: ").strip()

                if not user_input:
                    continue

                # Handle commands
                if user_input.startswith("/"):
                    if user_input == "/quit":
                        print("\n👋 Goodbye! Session summary:")
                        print(f"Duration: {(datetime.now() - self.session_start).seconds // 60} minutes")
                        print(f"Queries processed: {len(self.conversation_log)}")
                        break
                    elif user_input == "/help":
                        self.display_welcome()
                        continue
                    elif user_input == "/departments":
                        self.display_departments()
                        continue
                    elif user_input == "/history":
                        self.show_history()
                        continue
                    else:
                        print(f"❌ Unknown command: {user_input}")
                        print("Available commands: /help, /departments, /history, /quit")
                        continue

                # Process operational query
                print("🔄 Processing your query...")
                response = await handle_operations_query(user_input, self.user_context)

                # Display formatted response
                print(self.format_response(response))

                # Log conversation
                self.conversation_log.append({
                    "timestamp": datetime.now().isoformat(),
                    "query": user_input,
                    "response": response
                })

            except KeyboardInterrupt:
                print("\n\n👋 Session interrupted. Goodbye!")
                break
            except Exception as e:
                print(f"❌ Error processing query: {e}")
                print("Please try again or use /help for assistance.")

    def show_history(self):
        """Show conversation history"""
        if not self.conversation_log:
            print("📝 No conversation history yet.")
            return

        print(f"\n📝 Conversation History ({len(self.conversation_log)} queries):")
        print("══════════════════════════════════════════════════════════════")

        for i, entry in enumerate(self.conversation_log[-10:], 1):  # Show last 10
            timestamp = entry["timestamp"][11:19]  # HH:MM:SS
            query = entry["query"][:50] + "..." if len(entry["query"]) > 50 else entry["query"]
            dept = entry["response"].get("department_name", "Unknown")

            print(f"{i:2d}. [{timestamp}] {query}")
            print(f"    → {dept}")
            print()

        if len(self.conversation_log) > 10:
            print(f"... and {len(self.conversation_log) - 10} earlier queries")

if __name__ == "__main__":
    chat = OperationsChat()
    asyncio.run(chat.run_chat_session())