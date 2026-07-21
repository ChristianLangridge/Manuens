from app.analysis.recoverability import field_recoverability


def test_lot_field_is_perishable_now() -> None:
    assert field_recoverability("lot") == "perishable_now"


def test_duration_field_is_perishable_today() -> None:
    assert field_recoverability("duration_min") == "perishable_today"


def test_unrecognised_field_is_stable() -> None:
    assert field_recoverability("concentration") == "stable"
