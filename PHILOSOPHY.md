# Design Philosophy

Why do JsonDatabase and JsonCollection exist, and what problems do they solve?

## The Problem

### Complex Tools for Simple Problems

When I needed to persist application data, I faced a spectrum of options:

**Heavy solutions**: SQLAlchemy, Django ORM, PostgreSQL
- Powerful but overkill for local data
- Complex setup for simple use cases
- Require spinning up servers
- Too many features you don't need

**Lightweight solutions**: TinyDB, shelve, pickle
- Simple and lightweight
- Completely untyped
- No validation, no IDE support
- Migrations are manual nightmares

**Middle ground**: SQLModel, Tortoise ORM
- Better typing than raw SQL
- Still require database servers
- Configuration overhead
- Workarounds for simple cases

### Core Frustrations

1. **Type system gap**: Solutions either have no typing or require verbose configurations
2. **Schema validation**: Writing exhaustive tests just to validate schema changes
3. **Migration burden**: Every schema change requires manual migration scripts
4. **Single-entity vs. collections**: Most tools assume one data structure, not collections of items
5. **Over-engineering**: Most solutions designed for servers, but I just need local app data

## The Inspiration

The tool that inspired jays-tools most was **TinyDB**.

### What I Loved About TinyDB

- Dead simple API: read, write, query
- Perfect for single-user local data
- No server setup needed
- File-based, easily tracked in git
- Great documentation
- Lightweight and understandable

### What I Wanted to Add

- **Full type support** with IDE autocomplete and type checking
- **Pydantic validation** for free schema checking
- **Automatic migrations** when schema changes
- **Collections support** for managing multiple entities
- **Async operations** without blocking event loops
- **Transparency** — understands what the tool does under the hood

## Design Principles

### 1. Strongly Typed, Never None

```python
# With jays-tools
db = JsonDatabase("app.json", AppState)
state = db.get_database()
state.config.debug  # IDE knows the type, no guessing
```

Pydantic validates every read and write. You never wonder what fields exist or what their types are.

### 2. Two Components, One Vision

**JsonDatabase** for single entities:
- App configuration and state
- Settings and preferences
- Unified data structures

**JsonCollection** for entity collections:
- User profiles and documents
- Session management
- Any collection of similar items

Both use the same validation, migration, and async patterns. Pick the right tool for your data structure.

### 3. Minimal API Surface

**JsonDatabase operations**:
- `get_database()` — Read current state
- `update_database(data)` — Write and persist

**JsonCollection operations**:
- `get(key)` / `update(key, data)` / `delete(key)` — CRUD
- `list_keys()` / `get_all()` — Queries
- `async_*` variants for all operations

No query language to learn, no complex ORM syntax. Just work with your data.

### 4. Predictable Lifecycle

```python
# Simple, understandable flow:
current = db.get_database()        # Read from cache/disk
current.config.setting = "value"   # Mutate in memory
db.update_database(current)        # Persist changes
# Done. No hidden side effects.
```

Easy to reason about, easy to debug, easy to test.

### 5. Transparent Migrations

Schema changes should be seamless:

```python
# V1: Basic user
class UserV1(MigratableModel):
    name: str = ""

# V2: Add email
class UserV2(MigratableModel, previous_model=UserV1):
    name: str = ""
    email: str = ""
    
    @staticmethod
    def migrate_from_previous(data):
        data["email"] = ""
        return data

# Loading old V1 data with V2 → automatic migration
```

No migration scripts, no downtime, no manual work.

### 6. Thread-Safe by Design

Both components use reentrant locks and atomic file writes:

- In-process operations are serialized and safe
- File corruption is prevented via temp-file-then-rename pattern
- Async operations are properly coordinated with locks
- Honest about limitations (no multi-process support)

### 7. Safe-by-Default Validation

Corrupted or incompatible JSON fails loudly with clear errors:

```python
# If JSON doesn't match your model, you know immediately:
ValueError: Failed to read database file app.json due to validation error:
- config: field required
- version: value is not a valid integer
```

Safe defaults prevent silent data corruption.

### 8. Practical Over Perfect

jays-tools is **not** trying to be:
- A distributed database
- A high-performance data warehouse
- A replacement for production databases
- Suitable for multi-process concurrency

jays-tools **is** perfect for:
- Local application data and configuration
- Prototypes and simple projects
- Testing and development
- Embedded data in standalone applications
- Git-friendly persistent storage

**Honest about limitations** beats pretending to do everything.

## When to Use jays-tools

### Perfect For

✅ **Local app data**: Configuration, user preferences, session data  
✅ **Prototypes**: Quick projects where speed matters  
✅ **Testing**: Temporary data stores in test suites  
✅ **Embedded storage**: Desktop apps needing persistence  
✅ **Git-friendly data**: Configuration in version control  
✅ **Learning**: Simple enough to understand completely  

### Not a Good Fit

❌ **Production services**: Multiple users, high concurrency → use PostgreSQL/MongoDB
❌ **Big data**: Gigabytes of data → use data warehouses  
❌ **Real-time collaboration**: Multiple writers → use proper databases  
❌ **Mission-critical systems**: Need ACID guarantees → use PostgreSQL/MySQL
## Comparisons to Alternatives

### vs. TinyDB

| Aspect | jays-tools | TinyDB |
|--------|---|---|
| **Typing** | Full (Pydantic) | None |
| **Validation** | Automatic | Manual |
| **Migrations** | Automatic | Manual |
| **Collections** | Built-in support | Manual querying |
| **Async** | Full support | Limited |
| **Learning Curve** | Very low | Very low |

**Summary**: "TinyDB with modern Python typing, automatic migrations, and collections support."

### vs. SQLAlchemy

| Aspect | jays-tools | SQLAlchemy |
|--------|---|---|
| **Typing** | Full (Pydantic) | Partial/Complex |
| **Setup** | None required | Database setup required |
| **Query Language** | N/A (Python objects) | SQL via ORM |
| **Transactions** | N/A (single-process) | Full ACID support |
| **Scaling** | Doesn't scale | Scales well |
| **Learning Curve** | Very low | Steep |

**Summary**: SQLAlchemy is "for when you need a real database." jays-tools is "for when you don't."

### vs. SQLModel

| Aspect | jays-tools | SQLModel |
|--------|---|---|
| **Typing** | Simple (Pydantic) | Complex (Pydantic + SQL) |
| **Setup** | None | Database setup required |
| **Purpose** | Local file storage | Server databases |
| **Learning Curve** | Low | Medium-High |

**Summary**: SQLModel tries to do both SQL and ORM; jays-tools does one thing well.

### vs. MongoDB/Firebase

| Aspect | jays-tools | MongoDB/Firebase |
|--------|---|---|
| **Setup** | None | Cloud/server setup |
| **Typing** | Full | Partial |
| **Cost** | Free | Pay-per-use |
| **Privacy** | Local files | Cloud-hosted |
| **Scaling** | Doesn't scale | Scales indefinitely |

**Summary**: Cloud databases are great for collaborative multi-user apps. jays-tools is for local single-process data.

## Design Decisions Explained

### Why file-based and not in-memory?

**Pros of file-based**:
- Data persists across application restarts
- Easy to backup, version control, debug
- No database server to manage
- Works offline

**Cons of file-based**:
- Slower than in-memory
- Not suitable for high-frequency operations
- Doesn't support network access

**Decision**: File-based is the right choice for local application data and prototypes.

### Why JSON and not binary?

**Pros of JSON**:
- Human-readable
- Easy to debug and inspect
- Version control friendly
- Ecosystem of tools
- Language-agnostic

**Cons of JSON**:
- Larger file size than binary
- Slower to parse than binary

**Decision**: Readability and debuggability matter more than size for local app data.

### Why Pydantic and not dataclasses?

**Pros of Pydantic**:
- Built-in validation
- Serialization/deserialization
- Clear error messages
- Strict types by default

**Cons of Pydantic**:
- Adds a dependency
- Slightly slower than dataclasses

**Decision**: Validation and clear errors are critical for data persistence.

### Why separate JsonDatabase and JsonCollection?

Different data patterns need different components:

- **JsonDatabase**: For single, unified data structures (app state, config)
- **JsonCollection**: For managing collections of similar items (users, documents)

Both share the same underlying principles but expose different APIs suited to their use cases.

### Why JSON, Not YAML/TOML/MessagePack?

**JSON**: Universal, human-readable, standard library support, no external dependencies.

**YAML/TOML**: Nice syntax, but parsing is slower and adds complexity.

**MessagePack**: Compact and fast, but not human-readable (bad for debugging).

### Why Context Manager was Removed?

The original design used context managers:
```python
# Old API (removed)
with db as data:
    data.users.append(user)
    db.set(data)
```

Simplified to:
```python
# New API (clearer)
data = db.get_database()
data.users.append(user)
db.update_database(data)
```

**Why**: More explicit, easier to reason about, no hidden lifecycle. Get → Mutate → Update. Clear as day.

### Why Not a Query Language?

```python
# Some databases do this:
result = db.query().filter(age > 18).all()

# JsonDatabase assumes you just use Python:
result = [u for u in users.items if u.age > 18]
```

**Why**: You already know Python. Adding a query DSL is complexity for no benefit. Your data structure is small enough to work with directly.

### Why Deep Copies?

Every returned value is a deep copy:
```python
data1 = db.get_database()
data1.users[0].name = "Hacked!"
data2 = db.get_database()
assert data2.users[0].name == "Alice"  # Original unchanged
```

**Why**: Prevents accidental mutations of internal state. Simple to reason about. Safe-by-default.

## Philosophy Summary

JsonDatabase is built on the belief that:

1. **Simple is better than complex** — Most projects don't need a full database
2. **Typing matters** — Modern Python should have great IDE support
3. **Migrations are inevitable** — Make them automatic, not manual
4. **Honest scope** — Don't pretend to do everything, do one thing well
5. **Developer experience** — The tool should be enjoyable to use

It fills a gap: more powerful than hand-rolled JSON parsing, simpler than a real database. Perfect for the projects in between.
