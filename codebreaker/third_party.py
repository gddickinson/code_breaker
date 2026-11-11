"""Third-party data that the public repository does not redistribute (see THIRD_PARTY.md).

need(path) returns the path, or explains how to fetch the file: scripts/fetch_sources.py downloads Didier Müller's
Le Figaro key tables and ads database and Klaus Schmeh's top-50 list from their public sites."""
from pathlib import Path


def need(path: Path) -> Path:
    if not path.exists():
        raise FileNotFoundError(f"{path.name} is third-party data not kept in the repository: run `python scripts/fetch_sources.py` (see THIRD_PARTY.md).")
    return path
