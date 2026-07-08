"""
Automated RAG series test — processes 3 connected meetings and prints context + output.

Usage (from apps/api):
    python scripts/test_rag_series.py

Optional:
    python scripts/test_rag_series.py --series my-test-series
    python scripts/test_rag_series.py --keep   # do not delete test meetings after run
"""
from __future__ import annotations

import argparse
import sys
import time
from datetime import datetime

# Windows console UTF-8
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Allow running as: python scripts/test_rag_series.py
sys.path.insert(0, ".")

from app.db.models import ActionItem, Meeting, SessionLocal, Summary, Transcript, User, generate_uuid
from app.services.ai_pipeline import finalize_meeting_insights
from app.services.rag import get_rag_service

SERIES = f"rag-autotest-{int(time.time())}"

MEETINGS = [
    {
        "title": "RAG Test - Kickoff",
        "transcript": (
            "Hello team. This is meeting one for Project Phoenix. "
            "We approved a total budget of fifty thousand dollars for this quarter. "
            "Kamal Kumar will lead the backend work. "
            "No task deadlines are assigned in this kickoff call."
        ),
        "expect_rag": False,
        "expect_keywords_in_context": [],
    },
    {
        "title": "RAG Test - Sprint 2",
        "transcript": (
            "Welcome back to Project Phoenix sprint two. "
            "Building on our approved budget from last time, Aditya must deliver the REST API "
            "by August first. The payment module is not started yet. "
            "Kamal confirmed the fifty thousand dollar budget still applies."
        ),
        "expect_rag": True,
        "expect_keywords_in_context": ["phoenix", "fifty thousand", "budget", "kickoff"],
    },
    {
        "title": "RAG Test - Status Review",
        "transcript": (
            "Phoenix project status update. Hassan will integrate Stripe payments "
            "by August fifteenth. We need Aditya's API from sprint two before payments go live. "
            "The overall Phoenix budget remains fifty thousand dollars."
        ),
        "expect_rag": True,
        "expect_keywords_in_context": ["phoenix", "api", "aditya", "august"],
    },
]


def _get_or_create_test_user(db) -> User:
    email = "rag-autotest@krai.local"
    user = db.query(User).filter(User.email == email).first()
    if user:
        return user
    user = User(email=email, full_name="RAG Auto Test")
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _create_meeting(db, user: User, spec: dict, series_id: str) -> Meeting:
    meeting = Meeting(
        id=generate_uuid(),
        user_id=user.id,
        title=spec["title"],
        platform="rag_test",
        status="awaiting_config",
        meeting_mode="connected",
        series_id=series_id,
        use_rag=True,
        started_at=datetime.utcnow(),
        ended_at=datetime.utcnow(),
    )
    db.add(meeting)
    db.flush()
    db.add(
        Transcript(
            meeting_id=meeting.id,
            full_text=spec["transcript"],
            segments_json=[{"speaker": "Speaker 1", "text": spec["transcript"], "start": 0, "end": 0}],
        )
    )
    db.commit()
    db.refresh(meeting)
    return meeting


def _print_section(title: str) -> None:
    print("\n" + "=" * 72)
    print(title)
    print("=" * 72)


def _check_keywords(text: str, keywords: list[str]) -> list[str]:
    lower = text.lower()
    missing = [k for k in keywords if k.lower() not in lower]
    return missing


def run(series_id: str, keep: bool) -> int:
    db = SessionLocal()
    rag = get_rag_service()
    user = _get_or_create_test_user(db)
    created_ids: list[str] = []
    failures = 0

    _print_section(f"RAG SERIES TEST — series_id: {series_id}")
    print(f"User: {user.email}")
    print(f"Chroma chunks before test: {rag.store.count_for_series(series_id)}")

    results = []

    for idx, spec in enumerate(MEETINGS, start=1):
        _print_section(f"MEETING {idx}/3 — {spec['title']}")

        meeting = _create_meeting(db, user, spec, series_id)
        created_ids.append(meeting.id)

        # Preview RAG context BEFORE finalize (same as pipeline)
        past_context, past_summaries = rag.get_context_for_transcript(
            spec["transcript"],
            series_id=series_id,
            use_rag=True,
            exclude_meeting_id=meeting.id,
        )

        print("\n--- Transcript (input) ---")
        print(spec["transcript"])

        print("\n--- RAG context retrieved (before processing) ---")
        if past_context:
            print(past_context)
        else:
            print("(none — first meeting in series or index empty)")

        print("\n--- Running finalize_meeting_insights ---")
        finalize_meeting_insights(db, meeting.id)
        db.refresh(meeting)

        summary_text = ""
        if meeting.summary:
            summary_text = meeting.summary.executive_summary or ""

        action_items = (
            db.query(ActionItem).filter(ActionItem.meeting_id == meeting.id).order_by(ActionItem.id).all()
        )

        indexed = rag.store.count_for_series(series_id)
        indexed_meetings = rag.store.list_meeting_ids(series_id)

        print("\n--- Output ---")
        print(f"Status:           {meeting.status}")
        print(f"rag_context_used: {meeting.rag_context_used}")
        print(f"Chroma chunks:    {indexed} (meetings indexed: {len(indexed_meetings)})")
        print(f"\nSummary:\n{summary_text or '(empty)'}")
        print("\nAction items:")
        if action_items:
            for item in action_items:
                print(f"  - {item.owner} | {item.task} | deadline: {item.deadline}")
        else:
            print("  (none)")

        # Validation
        ok = meeting.status == "ready"
        if spec["expect_rag"] and not meeting.rag_context_used:
            print("\n[FAIL] Expected rag_context_used=True")
            ok = False
            failures += 1
        if not spec["expect_rag"] and meeting.rag_context_used:
            print("\n[NOTE] First meeting used RAG context (unexpected but not fatal)")

        if spec["expect_keywords_in_context"]:
            missing = _check_keywords(past_context, spec["expect_keywords_in_context"])
            if missing:
                print(f"\n[FAIL] RAG context missing keywords: {missing}")
                ok = False
                failures += 1
            else:
                print(f"\n[PASS] RAG context contains expected keywords: {spec['expect_keywords_in_context']}")

        if ok and meeting.status == "ready":
            print("\n[PASS] Meeting processed OK")

        results.append(
            {
                "meeting_id": meeting.id,
                "title": spec["title"],
                "rag_context_used": meeting.rag_context_used,
                "context_preview": (past_context or "")[:500],
                "summary": summary_text[:300],
                "action_count": len(action_items),
            }
        )

    _print_section("FINAL REPORT")
    for r in results:
        print(f"\n[{r['title']}]")
        print(f"  id: {r['meeting_id']}")
        print(f"  rag_context_used: {r['rag_context_used']}")
        print(f"  action_items: {r['action_count']}")
        print(f"  context preview: {r['context_preview'][:200]}...")
        print(f"  summary preview: {r['summary'][:200]}...")

    print(f"\nTotal failures: {failures}")
    print(f"Series '{series_id}' — view in UI under Connected Projects")

    if not keep:
        print("\nCleaning up test meetings from database (Chroma index kept for inspection)...")
        for mid in created_ids:
            m = db.query(Meeting).filter(Meeting.id == mid).first()
            if m:
                db.delete(m)
        db.commit()
        print("DB cleanup done. Chroma vectors remain under apps/api/chroma_data.")
    else:
        print("\n--keep set: test meetings left in DB.")
        for mid in created_ids:
            print(f"  meeting_id={mid}")

    db.close()
    return 1 if failures else 0


def main() -> None:
    parser = argparse.ArgumentParser(description="Automated RAG connected-series test")
    parser.add_argument("--series", default=SERIES, help="series_id to use")
    parser.add_argument("--keep", action="store_true", help="Keep test meetings in DB")
    args = parser.parse_args()
    raise SystemExit(run(args.series, args.keep))


if __name__ == "__main__":
    main()
