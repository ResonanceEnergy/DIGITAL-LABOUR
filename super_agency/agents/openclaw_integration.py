#!/usr/bin/env python3
"""
OpenClaw Integration Agent for Bit Rage Labour

Integrates OpenClaw autonomous AI agent capabilities into the Bit Rage Labour platform.
Provides messaging interfaces, workflow automation, and autonomous task execution.
"""

import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from .common import CONFIG, Log, ensure_dir, get_portfolio

# OpenClaw configuration
OPENCLAW_CONFIG_DIR = Path.home() / ".openclaw"
OPENCLAW_SKILLS_DIR = OPENCLAW_CONFIG_DIR / "skills"
OPENCLAW_SESSIONS_DIR = OPENCLAW_CONFIG_DIR / "sessions"


class OpenClawIntegrationAgent:
    """AI-powered agent for integrating OpenClaw autonomous capabilities"""

    def __init__(self, model_client=None):
        self.name = "OpenClawIntegrationAgent"
        self.model_client = model_client
        self.status = "initialized"
        self.openclaw_path = self._find_openclaw()

        # Create AutoGen agent if model client is available
        if self.model_client:
            from autogen_agentchat.agents import AssistantAgent

            self.agent = AssistantAgent(
                name="openclaw_integrator",
                system_message="""You are an expert OpenClaw integration specialist.
                Your role is to seamlessly integrate OpenClaw autonomous AI capabilities
                into the Bit Rage Labour platform, enabling advanced messaging interfaces,
                workflow automation, and autonomous task execution.

                Key responsibilities:
                - Configure OpenClaw messaging platforms (Telegram, Discord, WhatsApp)
                - Create and manage OpenClaw skills for Bit Rage Labour workflows
                - Set up secure communication channels between agents
                - Monitor and optimize OpenClaw performance
                - Implement CRITICAL security boundaries and access controls
                - Enable autonomous task delegation to OpenClaw
                - Prevent prompt injection and malicious skill execution
                - Monitor API costs and prevent budget overruns

                CRITICAL SECURITY REQUIREMENTS:
                - NEVER run OpenClaw on primary machines or with access to real accounts
                - ALWAYS use sandboxed environments (VPS, dedicated Mac Mini, VM)
                - Create dedicated burner accounts for all services
                - Implement strict permission controls and cost limits
                - Monitor for prompt injection attempts
                - Use read-only access wherever possible
                - Regular security audits and log reviews

                Focus on creating powerful, secure integrations that enhance BIT RAGE LABOUR autonomy.""",
                model_client=self.model_client,)
        else:
            self.agent = None

    def _find_openclaw(self) -> Optional[Path]:
        """Find OpenClaw installation path with detailed logging."""
        print("--- Debug: Starting _find_openclaw ---")

        # On Windows, pnpm creates a cmd shim. We need to find that.
        if sys.platform == "win32":
            try:
                print("Debug: Running 'where openclaw' on Windows...")
                # Using shell=True is often necessary for `where` on Windows
                result = subprocess.run(
                    "where openclaw", capture_output=True, text=True,
                    check=False, shell=True)
                print(
                    f"Debug: 'where' command returned code: {result.returncode}")
                print(f"Debug: 'where' stdout: {result.stdout.strip()}")
                print(f"Debug: 'where' stderr: {result.stderr.strip()}")

                if result.returncode == 0 and result.stdout.strip():
                    # `where` can return multiple paths, prioritize the .cmd file
                    paths = result.stdout.strip().split('\n')
                    cmd_path = next(
                        (p.strip() for p in paths
                         if p.strip().endswith('.cmd')),
                        None)

                    if cmd_path:
                        found_path = Path(cmd_path)
                        print(
                            f"Debug: Found .cmd path with 'where': {found_path}")
                        if found_path.exists():
                            print(
                                "--- Debug: _find_openclaw successful (found .cmd with 'where') ---")
                            return found_path

                    # Fallback to the first path if no .cmd is found
                    first_path_str = paths[0].strip()
                    found_path = Path(first_path_str)
                    print(
                        f"Debug: Found path with 'where' (fallback): {found_path}")
                    if found_path.exists():
                        print(
                            "--- Debug: _find_openclaw successful (found with 'where') ---")
                        return found_path
                    else:
                        print(
                            f"Debug: Path from 'where' does not exist: {found_path}")

            except Exception as e:
                print(f"Debug: Exception running 'where openclaw': {e}")

        # Fallback to checking common installation locations
        print("Debug: Falling back to checking common paths...")
        possible_paths = [
            Path.home() / "AppData" / "Roaming" / "npm" / \
                      "openclaw.cmd", # Global npm on Windows
            Path.home() / ".local" / "bin" / "openclaw", # Common for pipx
            Path.home() / ".openclaw" / "bin" / "claw",
            Path.home() / "opt" / "openclaw" / "bin" / "claw",
            Path("/usr/local/bin/claw"),
            Path("/usr/bin/claw"),
        ]

        for path in possible_paths:
            print(f"Debug: Checking path: {path}")
            if path.exists():
                print(f"Debug: Found existing path: {path}")
                print("--- Debug: _find_openclaw successful (found in common paths) ---")
                return path

        # Try to find in PATH using 'which' (for non-Windows)
        if sys.platform != "win32":
            try:
                print("Debug: Running 'which openclaw'...")
                result = subprocess.run(
                    ["which", "openclaw"],
                    capture_output=True, text=True, check=False)
                print(
                    f"Debug: 'which' command returned code: {result.returncode}")
                print(f"Debug: 'which' stdout: {result.stdout.strip()}")
                if result.returncode == 0:
                    found_path = Path(result.stdout.strip())
                    print(f"Debug: Found path with 'which': {found_path}")
                    print(
                        "--- Debug: _find_openclaw successful (found with 'which') ---")
                    return found_path
            except Exception as e:
                print(f"Debug: Exception running 'which': {e}")

        print("--- Debug: _find_openclaw failed to find executable ---")
        return None

    def is_openclaw_installed(self) -> bool:
        """Check if OpenClaw is installed and accessible"""
        return self.openclaw_path is not None and self.openclaw_path.exists()

    def install_openclaw(self) -> Dict[str, Any]:
        """Install OpenClaw using the official installation script"""
        try:
            # Check if already installed
            if self._find_openclaw():
                Log.info("OpenClaw is already installed")
                return {
                    "success": True,
                    "message": "OpenClaw is already installed",
                    "path": str(self.openclaw_path),
                    "agent": self.name,
                    "timestamp": self._now_iso(),
                    "status": "success",
                }

            Log.info("OpenClaw not found. Manual installation required.")
            Log.info("Please run the following command manually in your terminal:")
            Log.info("curl -fsSL https://openclaw.ai/install.sh | bash")
            Log.info("After installation, verify with: openclaw --version")

            # Try automatic installation (may require sudo)
            Log.info("Attempting automatic installation...")
            try:
                result = subprocess.run(
                    ["curl", "-fsSL", "https://openclaw.ai/install.sh"],
                    capture_output=True,
                    text=True,
                    timeout=30,
                    check=False,
                )

                if result.returncode != 0:
                    return {
                        "success": False,
                        "error": f"Failed to download install script: {result.stderr}",
                        "agent": self.name,
                        "timestamp": self._now_iso(),
                        "status": "error",
                    }

                # Execute the downloaded script
                install_script = result.stdout
                result = subprocess.run(
                    ["bash", "-c", install_script],
                    capture_output=True,
                    text=True,
                    timeout=120,  # Give more time for installation
                    check=False,
                )

                if result.returncode == 0:
                    # Re-find the path after installation
                    self.openclaw_path = self._find_openclaw()
                    Log.info("OpenClaw installed successfully")
                    return {
                        "success": True,
                        "message": "OpenClaw installed successfully",
                        "path": str(self.openclaw_path),
                        "agent": self.name,
                        "timestamp": self._now_iso(),
                        "status": "success",
                    }
                else:
                    Log.warn(f"Automatic installation failed: {result.stderr}")
                    Log.info(
                        "Please install OpenClaw manually using the command above."
                    )

            except subprocess.TimeoutExpired:
                Log.warn(
                    "Installation timed out - may require manual installation")

            return {
                "success": False,
                "error": "Automatic installation failed. Please install manually.",
                "manual_command": "curl -fsSL https://openclaw.ai/install.sh | bash",
                "agent": self.name,
                "timestamp": self._now_iso(),
                "status": "error",
            }

        except Exception as e:
            Log.error(f"OpenClaw installation failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "agent": self.name,
                "timestamp": self._now_iso(),
                "status": "error",
            }

    def configure_messaging_platform(
        self, platform: str, config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Configure OpenClaw for a messaging platform"""
        try:
            if not self.is_openclaw_installed():
                return {
                    "success": False,
                    "error": "OpenClaw not installed",
                    "agent": self.name,
                    "timestamp": self._now_iso(),
                    "status": "error",
                }

            # Validate platform
            supported_platforms = ["telegram",
                "discord", "whatsapp", "signal", "slack"]
            if platform.lower() not in supported_platforms:
                return {
                    "success": False,
                    "error": f"Unsupported platform: {platform}",
                    "supported": supported_platforms,
                    "agent": self.name,
                    "timestamp": self._now_iso(),
                    "status": "error",
                }

            # Configure the platform
            cmd = [str(self.openclaw_path), "config",
                       "platform", platform.lower()]

            # Add platform-specific config
            if platform.lower() == "telegram":
                if "bot_token" in config:
                    cmd.extend(["--token", config["bot_token"]])
            elif platform.lower() == "discord":
                if "bot_token" in config:
                    cmd.extend(["--token", config["bot_token"]])
            # Add other platform configs as needed

            result = subprocess.run(
                cmd, capture_output=True, text=True, check=False)

            if result.returncode == 0:
                Log.info(f"Configured OpenClaw for {platform}")
                return {
                    "success": True,
                    "message": f"Successfully configured {platform} integration",
                    "platform": platform,
                    "agent": self.name,
                    "timestamp": self._now_iso(),
                    "status": "success",
                }
            else:
                return {
                    "success": False,
                    "error": f"Configuration failed: {result.stderr}",
                    "agent": self.name,
                    "timestamp": self._now_iso(),
                    "status": "error",
                }

        except Exception as e:
            Log.error(f"Platform configuration failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "agent": self.name,
                "timestamp": self._now_iso(),
                "status": "error",
            }

    def create_BIT RAGE LABOUR_skill(
        self, skill_name: str, description: str, code: str
    ) -> Dict[str, Any]:
        """Create a custom OpenClaw skill for Bit Rage Labour integration"""
        try:
            ensure_dir(OPENCLAW_SKILLS_DIR)

            skill_path = OPENCLAW_SKILLS_DIR / f"{skill_name}.js"

            # Create skill template
            skill_template = f"""
// BIT RAGE LABOUR Integration Skill: {skill_name}
// {description}

const {{ exec }} = require('child_process');
const path = require('path');

class {skill_name}Skill {{
    constructor() {{
        this.name = '{skill_name}';
        this.description = '{description}';
    }}

    async execute(message, context) {{
        try {{
            // BIT RAGE LABOUR integration code
            {code}

            return {{
                success: true,
                message: '{skill_name} executed successfully'
            }};
        }} catch (error) {{
            console.error('Skill execution failed:', error);
            return {{
                success: false,
                error: error.message
            }};
        }}
    }}
}}

module.exports = {skill_name}Skill;
"""

            skill_path.write_text(skill_template, encoding="utf-8")

            # Register the skill with OpenClaw
            if self.openclaw_path:
                cmd = [str(self.openclaw_path), "skill",
                           "register", str(skill_path)]
                result = subprocess.run(
                    cmd, capture_output=True, text=True, check=False
                )

                if result.returncode == 0:
                    Log.info(f"Created OpenClaw skill: {skill_name}")
                    return {
                        "success": True,
                        "message": f"Created and registered skill: {skill_name}",
                        "skill_path": str(skill_path),
                        "agent": self.name,
                        "timestamp": self._now_iso(),
                        "status": "success",
                    }
                else:
                    return {
                        "success": False,
                        "error": f"Skill registration failed: {result.stderr}",
                        "agent": self.name,
                        "timestamp": self._now_iso(),
                        "status": "error",
                    }
            else:
                return {
                    "success": True,
                    "message": f"Created skill file: {skill_name} (OpenClaw not available for registration)",
                    "skill_path": str(skill_path),
                    "agent": self.name,
                    "timestamp": self._now_iso(),
                    "status": "success",
                }

        except Exception as e:
            Log.error(f"Skill creation failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "agent": self.name,
                "timestamp": self._now_iso(),
                "status": "error",
            }

    def send_message_to_openclaw(
        self, platform: str, message: str, context: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Send a message to OpenClaw for processing"""
        try:
            if not self.is_openclaw_installed():
                return {
                    "success": False,
                    "error": "OpenClaw not installed",
                    "agent": self.name,
                    "timestamp": self._now_iso(),
                    "status": "error",
                }

            # Prepare message payload
            payload = {
                "message": message,
                "platform": platform,
                "context": context or {},
                "timestamp": self._now_iso(),
            }

            # Send via OpenClaw CLI
            cmd = [str(self.openclaw_path), "message",
                       platform, json.dumps(payload)]

            result = subprocess.run(
                cmd, capture_output=True, text=True, check=False)

            if result.returncode == 0:
                response = json.loads(
                    result.stdout) if result.stdout.strip() else {}
                return {
                    "success": True,
                    "message": "Message sent to OpenClaw successfully",
                    "response": response,
                    "agent": self.name,
                    "timestamp": self._now_iso(),
                    "status": "success",
                }
            else:
                return {
                    "success": False,
                    "error": f"Message send failed: {result.stderr}",
                    "agent": self.name,
                    "timestamp": self._now_iso(),
                    "status": "error",
                }

        except Exception as e:
            Log.error(f"Message send failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "agent": self.name,
                "timestamp": self._now_iso(),
                "status": "error",
            }

    def execute(self, task: str) -> Dict[str, Any]:
        """Execute OpenClaw integration tasks"""
        try:
            if "install" in task.lower() and "openclaw" in task.lower():
                return self.install_openclaw()

            elif "configure" in task.lower() and "platform" in task.lower():
                # Parse platform configuration request
                # This would need more sophisticated parsing in production
                return {
                    "success": False,
                    "error": "Platform configuration requires specific parameters",
                    "agent": self.name,
                    "timestamp": self._now_iso(),
                    "status": "error",
                }

            elif "create" in task.lower() and "skill" in task.lower():
                # Parse skill creation request
                return {
                    "success": False,
                    "error": "Skill creation requires specific parameters",
                    "agent": self.name,
                    "timestamp": self._now_iso(),
                    "status": "error",
                }

            else:
                # General OpenClaw operations
                return {
                    "success": True,
                    "message": f"OpenClaw integration task processed: {task}",
                    "installed": self.is_openclaw_installed(),
                    "agent": self.name,
                    "timestamp": self._now_iso(),
                    "status": "success",
                }

        except Exception as e:
            Log.error(f"OpenClaw integration execution failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "agent": self.name,
                "timestamp": self._now_iso(),
                "status": "error",
            }

    def security_audit(self) -> Dict[str, Any]:
        """
        Perform comprehensive security audit of OpenClaw integration.
        Based on critical security issues identified in OpenClaw community.
        """
        audit_results = {
            "audit_timestamp": self._now_iso(),
            "overall_risk_level": "UNKNOWN",
            "critical_issues": [],
            "warnings": [],
            "recommendations": [],
            "checks_performed": [],
        }

        try:
            # Check 1: Installation status
            is_installed = self._find_openclaw() is not None
            audit_results["checks_performed"].append(
                {
                    "check": "openclaw_installation",
                    "status": "PASS" if is_installed else "FAIL",
                    "details": f"OpenClaw {'is' if is_installed else 'is not'} installed",
                }
            )

            if not is_installed:
                audit_results["critical_issues"].append(
                    "OpenClaw not found - cannot perform security audit"
                )
                audit_results["overall_risk_level"] = "UNKNOWN"
                return audit_results

            # Check 2: Configuration directory exposure
            config_dir = Path.home() / ".openclaw"
            if config_dir.exists():
                # Check if config directory is world-readable
                import stat

                config_stat = config_dir.stat()
                if config_stat.st_mode & stat.S_IROTH:  # World readable
                    audit_results["critical_issues"].append(
                        "OpenClaw config directory is world-readable - API keys may be exposed"
                    )
                    audit_results["recommendations"].append(
                        "Run: chmod 700 ~/.openclaw to restrict access"
                    )

                audit_results["checks_performed"].append(
                    {
                        "check": "config_directory_permissions",
                        "status": (
                            "FAIL" if config_stat.st_mode & stat.S_IROTH else "PASS"
                        ),
                        "details": f"Config directory permissions: {oct(config_stat.st_mode)}",
                    }
                )

            # Check 3: Check for plaintext credentials
            credentials_found = []
            if config_dir.exists():
                for config_file in config_dir.rglob("*.json"):
                    try:
                        with open(config_file, "r") as f:
                            content = f.read()
                            # Look for API key patterns
                            if "sk-" in content or "api" in content.lower():
                                credentials_found.append(str(config_file))
                    except (OSError, UnicodeDecodeError):
                        pass

            if credentials_found:
                audit_results["critical_issues"].append(
                    f"Potential plaintext credentials found in: {', '.join(credentials_found)}"
                )
                audit_results["recommendations"].append(
                    "Move credentials to secure key management system"
                )

            audit_results["checks_performed"].append(
                {
                    "check": "plaintext_credentials",
                    "status": "FAIL" if credentials_found else "PASS",
                    "details": f"Found {len(credentials_found)} files with potential credentials",
                }
            )

            # Check 4: Network exposure check
            try:
                import socket

                # Check if OpenClaw is listening on any ports
                result = subprocess.run(
                    ["lsof", "-i", "-P", "-n"],
                    capture_output=True,
                    text=True,
                    timeout=10,
                )
                open_ports = []
                for line in result.stdout.split("\n"):
                    if "openclaw" in line.lower() or "node" in line.lower():
                        parts = line.split()
                        if len(parts) >= 9:
                            port_info = parts[8]
                            if ":" in port_info:
                                open_ports.append(port_info)

                if open_ports:
                    audit_results["warnings"].append(
                        f"OpenClaw has open network ports: {', '.join(open_ports)}"
                    )
                    audit_results["recommendations"].append(
                        "Ensure OpenClaw is bound to localhost only (127.0.0.1)"
                    )

                audit_results["checks_performed"].append(
                    {
                        "check": "network_exposure",
                        "status": "WARN" if open_ports else "PASS",
                        "details": f"Open ports: {open_ports if open_ports else 'None'}",
                    }
                )

            except Exception as e:
                audit_results["checks_performed"].append(
                    {
                        "check": "network_exposure",
                        "status": "ERROR",
                        "details": f"Could not check network exposure: {e}",
                    }
                )

            # Check 5: Skills directory security
            skills_dir = config_dir / "skills"
            if skills_dir.exists():
                skill_count = len(list(skills_dir.glob("*.js")))
                audit_results["checks_performed"].append(
                    {
                        "check": "skills_count",
                        "status": "INFO",
                        "details": f"Found {skill_count} skills installed",
                    }
                )

                if skill_count > 0:
                    audit_results["warnings"].append(
                        f"{skill_count} skills installed - review for malicious code"
                    )
                    audit_results["recommendations"].append(
                        "Audit all installed skills for security vulnerabilities"
                    )

            # Check 6: Cost monitoring
            audit_results["recommendations"].append(
                "Implement API cost monitoring and daily limits"
            )
            audit_results["recommendations"].append(
                "Use cheaper models (Haiku/Kimi) for routine tasks"
            )

            # Determine overall risk level
            critical_count = len(audit_results["critical_issues"])
            warning_count = len(audit_results["warnings"])

            if critical_count > 0:
                audit_results["overall_risk_level"] = "CRITICAL"
            elif warning_count > 2:
                audit_results["overall_risk_level"] = "HIGH"
            elif warning_count > 0:
                audit_results["overall_risk_level"] = "MEDIUM"
            else:
                audit_results["overall_risk_level"] = "LOW"

            # Add general recommendations
            audit_results["recommendations"].extend(
                [
                    "Run OpenClaw in isolated environment (VPS/Mac Mini/VM)",
                    "Create dedicated burner accounts for all services",
                    "Never connect to password managers or primary accounts",
                    "Implement prompt injection detection",
                    "Regular security audits and log monitoring",
                    "Use read-only permissions wherever possible",
                ]
            )

        except Exception as e:
            audit_results["critical_issues"].append(
                f"Security audit failed: {e}")
            audit_results["overall_risk_level"] = "ERROR"

        return audit_results

    def _now_iso(self) -> str:
        """Get current timestamp in ISO format"""
        import datetime

        return datetime.datetime.now().astimezone().isoformat()
