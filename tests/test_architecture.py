"""Tests for jays_tools.architecture module.

Tests cover:
- Abstract base classes and instantiation rules
- Concrete implementations of layers
- Generic typing and dependency injection
- Initialization and attribute storage
- Model type hierarchy
"""

import pytest
from typing import TypedDict

from jays_tools.architecture import (
    Adapter,
    Repository,
    Service,
    DomainUseCase,
    UseCase,
    DomainModel,
    AggregateRoot,
    RequestDTO,
    ResponseDTO,
    AdapterModel,
)


# ============================================================================
# Abstract Layer Tests
# ============================================================================

class TestAdapterAbstractClass:
    """Test suite for Adapter abstract base class."""

    def test_adapter_concrete_implementation(self):
        """Concrete Adapter implementation can be instantiated."""
        class ConcreteAdapter(Adapter):
            def _abstract_marker(self) -> None:
                pass

        adapter = ConcreteAdapter()
        assert isinstance(adapter, Adapter)
        assert isinstance(adapter, ConcreteAdapter)


class TestRepositoryAbstractClass:
    """Test suite for Repository abstract base class."""

    def test_repository_concrete_implementation(self):
        """Concrete Repository implementation can be instantiated."""
        class ConcreteRepository(Repository):
            def _abstract_marker(self) -> None:
                pass

        repo = ConcreteRepository()
        assert isinstance(repo, Repository)
        assert isinstance(repo, ConcreteRepository)


class TestServiceAbstractClass:
    """Test suite for Service abstract base class."""

    def test_service_concrete_implementation(self):
        """Concrete Service implementation can be instantiated."""
        class ConcreteService(Service):
            def _abstract_marker(self) -> None:
                pass

        service = ConcreteService()
        assert isinstance(service, Service)
        assert isinstance(service, ConcreteService)


# ============================================================================
# DomainUseCase Tests
# ============================================================================

class TestDomainUseCaseInitialization:
    """Test suite for DomainUseCase initialization."""

    def test_domain_usecase_init_stores_dependencies(self):
        """DomainUseCase.__init__ stores repos, services, and adapters."""
        class TestRepos(TypedDict):
            user_repo: str

        class TestServices(TypedDict):
            calc_service: str

        repos: TestRepos = {"user_repo": "repo_instance"}
        services: TestServices = {"calc_service": "service_instance"}
        adapters: dict = {}

        class TestDomainUseCase(DomainUseCase[TestRepos, TestServices, dict]):
            @classmethod
            def init(cls):
                return cls(repos, services, adapters)

        usecase = TestDomainUseCase(repos, services, adapters)
        assert usecase.repos == repos
        assert usecase.services == services
        assert usecase.adapters == adapters

    def test_domain_usecase_init_with_empty_deps(self):
        """DomainUseCase.__init__ works with empty dependency dicts."""
        class TestDomainUseCase(DomainUseCase[dict, dict, dict]):
            @classmethod
            def init(cls):
                return cls({}, {}, {})

        usecase = TestDomainUseCase({}, {}, {})
        assert usecase.repos == {}
        assert usecase.services == {}
        assert usecase.adapters == {}

    def test_domain_usecase_init_must_return_instance(self):
        """DomainUseCase.init() must return a properly initialized instance."""
        class ProperUseCase(DomainUseCase[dict, dict, dict]):
            @classmethod
            def init(cls):
                return cls({"repo": "r1"}, {"svc": "s1"}, {"adp": "a1"})

        instance = ProperUseCase.init()
        assert instance is not None
        assert isinstance(instance, ProperUseCase)
        assert instance.repos == {"repo": "r1"}
        assert instance.services == {"svc": "s1"}
        assert instance.adapters == {"adp": "a1"}

    def test_domain_usecase_init_implementation_works(self):
        """Concrete DomainUseCase.init() implementation is callable."""
        class TestRepos(TypedDict):
            pass

        class ConcreteUseCase(DomainUseCase[TestRepos, dict, dict]):
            @classmethod
            def init(cls):
                return cls({}, {}, {})

        usecase = ConcreteUseCase.init()
        assert isinstance(usecase, ConcreteUseCase)
        assert isinstance(usecase, DomainUseCase)


class TestDomainUseCaseGenericTypes:
    """Test suite for DomainUseCase generic type parameters."""

    def test_domain_usecase_multiple_type_params(self):
        """DomainUseCase accepts multiple generic type parameters."""
        class ReposType(TypedDict):
            user: str
            product: str

        class ServicesType(TypedDict):
            calc: str

        class AdaptersType(TypedDict):
            api: str

        class MultiTypeUseCase(
            DomainUseCase[ReposType, ServicesType, AdaptersType]
        ):
            @classmethod
            def init(cls):
                repos: ReposType = {"user": "u", "product": "p"}
                services: ServicesType = {"calc": "c"}
                adapters: AdaptersType = {"api": "a"}
                return cls(repos, services, adapters)

        usecase = MultiTypeUseCase.init()
        assert len(usecase.repos) == 2
        assert len(usecase.services) == 1
        assert len(usecase.adapters) == 1


# ============================================================================
# UseCase Tests
# ============================================================================

class TestUseCaseInitialization:
    """Test suite for UseCase initialization."""

    def test_usecase_init_stores_domain(self):
        """UseCase.__init__ stores the domain usecase."""
        class TestDomainUseCases(TypedDict):
            calculate: str

        domain: TestDomainUseCases = {"calculate": "instance"}

        class TestUseCase(UseCase[TestDomainUseCases]):
            @classmethod
            def init(cls):
                return cls(domain)

        usecase = TestUseCase(domain)
        assert usecase.domain == domain

    def test_usecase_init_with_empty_domain(self):
        """UseCase.__init__ works with empty domain dict."""
        class TestUseCase(UseCase[dict]):
            @classmethod
            def init(cls):
                return cls({})

        usecase = TestUseCase({})
        assert usecase.domain == {}

    def test_usecase_init_must_return_instance(self):
        """UseCase.init() must return a properly initialized instance."""
        class ProperUseCase(UseCase[dict]):
            @classmethod
            def init(cls):
                return cls({"domain": "d1"})

        instance = ProperUseCase.init()
        assert instance is not None
        assert isinstance(instance, ProperUseCase)
        assert instance.domain == {"domain": "d1"}

    def test_usecase_init_implementation_works(self):
        """Concrete UseCase.init() implementation is callable."""
        class ConcreteUseCase(UseCase[dict]):
            @classmethod
            def init(cls):
                return cls({})

        usecase = ConcreteUseCase.init()
        assert isinstance(usecase, ConcreteUseCase)
        assert isinstance(usecase, UseCase)


class TestUseCaseGenericTypes:
    """Test suite for UseCase generic type parameters."""

    def test_usecase_single_type_param(self):
        """UseCase accepts a single generic type parameter for domain usecases."""
        class DomainUseCasesType(TypedDict):
            calculate: str
            transform: str

        domain: DomainUseCasesType = {"calculate": "c", "transform": "t"}

        class AppUseCase(UseCase[DomainUseCasesType]):
            @classmethod
            def init(cls):
                return cls(domain)

        usecase = AppUseCase.init()
        assert len(usecase.domain) == 2


# ============================================================================
# Model Type Tests
# ============================================================================

class TestDomainModelAbstractClass:
    """Test suite for DomainModel abstract base class."""

    def test_domain_model_concrete_implementation(self):
        """Concrete DomainModel implementation can be instantiated."""
        class User(DomainModel):
            def _abstract_marker(self) -> None:
                pass

        user = User()
        assert isinstance(user, DomainModel)
        assert isinstance(user, User)


class TestAggregateRootHierarchy:
    """Test suite for AggregateRoot model hierarchy."""

    def test_aggregate_root_is_domain_model(self):
        """AggregateRoot is a subclass of DomainModel."""
        assert issubclass(AggregateRoot, DomainModel)

    def test_aggregate_root_concrete_implementation(self):
        """Concrete AggregateRoot implementation can be instantiated."""
        class UserAggregate(AggregateRoot):
            def _abstract_marker(self) -> None:
                pass

        aggregate = UserAggregate()
        assert isinstance(aggregate, AggregateRoot)
        assert isinstance(aggregate, DomainModel)
        assert isinstance(aggregate, UserAggregate)


class TestRequestDTOAbstractClass:
    """Test suite for RequestDTO abstract base class."""

    def test_request_dto_concrete_implementation(self):
        """Concrete RequestDTO implementation can be instantiated."""
        class CreateUserRequest(RequestDTO):
            def _abstract_marker(self) -> None:
                pass

        request = CreateUserRequest()
        assert isinstance(request, RequestDTO)
        assert isinstance(request, CreateUserRequest)


class TestResponseDTOAbstractClass:
    """Test suite for ResponseDTO abstract base class."""

    def test_response_dto_concrete_implementation(self):
        """Concrete ResponseDTO implementation can be instantiated."""
        class UserResponse(ResponseDTO):
            def _abstract_marker(self) -> None:
                pass

        response = UserResponse()
        assert isinstance(response, ResponseDTO)
        assert isinstance(response, UserResponse)


class TestAdapterModelAbstractClass:
    """Test suite for AdapterModel abstract base class."""

    def test_adapter_model_concrete_implementation(self):
        """Concrete AdapterModel implementation can be instantiated."""
        class UserDatabaseModel(AdapterModel):
            def _abstract_marker(self) -> None:
                pass

        model = UserDatabaseModel()
        assert isinstance(model, AdapterModel)
        assert isinstance(model, UserDatabaseModel)


# ============================================================================
# Integration Tests
# ============================================================================

class TestArchitectureLayerIntegration:
    """Test suite for integrated architecture layer usage."""

    def test_full_stack_with_concrete_implementations(self):
        """Full architecture stack with all concrete implementations."""
        # Layer implementations
        class UserRepository(Repository):
            def _abstract_marker(self) -> None:
                pass

            def get_user(self, user_id: int):
                return f"user_{user_id}"

        class RankCalculator(Service):
            def _abstract_marker(self) -> None:
                pass

            def calculate_rank(self, score: int) -> str:
                return f"rank_{score}"

        class APIAdapter(Adapter):
            def _abstract_marker(self) -> None:
                pass

            def send(self, data: str) -> str:
                return f"sent_{data}"

        # Domain usecase
        class UserRepos(TypedDict):
            user: UserRepository

        class UserServices(TypedDict):
            rank: RankCalculator

        class UserAdapters(TypedDict):
            api: APIAdapter

        class RecalculateUser(DomainUseCase[UserRepos, UserServices, UserAdapters]):
            @classmethod
            def init(cls):
                repos: UserRepos = {"user": UserRepository()}
                services: UserServices = {"rank": RankCalculator()}
                adapters: UserAdapters = {"api": APIAdapter()}
                return cls(repos, services, adapters)

        # Use case
        class UpdateUserUseCase(UseCase[dict]):
            @classmethod
            def init(cls):
                return cls({"recalculate": RecalculateUser.init()})

        # Execute
        usecase = UpdateUserUseCase.init()
        assert isinstance(usecase, UseCase)
        assert "recalculate" in usecase.domain
        domain_uc = usecase.domain["recalculate"]
        assert isinstance(domain_uc, DomainUseCase)
        assert "user" in domain_uc.repos
        assert "rank" in domain_uc.services
        assert "api" in domain_uc.adapters

    def test_models_in_domain_logic_flow(self):
        """Model types form a logical flow through architecture."""
        # Request comes in
        class SubmitScoreRequest(RequestDTO):
            def _abstract_marker(self) -> None:
                pass

        # Converted to domain entity
        class PlayerScore(DomainModel):
            def _abstract_marker(self) -> None:
                pass

        # Multiple domain entities grouped
        class PlayerAggregate(AggregateRoot):
            def _abstract_marker(self) -> None:
                pass

        # Stored as adapter model
        class PlayerDatabaseRow(AdapterModel):
            def _abstract_marker(self) -> None:
                pass

        # Response sent back
        class ScoreSubmittedResponse(ResponseDTO):
            def _abstract_marker(self) -> None:
                pass

        # Verify hierarchy
        assert issubclass(PlayerAggregate, DomainModel)
        assert issubclass(PlayerScore, DomainModel)
        request = SubmitScoreRequest()
        score = PlayerScore()
        aggregate = PlayerAggregate()
        db_row = PlayerDatabaseRow()
        response = ScoreSubmittedResponse()

        assert isinstance(request, RequestDTO)
        assert isinstance(score, DomainModel)
        assert isinstance(aggregate, DomainModel)
        assert isinstance(db_row, AdapterModel)
        assert isinstance(response, ResponseDTO)


# ============================================================================
# Edge Cases and Error Handling
# ============================================================================

class TestEdgeCases:
    """Test suite for edge cases and boundary conditions."""

    def test_usecase_with_nested_domain_usecases(self):
        """UseCase can hold domain usecases that reference each other."""
        class InnerUseCase(DomainUseCase[dict, dict, dict]):
            @classmethod
            def init(cls):
                return cls({}, {}, {})

        class OuterUseCase(UseCase[dict]):
            @classmethod
            def init(cls):
                inner = InnerUseCase.init()
                return cls({"inner": inner})

        usecase = OuterUseCase.init()
        assert "inner" in usecase.domain
        assert isinstance(usecase.domain["inner"], DomainUseCase)

    def test_concrete_class_attributes_preserved(self):
        """Concrete implementations can have custom attributes."""
        class CustomService(Service):
            def _abstract_marker(self) -> None:
                pass

            def __init__(self, name: str):
                self.name = name

        service = CustomService("test_service")
        assert service.name == "test_service"

    def test_multiple_inheritance_with_models(self):
        """Model types can be extended with multiple mixins."""
        class Timestamped:
            created_at: str = "2026-04-22"

        class VersionedModel(DomainModel, Timestamped):
            def _abstract_marker(self) -> None:
                pass

        model = VersionedModel()
        assert isinstance(model, DomainModel)
        assert hasattr(model, "created_at")
