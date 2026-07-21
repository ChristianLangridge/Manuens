from app.analysis.severity import deviation_severity, reagent_gap_severity


def test_critical_reagent_class_is_critical() -> None:
    assert reagent_gap_severity("protein G beads") == "critical"


def test_buffer_reagent_is_low() -> None:
    assert reagent_gap_severity("PBS-T") == "low"


def test_material_deviation_on_high_sensitivity_step() -> None:
    # 120 actual vs 240 expected, tolerance 30 -> well outside tolerance on a high-sensitivity step
    assert deviation_severity(sensitivity="high", expected=240, actual=120, tolerance=30) == "material"


def test_same_deviation_on_low_sensitivity_step_is_informational() -> None:
    assert (
        deviation_severity(sensitivity="low", expected=240, actual=120, tolerance=30)
        == "informational"
    )


def test_deviation_within_tolerance_is_not_flagged() -> None:
    assert deviation_severity(sensitivity="high", expected=240, actual=230, tolerance=30) is None
