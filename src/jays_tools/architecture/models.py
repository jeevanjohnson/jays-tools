"""Model types for clean architecture."""

from abc import ABC


class DomainModel(ABC):
    """Single business thing used throughout your server for calculations and logic."""
    pass


class AggregateRoot(DomainModel, ABC):
    """Multiple DomainModels grouped together - use throughout your server when they change together."""
    pass


class RequestDTO(ABC):
    """API request format - what you receive."""
    pass


class ResponseDTO(ABC):
    """API response format - what you send back."""
    pass


class AdapterModel(ABC):
    """How data is stored in database or external service."""
    pass


__all__ = [
    "DomainModel",
    "AggregateRoot",
    "RequestDTO",
    "ResponseDTO",
    "AdapterModel",
]