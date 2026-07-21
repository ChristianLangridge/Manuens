import re

from fastapi.testclient import TestClient

CALIBRATION_NOTE = (
    "ran the IP, 4C ON, used the new lot of protein G beads, only 2h on the ab bc I was late, "
    "spun 12k"
)


def test_index_lists_protocols(client: TestClient) -> None:
    response = client.get("/")
    assert response.status_code == 200
    assert "Co-Immunoprecipitation" in response.text


def test_post_calibration_note_returns_200_with_findings(client: TestClient) -> None:
    response = client.post(
        "/runs",
        data={"protocol_id": "co_immunoprecipitation", "note_text": CALIBRATION_NOTE},
    )

    assert response.status_code == 200
    assert "gap" in response.text
    assert "deviation" in response.text
    assert "ambiguity" in response.text
    assert "protein G beads" in response.text


def test_answering_a_gap_clears_it_from_the_findings_panel(client: TestClient) -> None:
    create_response = client.post(
        "/runs",
        data={"protocol_id": "co_immunoprecipitation", "note_text": CALIBRATION_NOTE},
    )
    run_id = re.search(r'hx-post="/runs/([\w-]+)/answer"', create_response.text).group(1)

    before = create_response.text
    assert before.count('name="field" value="lot"') == 1

    answer_response = client.post(
        f"/runs/{run_id}/answer",
        data={"step_id": "2", "field": "lot", "answer": "PG-9001"},
    )

    assert answer_response.status_code == 200
    assert 'name="field" value="lot"' not in answer_response.text
    assert "PG-9001" in answer_response.text


def test_extraction_failure_degrades_visibly_instead_of_500ing(
    client: TestClient, monkeypatch
) -> None:
    import app.main as main_module

    class _FailingExtractor:
        async def extract(self, note_text: str, protocol) -> None:  # noqa: ANN001
            raise RuntimeError("model unreachable")

    monkeypatch.setattr(main_module, "get_extractor", lambda: _FailingExtractor())

    response = client.post(
        "/runs",
        data={"protocol_id": "co_immunoprecipitation", "note_text": "anything at all"},
    )

    assert response.status_code == 200
    assert "extraction unavailable" in response.text.lower()
