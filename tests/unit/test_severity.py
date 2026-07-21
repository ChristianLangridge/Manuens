from app.analysis.severity import reagent_gap_severity


def test_critical_reagent_class_is_critical() -> None:
    assert reagent_gap_severity("protein G beads") == "critical"
