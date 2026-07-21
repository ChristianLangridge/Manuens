import pytest
from pydantic import ValidationError

from app.models import Finding, Step


def test_step_rejects_invalid_sensitivity() -> None:
    with pytest.raises(ValidationError):
        Step(
            id="1",
            name="Incubate",
            required_fields=["duration_min"],
            expected_values={},
            tolerance={},
            sensitivity="medium",
        )


def test_finding_rejects_invalid_type() -> None:
    with pytest.raises(ValidationError):
        Finding(
            type="issue",
            severity="critical",
            recoverability="perishable_now",
            message="bead lot missing",
            step_id="3",
            field="lot",
        )
