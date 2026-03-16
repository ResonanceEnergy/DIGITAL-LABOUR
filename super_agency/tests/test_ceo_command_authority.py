import pytest
from datetime import datetime
from ceo_command_authority import (
    CEOCommandAuthority, ExecutiveDecision,
    ExecutiveOverride, DecisionAuthority, DecisionCategory
)

# Fixtures


@pytest.fixture
def sample_config():
    return {
        "log_level": "INFO",
        "matrix_file_path": "decision_matrix.json"
    }


@pytest.fixture
def mock_load_config(mocker, sample_config):
    mocker.patch(
        'ceo_command_authority.CEOCommandAuthority._load_config',
        return_value=sample_config)
    mocker.patch(
        'ceo_command_authority.CEOCommandAuthority._load_decision_matrix',
        return_value={})


@pytest.fixture
def ceo_command_authority(mock_load_config):
    return CEOCommandAuthority()

# Tests


def test_initialization_sets_up_logging_and_decision_matrix(
        mocker, sample_config):
    mocker.patch(
        'ceo_command_authority.CEOCommandAuthority._load_config',
        return_value=sample_config)
    mock_logging_setup = mocker.patch(
        'ceo_command_authority.CEOCommandAuthority._setup_logging')
    mock_load_matrix = mocker.patch(
        'ceo_command_authority.CEOCommandAuthority._load_decision_matrix',
        return_value={})
    ca = CEOCommandAuthority()

    assert ca.config_path == (
        "ceo_authority_config.json"
    ), "Config path should be set to a default value"
    assert ca.config == sample_config, "Config should be loaded correctly"
    mock_logging_setup.assert_called_once_with(
    ), "Logging setup should be called during initialization"
    mock_load_matrix.assert_called_once_with(
    ), "Decision matrix should be loaded during initialization"


def test_decision_routing_matrix_loaded_correctly(ceo_command_authority):
    assert ceo_command_authority.decision_matrix == {
    }, "Decision matrix should be initially empty or mock value"


def test_executive_decision_dataclass_initialization():
    decision = ExecutiveDecision(
        decision_id="123",
        category=DecisionCategory.FINANCIAL,
        title="Budget Approval Q4",
        description="Approval needed for Q4 budget",
        impact_level="HIGH",
        authority_required=DecisionAuthority.CEO_APPROVAL,
        proposed_by="Finance Committee",
        ethical_assessment={"integrity": 0.8, "transparency": 0.9},
        risk_assessment={
            "financial_risk": "medium",
            "operational_risk": "low"},
        timeline="2023-10-31 12:00:00"
    )

    assert decision.decision_id == "123", (
        "Decision ID should be initialized correctly"
    )
    assert decision.category == DecisionCategory.FINANCIAL, (
        "Category should match the input"
    )
    assert decision.title == "Budget Approval Q4", (
        "Title should be initialized correctly"
    )
    assert decision.status == "pending", "Default status should be 'pending'"


def test_executive_override_status_deactivation():
    override = ExecutiveOverride(
        override_id="override_001",
        reason="Critical Security Breach",
        declared_by="CEO",
        declared_at="2023-10-20 08:30:00",
        affected_systems=["network", "database"],
        override_duration=24
    )

    assert override.status == "active", "Override should be active by default"
    assert override.deactivated_at is None, (
        "Deactivated_at should be None by default"
    )
    assert override.override_duration == 24, (
        "Override duration should match the input"
    )

    # Simulate deactivation
    override.status = "inactive"
    deactivation_time = datetime.now().isoformat()
    override.deactivated_at = deactivation_time
    override.deactivation_reason = "Issue resolved"

    assert override.status == "inactive", (
        "Override status should change to inactive"
        " after deactivation"
    )
    assert override.deactivated_at == deactivation_time, (
        "Deactivation timestamp should be set"
    )
    assert override.deactivation_reason == "Issue resolved", (
        "Deactivation reason should be logged"
    )


def test_error_conditions_during_initialization(mocker):
    mocker.patch(
        'ceo_command_authority'
        '.CEOCommandAuthority._load_config',
        side_effect=FileNotFoundError(
            "Configuration file not found",
        ),
    )

    with pytest.raises(
        FileNotFoundError,
        match="Configuration file not found",
    ):
        CEOCommandAuthority()  # noqa: F841


@pytest.mark.parametrize("decision_id, category, expected", [
    ("1", DecisionCategory.STRATEGIC, DecisionCategory.STRATEGIC),
    ("2", DecisionCategory.OPERATIONAL, DecisionCategory.OPERATIONAL),
])
def test_decision_category_initialization(decision_id, category, expected):
    decision = ExecutiveDecision(
        decision_id=decision_id,
        category=category,
        title="Test Decision",
        description="Test Description",
        impact_level="LOW",
        authority_required=DecisionAuthority.NCC_AUTONOMOUS,
        proposed_by="Test Proposer",
        ethical_assessment={},
        risk_assessment={},
        timeline="2023-12-10 10:00:00"
    )

    assert decision.category == expected, (
        "Decision category should initialize"
        " to the given category"
    )


def test_decision_authority_enum():
    assert (
        DecisionAuthority.CEO_APPROVAL.value
        == "ceo_approval"
    ), "CEO approval should match the defined value"
    assert (
        DecisionAuthority.EXECUTIVE_OVERRIDE.value
        == "executive_override"
    ), "Executive override should match the defined value"


@pytest.mark.xfail(
    raises=KeyError,
    reason=(
        "This case expects to access"
        " a non-existent element."
    ),
)
def test_accessing_nonexistent_decision_fails(
    ceo_command_authority,
):
    ceo_command_authority.active_decisions[  # noqa: F841
        'nonexistent_id'
    ]
