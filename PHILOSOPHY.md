# Philosophy

Why these tools exist and the reasoning behind them.

## The Starting Point

I needed simple ways to persist data in my projects without heavyweight frameworks.

**The spectrum of options:**

**Heavy**: SQLAlchemy, Django ORM, PostgreSQL (powerful but overkill for local app data)
**Lightweight**: TinyDB, pickle, shelve (simple but completely untyped, no validation)
**Middle**: SQLModel, Tortoise ORM (better typing but still complex)

**What I needed**: Type safety, validation, automatic migrations, no servers.

## The Evolution

### 1. JsonDatabase: Type Safety for JSON

TinyDB showed that simple file-based storage works well for single-entity persistence.

**TinyDB had**: Simple API, no server needed, file-based, lightweight
**TinyDB lacked**: Type safety, validation, automatic migrations, IDE support

JsonDatabase adds Pydantic's type safety and validation.

### 2. JsonCollection: Distributed Storage

Reading the entire app state file became slow as projects grew. Even with caching, the full-file read was a bottleneck.

Solution: Store each entity as its own file instead of one large file.

```python
# Before: app_state.json (all users in one file)
# After: data/users/user_123.json, data/users/user_456.json (isolated reads)
```

This avoids O(n) reads—accessing one user is O(1) regardless of total user count.

### 3. SQLDatabase: Efficient Queries

Distributed files still have limits. Querying "all users with status=active" requires reading every file. Filtering in Python is slow for large datasets.

SQLite is better than files when you need queries. Simpler than SQLAlchemy/SQLModel.

SQLDatabase wraps SQLite with automatic migrations and type-safe row models.

### 4. Automatic Migrations

Schema changes are tedious: write migration scripts, track state, debug failures, revert.

Solution: Version your models, let the framework handle the transformation.

Each model version chains to the previous version. The migrate() method transforms old data to new schema.

## Design Principles

### 1. Strongly Typed, Never None

Use Pydantic for all data. Your editor knows what fields exist. Type checking catches mistakes early.

### 2. One Tool, One Job

- **JsonDatabase**: Single entity persistence
- **JsonCollection**: Multi-entity distributed storage
- **SQLDatabase**: Relational queries and complex data
- Choose the right tool for your data structure

### 3. Minimal API Surface

No query language to learn. No complex ORM syntax. Just work with your data.

```python
# JsonDatabase
state = db.get_database()
db.update_database(state)

# JsonCollection
collection.get(key)
collection.update(key, data)

# SQLDatabase
await db.select_one(Model, filter=EqualTo("field", value))
await db.insert(Model, instance)
```

### 4. Async-First

Non-blocking I/O by default. Thread pools handle blocking operations seamlessly.

### 5. Transparent

You understand what the tool does under the hood. No hidden magic. Easy to debug and reason about.

## The Architecture Framework

Without discipline, projects become tangled: services call repositories, which call adapters, which call services. Everything knows about everything.

Solution: Five layers with clear direction. Only call down, never up.

```
UseCase
  ↓
DomainUseCase
  ↓
Service, Repository, Adapter
```

This ensures:
- Services are testable without mocks (pure functions)
- Repositories are isolated and mockable
- Clear paths for refactoring
- New developers understand structure immediately

## Summary

I created these tools because I needed:
- Type safety without complexity
- Simple persistence that scales from JSON to SQLite
- Automatic migrations that work
- Architectural discipline for larger projects

They're not designed for everyone, just for projects like mine.
