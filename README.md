# Jays Tools

Utilities for data persistence and application architecture that I use in my projects.

## Quick Start

```bash
pip install jays-tools
```

## Overview

| Need | Tool |
|------|------|
| App config/state | **JsonDatabase** — Single-entity JSON storage with validation |
| Multiple entities | **JsonCollection** — File-based distributed storage |
| Complex queries | **SQLDatabase** — Type-safe SQLite with filtering |
| Code structure | **Architecture Framework** — Five disciplined layers |
| Service lifecycle | **Service Management** — Startup/shutdown coordination |

Read [PHILOSOPHY.md](./PHILOSOPHY.md) to understand the design reasoning.

## Features

### JsonDatabase
Single-entity JSON storage with Pydantic validation and automatic migrations.

```python
from jays_tools.json_database import JsonDatabase
from jays_tools.json_database.models import MigratableModel

class AppSettings(MigratableModel):
    debug: bool = False

db = JsonDatabase("settings.json", AppSettings)
settings = db.get_database()
settings.debug = True
db.update_database(settings)
```

### JsonCollection
Directory-based entity collections for distributed file storage and faster reads.

```python
from jays_tools.json_collection import JsonCollection
from jays_tools.json_database.models import MigratableModel

class User(MigratableModel):
    name: str = ""
    email: str = ""

collection = JsonCollection("data/users", model=User)
collection.update("user_123", User(name="Alice", email="alice@example.com"))
```

### SQLDatabase
Async SQLite database with type-safe row models and automatic migrations.

```python
from jays_tools.sql_database import SQLDatabase, EqualTo

# Initialize with table models
db = SQLDatabase("app.db", tables=[User, Post])
await db.initialize()

# Insert
user = User(name="Alice", email="alice@example.com")
await db.insert(user)

# Find with filters
results = await db.find(User, EqualTo("email", "alice@example.com"))
for user in results:
    print(user.name)
```

### Clean Architecture Framework
Five disciplined layers with type-safe dependency injection. Separate concerns into:
- **Service**: Business logic (validation, calculations)
- **Repository**: Data access (I/O, persistence)
- **Adapter**: External integrations (APIs)
- **DomainUseCase**: Workflow orchestration
- **UseCase**: Entry-point formatting (HTTP, CLI)

```python
from jays_tools.architecture import Service, Repository, DomainUseCase

class CreateUserUseCase(DomainUseCase):
    async def execute(self, name: str, email: str):
        if not self.services["validation"].validate_email(email):
            raise ValueError("Invalid email")
        await self.repos["users"].save_user(name, email)
        return {"name": name, "email": email}
```

### Service Management
Lifecycle management for long-running services with coordinated startup and shutdown.

**Structure**:
```
server/
├── __init__.py
└── service.py

main.py
```

**In `server/service.py`**:
```python
from jays_tools.services import Service, ReadinessSignal

def main(readiness_signal: ReadinessSignal):
    print("Starting server...")
    readiness_signal.set()

def shutdown():
    print("Shutting down server...")

def ServerService() -> Service:
    return Service(
        name="ServerService",
        start=main,
        stop=shutdown,
    )
```

**In `main.py`**:
```python
from jays_tools.services import start_services, join_services, stop_services
from server.service import ServerService

if __name__ == "__main__":
    services = [ServerService()]
    start_services(services)
    join_services(services)
    stop_services(services)
```

## Core Principles

**Type Safety**: All utilities leverage Pydantic for validation. Your editor knows what fields exist and their types.

**Automatic Migrations**: Update schemas without migration scripts. Old data automatically transforms to new versions.

**Async-First**: All I/O operations are async-first for non-blocking execution.

**Minimal APIs**: Simple, predictable interfaces. No complex query languages or hidden magic.

## Documentation

- **[PHILOSOPHY.md](./PHILOSOPHY.md)** — Design reasoning and evolution of each tool

## Common Patterns

### Layered Architecture
Organize code with clear separation: Repositories handle I/O, Services handle logic, UseCases coordinate.

```python
# Repository: I/O
class FileRepository(Repository):
    async def read_csv(self, path: str) -> str:
        with open(path) as f:
            return f.read()

# Service: Logic
class CSVParsingService(Service):
    def parse_csv(self, raw: str) -> list[dict]:
        lines = raw.strip().split('\n')
        headers = lines[0].split(',')
        return [dict(zip(headers, line.split(','))) for line in lines[1:]]

# DomainUseCase: Orchestration
class ImportUseCase(DomainUseCase):
    async def execute(self, path: str):
        raw = await self.repos["files"].read_csv(path)
        parsed = self.services["parsing"].parse_csv(raw)
```

### Database Queries
Use filter objects to query SQLDatabase:

```python
from jays_tools.sql_database import EqualTo, Like, GreaterThan

# Simple filters
results = await db.find(User, EqualTo("email", "alice@example.com"))
results = await db.find(User, Like("name", "Al%"))

# Combined filters
active_users = await db.find(
    User, 
    EqualTo("status", "active") & GreaterThan("user_id", 100)
)
```

## Testing

Each layer is independently testable without complex mocks:

```python
# Service test (pure function)
def test_validate_email():
    service = ValidationService()
    assert service.validate_email("test@example.com")

# UseCase integration test
@pytest.mark.asyncio
async def test_create_user_flow():
    usecase = CreateUserUseCase.init()
    result = await usecase.execute("Alice", "alice@example.com")
    assert result["email"] == "alice@example.com"
```

## Project Structure Example

```
my_app/
├── src/
│   ├── models/
│   │   ├── domain.py        # DomainModel, AggregateRoot
│   │   ├── requests.py      # RequestDTO
│   │   ├── responses.py     # ResponseDTO
│   │   └── database.py      # AdapterModel, MigratableRow
│   ├── services/
│   │   └── user.py          # UserService
│   ├── repositories/
│   │   └── user.py          # UserRepository
│   ├── adapters/
│   │   └── payment.py       # PaymentAdapter
│   ├── domain_usecases/
│   │   └── create_user.py   # CreateUserUseCase
│   ├── usecases/
│   │   └── http/
│   │       └── create_user.py  # HTTP entry point
│   └── main.py
└── tests/
    ├── test_services.py
    ├── test_repositories.py
    ├── test_usecases.py
    └── test_integration.py
```

## License

MIT
