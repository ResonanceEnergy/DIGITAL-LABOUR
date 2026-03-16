import logging
import pytest
from unittest.mock import Mock, patch
from cpu_task_manager import CPURegulator, TaskPriority, TaskStatus, Task


@pytest.fixture
def default_cpu_regulator():
    return CPURegulator()


@pytest.fixture
def critical_task():
    return Task(
        id='1',
        name='Critical Task',
        priority=TaskPriority.CRITICAL,
        function=lambda: "test",
    )


def test_cpu_regulator_initialization(default_cpu_regulator):
    assert default_cpu_regulator.target_cpu_percent == 80.0, (
        "Default target CPU percentage should be 80"
    )
    assert default_cpu_regulator.memory_threshold == 85.0, (
        "Default memory threshold should be 85"
    )
    assert not default_cpu_regulator.is_regulating, (
        "CPU regulation should not be running initially"
    )


def test_cpu_regulator_start_regulation(default_cpu_regulator):
    with patch('threading.Thread.start', Mock()) as mock_start_thread:
        default_cpu_regulator.start_regulation()
        assert default_cpu_regulator.is_regulating, (
            "Regulation should be marked as started"
        )
        mock_start_thread.assert_called_once()


def test_cpu_regulator_start_regulation_already_started(
        default_cpu_regulator, caplog):
    default_cpu_regulator.is_regulating = True
    with caplog.at_level(logging.WARNING):
        default_cpu_regulator.start_regulation()
    assert "CPU regulation already running" in caplog.text, (
        "Warning should be logged if regulation starts "
        "with an existing running state"
    )


def test_task_creation_with_default_values():
    task = Task(
        id='1',
        name='Sample Task',
        priority=TaskPriority.NORMAL,
        function=lambda: "result",
    )
    assert task.status == TaskStatus.PENDING, (
        "New tasks should default to a pending status"
    )
    assert task.created_at is not None, (
        "Task creation timestamp should be set"
    )
    assert task.completed_at is None, (
        "Task completion timestamp should be None"
    )


def test_task_execution_and_result(critical_task):
    critical_task.function = lambda: "expected_result"
    assert critical_task.function(
    ) == "expected_result", (
        "Task execution should produce the expected result"
    )


def test_task_with_cpu_limit():
    mock_function = Mock(return_value="done")
    task = Task(
        id='2',
        name='CPU Limited Task',
        priority=TaskPriority.HIGH,
        function=mock_function,
        cpu_limit=50.0
    )
    assert task.cpu_limit == 50.0, (
        "CPU limit should be set to the specified value"
    )


@pytest.mark.parametrize("priority, expected_priority", [
    (TaskPriority.CRITICAL, 1),
    (TaskPriority.HIGH, 2),
    (TaskPriority.NORMAL, 3),
    (TaskPriority.LOW, 4),
    (TaskPriority.BACKGROUND, 5),
])
def test_task_priority_enum(priority, expected_priority):
    assert priority.value == expected_priority, (
        f"Task priority {priority} should have "
        f"corresponding enum value {expected_priority}"
    )


def test_task_status_enum():
    assert TaskStatus.PENDING.value == "pending", (
        "TaskStatus.PENDING should correspond "
        "to the correct string value"
    )
    assert TaskStatus.COMPLETED.value == "completed", (
        "TaskStatus.COMPLETED should correspond "
        "to the correct string value"
    )


def test_task_dependency_handling():
    task = Task(
        id='3',
        name='Dependent Task',
        priority=TaskPriority.LOW,
        function=lambda: "result",
        dependencies=['task1', 'task2']
    )
    assert task.dependencies == [
        'task1', 'task2'], (
        "Task should maintain correct "
        "list of dependencies"
    )
