# Code Breaker

Local web app for learning, making and breaking ciphers, with case files on unsolved ciphers.

@INTERFACE.md

- Run: `.venv/bin/python run.py`, then open http://127.0.0.1:8000
- Test: `PYTHONPATH=. .venv/bin/python -m pytest -q tests/`
- Keep every file under 500 lines. Update INTERFACE.md and SESSION_LOG.md when the structure changes.
- Never type ciphertexts from memory: extract them from a recorded source and add an integrity test.
- A mystery result counts only with a positive control and a null comparison (`codebreaker/validation.py`).
