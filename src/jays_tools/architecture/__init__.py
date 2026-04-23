"""jays_tools Clean Architecture Framework.

Type-safe architectural layers with TypedDict dependency injection.

CORE EXPORTS:
- Adapter, Repository, Service, DomainUseCase, UseCase (layers)
- DomainModel, RequestDTO, ResponseDTO, AdapterModel (model types)

QUICK START:
```python
from jays_tools.architecture import DomainModel, DomainUseCase, RequestDTO

# Define domain model
class Profile(DomainModel):
    user_id: int
    name: str

# Define domain usecase
class RecalculateStats(DomainUseCase):
    @classmethod
    def init(cls):
        # Wire dependencies
        return cls(repos={...}, services={...}, adapters={})
    
    async def execute(self, user_id: int) -> Profile:
        # Business logic
        pass

# Use it
profile = await RecalculateStats.init().execute(123)
```

See MODELS.md for model organization patterns.
"""

from jays_tools.architecture.base import (
    Adapter,
    Repository,
    Service,
    DomainUseCase,
    UseCase,
)
from jays_tools.architecture.models import (
    DomainModel,
    AggregateRoot,
    RequestDTO,
    ResponseDTO,
    AdapterModel,
)

__all__ = [
    "Adapter",
    "Repository",
    "Service",
    "DomainUseCase",
    "UseCase",
    "DomainModel",
    "AggregateRoot",
    "RequestDTO",
    "ResponseDTO",
    "AdapterModel",
]

