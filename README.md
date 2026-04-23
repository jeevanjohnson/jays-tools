# Jays Tools

Utilities for data persistence and application architecture that I use in my projects.

See [PHILOSOPHY.md](./PHILOSOPHY.md) for the reasoning behind each tool.

## Installation

```bash
pip install jays-tools
```

## Features

### JsonDatabase
Single-entity JSON storage with Pydantic validation and automatic migrations.

**Quick example**:
```python
from jays_tools.json_database import JsonDatabase
from jays_tools.json_database.models import MigratableModel

class AppSettings(MigratableModel):
    debug: bool = False
    api_key: str = ""

db = JsonDatabase("settings.json", AppSettings)
settings = db.get_database()
settings.debug = True
db.update_database(settings)
```

### JsonCollection
Directory-based entity collections for distributed file storage and faster reads.

**Quick example**:
```python
from jays_tools.json_collection import JsonCollection
from jays_tools.json_database.models import MigratableModel

class User(MigratableModel):
    name: str = ""
    email: str = ""

collection = JsonCollection("data/users", model=User)
collection.update("user_123", User(name="Alice", email="alice@example.com"))
user = collection.get("user_123").get_database()
```

### SQLDatabase
Async SQLite database with type-safe row models and automatic migrations.

**Quick example**:
```python
from jays_tools.sql_database import SQLDatabase, MigratableRow

class User(MigratableRow):
    name: str = ""
    email: str = ""

db = SQLDatabase("app.db", [User])
await db.initialize()

user = User(name="Alice", email="alice@example.com")
await db.insert(User, user)

result = await db.select_one(User, filter=EqualTo("email", "alice@example.com"))
```

### Clean Architecture Framework
Five disciplined layers with type-safe dependency injection.

**Layers**:
- **Service**: Pure business logic (calculations, validation)
- **Repository**: Data access (files, databases, I/O)
- **Adapter**: External integrations (APIs, services)
- **DomainUseCase**: Business workflow orchestration
- **UseCase**: Entry-point specific formatting (HTTP, CLI, etc.)

**Quick example**:
```python
from typing import TypedDict
from jays_tools.architecture import Service, Repository, DomainUseCase

class ValidationService(Service):
    def validate_email(self, email: str) -> bool:
        return "@" in email

class UserRepository(Repository):
    async def save_user(self, name: str, email: str) -> None:
        # Persist user
        pass

class UserRepos(TypedDict):
    users: UserRepository

class UserServices(TypedDict):
    validation: ValidationService

class CreateUserUseCase(DomainUseCase[UserRepos, UserServices, dict]):
    @classmethod
    def init(cls):
        return cls(
            repos={"users": UserRepository()},
            services={"validation": ValidationService()},
            adapters={}
        )
    
    async def execute(self, name: str, email: str):
        if not self.services["validation"].validate_email(email):
            raise ValueError("Invalid email")
        await self.repos["users"].save_user(name, email)
        return {"name": name, "email": email}
```

## Core Features

### Type Safety
All utilities leverage Pydantic for validation. Your editor knows what fields exist and what types they have.

### Automatic Migrations  
Update your schema without migration scripts. Old data automatically transforms to new versions.

### Async Throughout
All I/O operations are async-first. Non-blocking by default.

## Which Tool to Use

| Use case | Tool |
|----------|------|
| App config/state | JsonDatabase |
| Multiple entities | JsonCollection |
| Queries and filtering | SQLDatabase |
| Code structure | Architecture Framework |

## Documentation

- **[PHILOSOPHY.md](./PHILOSOPHY.md)** — Why these tools exist and design decisions

## Common Patterns

### File Reading + Parsing
```python
# Repository handles I/O
class FileRepository(Repository):
    async def read_csv(self, path: str) -> str:
        with open(path) as f:
            return f.read()

# Service handles logic
class CSVParsingService(Service):
    def parse_csv(self, raw: str) -> list[dict]:
        lines = raw.strip().split('\n')
        headers = lines[0].split(',')
        return [dict(zip(headers, line.split(','))) for line in lines[1:]]

# DomainUseCase orchestrates
class ImportUseCase(DomainUseCase):
    async def execute(self, path: str):
        raw = await self.repos["files"].read_csv(path)
        parsed = self.services["parsing"].parse_csv(raw)
        # Process parsed data
```

### External API Integration
```python
# Adapter wraps service
class PaymentAdapter(Adapter):
    async def charge(self, amount: float, token: str) -> dict:
        response = await requests.post("https://payment-api.com/charge", ...)
        return response.json()

# Service validates
class PaymentService(Service):
    def validate_amount(self, amount: float) -> bool:
        return amount > 0

# DomainUseCase coordinates
class ProcessOrderUseCase(DomainUseCase):
    async def execute(self, order_id: int, amount: float, token: str):
        if not self.services["payment"].validate_amount(amount):
            raise ValueError("Invalid amount")
        result = await self.adapters["payment"].charge(amount, token)
        # Record payment
```

### SQL Database with Filtering
```python
from jays_tools.sql_database import EqualTo, Like, LessThan

# Find users by email
user = await db.select_one(User, filter=EqualTo("email", "alice@example.com"))

# Find users with names starting with "Al"
users = await db.select_all(User, filter=Like("name", "Al%"))

# Find users with ID less than 10
recent = await db.select_all(User, filter=LessThan("user_id", 10))

# Combine filters
from jays_tools.sql_database import GreaterThan
filter_obj = EqualTo("status", "active") & GreaterThan("user_id", 100)
active_users = await db.select_all(User, filter=filter_obj)
```

## Testing

Each layer is independently testable:

```python
# Test service (no mocks needed)
def test_validate_email():
    service = ValidationService()
    assert service.validate_email("test@example.com")

# Test repository (mock storage)
@pytest.mark.asyncio
async def test_save_user(tmp_path):
    repo = UserRepository(db)
    await repo.save_user(user)
    saved = await repo.get_user(user.id)
    assert saved.email == user.email

# Test usecase (integration)
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
