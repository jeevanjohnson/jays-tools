from pathlib import Path


def JsonFile(path: str | Path) -> Path:
	normalized = Path(path)

	# Ensure database files always use a .json suffix.
	if normalized.suffix.lower() != ".json":
		normalized = normalized.with_suffix(".json")

	return normalized
