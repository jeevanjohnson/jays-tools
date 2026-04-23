"""Tests for SQL query filters and batch operations."""

import pytest
import tempfile
from pathlib import Path

from jays_tools.sql_database import (
    SQLDatabase,
    MigratableRow,
    Field,
    ComparisonFilter,
    LikeFilter,
    InFilter,
    BetweenFilter,
    Filter,
    EqualTo,
    NotEqualTo,
    LessThan,
    LessThanOrEqualTo,
    GreaterThan,
    GreaterThanOrEqualTo,
    Like,
    In_,
    Between,
)


# Test models
class PersonV1(MigratableRow):
    name: str = ""
    age: int = 0
    email: str = ""


class ProductV1(MigratableRow):
    title: str = ""
    price: float = 0.0
    quantity: int = 0


class TestFilterClasses:
    """Test individual filter types."""

    def test_comparison_filter_equality(self):
        """Test ComparisonFilter with equality operator."""
        f = ComparisonFilter("age", "==", 30)
        sql, params = f.to_sql()
        assert sql == "age = ?"
        assert params == [30]

    def test_comparison_filter_greater_than(self):
        """Test ComparisonFilter with > operator."""
        f = ComparisonFilter("age", ">", 30)
        sql, params = f.to_sql()
        assert sql == "age > ?"
        assert params == [30]

    def test_comparison_filter_less_than_or_equal(self):
        """Test ComparisonFilter with <= operator."""
        f = ComparisonFilter("age", "<=", 25)
        sql, params = f.to_sql()
        assert sql == "age <= ?"
        assert params == [25]

    def test_like_filter(self):
        """Test LikeFilter for pattern matching."""
        f = LikeFilter("name", "%alice%")
        sql, params = f.to_sql()
        assert sql == "name LIKE ?"
        assert params == ["%alice%"]

    def test_in_filter(self):
        """Test InFilter for membership checking."""
        f = InFilter("age", [25, 30, 35])
        sql, params = f.to_sql()
        assert sql == "age IN (?,?,?)"
        assert params == [25, 30, 35]

    def test_in_filter_single_value(self):
        """Test InFilter with single value."""
        f = InFilter("status", ["active"])
        sql, params = f.to_sql()
        assert sql == "status IN (?)"
        assert params == ["active"]

    def test_between_filter(self):
        """Test BetweenFilter for range queries."""
        f = BetweenFilter("age", 25, 35)
        sql, params = f.to_sql()
        assert sql == "age BETWEEN ? AND ?"
        assert params == [25, 35]


class TestFieldOperators:
    """Test explicit filter constructor functions."""

    def test_field_equality_operator(self):
        """Test EqualTo filter function."""
        f = EqualTo("age", 30)
        assert isinstance(f, ComparisonFilter)
        sql, params = f.to_sql()
        assert sql == "age = ?"
        assert params == [30]

    def test_field_not_equal_operator(self):
        """Test NotEqualTo filter function."""
        f = NotEqualTo("age", 30)
        assert isinstance(f, ComparisonFilter)
        sql, params = f.to_sql()
        assert sql == "age != ?"
        assert params == [30]

    def test_field_greater_than_operator(self):
        """Test GreaterThan filter function."""
        f = GreaterThan("age", 30)
        assert isinstance(f, ComparisonFilter)
        sql, params = f.to_sql()
        assert sql == "age > ?"
        assert params == [30]

    def test_field_greater_equal_operator(self):
        """Test GreaterThanOrEqualTo filter function."""
        f = GreaterThanOrEqualTo("age", 30)
        assert isinstance(f, ComparisonFilter)
        sql, params = f.to_sql()
        assert sql == "age >= ?"
        assert params == [30]

    def test_field_less_than_operator(self):
        """Test LessThan filter function."""
        f = LessThan("age", 25)
        assert isinstance(f, ComparisonFilter)
        sql, params = f.to_sql()
        assert sql == "age < ?"
        assert params == [25]

    def test_field_less_equal_operator(self):
        """Test LessThanOrEqualTo filter function."""
        f = LessThanOrEqualTo("age", 25)
        assert isinstance(f, ComparisonFilter)
        sql, params = f.to_sql()
        assert sql == "age <= ?"
        assert params == [25]

    def test_field_like_method(self):
        """Test Like filter function."""
        f = Like("name", "%alice%")
        assert isinstance(f, LikeFilter)
        sql, params = f.to_sql()
        assert sql == "name LIKE ?"
        assert params == ["%alice%"]

    def test_field_in_method(self):
        """Test In_ filter function."""
        f = In_("age", [25, 30, 35])
        assert isinstance(f, InFilter)
        sql, params = f.to_sql()
        assert sql == "age IN (?,?,?)"
        assert params == [25, 30, 35]

    def test_field_between_method(self):
        """Test Between filter function."""
        f = Between("age", 25, 35)
        assert isinstance(f, BetweenFilter)
        sql, params = f.to_sql()
        assert sql == "age BETWEEN ? AND ?"
        assert params == [25, 35]


class TestFilterCombination:
    """Test combining filters with AND and OR operators."""

    def test_filter_and_operator(self):
        """Test combining filters with & (AND)."""
        age_filter = GreaterThanOrEqualTo("age", 30)
        name_filter = EqualTo("name", "Alice")
        f = age_filter & name_filter
        sql, params = f.to_sql()
        assert "AND" in sql
        assert params == [30, "Alice"]

    def test_filter_or_operator(self):
        """Test combining filters with | (OR)."""
        age_filter = GreaterThan("age", 30)
        status_filter = EqualTo("status", "admin")
        f = age_filter | status_filter
        sql, params = f.to_sql()
        assert "OR" in sql
        assert params == [30, "admin"]

    def test_filter_multiple_conditions(self):
        """Test combining three or more filters."""
        age_gte = GreaterThanOrEqualTo("age", 25)
        age_lte = LessThanOrEqualTo("age", 35)
        name_like = Like("name", "%alice%")
        f = age_gte & age_lte & name_like
        sql, params = f.to_sql()
        assert sql.count("AND") == 2
        assert len(params) == 3  # 25, 35, %alice%

    def test_filter_complex_expression(self):
        """Test complex filter expression with mixed operators."""
        # (age >= 25 AND age <= 35) OR (status == "admin" AND name LIKE "%admin%")
        age_gte = GreaterThanOrEqualTo("age", 25)
        age_lte = LessThanOrEqualTo("age", 35)
        status_eq = EqualTo("status", "admin")
        name_like = Like("name", "%admin%")
        f = (age_gte & age_lte) | (status_eq & name_like)
        sql, params = f.to_sql()
        # Verify structure has both AND and OR
        assert "AND" in sql
        assert "OR" in sql
        assert len(params) == 4  # 25, 35, admin, %admin%


class TestExplicitFilters:
    """Test explicit filter constructor functions."""

    def test_explicit_filters_work(self):
        """Test that explicit filter functions work cleanly."""
        f = GreaterThanOrEqualTo("age", 30)
        assert isinstance(f, ComparisonFilter)
        sql, params = f.to_sql()
        assert sql == "age >= ?"
        assert params == [30]

    def test_all_explicit_operators(self):
        """Test all explicit operator functions."""
        # Greater than
        assert isinstance(GreaterThan("age", 30), ComparisonFilter)
        # Less than
        assert isinstance(LessThan("age", 30), ComparisonFilter)
        # Less than or equal
        assert isinstance(LessThanOrEqualTo("age", 30), ComparisonFilter)
        # Equal
        assert isinstance(EqualTo("age", 30), ComparisonFilter)
        # Not equal
        assert isinstance(NotEqualTo("age", 30), ComparisonFilter)

    def test_explicit_like_filter(self):
        """Test explicit Like filter function."""
        f = Like("name", "%alice%")
        assert isinstance(f, LikeFilter)
        sql, params = f.to_sql()
        assert sql == "name LIKE ?"
        assert params == ["%alice%"]

    def test_explicit_in_filter(self):
        """Test explicit In_ filter function."""
        f = In_("age", [25, 30, 35])
        assert isinstance(f, InFilter)
        sql, params = f.to_sql()
        assert sql == "age IN (?,?,?)"
        assert params == [25, 30, 35]

    def test_explicit_between_filter(self):
        """Test explicit Between filter function."""
        f = Between("age", 25, 35)
        assert isinstance(f, BetweenFilter)
        sql, params = f.to_sql()
        assert sql == "age BETWEEN ? AND ?"
        assert params == [25, 35]

    def test_explicit_combined_filters(self):
        """Test combining explicit filters with AND."""
        age_gte = GreaterThanOrEqualTo("age", 25)
        age_lte = LessThanOrEqualTo("age", 35)
        f = age_gte & age_lte
        sql, params = f.to_sql()
        assert "AND" in sql
        assert len(params) == 2

    def test_explicit_in_database_query(self):
        """Test explicit filters in actual database query."""
        pytest.importorskip("aiosqlite")

        async def run_query():
            with tempfile.TemporaryDirectory() as tmpdir:
                db_path = Path(tmpdir) / "test.db"
                db = SQLDatabase(db_path, [PersonV1])

                # Insert test data
                await db.insert(PersonV1(name="Alice", age=30, email="alice@example.com"))
                await db.insert(PersonV1(name="Bob", age=25, email="bob@example.com"))
                await db.insert(PersonV1(name="Charlie", age=35, email="charlie@example.com"))

                # Query using explicit filter functions
                results = await db.find(PersonV1, GreaterThanOrEqualTo("age", 30))

                assert len(results) == 2
                names = {r.name for r in results}
                assert names == {"Alice", "Charlie"}

        import asyncio
        asyncio.run(run_query())


class TestDatabaseFindWithFilters:
    """Test SQLDatabase.find() with Filter objects."""

    @pytest.mark.asyncio
    async def test_find_with_equality_filter(self):
        """Test find() with equality filter."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            db = SQLDatabase(db_path, [PersonV1])

            # Insert test data
            await db.insert(PersonV1(name="Alice", age=30, email="alice@example.com"))
            await db.insert(PersonV1(name="Bob", age=25, email="bob@example.com"))
            await db.insert(PersonV1(name="Charlie", age=30, email="charlie@example.com"))

            # Query with filter
            name_filter = EqualTo("name", "Alice")
            results = await db.find(PersonV1, name_filter)

            assert len(results) == 1
            assert results[0].name == "Alice"

    @pytest.mark.asyncio
    async def test_find_with_greater_than_filter(self):
        """Test find() with > filter."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            db = SQLDatabase(db_path, [PersonV1])

            # Insert test data
            await db.insert(PersonV1(name="Alice", age=30, email="alice@example.com"))
            await db.insert(PersonV1(name="Bob", age=25, email="bob@example.com"))
            await db.insert(PersonV1(name="Charlie", age=35, email="charlie@example.com"))

            # Query with filter
            age_filter = GreaterThan("age", 28)
            results = await db.find(PersonV1, age_filter)

            assert len(results) == 2
            assert all(r.age > 28 for r in results)

    @pytest.mark.asyncio
    async def test_find_with_range_filter(self):
        """Test find() with BETWEEN filter."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            db = SQLDatabase(db_path, [PersonV1])

            # Insert test data
            for i in range(1, 6):
                await db.insert(PersonV1(name=f"Person{i}", age=20 + i * 5, email=f"p{i}@example.com"))

            # Query with BETWEEN
            age_filter = Between("age", 25, 35)
            results = await db.find(PersonV1, age_filter)

            assert len(results) == 3
            assert all(25 <= r.age <= 35 for r in results)

    @pytest.mark.asyncio
    async def test_find_with_in_filter(self):
        """Test find() with IN filter."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            db = SQLDatabase(db_path, [PersonV1])

            # Insert test data
            await db.insert(PersonV1(name="Alice", age=30, email="alice@example.com"))
            await db.insert(PersonV1(name="Bob", age=25, email="bob@example.com"))
            await db.insert(PersonV1(name="Charlie", age=35, email="charlie@example.com"))
            await db.insert(PersonV1(name="David", age=40, email="david@example.com"))

            # Query with IN
            age_filter = In_("age", [25, 35])
            results = await db.find(PersonV1, age_filter)

            assert len(results) == 2
            assert all(r.age in [25, 35] for r in results)

    @pytest.mark.asyncio
    async def test_find_with_combined_filters(self):
        """Test find() with combined filters (AND)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            db = SQLDatabase(db_path, [PersonV1])

            # Insert test data
            await db.insert(PersonV1(name="Alice", age=30, email="alice@example.com"))
            await db.insert(PersonV1(name="Alice", age=25, email="alice2@example.com"))
            await db.insert(PersonV1(name="Bob", age=30, email="bob@example.com"))

            # Query with combined filters
            filter_obj = EqualTo("age", 30) & EqualTo("name", "Alice")
            results = await db.find(PersonV1, filter_obj)

            assert len(results) == 1
            assert results[0].name == "Alice"
            assert results[0].age == 30

    @pytest.mark.asyncio
    async def test_find_with_no_filter(self):
        """Test find() with no filter returns all."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            db = SQLDatabase(db_path, [PersonV1])

            # Insert test data
            await db.insert(PersonV1(name="Alice", age=30, email="alice@example.com"))
            await db.insert(PersonV1(name="Bob", age=25, email="bob@example.com"))

            # Query without filter
            results = await db.find(PersonV1)

            assert len(results) == 2

    @pytest.mark.asyncio
    async def test_find_with_dict_filter_backwards_compatible(self):
        """Test find() still works with dict filters (backwards compatibility)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            db = SQLDatabase(db_path, [PersonV1])

            # Insert test data
            await db.insert(PersonV1(name="Alice", age=30, email="alice@example.com"))
            await db.insert(PersonV1(name="Bob", age=25, email="bob@example.com"))

            # Query with dict (old style)
            results = await db.find(PersonV1, {"name": "Alice"})

            assert len(results) == 1
            assert results[0].name == "Alice"


class TestBatchInsert:
    """Test SQLDatabase.batch_insert() method."""

    @pytest.mark.asyncio
    async def test_batch_insert_basic(self):
        """Test basic batch insert."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            db = SQLDatabase(db_path, [PersonV1])

            # Create batch of entries
            entries = [
                PersonV1(name=f"Person{i}", age=20 + i, email=f"p{i}@example.com")
                for i in range(100)
            ]

            # Insert batch
            results = await db.batch_insert(entries)

            assert len(results) == 100
            # Check IDs were assigned
            assert all(r.id is not None for r in results)
            assert results[0].id == 1
            assert results[-1].id == 100

    @pytest.mark.asyncio
    async def test_batch_insert_empty_list(self):
        """Test batch insert with empty list."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            db = SQLDatabase(db_path, [PersonV1])

            results = await db.batch_insert([])

            assert results == []

    @pytest.mark.asyncio
    async def test_batch_insert_different_types_raises_error(self):
        """Test batch insert with mixed types raises error."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            db = SQLDatabase(db_path, [PersonV1, ProductV1])

            entries = [
                PersonV1(name="Alice", age=30, email="alice@example.com"),
                ProductV1(title="Laptop", price=999.99, quantity=5),
            ]

            with pytest.raises(ValueError, match="same model type"):
                await db.batch_insert(entries)

    @pytest.mark.asyncio
    async def test_batch_insert_and_query(self):
        """Test batch insert then query results."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            db = SQLDatabase(db_path, [PersonV1])

            # Create and insert batch
            entries = [
                PersonV1(name="Alice", age=30, email="alice@example.com"),
                PersonV1(name="Bob", age=25, email="bob@example.com"),
                PersonV1(name="Charlie", age=35, email="charlie@example.com"),
            ]
            results = await db.batch_insert(entries)

            # Query back
            age_filter = GreaterThanOrEqualTo("age", 30)
            found = await db.find(PersonV1, age_filter)

            assert len(found) == 2
            names = {r.name for r in found}
            assert names == {"Alice", "Charlie"}


class TestBatchUpdate:
    """Test SQLDatabase.batch_update() method."""

    @pytest.mark.asyncio
    async def test_batch_update_basic(self):
        """Test basic batch update."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            db = SQLDatabase(db_path, [PersonV1])

            # Insert entries
            entries = [
                PersonV1(name="Alice", age=30, email="alice@example.com"),
                PersonV1(name="Bob", age=25, email="bob@example.com"),
                PersonV1(name="Charlie", age=35, email="charlie@example.com"),
            ]
            inserted = await db.batch_insert(entries)

            # Modify and update
            for entry in inserted:
                entry.age += 10

            results = await db.batch_update(inserted)

            assert len(results) == 3
            assert results[0].age == 40
            assert results[1].age == 35
            assert results[2].age == 45

    @pytest.mark.asyncio
    async def test_batch_update_empty_list(self):
        """Test batch update with empty list."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            db = SQLDatabase(db_path, [PersonV1])

            results = await db.batch_update([])

            assert results == []

    @pytest.mark.asyncio
    async def test_batch_update_without_ids_raises_error(self):
        """Test batch update without IDs raises error."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            db = SQLDatabase(db_path, [PersonV1])

            entries = [
                PersonV1(name="Alice", age=30, email="alice@example.com"),
                PersonV1(name="Bob", age=25, email="bob@example.com"),
            ]

            with pytest.raises(ValueError, match="must have IDs"):
                await db.batch_update(entries)

    @pytest.mark.asyncio
    async def test_batch_update_different_types_raises_error(self):
        """Test batch update with mixed types raises error."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            db = SQLDatabase(db_path, [PersonV1, ProductV1])

            p = PersonV1(name="Alice", age=30, email="alice@example.com")
            p.id = 1

            entries: list[PersonV1 | ProductV1] = [p]
            # Try to mix types
            entries.append(ProductV1(title="Laptop", price=999.99, quantity=5))
            entries[-1].id = 2

            with pytest.raises(ValueError, match="same model type"):
                await db.batch_update(entries[:1] + entries[1:])

    @pytest.mark.asyncio
    async def test_batch_update_persists(self):
        """Test batch update changes persist to database."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            db = SQLDatabase(db_path, [PersonV1])

            # Insert
            inserted = await db.batch_insert([
                PersonV1(name="Alice", age=30, email="alice@example.com"),
                PersonV1(name="Bob", age=25, email="bob@example.com"),
            ])

            # Update
            inserted[0].name = "Alicia"
            inserted[1].age = 26
            await db.batch_update(inserted)

            # Query to verify
            found = await db.find(PersonV1, EqualTo("name", "Alicia"))
            assert len(found) == 1
            assert found[0].age == 30

            found = await db.find(PersonV1, EqualTo("age", 26))
            assert len(found) == 1
            assert found[0].name == "Bob"
