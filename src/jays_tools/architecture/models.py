"""Model types for clean architecture."""


class DomainModel:
    """Single business thing used throughout your server for calculations and logic."""
    pass


class AggregateRoot(DomainModel):
    """Multiple DomainModels grouped together - use throughout your server when they change together."""
    pass


class RequestDTO:
    """API request format - what you receive."""
    pass


class ResponseDTO:
    """API response format - what you send back."""
    pass


class AdapterModel:
    """How data is stored in database or external service."""
    pass
