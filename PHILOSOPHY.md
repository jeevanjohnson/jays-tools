# JsonDatabase Philosophy

Why does JsonDatabase exist, and what problems does it solve?

## The Problem

### Complex Tools for Simple Problems

When I needed to persist application data, I faced a spectrum of options:

**Heavy solutions**: SQLAlchemy, Django ORM, PostgreSQL
- Powerful but overkill for local data
- Setup complexity for simple use cases
- Require spinning up servers
- Too many features you don't need

**Lightweight solutions**: TinyDB, shelve, pickle
- Simple and lightweight
- But completely untyped
- No validation, no IDE support
- Migrations are manual nightmares

**Middle ground**: SQLModel, Tortoise ORM
- Better typing than raw SQL
- Still require database servers
- Configuration overhead
- Sometimes feel hacky with workarounds

### My Frustrations

1. **Typing overhead**: Many solutions either have no typing or require verbose configurations
2. **Schema validation**: Writing exhaustive tests just to validate schema changes
3. **Migration burden**: No automatic migrations; every schema change is manual
4. **Single-process indifference**: Most databases assume multiple concurrent users, but I just need local app data

## The Inspiration

The tool that inspired JsonDatabase most was **TinyDB**.

### What I Loved About TinyDB

- Dead simple API: insert, update, query
- Perfect for single-user, local data
- No server setup needed
- File-based, easily tracked in git
- Great documentation

### What I Wanted to Add

- **Full type support** with IDE autocomplete
- **Pydantic validation** for free schema checking
- **Automatic migrations** when schema changes
- **Async support** without event loop blocking
- **Transparency** — understands what the tool does under the hood

## Design Principles

### 1. Strongly Typed, Never None

```python
# With JsonDatabase
db = JsonDatabase("users.json", Users)
users = db.get_database()
users.total  # IDE knows this is an int, no guessing
```

Pydantic validates every read and write. You never wonder what fields exist or what their types are.

### 2. Minimal API Surface

Three core operations:
- `get_database()` — Read current state
- `update_database(data)` — Write and persist
- `async_*` versions for async contexts

No query language to learn, no complex ORM syntax. Just get your data and work with it.

### 3. Predictable Lifecycle

```python
# Simple, understandable flow:
current = db.get_database()      # Read from cache/disk
current.users.append(new_user)   # Mutate in memory
db.update_database(current)      # Persist changes
# Done. No hidden side effects.
```

Easy to reason about, easy to debug, easy to test.

### 4. Transparent Migrations

Schema changes should be painless:

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

### 5. Safe-by-Default Validation

Corrupted or incompatible JSON fails loudly with clear error messages:

```python
# If JSON doesn't match your model, you know immediately:
ValueError: Failed to read database file users.json due to validation error:
- name: field required
- email: value is not a valid string
```

Safe defaults prevent silent data corruption.

### 6. Practical Over Perfect

JsonDatabase is **not** trying to be:
- A distributed database
- A high-performance data warehouse
- A replacement for production databases
- Suitable for multi-process access

JsonDatabase **is** perfect for:
- Local application data
- Configuration stores
- Single-user prototypes
- Testing and development
- Embedded data in desktop apps

**Honest about limitations** beats pretending to do everything.

## When to Use JsonDatabase

### Perfect For

✅ **Local app data**: Configuration, user preferences, session data  
✅ **Prototypes**: Quick projects where speed matters more than scale  
✅ **Testing**: Temporary data stores in test suites  
✅ **Embedded storage**: Desktop apps that need persistence  
✅ **Git-friendly data**: Configuration that goes in version control  
✅ **Learning**: Simple enough to understand completely  

### Not a Good Fit

❌ **Production services**: Multiple users, high concurrency → use PostgreSQL  
❌ **Big data**: Gigabytes of data → use data warehouses  
❌ **Real-time collab**: Multiple writers → use proper databases  
❌ **Mission-critical**: Need ACID guarantees → use PostgreSQL, MySQL  

## Comparison to Alternatives

### vs. TinyDB

| Aspect | JsonDatabase | TinyDB |
|--------|---|---|
| **Typing** | Full (Pydantic) | None |
| **Validation** | Automatic | Manual |
| **Migrations** | Automatic | Manual |
| **Query Language** | N/A (data is Python objects) | Custom query language |
| **Learning Curve** | Very low | Very low |

JsonDatabase is "TinyDB with modern Python typing and automatic migrations."

### vs. SQLAlchemy

| Aspect | JsonDatabase | SQLAlchemy |
|--------|---|---|
| **Typing** | Full | Partial |
| **Setup** | None | Database setup required |
| **Transactions** | N/A | Full support |
| **Scaling** | Doesn't scale | Scales well |
| **Learning Curve** | Very low | Steep |

SQLAlchemy is "for when you need a real database." JsonDatabase is "for when you don't."

### vs. SQLModel

| Aspect | JsonDatabase | SQLModel |
|--------|---|---|
| **Typing** | Simple (uses Pydantic) | Complex (hybrid Pydantic/SQL) |
| **Setup** | None | Database setup required |
| **Maturity** | Focused | Broad |
| **Learning Curve** | Low | Medium |

SQLModel tries to do both; JsonDatabase does one thing well.

## Design Decisions Explained

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
