"""Show full RAG results for a connected series."""
from __future__ import annotations

import argparse
import sys

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

sys.path.insert(0, ".")

from app.db.models import ActionItem, Meeting, SessionLocal, Summary, Transcript
from app.services.rag import get_rag_service


def show(series_id: str) -> None:
    db = SessionLocal()
    rag = get_rag_service()

    meetings = (
        db.query(Meeting)
        .filter(Meeting.series_id == series_id)
        .order_by(Meeting.started_at)
        .all()
    )

    print(f"Series: {series_id}")
    print(f"Meetings found: {len(meetings)}")
    print(f"Chroma chunks: {rag.store.count_for_series(series_id)}")
    print(f"Indexed meeting IDs: {rag.store.list_meeting_ids(series_id)}")
    print()

    if not meetings:
        print("No meetings in DB for this series.")
        db.close()
        return

    for i, m in enumerate(meetings, 1):
        t = db.query(Transcript).filter(Transcript.meeting_id == m.id).first()
        s = db.query(Summary).filter(Summary.meeting_id == m.id).first()
        items = db.query(ActionItem).filter(ActionItem.meeting_id == m.id).all()
        transcript = t.full_text if t else ""

        # Context available only from meetings processed BEFORE this one
        prior_ids = {x.id for x in meetings if x.started_at < m.started_at}
        hits = rag.retrieve(transcript[:1000], top_k=5, series_id=series_id)
        hits = [
            h
            for h in hits
            if h["metadata"].get("meeting_id") in prior_ids
            and h["metadata"].get("meeting_id") != m.id
        ]
        if hits:
            context_lines = [f"Relevant context from previous meetings in series '{series_id}':"]
            for hit in hits:
                metadata = hit["metadata"]
                chunk_type = metadata.get("chunk_type", "transcript")
                timestamp = metadata.get("timestamp", "unknown time")
                context_lines.append(f"[{chunk_type} | {timestamp}] {hit['text']}")
            past_context = "\n".join(context_lines)
        else:
            past_context = ""

        print("=" * 72)
        print(f"MEETING {i}: {m.title}")
        print(f"id: {m.id}")
        print(f"rag_context_used: {m.rag_context_used}")
        print(f"status: {m.status}")
        print()
        print("--- Transcript ---")
        print(transcript)
        print()
        print("--- RAG context (at processing time) ---")
        print(past_context if past_context else "(none)")
        print()
        print("--- Summary ---")
        print(s.executive_summary if s and s.executive_summary else "(empty)")
        print()
        print("--- Action items ---")
        if items:
            for a in items:
                print(f"  - {a.owner} | {a.task} | deadline: {a.deadline}")
        else:
            print("  (none)")
        print()

    db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("series_id", nargs="?", default="rag-autotest-1783495534")
    args = parser.parse_args()
    show(args.series_id)
