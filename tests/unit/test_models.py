import pytest
from pydantic import ValidationError

from app.models import Step


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
