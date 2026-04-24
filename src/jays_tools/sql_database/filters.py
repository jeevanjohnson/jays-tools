"""SQL query filter system with operator overloading for clean query building.

This module provides a class-based approach to building SQL filters:

    from jays_tools.sql_database.filters import Field
    
    age = Field("age")
    name = Field("name")
    
    # Create filters using operators
    await db.find(UserV1, age >= 30)
    await db.find(UserV1, (age > 25) & (age < 35))
    await db.find(UserV1, name.like("%alice%"))
    await db.find(UserV1, age.in_([25, 30, 35]))
"""

from abc import ABC, abstractmethod
from typing import Any, Generic, TypeVar


T = TypeVar("T")


class Filter(ABC):
    """Base class for all SQL filters.
    
    Subclasses implement specific filter logic and SQL generation.
    """

    @abstractmethod
    def to_sql(self) -> tuple[str, list[Any]]:
        """Convert filter to SQL WHERE clause and parameters.
        
        Returns:
            Tuple of (where_clause_sql: str, parameters: list[Any])
            where_clause_sql uses ? placeholders for parameters
        """
        pass
    
    def __and__(self, other: "Filter") -> "FilterGroup":
        """Combine filters with AND operator."""
        if not isinstance(other, Filter):
            return NotImplemented
        return FilterGroup(self, other, "AND")
    
    def __or__(self, other: "Filter") -> "FilterGroup":
        """Combine filters with OR operator."""
        if not isinstance(other, Filter):
            return NotImplemented
        return FilterGroup(self, other, "OR")


class ComparisonFilter(Filter):
    """Comparison filters for >, <, >=, <=, ==, !=.
    
    Examples:
        age >= 30  -> ComparisonFilter("age", ">=", 30)
        name == "Alice"  -> ComparisonFilter("name", "==", "Alice")
    """

    def __init__(self, field: str, operator: str, value: Any):
        self.field = field
        self.operator = operator
        self.value = value

    def to_sql(self) -> tuple[str, list[Any]]:
        """Convert to SQL comparison clause."""
        # Map Python operators to SQL operators
        sql_operator = {
            "==": "=",
            "!=": "!=",
            ">": ">",
            "<": "<",
            ">=": ">=",
            "<=": "<=",
        }.get(self.operator, self.operator)

        where_clause = f"{self.field} {sql_operator} ?"
        return where_clause, [self.value]


class LikeFilter(Filter):
    """SQL LIKE filter for pattern matching.
    
    Examples:
        name.like("%alice%")  -> LikeFilter("name", "%alice%")
    """

    def __init__(self, field: str, pattern: str):
        self.field = field
        self.pattern = pattern

    def to_sql(self) -> tuple[str, list[Any]]:
        """Convert to SQL LIKE clause."""
        where_clause = f"{self.field} LIKE ?"
        return where_clause, [self.pattern]


class InFilter(Filter):
    """SQL IN filter for checking membership.
    
    Examples:
        age.in_([25, 30, 35])  -> InFilter("age", [25, 30, 35])
    """

    def __init__(self, field: str, values: list[Any]):
        self.field = field
        self.values = values

    def to_sql(self) -> tuple[str, list[Any]]:
        """Convert to SQL IN clause."""
        placeholders = ",".join("?" * len(self.values))
        where_clause = f"{self.field} IN ({placeholders})"
        return where_clause, self.values


class BetweenFilter(Filter):
    """SQL BETWEEN filter for range queries.
    
    Examples:
        age.between(25, 35)  -> BetweenFilter("age", 25, 35)
    """

    def __init__(self, field: str, min_value: Any, max_value: Any):
        self.field = field
        self.min_value = min_value
        self.max_value = max_value

    def to_sql(self) -> tuple[str, list[Any]]:
        """Convert to SQL BETWEEN clause."""
        where_clause = f"{self.field} BETWEEN ? AND ?"
        return where_clause, [self.min_value, self.max_value]


class FilterGroup(Filter):
    """Combines multiple filters with AND or OR logic.
    
    Created when using & (AND) or | (OR) operators on filters.
    """

    def __init__(self, left: Filter, right: Filter, operator: str):
        self.left = left
        self.right = right
        self.operator = operator

    def to_sql(self) -> tuple[str, list[Any]]:
        """Convert combined filters to SQL WHERE clause."""
        left_sql, left_params = self.left.to_sql()
        right_sql, right_params = self.right.to_sql()

        # Wrap in parentheses to ensure correct precedence
        where_clause = f"({left_sql}) {self.operator} ({right_sql})"
        params = left_params + right_params

        return where_clause, params


class QueryField:
    """Field reference (placeholder for type hints).
    
    Use explicit filter functions instead:
        GreaterThanOrEqualTo("age", 30)
        EqualTo("name", "Alice")
        Like("name", "%alice%")
        In_("age", [25, 30, 35])
        Between("age", 25, 35)
    """

    def __init__(self, field_name: str):
        self.field_name = field_name


# Explicit filter constructors
def EqualTo(field: str, value: Any) -> ComparisonFilter:
    """Create equality filter (field == value)."""
    return ComparisonFilter(field, "==", value)


def NotEqualTo(field: str, value: Any) -> ComparisonFilter:
    """Create not-equal filter (field != value)."""
    return ComparisonFilter(field, "!=", value)


def LessThan(field: str, value: Any) -> ComparisonFilter:
    """Create less-than filter (field < value)."""
    return ComparisonFilter(field, "<", value)


def LessThanOrEqualTo(field: str, value: Any) -> ComparisonFilter:
    """Create less-than-or-equal filter (field <= value)."""
    return ComparisonFilter(field, "<=", value)


def GreaterThan(field: str, value: Any) -> ComparisonFilter:
    """Create greater-than filter (field > value)."""
    return ComparisonFilter(field, ">", value)


def GreaterThanOrEqualTo(field: str, value: Any) -> ComparisonFilter:
    """Create greater-than-or-equal filter (field >= value)."""
    return ComparisonFilter(field, ">=", value)


def Like(field: str, pattern: str) -> LikeFilter:
    """Create LIKE filter for pattern matching."""
    return LikeFilter(field, pattern)


def In_(field: str, values: list[Any]) -> InFilter:
    """Create IN filter for membership checking."""
    return InFilter(field, values)


def Between(field: str, min_value: Any, max_value: Any) -> BetweenFilter:
    """Create BETWEEN filter for range queries."""
    return BetweenFilter(field, min_value, max_value)


__all__ = [
    "Filter",
    "ComparisonFilter",
    "LikeFilter",
    "InFilter",
    "BetweenFilter",
    "FilterGroup",
    "QueryField",
    "EqualTo",
    "NotEqualTo",
    "LessThan",
    "LessThanOrEqualTo",
    "GreaterThan",
    "GreaterThanOrEqualTo",
    "Like",
    "In_",
    "Between",
]
