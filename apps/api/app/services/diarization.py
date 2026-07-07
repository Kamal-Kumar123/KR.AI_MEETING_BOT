"""Lightweight speaker diarization.

Assigns a speaker label to each transcript segment by clustering short
speaker embeddings extracted from the recording audio.

Design goals for this project:
- No HuggingFace token required (unlike pyannote.audio).
- Graceful fallback: if optional deps are missing or audio is too short,
  every segment is labelled "Speaker 1" and the transcript still works.

Optional dependencies (install for real speaker separation):
    pip install resemblyzer scikit-learn librosa
"""
from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

TARGET_SR = 16000


def _load_audio_16k_mono(path: str):
    """Decode any audio file to a 16k mono float32 numpy array."""
    try:
        from faster_whisper.audio import decode_audio

        return decode_audio(path, sampling_rate=TARGET_SR)
    except Exception:
        pass
    # Fallback via librosa (handles more container formats).
    import librosa

    audio, _ = librosa.load(path, sr=TARGET_SR, mono=True)
    return audio


# Cosine-distance threshold for the initial split with average-linkage
# agglomerative clustering on Resemblyzer embeddings.
SPEAKER_SPLIT_THRESHOLD = 0.40
# Two cluster centroids closer than this are treated as the SAME person
# (guards against one voice's tonal variation being split into many speakers).
MERGE_CENTROID_DIST = 0.55
# A real speaker must occupy at least this share of the speech windows;
# smaller clusters are stray/noise and get merged into the nearest speaker.
MIN_SPEAKER_SHARE = 0.15
MAX_SPEAKERS = 6


def diarize_segments(audio_path: str, segments: list[dict]) -> tuple[list[dict], int]:
    """Return (segments_with_speaker, num_speakers).

    Uses dense sliding-window voice embeddings (works even for a couple of
    short utterances) and auto-detects the number of speakers by how different
    the voices are. On any failure every segment falls back to "Speaker 1".
    """
    labelled = [dict(seg) for seg in segments]

    def _all_single():
        for s in labelled:
            s["speaker"] = "Speaker 1"
        return labelled, 1

    if not segments:
        return labelled, 0

    try:
        import numpy as np
        from resemblyzer import VoiceEncoder
        from sklearn.cluster import AgglomerativeClustering
    except Exception as exc:  # deps not installed
        logger.warning("Diarization deps unavailable (%s); using single speaker", exc)
        return _all_single()

    try:
        audio = _load_audio_16k_mono(audio_path)
    except Exception as exc:
        logger.warning("Diarization audio decode failed (%s)", exc)
        return _all_single()

    encoder = VoiceEncoder(verbose=False)

    # Dense partial embeddings across the whole recording (rate = windows/sec).
    try:
        _, cont_embeds, wav_splits = encoder.embed_utterance(
            audio, return_partials=True, rate=4
        )
    except Exception as exc:
        logger.warning("Diarization embedding failed (%s)", exc)
        return _all_single()

    if cont_embeds is None or len(cont_embeds) < 2:
        return _all_single()

    cont_embeds = np.asarray(cont_embeds)
    wav_splits = list(wav_splits)

    # Cap windows for long meetings so agglomerative clustering stays cheap.
    MAX_WINDOWS = 1500
    if len(cont_embeds) > MAX_WINDOWS:
        idx = np.linspace(0, len(cont_embeds) - 1, MAX_WINDOWS).astype(int)
        cont_embeds = cont_embeds[idx]
        wav_splits = [wav_splits[i] for i in idx]

    # Auto number of speakers via distance threshold (no need to know count).
    clustering = AgglomerativeClustering(
        n_clusters=None,
        distance_threshold=SPEAKER_SPLIT_THRESHOLD,
        metric="cosine",
        linkage="average",
    )
    win_labels = clustering.fit_predict(cont_embeds)

    if len(set(win_labels)) <= 1:
        return _all_single()

    # --- Robustness pass: avoid splitting ONE person into several speakers. ---
    def _unit(v):
        return v / (np.linalg.norm(v) + 1e-8)

    def _centroid(lbl):
        return _unit(cont_embeds[win_labels == lbl].mean(axis=0))

    def _cos_dist(a, b):
        return 1.0 - float(np.dot(_unit(a), _unit(b)))

    # 1) Merge clusters whose voice centroids are too similar to be different
    #    people (same speaker, just tonal/phonetic variation).
    changed = True
    while changed:
        changed = False
        labels_now = sorted(set(win_labels))
        if len(labels_now) <= 1:
            break
        cents = {l: _centroid(l) for l in labels_now}
        best_pair, best_d = None, MERGE_CENTROID_DIST
        for i in range(len(labels_now)):
            for j in range(i + 1, len(labels_now)):
                d = _cos_dist(cents[labels_now[i]], cents[labels_now[j]])
                if d < best_d:
                    best_d, best_pair = d, (labels_now[i], labels_now[j])
        if best_pair:
            win_labels[win_labels == best_pair[1]] = best_pair[0]
            changed = True

    # 2) Drop tiny clusters (spurious speaker from a single stray window) by
    #    reassigning their windows to the nearest surviving speaker centroid.
    total = len(win_labels)
    labels_now = sorted(set(win_labels))
    counts = {l: int((win_labels == l).sum()) for l in labels_now}
    strong = [l for l in labels_now if counts[l] / total >= MIN_SPEAKER_SHARE]
    if not strong:
        strong = [max(counts, key=counts.get)]
    if len(strong) < len(labels_now):
        strong_cents = {l: _centroid(l) for l in strong}
        for weak in [l for l in labels_now if l not in strong]:
            idxs = np.where(win_labels == weak)[0]
            for k in idxs:
                nearest = min(strong, key=lambda l: _cos_dist(cont_embeds[k], strong_cents[l]))
                win_labels[k] = nearest

    num_speakers = len(set(win_labels))
    if num_speakers <= 1:
        return _all_single()
    if num_speakers > MAX_SPEAKERS:
        clustering = AgglomerativeClustering(
            n_clusters=2, metric="cosine", linkage="average"
        )
        win_labels = clustering.fit_predict(cont_embeds)
        num_speakers = 2

    # Window centre times (seconds) for aligning to transcript segments.
    win_centres = [
        ((sl.start + sl.stop) / 2.0) / TARGET_SR for sl in wav_splits
    ]

    # Stable "Speaker N" numbering by first appearance in time.
    order: dict[int, int] = {}
    for lbl in win_labels:
        if lbl not in order:
            order[lbl] = len(order) + 1

    def speaker_for_range(start: float, end: float) -> str:
        votes: dict[int, int] = {}
        for c, lbl in zip(win_centres, win_labels):
            if start <= c <= end:
                votes[lbl] = votes.get(lbl, 0) + 1
        if not votes:
            # nearest window
            nearest = min(
                range(len(win_centres)),
                key=lambda i: abs(win_centres[i] - (start + end) / 2.0),
            )
            lbl = win_labels[nearest]
        else:
            lbl = max(votes, key=votes.get)
        return f"Speaker {order[lbl]}"

    for seg in labelled:
        seg["speaker"] = speaker_for_range(
            float(seg.get("start", 0.0)), float(seg.get("end", 0.0))
        )

    return labelled, num_speakers


def build_diarized_text(segments: list[dict]) -> str:
    """Render segments as 'Speaker N: text', merging consecutive same-speaker turns."""
    lines: list[str] = []
    current_speaker = None
    buffer: list[str] = []

    def flush():
        if buffer and current_speaker:
            lines.append(f"{current_speaker}: {' '.join(buffer).strip()}")

    for seg in segments:
        speaker = seg.get("speaker", "Speaker 1")
        text = seg.get("text", "").strip()
        if not text:
            continue
        if speaker != current_speaker:
            flush()
            current_speaker = speaker
            buffer = [text]
        else:
            buffer.append(text)
    flush()
    return "\n".join(lines)
