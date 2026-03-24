#!/usr/bin/env python3
"""
NCC Resource Allocator
Manages computational and API resources for Bit Rage Systems operations
"""

import json
import os
import psutil
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import logging

class ResourceType:
    CPU = "cpu"
    MEMORY = "memory"
    DISK = "disk"
    NETWORK = "network"
    API_QUOTA = "api_quota"

class NCCResourceAllocator:
    """Neural Command Center - Resource management and optimization"""

    def __init__(self, config_path: str = "ncc_resource_config.json"):
        self.config_path = config_path
        self.config = self.load_config()
        self.setup_logging()
        self.resource_usage = self.initialize_resource_tracking()
        self.allocation_history = []

    def load_config(self) -> Dict:
        """Load resource allocation configuration"""
        default_config = {
            "resources": {
                "cpu_limit_percent": 80,
                "memory_limit_percent": 85,
                "disk_limit_percent": 90,
                "api_quota_limit": 1000,
                "allocation_strategy": "fair_share",
                "monitoring_interval": 30
            },
            "optimization": {
                "auto_scale": True,
                "predictive_allocation": True,
                "resource_reservation": True,
                "emergency_override": True
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
        """Setup resource allocation logging"""
        os.makedirs("ncc_logs", exist_ok=True)

        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - NCC-Resource - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('ncc_logs/resource_allocation.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger("NCC-Resource")

    def initialize_resource_tracking(self) -> Dict:
        """Initialize resource usage tracking"""
        return {
            "cpu": {"allocated": 0, "available": 100, "limit": self.config["resources"]["cpu_limit_percent"]},
            "memory": {"allocated": 0, "available": 100, "limit": self.config["resources"]["memory_limit_percent"]},
            "disk": {"allocated": 0, "available": 100, "limit": self.config["resources"]["disk_limit_percent"]},
            "api_quota": {"allocated": 0, "available": self.config["resources"]["api_quota_limit"], "limit": self.config["resources"]["api_quota_limit"]},
            "active_allocations": {}
        }

    def get_system_resources(self) -> Dict:
        """Get current system resource usage"""
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')

        return {
            "cpu_percent": cpu_percent,
            "memory_percent": memory.percent,
            "memory_available_gb": memory.available / (1024**3),
            "disk_percent": disk.percent,
            "disk_available_gb": disk.free / (1024**3),
            "timestamp": datetime.now().isoformat()
        }

    def allocate_resources(
            self, requester: str, requirements: Dict) ->Optional[str]:
        """Allocate resources for a requester"""

        allocation_id = f"alloc_{requester}_{int(time.time())}"

        # Check if allocation is possible
        if not self.can_allocate(requirements):
            self.logger.warning(
                f"Cannot allocate resources for {requester}: insufficient resources")
            return None

        # Perform allocation
        allocation = {
            "id": allocation_id,
            "requester": requester,
            "requirements": requirements.copy(),
            "allocated_at": datetime.now().isoformat(),
            "status": "active"
        }

        # Update resource tracking
        for resource_type, amount in requirements.items():
            if resource_type in self.resource_usage:
                self.resource_usage[resource_type]["allocated"] += amount
                self.resource_usage[resource_type]["available"] -= amount

        self.resource_usage["active_allocations"][allocation_id] = allocation
        self.allocation_history.append(allocation)

        self.logger.info(
            f"Resources allocated for {requester}: {allocation_id}")
        return allocation_id

    def deallocate_resources(self, allocation_id: str) -> bool:
        """Deallocate resources"""

        if allocation_id not in self.resource_usage["active_allocations"]:
            self.logger.warning(f"Allocation not found: {allocation_id}")
            return False

        allocation = self.resource_usage["active_allocations"][allocation_id]

        # Return resources
        for resource_type, amount in allocation["requirements"].items():
            if resource_type in self.resource_usage:
                self.resource_usage[resource_type]["allocated"] -= amount
                self.resource_usage[resource_type]["available"] += amount

        # Update allocation status
        allocation["deallocated_at"] = datetime.now().isoformat()
        allocation["status"] = "completed"

        del self.resource_usage["active_allocations"][allocation_id]

        self.logger.info(f"Resources deallocated: {allocation_id}")
        return True

    def can_allocate(self, requirements: Dict) -> bool:
        """Check if resource allocation is possible"""

        for resource_type, amount in requirements.items():
            if resource_type in self.resource_usage:
                available = self.resource_usage[resource_type]["available"]
                limit = self.resource_usage[resource_type]["limit"]

                # Check against both available and limit
                if available < amount:
                    return False

                # For system resources, check actual usage
                if resource_type == "cpu":
                    current_usage = self.get_system_resources()["cpu_percent"]
                    if current_usage + amount > limit:
                        return False
                elif resource_type == "memory":
                    current_usage = self.get_system_resources()[
                                                              "memory_percent"]
                    if current_usage + amount > limit:
                        return False

        return True

    def optimize_allocation(self):
        """Optimize resource allocation based on usage patterns"""

        # Analyze allocation history for patterns
        recent_allocations = [
            a for a in self.allocation_history
            if datetime.fromisoformat(a["allocated_at"]) >datetime.now() -
            timedelta(hours=1)]

        # Identify over-allocated resources
        for resource_type, data in self.resource_usage.items():
            if resource_type != "active_allocations":
                utilization = (
                    data["allocated"] /
                    (data["allocated"] +data["available"])) *100

                if utilization > 90:
                    self.logger.warning(
                        f"High utilization detected: {resource_type} at {utilization:.1f}%")
                    # Could trigger auto-scaling or reallocation here

    def get_resource_status(self) -> Dict:
        """Get comprehensive resource status"""

        system_resources = self.get_system_resources()

        status = {
            "system_resources": system_resources,
            "allocation_tracking": self.resource_usage.copy(),
            "active_allocations_count": len(self.resource_usage["active_allocations"]),
            "recent_allocations": len([a for a in self.allocation_history
                                     if datetime.fromisoformat(a["allocated_at"]) > datetime.now() - timedelta(hours=1)]),
            "optimization_needed": self.check_optimization_needed(),
            "health_score": self.calculate_health_score()
        }

        return status

    def check_optimization_needed(self) -> bool:
        """Check if resource optimization is needed"""

        for resource_type, data in self.resource_usage.items():
            if resource_type != "active_allocations":
                utilization = (
                    data["allocated"] /
                    max(data["allocated"] +data["available"],
                        1)) *100
                if utilization > 85:
                    return True

        return False

    def calculate_health_score(self) -> float:
        """Calculate resource health score (0-100)"""

        score = 100

        # Deduct points for high utilization
        for resource_type, data in self.resource_usage.items():
            if resource_type != "active_allocations":
                utilization = (
                    data["allocated"] /
                    max(data["allocated"] +data["available"],
                        1)) *100
                if utilization > 90:
                    score -= 20
                elif utilization > 75:
                    score -= 10

        # Deduct points for system resource issues
        system = self.get_system_resources()
        if system["cpu_percent"] > 80:
            score -= 15
        if system["memory_percent"] > 80:
            score -= 15
        if system["disk_percent"] > 85:
            score -= 10

        return max(0, score)

    def emergency_resource_freeup(self):
        """Emergency resource deallocation for critical operations"""

        self.logger.warning("Emergency resource freeup initiated")

        # Deallocate oldest non-critical allocations
        critical_allocation_ids = []

        for alloc_id, allocation in self.resource_usage["active_allocations"].items():
            # Mark critical allocations (intelligence, api management)
            if "intelligence" in allocation["requester"].lower() or "api" in allocation["requester"].lower():
                critical_allocation_ids.append(alloc_id)

        # Deallocate non-critical allocations
        deallocated_count = 0
        for alloc_id in list(self.resource_usage["active_allocations"].keys()):
            if alloc_id not in critical_allocation_ids:
                self.deallocate_resources(alloc_id)
                deallocated_count += 1

        self.logger.info(
            f"Emergency freeup completed: {deallocated_count} allocations deallocated")

    def save_state(self):
        """Save resource allocation state"""
        state = {
            "resource_usage": self.resource_usage,
            # Keep last 50
            "allocation_history": self.allocation_history[-50:],
            "timestamp": datetime.now().isoformat()
        }

        with open("ncc_resource_state.json", 'w') as f:
            json.dump(state, f, indent=2)

    def load_state(self):
        """Load previous resource state"""
        if os.path.exists("ncc_resource_state.json"):
            with open("ncc_resource_state.json", 'r') as f:
                state = json.load(f)
                self.resource_usage = state.get(
                    "resource_usage", self.initialize_resource_tracking())
                self.allocation_history = state.get("allocation_history", [])

# Global resource allocator instance
resource_allocator = NCCResourceAllocator()

def allocate_resources(requester: str, requirements: Dict) -> Optional[str]:
    """Convenience function for resource allocation"""
    return resource_allocator.allocate_resources(requester, requirements)

def deallocate_resources(allocation_id: str) -> bool:
    """Convenience function for resource deallocation"""
    return resource_allocator.deallocate_resources(allocation_id)

def get_resource_status():
    """Get current resource status"""
    return resource_allocator.get_resource_status()

if __name__ == "__main__":
    # Test Resource Allocator
    print("⚡ NCC Resource Allocator Test")
    print("=" * 40)

    # Test resource allocation
    alloc1 = allocate_resources("council_52", {"cpu": 20, "memory": 30})
    print(f"Allocated resources: {alloc1}")

    alloc2 = allocate_resources("ncl_processor", {"cpu": 15, "api_quota": 50})
    print(f"Allocated resources: {alloc2}")

    # Get status
    status = get_resource_status()
    print(f"Active allocations: {status['active_allocations_count']}")
    print(f"Health score: {status['health_score']}")

    # Deallocate
    if alloc1:
        deallocate_resources(alloc1)
        print("Deallocated first allocation")

    # Final status
    final_status = get_resource_status()
    print(
        f"Final active allocations: {final_status['active_allocations_count']}")

    print("\n✅ NCC Resource Allocator Ready!")
    print("   • Resource tracking: Active")
    print("   • Allocation management: Operational")
    print("   • Optimization monitoring: Enabled")