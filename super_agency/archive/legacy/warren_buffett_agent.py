#!/usr/bin/env python3
"""
Warren Buffett Agent - Executive Council Member
Focus: Value Investing, Business Strategy, and Long-term Value Creation
"""

import hashlib
import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional


class WarrenBuffettAgent:
    """Warren Buffett Agent - Council Member for Investment and Business Strategy"""

    def __init__(self):
        self.doctrine = self.load_doctrine()
        self.decision_authority = {
            "investment_decisions": "BUFFETT_FINAL",
            "business_acquisitions": "BUFFETT_STRATEGIC",
            "value_assessment": "BUFFETT_VALUE_LEAD",
            "long_term_strategy": "BUFFETT_INVESTMENT_OVERRIDE",
            "capital_allocation": "BUFFETT_APPROVAL",
            "business_ethics": "BUFFETT_ETHICAL_LEAD"
        }
        self.setup_logging()

    def load_doctrine(self) -> Dict:
        """Load Warren Buffett Investment Doctrine"""
        doctrine = {
            "mission": "create long-term shareholder value through prudent investment and ethical business practices",
            "authority_structure": "Lead investment decisions with value-focused oversight",
            "value_hierarchy": ["Outstanding", "Excellent", "Good", "Fair", "Poor"],
            "decision_categories": ["Investment", "Strategic", "Operational"],
            "ethical_framework": "integrity, transparency, and long-term value creation over short-term gains",
            "oversight_requirement": "MANDATORY for major investment decisions",
            "approval_threshold": "BUFFETT_FINAL for significant capital allocations"
        }
        return doctrine

    def setup_logging(self):
        """Setup Warren Buffett Agent logging"""
        os.makedirs("buffett_investments", exist_ok=True)

        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - WARREN BUFFETT AGENT - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('buffett_investments/buffett_investment_log.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger("WarrenBuffettAgent")

    def evaluate_investment_value(self, investment: Dict) -> Dict:
        """Evaluate investment value potential"""

        value_score = 100
        concerns = []
        recommendations = []

        # Check long-term potential
        if "long_term" not in str(investment).lower():
            value_score -= 20
            concerns.append("Investment lacks long-term value proposition")

        # Check competitive advantage
        if "moat" not in str(investment).lower() and "advantage" not in str(investment).lower():
            value_score -= 15
            concerns.append("No clear competitive advantage identified")

        # Check management quality
        if "management" not in str(investment).lower():
            value_score -= 10
            recommendations.append("Assess management quality and integrity")

        return {
            "value_score": max(0, value_score),
            "concerns": concerns,
            "recommendations": recommendations,
            "approval_required": value_score >= 85
        }

    def provide_investment_guidance(self, topic: str) -> str:
        """Provide investment guidance on business topics"""
        guidance_templates = {
            "value": "Buy wonderful businesses at fair prices, not fair businesses at wonderful prices.",
            "patience": "The stock market is a device for transferring money from the impatient to the patient.",
            "risk": "Risk comes from not knowing what you're doing.",
            "ethics": "It takes 20 years to build a reputation and five minutes to ruin it."
        }

        return guidance_templates.get(topic.lower(), "Invest in businesses you understand and believe in for the long term.")

    def run_investment_cycle(self):
        """Run investment analysis and value assessment cycle"""
        self.logger.info("Starting Warren Buffett investment cycle")

        # Simulate real work: analyze investment opportunities and assess value
        investments_to_analyze = [
            {"company": "Apple Inc", "sector": "Technology", "description": "Consumer electronics and software"},
            {"company": "Berkshire Hathaway", "sector": "Conglomerate", "description": "Diversified holdings company"},
            {"company": "Coca-Cola", "sector": "Beverages", "description": "Global beverage company"}
        ]

        for investment in investments_to_analyze:
            value_assessment = self.evaluate_investment_value(investment)
            guidance = self.provide_investment_guidance("value")

            # Log actual work being done
            self.logger.info(f"Assessed {investment['company']}: Value Score {value_assessment['value_score']}")
            if value_assessment['concerns']:
                self.logger.warning(f"Value concerns for {investment['company']}: {value_assessment['concerns']}")

            # Save assessment results
            self.save_value_assessment(investment, value_assessment, guidance)

    def save_value_assessment(self, investment: Dict, assessment: Dict, guidance: str):
        """Save value assessment results to file"""
        results_dir = Path("buffett_investments/assessments")
        results_dir.mkdir(exist_ok=True)

        result_file = results_dir / f"{investment['company'].lower().replace(' ', '_')}_assessment.json"
        result_data = {
            "timestamp": datetime.now().isoformat(),
            "investment": investment,
            "value_assessment": assessment,
            "investment_guidance": guidance,
            "agent": "Warren Buffett Agent"
        }

        with open(result_file, 'w') as f:
            json.dump(result_data, f, indent=2)

        self.logger.info(f"Saved value assessment to {result_file}")

    def execute_work_cycle(self):
        """Execute a complete work cycle for the agent"""
        self.logger.info("📈 WARREN BUFFETT AGENT - Executing Investment Work Cycle")
        self.run_investment_cycle()
        self.logger.info("✅ WARREN BUFFETT AGENT - Work Cycle Completed")
