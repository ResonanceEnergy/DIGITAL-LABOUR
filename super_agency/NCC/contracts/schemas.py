"""
NCC Schema Validation Classes
Python classes for validating NCC data structures
"""

import json
from typing import Dict, List, Any, Optional
from datetime import datetime
from pathlib import Path

class ValidationError(Exception):
    """Schema validation error"""
    pass

class BaseSchema:
    """Base schema class with common validation methods"""

    @classmethod
    def validate(cls, data: Dict[str, Any]) -> bool:
        """Validate data against schema"""
        try:
            cls._validate_required_fields(data)
            cls._validate_field_types(data)
            cls._validate_field_values(data)
            return True
        except ValidationError:
            return False

    @classmethod
    def _validate_required_fields(cls, data: Dict[str, Any]) -> None:
        """Validate required fields are present"""
        required_fields = getattr(cls, 'REQUIRED_FIELDS', [])
        for field in required_fields:
            if field not in data:
                raise ValidationError(f"Missing required field: {field}")

    @classmethod
    def _validate_field_types(cls, data: Dict[str, Any]) -> None:
        """Validate field types"""
        field_types = getattr(cls, 'FIELD_TYPES', {})
        for field, expected_type in field_types.items():
            if field in data:
                value = data[field]
                if not cls._check_type(value, expected_type):
                    raise ValidationError(
                        f"Field {field} has wrong type. Expected {expected_type}, got {type(value)}")

    @classmethod
    def _validate_field_values(cls, data: Dict[str, Any]) -> None:
        """Validate field values (enums, ranges, etc.)"""
        pass

    @classmethod
    def _check_type(cls, value: Any, expected_type: str) -> bool:
        """Check if value matches expected type"""
        type_map = {
            'string': str,
            'number': (int, float),
            'integer': int,
            'boolean': bool,
            'object': dict,
            'array': list
        }

        if expected_type in type_map:
            return isinstance(value, type_map[expected_type])

        return True  # Unknown types pass validation

class CommandRecord(BaseSchema):
    """Command record schema"""

    REQUIRED_FIELDS = ['id', 'type', 'priority', 'payload', 'requester']
    FIELD_TYPES = {
        'id': 'string',
        'type': 'string',
        'priority': 'string',
        'payload': 'object',
        'requester': 'string',
        'description': 'string',
        'status': 'string',
        'created_at': 'string',
        'resource_requirements': 'object'
    }

    VALID_PRIORITIES = ['critical', 'high', 'medium', 'low']
    VALID_TYPES = ['intelligence_gathering', 'resource_allocation',
                   'api_management', 'account_management',
                    'system_maintenance', 'council_coordination']
    VALID_STATUSES = ['pending', 'executing',
        'completed', 'failed', 'cancelled']

    @classmethod
    def _validate_field_values(cls, data: Dict[str, Any]) -> None:
        """Validate command-specific field values"""
        if 'priority' in data and data['priority'] not in cls.VALID_PRIORITIES:
            raise ValidationError(f"Invalid priority: {data['priority']}")

        if 'type' in data and data['type'] not in cls.VALID_TYPES:
            raise ValidationError(f"Invalid command type: {data['type']}")

        if 'status' in data and data['status'] not in cls.VALID_STATUSES:
            raise ValidationError(f"Invalid status: {data['status']}")

class IntelligenceRecord(BaseSchema):
    """Intelligence record schema"""

    REQUIRED_FIELDS = ['id', 'source', 'type', 'content', 'confidence']
    FIELD_TYPES = {
        'id': 'string',
        'source': 'string',
        'type': 'string',
        'content': 'object',
        'confidence': 'number',
        'metadata': 'object',
        'correlations': 'array',
        'insights': 'array',
        'processing_status': 'string',
        'retention_policy': 'object'
    }

    VALID_SOURCES = ['youtube_council', 'microsoft_graph', 'azure_management',
                     'ncl_second_brain', 'system_monitoring', 'external_api']
    VALID_TYPES = [
        'video_transcript', 'email_content', 'system_log', 'api_response',
        'user_behavior', 'market_data', 'threat_intelligence']
    VALID_PROCESSING_STATUSES = [
        'raw', 'processed', 'analyzed', 'synthesized', 'archived']

    @classmethod
    def _validate_field_values(cls, data: Dict[str, Any]) -> None:
        """Validate intelligence-specific field values"""
        if 'source' in data and data['source'] not in cls.VALID_SOURCES:
            raise ValidationError(f"Invalid source: {data['source']}")

        if 'type' in data and data['type'] not in cls.VALID_TYPES:
            raise ValidationError(f"Invalid intelligence type: {data['type']}")

        if 'confidence' in data:
            confidence = data['confidence']
            if not (0 <= confidence <= 1):
                raise ValidationError(
                    f"Confidence must be between 0 and 1, got {confidence}")

        if 'processing_status' in data and data['processing_status'] not in cls.VALID_PROCESSING_STATUSES:
            raise ValidationError(
                f"Invalid processing status: {data['processing_status']}")

class ResourceRecord(BaseSchema):
    """Resource record schema"""

    REQUIRED_FIELDS = ['id', 'type', 'capacity', 'current_usage']
    FIELD_TYPES = {
        'id': 'string',
        'type': 'string',
        'capacity': 'number',
        'current_usage': 'number',
        'allocation_history': 'array',
        'optimization_suggestions': 'array',
        'health_status': 'string',
        'last_updated': 'string'
    }

    VALID_TYPES = ['cpu', 'memory', 'disk',
        'network', 'api_quota', 'compute_instance']
    VALID_HEALTH_STATUSES = ['healthy', 'warning', 'critical', 'unknown']

    @classmethod
    def _validate_field_values(cls, data: Dict[str, Any]) -> None:
        """Validate resource-specific field values"""
        if 'type' in data and data['type'] not in cls.VALID_TYPES:
            raise ValidationError(f"Invalid resource type: {data['type']}")

        if 'health_status' in data and data['health_status'] not in cls.VALID_HEALTH_STATUSES:
            raise ValidationError(
                f"Invalid health status: {data['health_status']}")

        if 'capacity' in data and data['capacity'] < 0:
            raise ValidationError(
                f"Capacity must be non-negative, got {data['capacity']}")

        if 'current_usage' in data and data['current_usage'] < 0:
            raise ValidationError(
                f"Current usage must be non-negative, got {data['current_usage']}")

class AuditRecord(BaseSchema):
    """Audit record schema"""

    REQUIRED_FIELDS = ['id', 'operation', 'timestamp', 'status']
    FIELD_TYPES = {
        'id': 'string',
        'operation': 'string',
        'timestamp': 'string',
        'status': 'string',
        'details': 'object',
        'user_context': 'object',
        'resource_impact': 'object',
        'compliance_flags': 'array',
        'oversight_review': 'object'
    }

    VALID_OPERATIONS = [
        'api_call', 'account_creation', 'resource_allocation',
        'intelligence_processing', 'command_execution', 'system_access']
    VALID_STATUSES = ['success', 'failure', 'warning', 'info']

    @classmethod
    def _validate_field_values(cls, data: Dict[str, Any]) -> None:
        """Validate audit-specific field values"""
        if 'operation' in data and data['operation'] not in cls.VALID_OPERATIONS:
            raise ValidationError(f"Invalid operation: {data['operation']}")

        if 'status' in data and data['status'] not in cls.VALID_STATUSES:
            raise ValidationError(f"Invalid status: {data['status']}")

# Convenience functions for validation
def validate_command(data: Dict[str, Any]) -> bool:
    """Validate command data"""
    return CommandRecord.validate(data)

def validate_intelligence(data: Dict[str, Any]) -> bool:
    """Validate intelligence data"""
    return IntelligenceRecord.validate(data)

def validate_resource(data: Dict[str, Any]) -> bool:
    """Validate resource data"""
    return ResourceRecord.validate(data)

def validate_audit(data: Dict[str, Any]) -> bool:
    """Validate audit data"""
    return AuditRecord.validate(data)

# Factory functions for creating validated records
def create_command_record(**kwargs) -> Dict[str, Any]:
    """Create a validated command record"""
    record = {
        'id': kwargs.get('id', f"cmd_{datetime.now().isoformat()}"),
        'type': kwargs.get('type', 'general'),
        'priority': kwargs.get('priority', 'medium'),
        'payload': kwargs.get('payload', {}),
        'requester': kwargs.get('requester', 'system'),
        'description': kwargs.get('description', ''),
        'status': kwargs.get('status', 'pending'),
        'created_at': kwargs.get('created_at', datetime.now().isoformat()),
        'resource_requirements': kwargs.get('resource_requirements', {})
    }

    if validate_command(record):
        return record
    else:
        raise ValidationError("Invalid command record data")

def create_intelligence_record(**kwargs) -> Dict[str, Any]:
    """Create a validated intelligence record"""
    record = {
        'id': kwargs.get('id', f"intel_{datetime.now().isoformat()}"),
        'source': kwargs.get('source', 'unknown'),
        'type': kwargs.get('type', 'general'),
        'content': kwargs.get('content', {}),
        'confidence': kwargs.get('confidence', 0.5),
        'metadata': kwargs.get('metadata', {}),
        'correlations': kwargs.get('correlations', []),
        'insights': kwargs.get('insights', []),
        'processing_status': kwargs.get('processing_status', 'raw'),
        'retention_policy': kwargs.get('retention_policy', {})
    }

    if validate_intelligence(record):
        return record
    else:
        raise ValidationError("Invalid intelligence record data")

def create_resource_record(**kwargs) -> Dict[str, Any]:
    """Create a validated resource record"""
    record = {
        'id': kwargs.get('id', f"res_{datetime.now().isoformat()}"),
        'type': kwargs.get('type', 'general'),
        'capacity': kwargs.get('capacity', 100),
        'current_usage': kwargs.get('current_usage', 0),
        'allocation_history': kwargs.get('allocation_history', []),
        'optimization_suggestions': kwargs.get('optimization_suggestions', []),
        'health_status': kwargs.get('health_status', 'healthy'),
        'last_updated': kwargs.get('last_updated', datetime.now().isoformat())
    }

    if validate_resource(record):
        return record
    else:
        raise ValidationError("Invalid resource record data")

def create_audit_record(**kwargs) -> Dict[str, Any]:
    """Create a validated audit record"""
    record = {
        'id': kwargs.get('id', f"audit_{datetime.now().isoformat()}"),
        'operation': kwargs.get('operation', 'general'),
        'timestamp': kwargs.get('timestamp', datetime.now().isoformat()),
        'status': kwargs.get('status', 'info'),
        'details': kwargs.get('details', {}),
        'user_context': kwargs.get('user_context', {}),
        'resource_impact': kwargs.get('resource_impact', {}),
        'compliance_flags': kwargs.get('compliance_flags', []),
        'oversight_review': kwargs.get('oversight_review', {})
    }

    if validate_audit(record):
        return record
    else:
        raise ValidationError("Invalid audit record data")