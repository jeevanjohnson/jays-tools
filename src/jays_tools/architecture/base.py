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


class Adapter:
    """Wraps external libraries and APIs."""
    pass


class Repository:
    """Data access layer - if it touches the filesystem, database, or any I/O, it belongs here."""
    pass


class Service:
    """Pure math and calculations - just raw arithmetic, no I/O, no files."""
    pass


class Adapters:
    """Container for all adapters."""
    pass


class Repositories:
    """Container for all repositories."""
    pass


class Services:
    """Container for all services."""
    pass


class DomainUseCase:
    """Orchestrates services, repositories, and adapters (shared across entry-points)."""
    _required_attrs = ('repositories', 'services', 'adapters')

    def __init_subclass__(cls, **kwargs) -> None:
        super().__init_subclass__(**kwargs)
        original_init = cls.__dict__.get('__init__')

        def checked_init(self, *args, **kwargs):
            if original_init is not None:
                original_init(self, *args, **kwargs)

            missing = [a for a in cls._required_attrs if not hasattr(self, a)]
            if missing:
                raise TypeError(
                    f"{cls.__name__}.__init__ must assign: {', '.join(missing)}"
                )

        cls.__init__ = checked_init


class DomainUseCases:
    """Container for all domain use cases."""
    pass


class UseCase:
    """Entry-point specific orchestration - formats response for specific client."""
    _required_attrs = ("domains",)

    def __init_subclass__(cls, **kwargs) -> None:
        super().__init_subclass__(**kwargs)
        original_init = cls.__dict__.get('__init__')

        def checked_init(self, *args, **kwargs):
            if original_init is not None:
                original_init(self, *args, **kwargs)

            missing = [a for a in cls._required_attrs if not hasattr(self, a)]
            if missing:
                raise TypeError(
                    f"{cls.__name__}.__init__ must assign: {', '.join(missing)}"
                )

        cls.__init__ = checked_init


class UseCases:
    """Container for all use cases."""
    pass
