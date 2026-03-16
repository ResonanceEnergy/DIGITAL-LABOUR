# REPO DEPOT FLYWHEEL - Quality Gates

import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from enum import Enum
import subprocess
import sys
import ast
import re
from pathlib import Path

logger = logging.getLogger(__name__)


class QualityGate(Enum):
    SYNTAX_CHECK = "syntax_check"
    LINTING = "linting"
    TYPE_CHECKING = "type_checking"
    UNIT_TESTS = "unit_tests"
    INTEGRATION_TESTS = "integration_tests"
    SECURITY_SCAN = "security_scan"
    PERFORMANCE_TEST = "performance_test"
    CODE_COVERAGE = "code_coverage"


class QualityResult(Enum):
    PASS = "pass"
    FAIL = "fail"
    WARNING = "warning"
    ERROR = "error"


@dataclass
class QualityCheck:
    gate: QualityGate
    name: str
    description: str
    required: bool = True
    timeout: int = 60  # seconds


@dataclass
class QualityReport:
    check_id: str
    gate: QualityGate
    result: QualityResult
    score: float  # 0.0 to 1.0
    details: Dict[str, Any]
    execution_time: float
    error_message: Optional[str] = None
    recommendations: List[str] = None

    def __post_init__(self):
        if self.recommendations is None:
            self.recommendations = []


@dataclass
class CodeSubmission:
    submission_id: str
    code: str
    language: str
    file_path: Optional[str] = None
    metadata: Dict[str, Any] = None
    submitted_at: datetime = None

    def __post_init__(self):
        if self.submitted_at is None:
            self.submitted_at = datetime.now()
        if self.metadata is None:
            self.metadata = {}


class QualityGateSystem:
    """
    Comprehensive quality assurance system for REPO DEPOT Flywheel.
    Performs automated testing, linting, and validation of generated code.
    """

    def __init__(self):
        self.quality_checks: Dict[QualityGate, QualityCheck] = {}
        self.reports: Dict[str, List[QualityReport]] = {}
        self.passing_threshold: float = 0.8  # 80% quality score required

        # Initialize default quality checks
        self._initialize_quality_checks()

    def _initialize_quality_checks(self):
        """Initialize default quality checks"""
        checks = [
            QualityCheck(
                gate=QualityGate.SYNTAX_CHECK,
                name="Syntax Validation",
                description="Check for syntax errors in generated code",
                required=True,
                timeout=10,
            ),
            QualityCheck(
                gate=QualityGate.LINTING,
                name="Code Linting",
                description="Check code style and potential issues",
                required=True,
                timeout=30,
            ),
            QualityCheck(
                gate=QualityGate.TYPE_CHECKING,
                name="Type Checking",
                description="Validate type annotations and type safety",
                required=False,
                timeout=60,
            ),
            QualityCheck(
                gate=QualityGate.UNIT_TESTS,
                name="Unit Testing",
                description="Run unit tests for generated code",
                required=True,
                timeout=120,
            ),
            QualityCheck(
                gate=QualityGate.SECURITY_SCAN,
                name="Security Analysis",
                description="Scan for security vulnerabilities",
                required=True,
                timeout=45,
            ),
            QualityCheck(
                gate=QualityGate.CODE_COVERAGE,
                name="Code Coverage",
                description="Measure test coverage of generated code",
                required=False,
                timeout=90,
            ),
        ]

        for check in checks:
            self.quality_checks[check.gate] = check

    async def validate_submission(self, submission: CodeSubmission) -> Dict[str, Any]:
        """
        Run all quality gates on a code submission.
        Returns comprehensive validation report.
        """
        logger.info(f"🔍 Starting quality validation for: {submission.submission_id}")

        reports = []
        total_score = 0.0
        required_checks_passed = 0
        required_checks_total = 0

        # Run all quality checks
        for gate, check in self.quality_checks.items():
            try:
                report = await self._run_quality_check(submission, check)
                reports.append(report)

                if check.required:
                    required_checks_total += 1
                    if report.result in [QualityResult.PASS, QualityResult.WARNING]:
                        required_checks_passed += 1

                total_score += report.score

            except Exception as e:
                logger.error(f"Quality check failed for {gate.value}: {e}")
                # Create error report
                error_report = QualityReport(
                    check_id=f"{submission.submission_id}_{gate.value}",
                    gate=gate,
                    result=QualityResult.ERROR,
                    score=0.0,
                    details={"error": str(e)},
                    execution_time=0.0,
                    error_message=str(e),
                )
                reports.append(error_report)

        # Calculate overall score
        overall_score = total_score / len(self.quality_checks) if self.quality_checks else 0.0

        # Determine final result
        if required_checks_passed < required_checks_total:
            final_result = "fail"
        elif overall_score >= self.passing_threshold:
            final_result = "pass"
        else:
            final_result = "warning"

        # Store reports
        self.reports[submission.submission_id] = reports

        result = {
            "submission_id": submission.submission_id,
            "final_result": final_result,
            "overall_score": overall_score,
            "required_checks_passed": required_checks_passed,
            "required_checks_total": required_checks_total,
            "reports": [self._report_to_dict(r) for r in reports],
            "validated_at": datetime.now().isoformat(),
        }

        logger.info(
            f"✅ Quality validation completed: {final_result} (score: {overall_score:.2f})"
        )
        return result

    async def _run_quality_check(
        self, submission: CodeSubmission, check: QualityCheck
    ) -> QualityReport:
        """Run a specific quality check"""
        start_time = asyncio.get_event_loop().time()

        try:
            if check.gate == QualityGate.SYNTAX_CHECK:
                result = await self._check_syntax(submission)
            elif check.gate == QualityGate.LINTING:
                result = await self._check_linting(submission)
            elif check.gate == QualityGate.TYPE_CHECKING:
                result = await self._check_types(submission)
            elif check.gate == QualityGate.UNIT_TESTS:
                result = await self._run_unit_tests(submission)
            elif check.gate == QualityGate.SECURITY_SCAN:
                result = await self._security_scan(submission)
            elif check.gate == QualityGate.CODE_COVERAGE:
                result = await self._check_coverage(submission)
            else:
                result = (
                    QualityResult.ERROR,
                    0.0,
                    {"error": "Unknown check type"},
                    ["Implement check"],
                )

            execution_time = asyncio.get_event_loop().time() - start_time

            return QualityReport(
                check_id=f"{submission.submission_id}_{check.gate.value}",
                gate=check.gate,
                result=result[0],
                score=result[1],
                details=result[2],
                execution_time=execution_time,
                recommendations=result[3] if len(result) > 3 else [],
            )

        except asyncio.TimeoutError:
            execution_time = asyncio.get_event_loop().time() - start_time
            return QualityReport(
                check_id=f"{submission.submission_id}_{check.gate.value}",
                gate=check.gate,
                result=QualityResult.ERROR,
                score=0.0,
                details={"timeout": True},
                execution_time=execution_time,
                error_message=f"Check timed out after {check.timeout} seconds",
            )

    async def _check_syntax(self, submission: CodeSubmission) -> tuple:
        """Check code syntax"""
        try:
            if submission.language.lower() == "python":
                ast.parse(submission.code)
                return QualityResult.PASS, 1.0, {"syntax_valid": True}, []
            else:
                return (
                    QualityResult.WARNING,
                    0.5,
                    {"syntax_check": "not_implemented"},
                    ["Implement syntax check for language"],
                )
        except SyntaxError as e:
            return (
                QualityResult.FAIL,
                0.0,
                {"syntax_error": str(e)},
                ["Fix syntax error", "Validate code before submission"],
            )

    async def _check_linting(self, submission: CodeSubmission) -> tuple:
        """Run linting checks"""
        issues = []

        if submission.language.lower() == "python":
            # Check for common issues
            lines = submission.code.split("\n")

            for i, line in enumerate(lines, 1):
                # Check line length
                if len(line) > 88:  # PEP8 limit
                    issues.append(f"Line {i}: Too long ({len(line)} chars)")

                # Check for unused imports (simplified)
                if line.strip().startswith("import ") or line.strip().startswith("from "):
                    # This is a very basic check
                    pass

                # Check for print statements in production code
                if "print(" in line and not line.strip().startswith("#"):
                    issues.append(f"Line {i}: Print statement in production code")

            if issues:
                score = max(0.0, 1.0 - (len(issues) * 0.1))
                return (
                    QualityResult.WARNING,
                    score,
                    {"lint_issues": issues},
                    ["Fix linting issues", "Follow coding standards"],
                )
            else:
                return QualityResult.PASS, 1.0, {"lint_clean": True}, []

        return (
            QualityResult.WARNING,
            0.5,
            {"linting": "not_implemented"},
            ["Implement linting for language"],
        )

    async def _check_types(self, submission: CodeSubmission) -> tuple:
        """Run type checking"""
        if submission.language.lower() == "python":
            # Check for type annotations
            tree = ast.parse(submission.code)
            has_type_hints = False

            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    if node.returns:
                        has_type_hints = True
                        break
                    if any(arg.annotation for arg in node.args.args):
                        has_type_hints = True
                        break

            if has_type_hints:
                return QualityResult.PASS, 1.0, {"type_hints": True}, []
            else:
                return (
                    QualityResult.WARNING,
                    0.7,
                    {"type_hints": False},
                    ["Add type annotations", "Consider using mypy"],
                )

        return (
            QualityResult.WARNING,
            0.5,
            {"type_checking": "not_implemented"},
            ["Implement type checking"],
        )

    async def _run_unit_tests(self, submission: CodeSubmission) -> tuple:
        """Run unit tests"""
        # This would normally run actual tests
        # For now, simulate basic checks
        if "test" in submission.code.lower() or "assert" in submission.code.lower():
            return QualityResult.PASS, 0.9, {"tests_present": True}, []
        else:
            return (
                QualityResult.WARNING,
                0.3,
                {"tests_missing": True},
                ["Add unit tests", "Ensure test coverage"],
            )

    async def _security_scan(self, submission: CodeSubmission) -> tuple:
        """Run security analysis"""
        vulnerabilities = []

        # Check for common security issues
        if "eval(" in submission.code:
            vulnerabilities.append("Use of eval() - security risk")

        if "exec(" in submission.code:
            vulnerabilities.append("Use of exec() - security risk")

        if "subprocess" in submission.code and "shell=True" in submission.code:
            vulnerabilities.append("Shell execution with shell=True")

        if "input(" in submission.code:
            vulnerabilities.append("Use of input() - potential injection")

        if vulnerabilities:
            score = max(0.0, 1.0 - (len(vulnerabilities) * 0.3))
            return (
                QualityResult.FAIL,
                score,
                {"vulnerabilities": vulnerabilities},
                ["Fix security issues", "Use secure coding practices"],
            )
        else:
            return QualityResult.PASS, 1.0, {"security_clean": True}, []

    async def _check_coverage(self, submission: CodeSubmission) -> tuple:
        """Check code coverage"""
        # Simplified coverage estimation
        code_lines = len(
            [
                line
                for line in submission.code.split("\n")
                if line.strip() and not line.strip().startswith("#")
            ]
        )
        test_lines = len(
            [
                line
                for line in submission.code.split("\n")
                if "test" in line.lower() or "assert" in line.lower()
            ]
        )

        if code_lines == 0:
            return QualityResult.WARNING, 0.0, {"coverage": 0}, ["Add testable code"]

        coverage = min(1.0, test_lines / max(1, code_lines / 10))  # Rough estimate
        return QualityResult.PASS, coverage, {"estimated_coverage": coverage}, []

    def _report_to_dict(self, report: QualityReport) -> Dict[str, Any]:
        """Convert quality report to dictionary"""
        return {
            "check_id": report.check_id,
            "gate": report.gate.value,
            "result": report.result.value,
            "score": report.score,
            "details": report.details,
            "execution_time": report.execution_time,
            "error_message": report.error_message,
            "recommendations": report.recommendations,
        }

    def get_quality_status(self) -> Dict[str, Any]:
        """Get overall quality system status"""
        total_reports = sum(len(reports) for reports in self.reports.values())
        passed_checks = 0
        failed_checks = 0

        for submission_reports in self.reports.values():
            for report in submission_reports:
                if report.result == QualityResult.PASS:
                    passed_checks += 1
                elif report.result in [QualityResult.FAIL, QualityResult.ERROR]:
                    failed_checks += 1

        return {
            "total_submissions": len(self.reports),
            "total_reports": total_reports,
            "passed_checks": passed_checks,
            "failed_checks": failed_checks,
            "quality_gates": len(self.quality_checks),
            "passing_threshold": self.passing_threshold,
        }

    def get_status(self) -> Dict[str, Any]:
        """Alias for get_quality_status() for backward compatibility"""
        return self.get_quality_status()


# Global quality gate system
quality_gates = QualityGateSystem()
