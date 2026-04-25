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

from abc import ABC, abstractmethod
from typing import Generic, Mapping, TypeAlias, TypeVar

T_Repositories = TypeVar("T_Repositories", bound=Mapping)
T_Services = TypeVar("T_Services", bound=Mapping)
T_Adapters = TypeVar("T_Adapters", bound=Mapping)
T_DomainUseCases = TypeVar("T_DomainUseCases", bound=Mapping)

NoRepositories: TypeAlias = dict
NoServices: TypeAlias = dict
NoAdapters: TypeAlias = dict


class Adapter(ABC):
    """Wraps external libraries and APIs."""

    pass


class Repository(ABC):
    """Data access layer - if it touches the filesystem, database, or any I/O, it belongs here."""

    pass


class Service(ABC):
    """Pure math and calculations - just raw arithmetic, no I/O, no files."""

    pass


class DomainUseCase(Generic[T_Repositories, T_Services, T_Adapters]):
    """Orchestrates services, repositories, and adapters (shared across entry-points)."""

    repositories: T_Repositories | NoRepositories
    services: T_Services | NoServices
    adapters: T_Adapters | NoAdapters

    def __init__(
        self,
        repositories: T_Repositories | None,
        services: T_Services | None,
        adapters: T_Adapters | None,
    ) -> None:
        self.repositories = repositories or NoRepositories()
        self.services = services or NoServices()
        self.adapters = adapters or NoAdapters()

    @classmethod
    @abstractmethod
    def init(cls) -> "DomainUseCase":
        """Initialize and return instance with all dependencies wired.

        Subclasses MUST implement this to explicitly declare how to create
        their adapters, repositories, and services.

        Example:
        ```python
        class RecalculateStats(DomainUseCase[UserRepositories, UserServices, NoAdapters]):
            @classmethod
            def init(cls) -> "RecalculateStats":
                repositories: UserRepositories = {
                    "users": JsonUserRepository("users.json"),
                }
                services: UserServices = {
                    "rank_calc": RankCalculator(),
                }
                return cls(repositories, services, NoAdapters())
        ```
        """
        pass


class UseCase(Generic[T_DomainUseCases]):
    """Entry-point specific orchestration - formats response for specific client."""

    def __init__(self, domain: T_DomainUseCases) -> None:
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
