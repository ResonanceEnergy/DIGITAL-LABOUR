#!/usr/bin/env python3
"""
Bit Rage Systems Oversight Framework
Comprehensive monitoring and audit system for APIs, accounts, and intelligence operations
"""

import json
import os
import time
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import hashlib
import requests

class OversightFramework:
    """Comprehensive oversight system for Bit Rage Systems operations"""

    def __init__(self, config_path: str = "oversight_config.json"):
        self.config_path = config_path
        self.config = self.load_config()
        self.setup_logging()
        self.metrics = {
            "api_calls": 0,
            "errors": 0,
            "security_events": 0,
            "account_changes": 0
        }
        self.alerts = []

    def load_config(self) -> Dict:
        """Load oversight configuration"""
        default_config = {
            "oversight": {
                "enabled": True,
                "log_level": "INFO",
                "alert_thresholds": {
                    "api_errors_per_hour": 10,
                    "security_events_per_day": 5,
                    "account_changes_per_day": 3
                },
                "monitoring": {
                    "api_response_times": True,
                    "quota_usage": True,
                    "access_patterns": True,
                    "data_quality": True
                },
                "audit": {
                    "retain_logs_days": 90,
                    "encrypt_sensitive_data": True,
                    "compliance_checks": True
                },
                "executive_ethics": {
                    "enabled": True,
                    "ethical_principles": [
                        "transparency",
                        "fairness",
                        "accountability",
                        "privacy",
                        "beneficence"
                    ],
                    "executive_decision_tracking": True,
                    "ethical_review_required": ["HIGH", "CRITICAL"],
                    "alert_on_ethical_violations": True
                }
            },
            "apis": {
                "youtube": {
                    "quota_limit": 10000,
                    "rate_limit_per_second": 1,
                    "alert_on_quota_percent": 80
                },
                "microsoft_graph": {
                    "rate_limit_per_second": 10,
                    "alert_on_errors": True
                }
            },
            "accounts": {
                "audit_creations": True,
                "audit_permissions": True,
                "alert_suspicious_activity": True,
                "require_approval_for_admin": True
            }
        }

        if os.path.exists(self.config_path):
            with open(self.config_path, 'r') as f:
                user_config = json.load(f)
                # Merge with defaults
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
        """Setup comprehensive logging system"""
        log_level = getattr(logging, self.config["oversight"]["log_level"])

        # Create logs directory if it doesn't exist
        os.makedirs("oversight_logs", exist_ok=True)

        logging.basicConfig(
            level=log_level,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('oversight_logs/oversight.log'),
                logging.FileHandler('oversight_logs/security.log'),
                logging.FileHandler('oversight_logs/api_audit.log'),
                logging.StreamHandler()
            ]
        )

        self.logger = logging.getLogger("SuperAgency.Oversight")
        self.security_logger = logging.getLogger("SuperAgency.Security")
        self.api_logger = logging.getLogger("SuperAgency.API")

    def audit_api_call(self, api_name: str, endpoint: str,
                        response_time: float, success: bool,
                       error_details: Optional[str]=None):
        """Audit API call with oversight"""
        self.metrics["api_calls"] += 1

        audit_entry = {
            "timestamp": datetime.now().isoformat(),
            "api_name": api_name,
            "endpoint": endpoint,
            "response_time": response_time,
            "success": success,
            "error_details": error_details
        }

        self.api_logger.info(f"API Call: {json.dumps(audit_entry)}")

        if not success:
            self.metrics["errors"] += 1
            self.check_error_thresholds()

        # Check response time thresholds
        if response_time > 5.0:  # 5 seconds threshold
            self.alerts.append({
                "type": "performance",
                "message": f"Slow API response: {api_name} took {response_time:.2f}s",
                "timestamp": datetime.now().isoformat()
            })

    def audit_account_change(self, account_type: str, action: str,
                           account_id: str, changed_by: str, details: Dict):
        """Audit account creation/modification"""
        self.metrics["account_changes"] += 1

        audit_entry = {
            "timestamp": datetime.now().isoformat(),
            "account_type": account_type,
            "action": action,
            # Hash for privacy
            "account_id": hashlib.sha256(account_id.encode()).hexdigest()[:16],
            "changed_by": changed_by,
            "details": details
        }

        self.security_logger.info(f"Account Change: {json.dumps(audit_entry)}")

        # Check for suspicious activity
        if self.is_suspicious_account_change(action, details):
            self.metrics["security_events"] += 1
            self.alerts.append({
                "type": "security",
                "message": f"Suspicious account change: {action} on {account_type}",
                "timestamp": datetime.now().isoformat()
            })

    def audit_intelligence_operation(
            self, operation_type: str, source: str, data_quality_score: float,
            ethical_compliance: bool):
        """Audit intelligence gathering operations"""
        audit_entry = {
            "timestamp": datetime.now().isoformat(),
            "operation_type": operation_type,
            "source": source,
            "data_quality_score": data_quality_score,
            "ethical_compliance": ethical_compliance
        }

        self.logger.info(f"Intelligence Operation: {json.dumps(audit_entry)}")

        # Check data quality
        if data_quality_score < 0.7:
            self.alerts.append({
                "type": "quality",
                "message": f"Low data quality score: {data_quality_score} from {source}",
                "timestamp": datetime.now().isoformat()
            })

        # Check ethical compliance
        if not ethical_compliance:
            self.alerts.append({
                "type": "ethics",
                "message": f"Ethical compliance violation in {operation_type} from {source}",
                "timestamp": datetime.now().isoformat()
            })

    def check_error_thresholds(self):
        """Check if error thresholds are exceeded"""
        # This would be called periodically to check accumulated metrics
        if self.metrics["errors"] >self.config["oversight"] [
            "alert_thresholds"] ["api_errors_per_hour"]:
            self.alerts.append({
                "type": "threshold",
                "message": f"API error threshold exceeded: {self.metrics['errors']} errors/hour",
                "timestamp": datetime.now().isoformat()
            })

    def is_suspicious_account_change(self, action: str, details: Dict) -> bool:
        """Determine if account change is suspicious"""
        suspicious_patterns = [
            "admin" in action.lower() and "emergency" not in str(details).lower(),
            "delete" in action.lower(),
            "password" in action.lower() and "reset" in action.lower(),
            len(str(details)) > 1000  # Unusually large change details
        ]
        return any(suspicious_patterns)

    def generate_oversight_report(self) -> Dict:
        """Generate comprehensive oversight report"""
        report = {
            "timestamp": datetime.now().isoformat(),
            "period": "last_24_hours",
            "metrics": self.metrics.copy(),
            "alerts": self.alerts.copy(),
            "system_health": self.assess_system_health(),
            "recommendations": self.generate_recommendations()
        }

        # Save report
        report_path = f"oversight_logs/report_{
            datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2)

        return report

    def assess_system_health(self) -> Dict:
        """Assess overall system health"""
        health_score = 100

        # Deduct points for issues
        if self.metrics["errors"] > 0:
            health_score -= min(self.metrics["errors"] * 5, 30)

        if self.metrics["security_events"] > 0:
            health_score -= min(self.metrics["security_events"] * 10, 40)

        if len(self.alerts) > 0:
            health_score -= min(len(self.alerts) * 5, 20)

        return {
            "score": max(0, health_score),
            "status": "healthy" if health_score >= 80 else "warning" if health_score >= 60 else "critical",
            "issues": len(self.alerts)
        }

    def generate_recommendations(self) -> List[str]:
        """Generate oversight recommendations"""
        recommendations = []

        if self.metrics["errors"] > 5:
            recommendations.append(
                "Review API error patterns and implement retry logic")

        if self.metrics["security_events"] > 0:
            recommendations.append(
                "Conduct security audit and review access controls")

        if len(self.alerts) > 3:
            recommendations.append(
                "Address outstanding alerts and improve monitoring thresholds")

        if not recommendations:
            recommendations.append("System operating within normal parameters")

        return recommendations

    def audit_executive_decision(self, executive: str, decision_type: str,
                                ethical_assessment: Dict, impact_level: str):
        """Audit executive decisions for ethical compliance"""
        if not self.config["oversight"]["executive_ethics"]["enabled"]:
            return

        ethical_score = self._calculate_ethical_score(ethical_assessment)

        # Log executive decision
        self.logger.info(
            f"Executive Decision Audit: {executive} - {decision_type} - Score: {ethical_score}")

        # Check if ethical review is required
        if impact_level in self.config["oversight"] ["executive_ethics"] [
            "ethical_review_required"]:
            if ethical_score < 0.8:  # Below 80% ethical compliance
                self.alerts.append({
                    "type": "executive_ethics",
                    "severity": "HIGH",
                    "message": f"Executive decision requires ethical review: {executive} - {decision_type}",
                    "ethical_score": ethical_score,
                    "timestamp": datetime.now().isoformat()
                })

        # Store executive decision record
        self._store_executive_decision(
            executive, decision_type, ethical_assessment, ethical_score)

    def _calculate_ethical_score(self, ethical_assessment: Dict) -> float:
        """Calculate ethical compliance score based on principles"""
        principles = self.config["oversight"] ["executive_ethics"] [
            "ethical_principles"]
        total_score = 0
        max_score = len(principles)

        for principle in principles:
            if principle in ethical_assessment:
                score = ethical_assessment[principle]
                if isinstance(score, (int, float)):
                    total_score += min(max(score, 0), 1)  # Clamp between 0-1
                elif isinstance(score, bool):
                    total_score += 1 if score else 0

        return total_score / max_score if max_score > 0 else 0

    def _store_executive_decision(
            self, executive: str, decision_type: str, ethical_assessment: Dict,
            ethical_score: float):
        """Store executive decision record for audit trail"""
        decision_record = {
            "executive": executive,
            "decision_type": decision_type,
            "ethical_assessment": ethical_assessment,
            "ethical_score": ethical_score,
            "timestamp": datetime.now().isoformat()
        }

        # Store in oversight logs
        log_file = f"oversight_logs/executive_decisions_{
            datetime.now().strftime('%Y%m%d')}.jsonl"
        with open(log_file, 'a') as f:
            f.write(json.dumps(decision_record) + '\n')

    def get_executive_ethics_report(self, days: int = 7) -> Dict:
        """Generate executive ethics compliance report"""
        report = {
            "period_days": days,
            "total_decisions": 0,
            "ethical_compliance_rate": 0,
            "decisions_by_executive": {},
            "ethical_violations": []
        }

        # Read executive decision logs
        start_date = datetime.now() - timedelta(days=days)
        total_score = 0

        for i in range(days):
            date = (start_date + timedelta(days=i)).strftime('%Y%m%d')
            log_file = f"oversight_logs/executive_decisions_{date}.jsonl"

            if os.path.exists(log_file):
                with open(log_file, 'r') as f:
                    for line in f:
                        try:
                            decision = json.loads(line.strip())
                            report["total_decisions"] += 1
                            total_score += decision["ethical_score"]

                            # Track by executive
                            exec_name = decision["executive"]
                            if exec_name not in report["decisions_by_executive"]:
                                report["decisions_by_executive"][exec_name] = []
                            report["decisions_by_executive"][exec_name].append(
                                decision)

                            # Track violations
                            if decision["ethical_score"] < 0.8:
                                report["ethical_violations"].append(decision)

                        except json.JSONDecodeError:
                            continue

        if report["total_decisions"] > 0:
            report["ethical_compliance_rate"] = total_score / \
                report["total_decisions"]

        return report

    def save_config(self):
        """Save current configuration"""
        with open(self.config_path, 'w') as f:
            json.dump(self.config, f, indent=2)

# Global oversight instance
oversight = OversightFramework()

def audit_api_call(api_name: str, endpoint: str, response_time: float,
                  success: bool, error_details: Optional[str] = None):
    """Convenience function for API auditing"""
    oversight.audit_api_call(
        api_name, endpoint, response_time, success, error_details)

def audit_account_change(account_type: str, action: str, account_id: str,
                        changed_by: str, details: Dict):
    """Convenience function for account auditing"""
    oversight.audit_account_change(
        account_type, action, account_id, changed_by, details)

# Convenience functions for external use
oversight = OversightFramework()

def audit_api_call(api_name: str, endpoint: str, response_time: float,
                  success: bool, error_message: str = None):
    """Convenience function for API auditing"""
    oversight.audit_api_call(
        api_name, endpoint, response_time, success, error_message)

def audit_account_change(account_type: str, action: str, account_id: str,
                        permission_level: str, details: Dict = None):
    """Convenience function for account auditing"""
    oversight.audit_account_change(
        account_type, action, account_id, permission_level, details)

def audit_intelligence_operation(
        operation_type: str, source: str, data_quality_score: float,
        ethical_compliance: bool):
    """Convenience function for intelligence auditing"""
    oversight.audit_intelligence_operation(
        operation_type, source, data_quality_score, ethical_compliance)

def audit_executive_decision(executive: str, decision_type: str,
                           ethical_assessment: Dict, impact_level: str):
    """Convenience function for executive decision auditing"""
    oversight.audit_executive_decision(
        executive, decision_type, ethical_assessment, impact_level)

def get_executive_ethics_report(days: int = 7) -> Dict:
    """Convenience function for executive ethics reporting"""
    return oversight.get_executive_ethics_report(days)
    # Test the oversight framework
    print("🛡️ Bit Rage Systems Oversight Framework Test")
    print("=" * 50)

    # Test API auditing
    audit_api_call("youtube", "/channels", 1.2, True)
    audit_api_call("youtube", "/videos", 0.8, False, "Rate limit exceeded")

    # Test account auditing
    audit_account_change(
        "microsoft", "create", "council52@domain.com", "admin",
        {"role": "intelligence"})

    # Test intelligence auditing
    audit_intelligence_operation(
        "youtube_monitoring", "Tom Bilyeu", 0.85, True)

    # Generate report
    report = oversight.generate_oversight_report()
    print(
        f"✅ Oversight report generated: {len(report['alerts'])} alerts, health score: {report['system_health']['score']}")

    print("\n📊 Oversight Framework Ready!")
    print("   • API call auditing: Active")
    print("   • Account change tracking: Active")
    print("   • Intelligence operation monitoring: Active")
    print("   • Alert system: Configured")
    print("   • Report generation: Functional")