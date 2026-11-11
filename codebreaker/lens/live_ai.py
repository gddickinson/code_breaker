"""The local vision model on hard live lines (Round 90c), when the user has switched the second reader on.

A hard line is one the frames do not agree on (live_session.Track.needs_help); after the thorough OCR analyser has
read its sharpest view, the vision model reads the same view. Its words are checked against all the OCR evidence for
that line (every frame's reading and the thorough one) with the Lens rule (ai_check.check). If every word is
confirmed, the model's reading joins the line's vote with the thorough analyser's weight; otherwise it is shown beside
the line as an AI suggestion, never as the line's text. Controls in live_ai_eval.py."""
import cv2

from . import ai_check

AI_WEIGHT = 3.0


def ask(session, track) -> None:
    """Called from the live session's background worker, after the thorough reading of a hard line."""
    view = getattr(track, "best_view", None)
    if view is None:
        return
    big = cv2.resize(view, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
    m = ai_check.model_words(big, timeout=60.0)
    if m is None or not m["words"]:
        return
    with session.lock:
        evidence = [w for txt in track.votes for w in txt.split()]
        lines = list(track.votes)
    c = ai_check.check(m["words"], evidence, lines)
    text = " ".join(m["words"])
    with session.lock:
        track.ai = {"text": text, "confirmed": c["confirmed"], "ai_only": c["ai_only"], "model": m["model"], "seconds": m["seconds"]}
        if not c["ai_only"]:
            track.votes[text] += AI_WEIGHT
