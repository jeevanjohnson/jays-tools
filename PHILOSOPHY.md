# Philosophy

Why these tools exist and the reasoning behind them.

## The Problem

I needed simple ways to persist data without heavyweight frameworks.

**The spectrum of options**:
- **Heavy**: SQLAlchemy, Django ORM, PostgreSQL → Overkill for local app data
- **Lightweight**: TinyDB, pickle, shelve → Simple but completely untyped
- **Middle**: SQLModel, Tortoise ORM → Better typing but complex

**What I needed**: Type safety, validation, automatic migrations, no servers.

## The Evolution

### 1. JsonDatabase: Type Safety for JSON

TinyDB was simple and file-based, but lacked type safety and validation.

**JsonDatabase adds**: Pydantic validation, IDE support, automatic migrations.

### 2. JsonCollection: Distributed Storage

Reading an entire app state file became slow as projects grew. Bottleneck: every access requires a full-file read.

**Solution**: Store each entity as its own file instead of one large file.

```python
# Before: app_state.json (all users in one file)
# After: data/users/user_123.json, data/users/user_456.json (isolated reads)
```

Result: O(1) reads instead of O(n).

### 3. SQLDatabase: Efficient Queries

Distributed files have limits. Querying "all users with status=active" requires reading every file.

**Solution**: Use SQLite for queries while keeping type safety and automatic migrations.

SQLDatabase wraps SQLite with Pydantic models and migration support.

### 4. Automatic Migrations

Schema changes are tedious: write migration scripts, track state, debug failures, revert.

**Solution**: Version your models. Let the framework handle the transformation.

Each model version implements `migrate()` to transform old data to new schema.

## Design Principles

### 1. Strongly Typed, Never None
Use Pydantic for all data. Your editor knows what fields exist. Type checking catches mistakes early.

### 2. One Tool, One Job
Pick the right tool for your data structure:
- **JsonDatabase**: Single entity persistence
- **JsonCollection**: Multi-entity distributed storage
- **SQLDatabase**: Relational queries and complex data

### 3. Minimal API Surface
No query language to learn. No complex ORM syntax. Just work with your data.

```python
db.get_database()           # JsonDatabase
db.update_database(data)    # JsonDatabase
collection.get(key)         # JsonCollection
collection.update(key, data)  # JsonCollection
```

### 4. Async-First
Non-blocking I/O by default. Thread pools handle blocking operations seamlessly.

### 5. Transparent
Easy to understand what happens under the hood. No hidden magic. Simple to debug and reason about.

## Architecture Framework

Projects become tangled without discipline: services call repositories, which call adapters, which call services. Everything knows about everything.

**Solution**: Five layers with clear direction. Only call down, never up.

```
UseCase (entry point)
  ↓
DomainUseCase (orchestration)
  ↓
Service, Repository, Adapter
```

This ensures:
- **Testability**: Services are pure functions, repositories are mockable
- **Clarity**: New developers understand structure immediately
- **Maintainability**: Clear paths for refactoring

## Summary

I created these tools because I needed:
- Type safety without complexity
- Simple persistence that scales from JSON to SQLite
- Automatic migrations that work
- Architectural discipline for larger projects

They're designed for projects like mine, not for everyone.
