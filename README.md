# Jays Tools

A collection of lightweight utilities for JSON-backed data persistence with full type safety, automatic migrations, and async support.

## Features

- **JsonDatabase**: Strongly-typed JSON database for single entities with Pydantic validation and automatic migrations
- **JsonCollection**: Directory-based entity collections for managing multiple related objects (one file per entity)
- Full type safety with IDE autocomplete and compile-time checking
- Transparent schema migrations as your models evolve
- Thread-safe operations with automatic concurrency handling
- Async support for non-blocking I/O
- Minimal, intuitive API

## Installation

```bash
pip install jays-tools
```

## Quick Start: JsonDatabase

A lightweight JSON database perfect for application state, configuration, and single-entity storage.

### Basic Usage

```python
from jays_tools.json_database import JsonDatabase
from pydantic import BaseModel

class AppState(BaseModel):
    total: int = 0
    users: list[dict] = []

# Create or load database (auto-created if missing)
db = JsonDatabase("app_state.json", AppState)

# Read, modify, and persist
state = db.get_database()
state.users.append({"id": 1, "name": "Alice"})
state.total = len(state.users)
db.update_database(state)

# Verify persistence
data = db.get_database()
print(data.total)   # 1
print(data.users)   # [{"id": 1, "name": "Alice"}]
```

### Async Support

```python
import asyncio

async def main():
    db = JsonDatabase("app_state.json", AppState)
    
    # Non-blocking read/write via thread pool
    state = await db.async_get_database()
    state.total += 1
    await db.async_update_database(state)

asyncio.run(main())
```

## Quick Start: JsonCollection

Store collections of entities as individual JSON files, automatically keyed by filename.

### Basic Usage

```python
from jays_tools.json_collection import JsonCollection
from pydantic import BaseModel

class User(BaseModel):
    name: str = ""
    email: str = ""

# Create or load collection
collection = JsonCollection("data/users", model=User)

# Create/update entities
user_data = User(name="Alice", email="alice@example.com")
collection.update("alice_id", user_data)

# List all keys
keys = collection.list_keys()  # ["alice_id"]

# Retrieve entities
user = collection.get("alice_id").get_database()
print(user.name)  # "Alice"

# Delete entities
collection.delete("alice_id")
```

### Async Collection Operations

```python
async def manage_users():
    collection = JsonCollection("data/users", model=User)
    
    # Async operations with built-in locking
    await collection.async_update("alice_id", user_data)
    all_users = await collection.async_get_all()
    await collection.async_delete("alice_id")

asyncio.run(manage_users())
```

## Key Concepts

### Type Safety

All data is validated with Pydantic models, providing full IDE support and compile-time type checking.

```python
db = JsonDatabase("config.json", MyConfig)
config = db.get_database()
config.api_key  # IDE autocomplete, full type information
```

### Automatic Migrations

Update your model schema without manual migration scripts. Old data automatically migrates to new versions.

See [ARCHITECTURE.md](./ARCHITECTURE.md#migrations) for detailed migration patterns and examples.

### Simple, Predictable API

**JsonDatabase** (single entity):
- `get_database()` → Read current state
- `update_database(data)` → Write and persist
- `async_get_database()` / `async_update_database()` → Async versions

**JsonCollection** (entity collections):
- `get(key)` → Retrieve entity by key (returns JsonDatabase instance)
- `update(key, data)` → Create or update entity
- `delete(key)` → Remove entity
- `list_keys()` → Get all entity keys
- `get_all()` / `update_all()` → Bulk operations
- `async_*` variants for all operations

## Project Structure

For projects using multiple data models and collections:

```
my_project/
├── src/
│   ├── models/
│   │   ├── __init__.py
│   │   ├── user.py
│   │   └── settings.py
│   └── main.py
└── data/
    ├── app_settings.json          # JsonDatabase
    ├── users/                     # JsonCollection
    │   ├── user_1.json
    │   ├── user_2.json
    │   └── user_3.json
    └── sessions/                  # JsonCollection
        ├── session_abc.json
        └── session_def.json
```

**Example: models/user.py**

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

# Export latest version
User = UserV2
```

**Example: src/main.py**

```python
from pathlib import Path
from jays_tools.json_collection import JsonCollection
from jays_tools.json_database import JsonDatabase
from src.models.user import User

# Setup directories
DATA_DIR = Path("data")
DATA_DIR.mkdir(exist_ok=True)

# Single database for app settings
settings_db = JsonDatabase(DATA_DIR / "app_settings.json", AppSettings)

# Collection for managing users
users_collection = JsonCollection(DATA_DIR / "users", model=User)

def main():
    # Work with collection
    user = User(name="Alice", email="alice@example.com")
    users_collection.update("user_alice", user)
    
    # List all users
    all_keys = users_collection.list_keys()
    print(f"Total users: {len(all_keys)}")
```

## Learning Resources

- [Architecture & Design](./ARCHITECTURE.md) — Internal structure, concurrency model, and design patterns
- [Design Philosophy](./PHILOSOPHY.md) — Inspiration and principles behind JsonDatabase and JsonCollection
- [API Reference](./API.md) — Detailed method documentation and type signatures

## Testing

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run all 91 tests
pytest tests/ -v

# Run with coverage
pytest --cov=src tests/
```

91 tests total: 39 for JsonDatabase, 52 for JsonCollection.

## License

MIT - See LICENSE file for details
