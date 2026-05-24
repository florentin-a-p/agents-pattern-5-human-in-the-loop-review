import json
import sys
from pathlib import Path

from fastapi.testclient import TestClient

APP_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(APP_DIR))

import run


def test_metadata_json_exists_and_has_required_fields() -> None:
    metadata_path = APP_DIR / "metadata.json"

    assert metadata_path.exists()
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))

    for field in ["name", "version", "use_case_id", "description", "entrypoint", "endpoint"]:
        assert metadata.get(field)
    assert metadata["use_case_id"] == "12"


def test_env_example_exists_and_contains_openai_base_url() -> None:
    env_path = APP_DIR / ".env.example"

    assert env_path.exists()
    assert "OPENAI_BASE_URL" in env_path.read_text(encoding="utf-8")


def test_post_run_returns_json_object(monkeypatch) -> None:
    monkeypatch.setenv("SAMPLE_MODE", "true")
    client = TestClient(run.app)

    response = client.post("/run", json={"sample_id": "sample_1"})

    assert response.status_code == 200
    payload = response.json()
    assert isinstance(payload, dict)
    assert payload["run_id"]
    assert payload["status"] == "completed"
    assert payload["final_action"]["action_type"] in {"allow", "warn", "remove", "suspend"}


def test_agent_trace_jsonl_is_written_during_run(monkeypatch) -> None:
    monkeypatch.setenv("SAMPLE_MODE", "true")
    trace_path = APP_DIR / "logs" / "agent_trace.jsonl"
    if trace_path.exists():
        trace_path.unlink()
    client = TestClient(run.app)

    response = client.post("/run", json={"sample_id": "sample_1"})

    assert response.status_code == 200
    assert trace_path.exists()
    lines = trace_path.read_text(encoding="utf-8").strip().splitlines()
    assert lines
    events = [json.loads(line) for line in lines]
    assert any(event["agent"] == "DetectionAgent" for event in events)
    assert any(event["agent"] == "ContextAnalysisAgent" for event in events)
    assert any(event["agent"] == "PolicyAgent" for event in events)


def test_final_action_changes_when_content_changes(monkeypatch) -> None:
    monkeypatch.setenv("SAMPLE_MODE", "true")
    client = TestClient(run.app)

    first = client.post(
        "/run",
        json={
            "content": "Buy now and click this link for a free prize.",
            "human_review_approved": True,
        },
    )
    second = client.post(
        "/run",
        json={
            "content": "You are a worthless loser.",
            "human_review_approved": True,
        },
    )

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["detection"]["category"] != second.json()["detection"]["category"]


def test_human_rejection_loops_back_without_final_action(monkeypatch) -> None:
    monkeypatch.setenv("SAMPLE_MODE", "true")
    client = TestClient(run.app)

    response = client.post("/run", json={"sample_id": "custom_sample_3"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "needs_human_review"
    assert payload["final_action"] is None
    assert payload["iterations_used"] >= 2


def test_context_feedback_can_lower_detection_risk(monkeypatch) -> None:
    monkeypatch.setenv("SAMPLE_MODE", "true")
    client = TestClient(run.app)

    response = client.post("/run", json={"sample_id": "sample_2"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["context_analysis"]["context_risk_modifier"] < 0
    assert payload["detection"]["risk_score"] < 0.73


def test_max_iterations_caps_agent_loop(monkeypatch) -> None:
    monkeypatch.setenv("SAMPLE_MODE", "true")
    client = TestClient(run.app)

    response = client.post("/run", json={"sample_id": "custom_sample_3", "max_iterations": 1})

    assert response.status_code == 200
    payload = response.json()
    assert payload["max_iterations"] == 1
    assert payload["iterations_used"] == 1
    assert payload["status"] == "needs_human_review"


def test_max_iterations_accepts_higher_user_budget(monkeypatch) -> None:
    monkeypatch.setenv("SAMPLE_MODE", "true")
    client = TestClient(run.app)

    response = client.post("/run", json={"sample_id": "sample_1", "max_iterations": 15})

    assert response.status_code == 200
    payload = response.json()
    assert payload["max_iterations"] == 15
    assert payload["iterations_used"] <= 15


def test_ambiguous_custom_request_can_use_many_agent_iterations(monkeypatch) -> None:
    monkeypatch.setenv("SAMPLE_MODE", "true")
    client = TestClient(run.app)

    response = client.post(
        "/run",
        json={
            "content_id": "post-many-loops",
            "user_id": "user-many-loops",
            "content": "You are an idiot and should shut up.",
            "conversation_history": [
                {"role": "user-many-loops", "content": "This person keeps derailing the thread."}
            ],
            "user_relationship": "strangers in a public discussion",
            "detected_language": "en",
            "locale": "en-US",
            "community_type": "public_forum",
            "human_review_approved": False,
            "human_rejection_reason": "Moderator rejected the recommendation and wants the agents to keep checking context.",
            "max_iterations": 10,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["max_iterations"] == 10
    assert payload["iterations_used"] == 10
    assert payload["policy"]["needs_more_context"] is True
    assert payload["status"] == "needs_human_review"
    assert payload["final_action"] is None


def test_sample_5_uses_ten_agent_iterations(monkeypatch) -> None:
    monkeypatch.setenv("SAMPLE_MODE", "true")
    client = TestClient(run.app)

    response = client.post("/run", json={"sample_id": "sample_5"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["iterations_used"] == 10
    assert payload["max_iterations"] == 10
    assert payload["policy"]["needs_more_context"] is True
    assert payload["final_action"] is None
