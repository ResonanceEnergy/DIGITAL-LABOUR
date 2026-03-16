"""
NCC API Management Adapter
Handles API key management, rate limiting, and API operations oversight
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import json
import os
from pathlib import Path

from ..engine.command_processor import NCCCommandProcessor
from ..engine.resource_allocator import NCCResourceAllocator
from ..contracts.schemas import AuditRecord, create_audit_record, create_command_record

class NCCAPIManagementAdapter:
    """
    Adapter for managing API operations, keys, and rate limiting within NCC
    """

    def __init__(self, api_config_path: str = "../../config/api_config.json"):
        self.api_config_path = Path(api_config_path)
        self.command_processor = NCCCommandProcessor()
        self.resource_allocator = NCCResourceAllocator()
        self.api_keys = self._load_api_keys()
        self.rate_limits = {}
        self.api_call_history = []
        self.audit_log = []

    def _load_api_keys(self) -> Dict[str, Dict[str, Any]]:
        """
        Load API keys from secure storage

        Returns:
            Dictionary of API configurations
        """
        if self.api_config_path.exists():
            try:
                with open(self.api_config_path, 'r') as f:
                    return json.load(f)
            except Exception as e:
                print(f"Error loading API config: {e}")

        # Return default structure if config doesn't exist
        return {
            "youtube_data_api": {
                "key": os.getenv("YOUTUBE_API_KEY", ""),
                "quota_limit": 10000,
                "quota_used": 0,
                "reset_date": (datetime.now() + timedelta(days=1)).isoformat()
            },
            "microsoft_graph": {
                "client_id": os.getenv("MS_GRAPH_CLIENT_ID", ""),
                "client_secret": os.getenv("MS_GRAPH_CLIENT_SECRET", ""),
                "tenant_id": os.getenv("MS_GRAPH_TENANT_ID", ""),
                "rate_limit": 1000,
                "calls_this_hour": 0
            },
            "azure_management": {
                "subscription_id": os.getenv("AZURE_SUBSCRIPTION_ID", ""),
                "client_id": os.getenv("AZURE_CLIENT_ID", ""),
                "client_secret": os.getenv("AZURE_CLIENT_SECRET", ""),
                "tenant_id": os.getenv("AZURE_TENANT_ID", ""),
                "rate_limit": 12000,
                "calls_this_hour": 0
            }
        }

    async def execute_api_call(self, api_name: str, endpoint: str,
                               method: str="GET",
                               payload: Optional[Dict[str, Any]]=None,
                               requester: str="system") ->Dict[str, Any]:
        """
        Execute an API call with oversight and rate limiting

        Args:
            api_name: Name of the API to call
            endpoint: API endpoint
            method: HTTP method
            payload: Request payload
            requester: Entity requesting the API call

        Returns:
            API call result
        """
        # Check rate limits and quotas
        rate_check = await self._check_rate_limits(api_name)
        if not rate_check["allowed"]:
            return {
                "success": False,
                "error": "Rate limit exceeded",
                "retry_after": rate_check["retry_after"]
            }

        # Allocate API call resource
        resource_allocated = await self.resource_allocator.allocate_resources({
            "api_calls": 1,
            "api_name": api_name
        })

        if not resource_allocated:
            return {
                "success": False,
                "error": "API call resource allocation failed"
            }

        # Create audit record
        audit_record = create_audit_record(
            id=f"api_{datetime.now().isoformat()}",
            operation="api_call",
            timestamp=datetime.now().isoformat(),
            status="pending",
            details={
                "api_name": api_name,
                "endpoint": endpoint,
                "method": method,
                "requester": requester
            },
            user_context={"user_id": requester},
            resource_impact={"api_calls": 1}
        )

        try:
            # Execute the API call (placeholder - actual implementation would make real API calls)
            result = await self._make_api_call(api_name, endpoint, method, payload)

            # Update audit record
            audit_record.status = "success" if result["success"] else "failure"
            audit_record.details["response"] = result

            # Update rate limits and quotas
            await self._update_rate_limits(api_name)

            # Log the call
            self.api_call_history.append({
                "timestamp": datetime.now().isoformat(),
                "api_name": api_name,
                "endpoint": endpoint,
                "success": result["success"],
                "requester": requester
            })

            return result

        except Exception as e:
            audit_record.status = "failure"
            audit_record.details["error"] = str(e)

            return {
                "success": False,
                "error": str(e)
            }

        finally:
            # Log audit record
            self.audit_log.append(audit_record)

            # Deallocate resource
            await self.resource_allocator.deallocate_resources({
                "api_calls": 1,
                "api_name": api_name
            })

    async def _make_api_call(self, api_name: str, endpoint: str, method: str,
                           payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Make the actual API call

        Args:
            api_name: API to call
            endpoint: Endpoint
            method: HTTP method
            payload: Request payload

        Returns:
            API response
        """
        # This is a placeholder - actual implementation would use appropriate API clients
        # For example, google-api-python-client for YouTube, msgraph for Microsoft Graph, etc.

        if api_name == "youtube_data_api":
            return await self._call_youtube_api(endpoint, method, payload)
        elif api_name == "microsoft_graph":
            return await self._call_microsoft_graph(endpoint, method, payload)
        elif api_name == "azure_management":
            return await self._call_azure_management(endpoint, method, payload)
        else:
            return {
                "success": False,
                "error": f"Unknown API: {api_name}"
            }

    async def _call_youtube_api(self, endpoint: str, method: str, payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Placeholder for YouTube API calls"""
        # Actual implementation would use google-api-python-client
        return {
            "success": True,
            "data": {"message": f"YouTube API call to {endpoint} simulated"}
        }

    async def _call_microsoft_graph(
        self, endpoint: str, method: str, payload:
        Optional[Dict[str, Any]]=None) ->Dict[
        str, Any]:
        """Placeholder for Microsoft Graph API calls"""
        # Actual implementation would use msgraph-sdk
        return {
            "success": True,
            "data": {"message": f"Microsoft Graph API call to {endpoint} simulated"}
        }

    async def _call_azure_management(
        self, endpoint: str, method: str, payload:
        Optional[Dict[str, Any]]=None) ->Dict[
        str, Any]:
        """Placeholder for Azure Management API calls"""
        # Actual implementation would use azure-mgmt-* packages
        return {
            "success": True,
            "data": {"message": f"Azure Management API call to {endpoint} simulated"}
        }

    async def _check_rate_limits(self, api_name: str) -> Dict[str, Any]:
        """
        Check if API call is within rate limits

        Args:
            api_name: API to check

        Returns:
            Rate limit check result
        """
        if api_name not in self.api_keys:
            return {"allowed": False, "error": "API not configured"}

        api_config = self.api_keys[api_name]
        current_time = datetime.now()

        # Check quota limits
        if "quota_limit" in api_config:
            quota_used = api_config.get("quota_used", 0)
            quota_limit = api_config["quota_limit"]

            if quota_used >= quota_limit:
                reset_date = datetime.fromisoformat(
                    api_config.get("reset_date", current_time.isoformat()))
                if current_time < reset_date:
                    return {
                        "allowed": False,
                        "retry_after": (reset_date - current_time).total_seconds()
                    }

        # Check rate limits (calls per hour)
        if "rate_limit" in api_config:
            calls_this_hour = api_config.get("calls_this_hour", 0)
            rate_limit = api_config["rate_limit"]

            if calls_this_hour >= rate_limit:
                # Reset counter at the top of the next hour
                next_hour = current_time.replace(
                    minute=0, second=0, microsecond=0) + timedelta(hours=1)
                return {
                    "allowed": False,
                    "retry_after": (next_hour - current_time).total_seconds()
                }

        return {"allowed": True}

    async def _update_rate_limits(self, api_name: str) -> None:
        """
        Update rate limit counters after successful API call

        Args:
            api_name: API that was called
        """
        if api_name in self.api_keys:
            api_config = self.api_keys[api_name]

            # Update quota usage
            if "quota_used" in api_config:
                api_config["quota_used"] += 1

            # Update hourly rate limit
            if "calls_this_hour" in api_config:
                api_config["calls_this_hour"] += 1

            # Save updated config
            await self._save_api_config()

    async def _save_api_config(self) -> None:
        """Save API configuration to file"""
        try:
            self.api_config_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.api_config_path, 'w') as f:
                json.dump(self.api_keys, f, indent=2)
        except Exception as e:
            print(f"Error saving API config: {e}")

    async def setup_api_key(self, api_name: str, key_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Set up or update API key configuration

        Args:
            api_name: API name
            key_data: API key and configuration data

        Returns:
            Setup result
        """
        # Create command for API key setup
        command = create_command_record(
            id=f"api_setup_{datetime.now().isoformat()}",
            type="api_management",
            priority="high",
            payload={
                "api_name": api_name,
                "key_data": key_data,
                "operation": "setup_key"
            },
            requester="api_adapter",
            description=f"Set up API key for {api_name}"
        )

        await self.command_processor.create_command(command)

        # Update API keys
        self.api_keys[api_name] = key_data
        await self._save_api_config()

        # Create audit record
        audit_record = create_audit_record(
            id=f"audit_api_setup_{datetime.now().isoformat()}",
            operation="account_management",
            timestamp=datetime.now().isoformat(),
            status="success",
            details={
                "api_name": api_name,
                "operation": "key_setup"
            }
        )
        self.audit_log.append(audit_record)

        return {
            "success": True,
            "api_name": api_name,
            "message": f"API key setup completed for {api_name}"
        }

    async def get_api_usage_report(self) -> Dict[str, Any]:
        """
        Generate API usage report

        Returns:
            Usage report
        """
        report = {
            "total_calls": len(self.api_call_history),
            "calls_by_api": {},
            "calls_by_requester": {},
            "recent_calls": self.api_call_history[-10:],  # Last 10 calls
            "rate_limit_status": {},
            "generated_at": datetime.now().isoformat()
        }

        # Aggregate calls by API
        for call in self.api_call_history:
            api_name = call["api_name"]
            requester = call["requester"]

            if api_name not in report["calls_by_api"]:
                report["calls_by_api"][api_name] = 0
            report["calls_by_api"][api_name] += 1

            if requester not in report["calls_by_requester"]:
                report["calls_by_requester"][requester] = 0
            report["calls_by_requester"][requester] += 1

        # Get rate limit status
        for api_name, config in self.api_keys.items():
            report["rate_limit_status"][api_name] = {
                "quota_used": config.get("quota_used", 0),
                "quota_limit": config.get("quota_limit", 0),
                "calls_this_hour": config.get("calls_this_hour", 0),
                "rate_limit": config.get("rate_limit", 0)
            }

        return report

    async def monitor_api_health(self) -> Dict[str, Any]:
        """
        Monitor API health and availability

        Returns:
            Health status report
        """
        health_report = {
            "apis_monitored": len(self.api_keys),
            "healthy_apis": 0,
            "unhealthy_apis": [],
            "rate_limit_warnings": [],
            "overall_health_score": 0.0
        }

        health_scores = []

        for api_name, config in self.api_keys.items():
            try:
                # Check API health (placeholder - actual implementation would test API connectivity)
                api_healthy = await self._check_api_health(api_name)

                if api_healthy:
                    health_report["healthy_apis"] += 1
                    health_scores.append(1.0)
                else:
                    health_report["unhealthy_apis"].append(api_name)
                    health_scores.append(0.0)

                # Check rate limit warnings
                if "quota_used" in config and "quota_limit" in config:
                    usage_ratio = config["quota_used"] / config["quota_limit"]
                    if usage_ratio > 0.8:  # Over 80% usage
                        health_report["rate_limit_warnings"].append({
                            "api": api_name,
                            "usage_ratio": usage_ratio,
                            "quota_used": config["quota_used"],
                            "quota_limit": config["quota_limit"]
                        })

            except Exception as e:
                print(f"Error checking {api_name} health: {e}")
                health_report["unhealthy_apis"].append(api_name)
                health_scores.append(0.0)

        if health_scores:
            health_report["overall_health_score"] = sum(
                health_scores) / len(health_scores)

        return health_report

    async def _check_api_health(self, api_name: str) -> bool:
        """
        Check if an API is healthy and accessible

        Args:
            api_name: API to check

        Returns:
            Health status
        """
        # Placeholder - actual implementation would make a test API call
        return True