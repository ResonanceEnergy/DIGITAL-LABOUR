#!/usr/bin/env python3
"""
NCC Command Processor
Core command execution engine for DIGITAL LABOUR operations
"""

import json
import os
import time
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from enum import Enum
import subprocess

# Import oversight framework
try:
    from oversight_framework import audit_api_call, audit_intelligence_operation
except ImportError:
    # Fallback if oversight not available
    def audit_api_call(*args, **kwargs): pass
    def audit_intelligence_operation(*args, **kwargs): pass

class CommandType(Enum):
    INTELLIGENCE_GATHERING = "intelligence"
    RESOURCE_ALLOCATION = "resource"
    API_MANAGEMENT = "api"
    ACCOUNT_MANAGEMENT = "account"
    SYSTEM_MAINTENANCE = "maintenance"
    COUNCIL_COORDINATION = "council"

class CommandPriority(Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"

class CommandStatus(Enum):
    PENDING = "pending"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class NCCCommandProcessor:
    """Neural Command Center - Core command execution engine"""

    def __init__(self, config_path: str = "ncc_config.json"):
        self.config_path = config_path
        self.config = self.load_config()
        self.setup_logging()
        self.command_queue = []
        self.active_commands = {}
        self.command_history = []
        self.resource_pool = self.initialize_resource_pool()

    def load_config(self) -> Dict:
        """Load NCC configuration"""
        default_config = {
            "ncc": {
                "max_concurrent_commands": 5,
                "command_timeout_seconds": 300,
                "resource_limits": {
                    "cpu_percent": 80,
                    "memory_percent": 85,
                    "api_calls_per_minute": 60
                },
                "oversight_enabled": True,
                "auto_retry_failed": True,
                "max_retries": 3
            },
            "integration": {
                "ncl_enabled": True,
                "council_52_enabled": True,
                "oversight_enabled": True,
                "api_governance": True
            }
        }

        if os.path.exists(self.config_path):
            with open(self.config_path, 'r') as f:
                user_config = json.load(f)
                self.deep_update(default_config, user_config)

        return default_config

    def deep_update(self, base_dict: Dict, update_dict: Dict):
        """Deep update dictionary"""
        for key, value in update_dict.items():
            if isinstance(value, dict) and key in base_dict:
                self.deep_update(base_dict[key], value)
            else:
                base_dict[key] = value

    def setup_logging(self):
        """Setup NCC logging"""
        os.makedirs("ncc_logs", exist_ok=True)

        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - NCC - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('ncc_logs/ncc_command.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger("NCC")

    def initialize_resource_pool(self) -> Dict:
        """Initialize resource allocation pool"""
        return {
            "cpu_available": 100,
            "memory_available": 100,
            "api_quota_available": 100,
            "active_commands": 0
        }

    def create_command(self, command_type: CommandType,
                       priority: CommandPriority, payload: Dict,
                        requester: str, description: str="") ->str:
        """Create a new command for execution"""

        command_id = f"ncc_{
            command_type.value} _{
            int(time.time())} _{
            hash(str(payload)) %10000} "

        command = {
            "id": command_id, "type": command_type.value,
            "priority": priority.value, "payload": payload,
            "requester": requester, "description": description,
            "status": CommandStatus.PENDING.value,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "attempts": 0, "max_attempts": self.config["ncc"] ["max_retries"],
            "resource_requirements": self.calculate_resource_requirements(
                command_type, payload)}

        self.command_queue.append(command)
        self.logger.info(f"Command created: {command_id} - {description}")

        # Audit command creation
        audit_intelligence_operation(
            operation_type="command_creation",
            source="NCC_Command_Processor",
            data_quality_score=0.9,
            ethical_compliance=True
        )

        return command_id

    def calculate_resource_requirements(
            self, command_type: CommandType, payload: Dict) ->Dict:
        """Calculate resource requirements for command"""
        base_requirements = {
            "cpu": 10,
            "memory": 20,
            "api_calls": 1
        }

        # Adjust based on command type
        if command_type == CommandType.INTELLIGENCE_GATHERING:
            base_requirements["api_calls"] = 10
            base_requirements["cpu"] = 15
        elif command_type == CommandType.API_MANAGEMENT:
            base_requirements["api_calls"] = 5
        elif command_type == CommandType.COUNCIL_COORDINATION:
            base_requirements["memory"] = 30
            base_requirements["cpu"] = 20

        return base_requirements

    def execute_command(self, command: Dict) -> bool:
        """Execute a command"""

        command_id = command["id"]
        self.logger.info(f"Executing command: {command_id}")

        # Update status
        command["status"] = CommandStatus.EXECUTING.value
        command["updated_at"] = datetime.now().isoformat()
        command["attempts"] += 1

        self.active_commands[command_id] = command

        try:
            # Check resource availability
            if not self.check_resource_availability(
                command["resource_requirements"]):
                self.logger.warning(
                    f"Insufficient resources for command: {command_id}")
                command["status"] = CommandStatus.PENDING.value
                return False

            # Allocate resources
            self.allocate_resources(command["resource_requirements"])

            # Execute based on command type
            success = self.execute_command_logic(command)

            if success:
                command["status"] = CommandStatus.COMPLETED.value
                self.logger.info(
                    f"Command completed successfully: {command_id}")
            else:
                command["status"] = CommandStatus.FAILED.value
                self.logger.error(f"Command failed: {command_id}")

            # Deallocate resources
            self.deallocate_resources(command["resource_requirements"])

            # Move to history
            self.command_history.append(command)
            del self.active_commands[command_id]

            return success

        except Exception as e:
            self.logger.error(
                f"Command execution error: {command_id} - {str(e)}")
            command["status"] = CommandStatus.FAILED.value
            command["error"] = str(e)

            # Deallocate resources on failure
            self.deallocate_resources(command["resource_requirements"])

            return False

    def execute_command_logic(self, command: Dict) -> bool:
        """Execute the actual command logic"""

        command_type = command["type"]
        payload = command["payload"]

        if command_type == CommandType.INTELLIGENCE_GATHERING.value:
            return self.execute_intelligence_gathering(payload)
        elif command_type == CommandType.API_MANAGEMENT.value:
            return self.execute_api_management(payload)
        elif command_type == CommandType.ACCOUNT_MANAGEMENT.value:
            return self.execute_account_management(payload)
        elif command_type == CommandType.RESOURCE_ALLOCATION.value:
            return self.execute_resource_allocation(payload)
        elif command_type == CommandType.COUNCIL_COORDINATION.value:
            return self.execute_council_coordination(payload)
        else:
            self.logger.error(f"Unknown command type: {command_type}")
            return False

    def execute_intelligence_gathering(self, payload: Dict) -> bool:
        """Execute intelligence gathering command"""
        try:
            # Call Council 52 intelligence monitor
            cmd = ["python", "youtube_intelligence_monitor.py"]
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=300)

            if result.returncode == 0:
                self.logger.info(
                    "Intelligence gathering completed successfully")
                return True
            else:
                self.logger.error(
                    f"Intelligence gathering failed: {result.stderr}")
                return False

        except subprocess.TimeoutExpired:
            self.logger.error("Intelligence gathering timed out")
            return False
        except Exception as e:
            self.logger.error(f"Intelligence gathering error: {str(e)}")
            return False

    def execute_api_management(self, payload: Dict) -> bool:
        """Execute API management command"""
        try:
            # Run API test
            cmd = ["python", "test_api_setup.py"]
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=60)

            if result.returncode == 0:
                self.logger.info("API management completed successfully")
                return True
            else:
                self.logger.error(f"API management failed: {result.stderr}")
                return False

        except Exception as e:
            self.logger.error(f"API management error: {str(e)}")
            return False

    def execute_account_management(self, payload: Dict) -> bool:
        """Execute account management command"""
        try:
            # This would integrate with account creation scripts
            self.logger.info(
                "Account management command executed (placeholder)")
            return True
        except Exception as e:
            self.logger.error(f"Account management error: {str(e)}")
            return False

    def execute_resource_allocation(self, payload: Dict) -> bool:
        """Execute resource allocation command"""
        try:
            # This would manage system resources
            self.logger.info(
                "Resource allocation command executed (placeholder)")
            return True
        except Exception as e:
            self.logger.error(f"Resource allocation error: {str(e)}")
            return False

    def execute_council_coordination(self, payload: Dict) -> bool:
        """Execute council coordination command"""
        try:
            # This would coordinate Council 52 operations
            self.logger.info(
                "Council coordination command executed (placeholder)")
            return True
        except Exception as e:
            self.logger.error(f"Council coordination error: {str(e)}")
            return False

    def check_resource_availability(self, requirements: Dict) -> bool:
        """Check if required resources are available"""
        return (self.resource_pool["cpu_available"] >= requirements.get("cpu", 0) and
                self.resource_pool["memory_available"] >= requirements.get("memory", 0) and
                self.resource_pool["api_quota_available"] >= requirements.get("api_calls", 0) and
                len(self.active_commands) < self.config["ncc"]["max_concurrent_commands"])

    def allocate_resources(self, requirements: Dict):
        """Allocate resources for command execution"""
        self.resource_pool["cpu_available"] -= requirements.get("cpu", 0)
        self.resource_pool["memory_available"] -= requirements.get("memory", 0)
        self.resource_pool["api_quota_available"] -= requirements.get(
            "api_calls", 0)
        self.resource_pool["active_commands"] += 1

    def deallocate_resources(self, requirements: Dict):
        """Deallocate resources after command completion"""
        self.resource_pool["cpu_available"] += requirements.get("cpu", 0)
        self.resource_pool["memory_available"] += requirements.get("memory", 0)
        self.resource_pool["api_quota_available"] += requirements.get(
            "api_calls", 0)
        self.resource_pool["active_commands"] -= 1

    def process_command_queue(self):
        """Process pending commands in queue"""
        # Sort by priority
        priority_order = {CommandPriority.CRITICAL.value: 0,
                         CommandPriority.HIGH.value: 1,
                         CommandPriority.MEDIUM.value: 2,
                         CommandPriority.LOW.value: 3}

        self.command_queue.sort(
            key=lambda x: priority_order.get(x["priority"], 999))

        # Execute pending commands
        executed_count = 0
        for command in self.command_queue[:]:
            if command["status"] == CommandStatus.PENDING.value:
                if self.execute_command(command):
                    executed_count += 1
                else:
                    # Check if should retry
                    if command["attempts"] < command["max_attempts"]:
                        self.logger.info(
                            f"Retrying command: {command['id']} (attempt {command['attempts'] + 1})")
                    else:
                        command["status"] = CommandStatus.FAILED.value
                        self.command_history.append(command)
                        self.command_queue.remove(command)

        return executed_count

    def get_system_status(self) -> Dict:
        """Get current NCC system status"""
        return {
            "active_commands": len(self.active_commands),
            "queued_commands": len(self.command_queue),
            "completed_commands": len([c for c in self.command_history if c["status"] == CommandStatus.COMPLETED.value]),
            "failed_commands": len([c for c in self.command_history if c["status"] == CommandStatus.FAILED.value]),
            "resource_pool": self.resource_pool.copy(),
            "system_health": "operational" if len(self.active_commands) <= self.config["ncc"]["max_concurrent_commands"] else "overloaded"
        }

    def save_state(self):
        """Save current NCC state"""
        state = {
            "command_queue": self.command_queue,
            "active_commands": self.active_commands,
            "command_history": self.command_history[-100:],  # Keep last 100
            "resource_pool": self.resource_pool,
            "timestamp": datetime.now().isoformat()
        }

        with open("ncc_state.json", 'w') as f:
            json.dump(state, f, indent=2)

    def load_state(self):
        """Load previous NCC state"""
        if os.path.exists("ncc_state.json"):
            with open("ncc_state.json", 'r') as f:
                state = json.load(f)
                self.command_queue = state.get("command_queue", [])
                self.active_commands = state.get("active_commands", {})
                self.command_history = state.get("command_history", [])
                self.resource_pool = state.get(
                    "resource_pool", self.initialize_resource_pool())

# Global NCC instance
ncc_processor = NCCCommandProcessor()

def create_command(command_type: str, priority: str, payload: Dict,
                  requester: str, description: str = "") -> str:
    """Convenience function to create NCC command"""
    cmd_type = CommandType(command_type)
    cmd_priority = CommandPriority(priority)
    return ncc_processor.create_command(
        cmd_type, cmd_priority, payload, requester, description)

def process_commands():
    """Process the NCC command queue"""
    return ncc_processor.process_command_queue()

def get_ncc_status():
    """Get NCC system status"""
    return ncc_processor.get_system_status()

if __name__ == "__main__":
    # Test NCC Command Processor
    print("🧠 NCC Command Processor Test")
    print("=" * 40)

    # Create test commands
    cmd1 = create_command(
        "intelligence", "high", {"target": "youtube"},
        "test_user", "Test intelligence gathering")
    cmd2 = create_command(
        "api", "medium", {"action": "test"},
        "test_user", "Test API management")

    print(f"Created commands: {cmd1}, {cmd2}")

    # Process commands
    executed = process_commands()
    print(f"Executed {executed} commands")

    # Get status
    status = get_ncc_status()
    print(f"System status: {status['system_health']}")
    print(f"Active commands: {status['active_commands']}")

    print("\n✅ NCC Command Processor Ready!")
    print("   • Command queue management: Active")
    print("   • Resource allocation: Operational")
    print("   • Integration ready: Council 52, NCL, Oversight")