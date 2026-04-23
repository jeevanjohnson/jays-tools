"""Clean Architecture framework for jays_tools.

Core Principles:
- Everything should ONLY call DOWN: Layers only depend on layers below them, never above.
- Never call UP: Lower layers must never know about or call higher layers.
- Testability: Each layer is isolated and independently testable.
- Good separation: Each layer has one clear responsibility.
- Reduce redundancy: Don't duplicate logic—keep it in one place.

Layer Stack (top to bottom):
    UseCase (application-specific orchestration)
        ↓ depends on (typed)
    DomainUseCase (business logic orchestration)
        ↓ depends on (typed)
    Service (pure calculations) + Repository (data access) + Adapter (external integration)

All layers are type-safe - mypy/Pylance will catch violations at development time.
"""

from typing import Generic, TypeVar
from abc import ABC, abstractmethod

# Type variables for generic layers
# Note: No bound=dict constraint - TypedDict is structural, not a dict subclass
T_Repos = TypeVar('T_Repos')
T_Services = TypeVar('T_Services')
T_Adapters = TypeVar('T_Adapters')
T_DomainUseCases = TypeVar('T_DomainUseCases')


class Adapter(ABC):
    """Wraps external libraries and APIs."""
    pass


class Repository(ABC):
    """Data access layer - if it touches the filesystem, database, or any I/O, it belongs here."""
    pass


class Service(ABC):
    """Pure math and calculations - just raw arithmetic, no I/O, no files."""
    pass


class DomainUseCase(Generic[T_Repos, T_Services, T_Adapters]):
    """Orchestrates services, repos, and adapters (shared across entry-points)."""
    
    def __init__(
        self,
        repos: T_Repos,
        services: T_Services,
        adapters: T_Adapters
    ):
        self.repos = repos
        self.services = services
        self.adapters = adapters
    
    @classmethod
    @abstractmethod
    def init(cls) -> "DomainUseCase":
        """Initialize and return instance with all dependencies wired.
        
        Subclasses MUST implement this to explicitly declare how to create
        their adapters, repositories, and services.
        
        Example:
        ```python
        class RecalculateStats(DomainUseCase[UserRepos, UserServices, {}]):
            @classmethod
            def init(cls) -> "RecalculateStats":
                repos: UserRepos = {
                    "users": JsonUserRepository("users.json"),
                }
                services: UserServices = {
                    "rank_calc": RankCalculator(),
                }
                return cls(repos, services, {})
        ```
        """
        pass


class UseCase(Generic[T_DomainUseCases]):
    """Entry-point specific orchestration - formats response for specific client."""
    
    def __init__(self, domain: T_DomainUseCases):
        self.domain = domain
    
    @classmethod
    @abstractmethod
    def init(cls) -> "UseCase":
        """Initialize and return instance with all domain usecases wired.
        
        Subclasses MUST implement this to explicitly declare which domain
        usecases they depend on.
        
        Example:
        ```python
        class SubmitScoreUseCase(UseCase[ServerDomainUseCases]):
            @classmethod
            def init(cls) -> "SubmitScoreUseCase":
                domain_usecases: ServerDomainUseCases = {
                    "recalculate": RecalculateStats.init(),
                }
                return cls(domain_usecases)
        ```
        """
        pass


__all__ = [
    "Adapter",
    "Repository",
    "Service",
    "DomainUseCase",
    "UseCase",
]
