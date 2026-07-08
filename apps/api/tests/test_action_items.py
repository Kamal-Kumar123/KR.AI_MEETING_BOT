"""Action item extraction tests (heuristics — no Gemini required)."""
from app.services.ai_pipeline import _extract_action_items_heuristic, collect_action_items

TASK_TRANSCRIPT = (
    "Hello. My name is Kamil Kumar. Today, I want to assign one task to Hassan. "
    "He has to complete his work by July 15. And, to Aditya, he has to complete his work by July 20."
)

PROJECT_VIA_TRANSCRIPT = (
    "Hello. My name is Kamil Kumar. Today, I am going to assign one project to Hassan. "
    "He has to complete his project to via July 15. And to Aditya, he has to complete his work "
    "via fifteen twentieth of July."
)


def _owners(items: list[dict]) -> set[str]:
    return {i["owner"] for i in items}


def test_heuristic_task_by_deadline():
    items = _extract_action_items_heuristic(TASK_TRANSCRIPT)
    assert len(items) >= 2
    assert "Hassan" in _owners(items)
    assert "Aditya" in _owners(items)


def test_heuristic_project_via_deadline():
    items = _extract_action_items_heuristic(PROJECT_VIA_TRANSCRIPT)
    assert len(items) >= 2
    assert "Hassan" in _owners(items)
    assert "Aditya" in _owners(items)


def test_collect_always_includes_heuristics_without_gemini(monkeypatch):
    """Even when Gemini is unavailable, heuristics must populate action items."""
    monkeypatch.setattr("app.services.ai_pipeline.gemini_available", lambda: False)
    items = collect_action_items(TASK_TRANSCRIPT, "", {})
    assert len(items) >= 2
    assert "Hassan" in _owners(items)
    assert "Aditya" in _owners(items)
