from pathlib import Path


def JsonFile(path: str | Path) -> Path:
    """Normalize file path to ensure .json suffix."""
    normalized = Path(path)

    # Ensure database files always use a .json suffix.
    if normalized.suffix.lower() != ".json":
        normalized = normalized.with_suffix(".json")

    return normalized
