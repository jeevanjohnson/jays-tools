# Jays Tools

A collection of lightweight utilities for common development tasks, designed for simplicity and type safety.

## Features

- **JsonDatabase**: JSON-backed database with Pydantic validation, automatic migrations, and async support
- Strongly typed with full IDE support
- Minimal API surface for quick adoption
- Transparent data migrations as your models evolve

## Installation

```bash
pip install jays-tools
```

## Quick Start: JsonDatabase

A lightweight, typed JSON database perfect for single-process applications, prototypes, and embedded data stores.

### Basic Usage

```python
from jays_tools.json_database import JsonDatabase
from pydantic import BaseModel

class Users(BaseModel):
    total: int = 0
    users: list[dict] = []

# Create or load database (file auto-created if missing)
db = JsonDatabase("users.json", Users)

# Read, modify, and persist
current = db.get_database()
current.users.append({"id": 1, "name": "Alice"})
current.total = len(current.users)
db.update_database(current)

# Access the data
data = db.get_database()
print(data.total)   # 1
print(data.users)   # [{"id": 1, "name": "Alice"}]
```

### Async Support

```python
import asyncio

async def main():
    db = JsonDatabase("users.json", Users)
    
    # Non-blocking read/write via thread pool
    current = await db.async_get_database()
    current.total += 1
    await db.async_update_database(current)

asyncio.run(main())
```

### Text Encoding & Legacy Files

By default, JsonDatabase uses UTF-8 with strict error handling. For legacy files with different encodings:

```python
# Read old Windows files (cp1252) and auto-normalize to UTF-8
db = JsonDatabase(
    "legacy_users.json",
    Users,
    # File will be rewritten as UTF-8 on next write
)
```

## Key Concepts

### Type-Safe by Default

Your database shape is defined with Pydantic models. Access data with full type hints and IDE autocomplete.

```python
db = JsonDatabase("config.json", MyConfig)
config = db.get_database()
config.api_key  # Full IDE support, no guessing types
```

### Automatic Migrations

Update your model, existing data migrates automatically. No manual migration scripts needed.

See [ARCHITECTURE.md](./ARCHITECTURE.md#migrations) for detailed migration examples.

### Simple API

Three core methods:
- `get_database()` → Read current state (returns a copy)
- `update_database(data)` → Write new state and persist to disk
- `async_get_database()` / `async_update_database()` → Async versions

## Recommended Project Structure

For projects with multiple data models:

```
my_project/
├── src/
│   ├── models/
│   │   ├── __init__.py
│   │   ├── user.py
│   │   └── settings.py
│   ├── database.py
│   └── main.py
└── data/
    ├── user.json
    ├── settings.json
    └── session.json
```

**models/user.py:**
```python
from typing import Any
from jays_tools.json_database.models import MigratableModel

class UserV1(MigratableModel):
    name: str = ""
    age: int = 0

class UserV2(MigratableModel, previous_model=UserV1):
    name: str = ""
    age: int = 0
    email: str = ""

    @staticmethod
    def migrate_from_previous(previous_data: dict[str, Any]) -> dict[str, Any]:
        previous_data["email"] = ""
        return previous_data

# Always export the latest version
User = UserV2
```

**src/database.py:**
```python
from pathlib import Path
from src.models.user import User
from jays_tools.json_database import JsonDatabase

DATA_DIR = Path("data")
DATA_DIR.mkdir(exist_ok=True)

user_db = JsonDatabase(DATA_DIR / "user.json", User)
```

**src/main.py:**
```python
from src.database import user_db

def main():
    user = user_db.get_database()
    user.name = "Alice"
    user.email = "alice@example.com"
    user_db.update_database(user)
```

## Learn More

- [Architecture & Design](./ARCHITECTURE.md) — Internal structure, design paradigm, and migration details
- [Design Philosophy](./PHILOSOPHY.md) — Inspiration and design principles behind JsonDatabase
- [API Reference](./docs/api.md) *(coming soon)*

## Testing

Run the comprehensive test suite:

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest tests/ -v

# With coverage
pytest --cov=src tests/
```

## License

MIT - See LICENSE file for details
