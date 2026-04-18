"""Tests for the JsonDatabase module."""

import asyncio
import json
import tempfile
from pathlib import Path
from typing import Any

import pytest
from pydantic import BaseModel, Field, ValidationError

from jays_tools.json_database.database import JsonDatabase, model_has_defaults
from jays_tools.json_database.models import MigratableModel


class SimpleModel(MigratableModel):
    """Simple test model with all defaults."""
    name: str = "default"
    value: int = 0
    active: bool = True


class ModelWithDefaults(MigratableModel):
    """Model with various default types."""
    title: str = ""
    count: int = 0
    tags: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ModelWithoutDefaults(BaseModel):
    """Model with required fields (no defaults)."""
    name: str
    value: int


class TestModelHasDefaults:
    """Tests for model_has_defaults helper function."""

    def test_model_with_defaults(self):
        """Should return True for models where all fields have defaults."""
        assert model_has_defaults(SimpleModel) is True

    def test_model_without_defaults(self):
        """Should return False for models with required fields."""
        assert model_has_defaults(ModelWithoutDefaults) is False


class TestJsonDatabaseInitialization:
    """Tests for JsonDatabase initialization and validation."""

    def test_init_with_valid_model(self):
        """Should create instance with valid model that has defaults."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db = JsonDatabase(
                path=Path(tmpdir) / "test.json",
                database_model=SimpleModel,
            )
            assert db.private_database_model == SimpleModel

    def test_init_with_model_without_defaults(self):
        """Should raise ValueError if model has required fields."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with pytest.raises(ValueError, match="requires all fields to have defaults"):
                JsonDatabase(
                    path=Path(tmpdir) / "test.json",
                    database_model=ModelWithoutDefaults, # type: ignore
                )

    def test_init_without_model(self):
        """Should raise ValueError if database_model is not provided."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with pytest.raises(ValueError, match="database_model is required"):
                JsonDatabase(path=Path(tmpdir) / "test.json", database_model=None)  # type: ignore

    def test_path_normalization(self):
        """Should normalize path to .json suffix."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db = JsonDatabase(
                path=Path(tmpdir) / "test",
                database_model=SimpleModel,
            )
            assert db.get_path().suffix == ".json"


class TestJsonDatabaseRead:
    """Tests for reading from database files."""

    def test_read_existing_file(self):
        """Should read and parse existing JSON file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.json"
            
            # Pre-create file with valid data
            db_path.write_text('{"name": "test", "value": 42, "active": false}')
            
            db = JsonDatabase(path=db_path, database_model=SimpleModel)
            result = db.get_database()
            
            assert result.name == "test"
            assert result.value == 42
            assert result.active is False

    def test_read_missing_file(self):
        """Should create default instance if file doesn't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.json"
            
            db = JsonDatabase(path=db_path, database_model=SimpleModel)
            result = db.get_database()
            
            assert db_path.exists()
            assert result.name == "default"
            assert result.value == 0
            assert result.active is True

    def test_read_empty_file(self):
        """Should create default instance if file is empty."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.json"
            db_path.write_text("")
            
            db = JsonDatabase(path=db_path, database_model=SimpleModel)
            result = db.get_database()
            
            assert result.name == "default"

    def test_read_invalid_json(self):
        """Should raise ValueError for invalid JSON."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.json"
            db_path.write_text("{ invalid json }")
            
            db = JsonDatabase(path=db_path, database_model=SimpleModel)
            
            with pytest.raises(ValueError, match="validation error"):
                db.get_database()

    def test_read_validation_error(self):
        """Should raise ValueError if JSON doesn't match model schema."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.json"
            db_path.write_text('{"name": "test", "value": "not an int"}')
            
            db = JsonDatabase(path=db_path, database_model=SimpleModel)
            
            with pytest.raises(ValueError, match="validation error"):
                db.get_database()

    def test_caching_prevents_reread(self):
        """Should use cached data on subsequent reads without re-reading file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.json"
            db_path.write_text('{"name": "original"}')
            
            db = JsonDatabase(path=db_path, database_model=SimpleModel)
            
            # First read
            result1 = db.get_database()
            assert result1.name == "original"
            
            # Modify file on disk
            db_path.write_text('{"name": "modified"}')
            
            # Second read should use cache, not file
            result2 = db.get_database()
            assert result2.name == "original"


class TestJsonDatabaseWrite:
    """Tests for writing to database files."""

    def test_write_creates_file(self):
        """Should create file if it doesn't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.json"
            
            db = JsonDatabase(path=db_path, database_model=SimpleModel)
            new_data = SimpleModel(name="written", value=99)
            
            db.write(new_data)
            
            assert db_path.exists()
            content = json.loads(db_path.read_text())
            assert content["name"] == "written"
            assert content["value"] == 99

    def test_write_creates_parent_directories(self):
        """Should create parent directories if they don't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "nested" / "dir" / "test.json"
            
            db = JsonDatabase(path=db_path, database_model=SimpleModel)
            new_data = SimpleModel(name="nested")
            
            db.write(new_data)
            
            assert db_path.exists()
            assert db_path.parent.exists()

    def test_write_updates_cache(self):
        """Should update internal cache when writing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db = JsonDatabase(
                path=Path(tmpdir) / "test.json",
                database_model=SimpleModel,
            )
            
            new_data = SimpleModel(name="cached", value=123)
            db.write(new_data)
            
            # Get data without reading file
            result = db.get_database()
            assert result.name == "cached"
            assert result.value == 123

    def test_write_formats_json_nicely(self):
        """Should write formatted JSON with indent."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.json"
            
            db = JsonDatabase(path=db_path, database_model=SimpleModel)
            new_data = SimpleModel(name="test", value=42)
            
            db.write(new_data)
            
            content = db_path.read_text()
            assert "\n" in content  # Should have newlines (formatted)
            assert "    " in content  # Should have indentation


class TestJsonDatabaseUpdate:
    """Tests for updating database."""

    def test_update_database(self):
        """Should update database and return copy."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db = JsonDatabase(
                path=Path(tmpdir) / "test.json",
                database_model=SimpleModel,
            )
            
            new_data = SimpleModel(name="updated", value=456, active=False)
            result = db.update_database(new_data)
            
            assert result.name == "updated"
            assert result.value == 456
            assert result.active is False

    def test_update_persists_to_disk(self):
        """Should persist updates to disk."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.json"
            
            db = JsonDatabase(path=db_path, database_model=SimpleModel)
            new_data = SimpleModel(name="persisted", value=789)
            
            db.update_database(new_data)
            
            # Verify in file
            content = json.loads(db_path.read_text())
            assert content["name"] == "persisted"
            assert content["value"] == 789


class TestJsonDatabaseDeepCopy:
    """Tests for deep copy behavior to prevent external mutations."""

    def test_get_returns_copy(self):
        """Should return deep copy to prevent external mutations."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db = JsonDatabase(
                path=Path(tmpdir) / "test.json",
                database_model=ModelWithDefaults,
            )
            
            data = db.get_database()
            data.tags.append("mutated")
            
            # Get again - should not have the mutation
            data2 = db.get_database()
            assert len(data2.tags) == 0

    def test_update_accepts_copy(self):
        """Should accept data and store as copy."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db = JsonDatabase(
                path=Path(tmpdir) / "test.json",
                database_model=ModelWithDefaults,
            )
            
            data = ModelWithDefaults(tags=["original"])
            db.update_database(data)
            
            # Mutate original
            data.tags.append("mutation")
            
            # Database should not be affected
            stored = db.get_database()
            assert stored.tags == ["original"]


class TestJsonDatabaseIntegration:
    """Integration tests for complete workflows."""

    def test_create_read_update_workflow(self):
        """Should handle full create, read, update workflow."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.json"
            
            # Create and write
            db = JsonDatabase(path=db_path, database_model=SimpleModel)
            initial = SimpleModel(name="initial", value=1)
            db.write(initial)
            
            # Read
            read_data = db.get_database()
            assert read_data.name == "initial"
            
            # Update
            updated = SimpleModel(name="updated", value=2)
            db.update_database(updated)
            
            # Verify update
            final = db.get_database()
            assert final.name == "updated"
            assert final.value == 2

    def test_multiple_instances_share_file(self):
        """Multiple instances should read same file (but won't share cache)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.json"
            
            db1 = JsonDatabase(path=db_path, database_model=SimpleModel)
            db1.write(SimpleModel(name="from_db1", value=1))
            
            # New instance reads same file
            db2 = JsonDatabase(path=db_path, database_model=SimpleModel)
            data2 = db2.get_database()
            
            assert data2.name == "from_db1"
            assert data2.value == 1

    def test_complex_model_with_defaults(self):
        """Should handle complex models with various default types."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db = JsonDatabase(
                path=Path(tmpdir) / "test.json",
                database_model=ModelWithDefaults,
            )
            
            data = ModelWithDefaults(
                title="test",
                tags=["python", "json"],
                metadata={"version": "1.0"}
            )
            
            db.write(data)
            retrieved = db.get_database()
            
            assert retrieved.title == "test"
            assert retrieved.tags == ["python", "json"]
            assert retrieved.metadata == {"version": "1.0"}


class TestAsyncGetDatabase:
    """Test suite for async_get_database method."""

    @pytest.mark.asyncio
    async def test_happy_path_basic(self):
        """Async get returns database copy from cache."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db = JsonDatabase(
                path=Path(tmpdir) / "test.json",
                database_model=SimpleModel,
            )
            db.private_database = SimpleModel(name="async_test", value=42)
            
            result = await db.async_get_database()
            
            assert result.name == "async_test"
            assert result.value == 42
            assert isinstance(result, SimpleModel)

    @pytest.mark.asyncio
    async def test_happy_path_initializes_if_not_cached(self):
        """Async get initializes database if cache is empty."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db = JsonDatabase(
                path=Path(tmpdir) / "test.json",
                database_model=SimpleModel,
            )
            
            result = await db.async_get_database()
            
            assert result.name == "default"
            assert result.value == 0
            assert result.active is True

    @pytest.mark.asyncio
    async def test_edge_case_returns_copy_not_reference(self):
        """Async get returns deep copy to prevent external mutations."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db = JsonDatabase(
                path=Path(tmpdir) / "test.json",
                database_model=ModelWithDefaults,
            )
            db.private_database = ModelWithDefaults(tags=["original"])
            
            result = await db.async_get_database()
            result.tags.append("mutated")
            
            # Get again - should not have mutation
            result2 = await db.async_get_database()
            assert result2.tags == ["original"]

    @pytest.mark.asyncio
    async def test_edge_case_concurrent_access(self):
        """Multiple concurrent async_get_database calls are safe with lock."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db = JsonDatabase(
                path=Path(tmpdir) / "test.json",
                database_model=SimpleModel,
            )
            
            # Create multiple concurrent tasks
            tasks = [db.async_get_database() for _ in range(5)]
            results = await asyncio.gather(*tasks)
            
            # All should succeed and return valid data
            assert len(results) == 5
            for result in results:
                assert isinstance(result, SimpleModel)
                assert result.name == "default"

    @pytest.mark.asyncio
    async def test_happy_path_respects_lock_order(self):
        """Lock ensures serialized access in async context."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.json"
            db = JsonDatabase(path=db_path, database_model=SimpleModel)
            
            # Warm up the cache
            await db.async_get_database()
            
            # Concurrent calls should all succeed
            results = await asyncio.gather(
                db.async_get_database(),
                db.async_get_database(),
                db.async_get_database(),
            )
            
            assert all(isinstance(r, SimpleModel) for r in results)


class TestAsyncUpdateDatabase:
    """Test suite for async_update_database method."""

    @pytest.mark.asyncio
    async def test_happy_path_basic(self):
        """Async update changes database and returns copy."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db = JsonDatabase(
                path=Path(tmpdir) / "test.json",
                database_model=SimpleModel,
            )
            
            new_data = SimpleModel(name="async_updated", value=99, active=False)
            result = await db.async_update_database(new_data)
            
            assert result.name == "async_updated"
            assert result.value == 99
            assert result.active is False

    @pytest.mark.asyncio
    async def test_happy_path_persists_to_disk(self):
        """Async update persists changes to file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.json"
            db = JsonDatabase(path=db_path, database_model=SimpleModel)
            
            new_data = SimpleModel(name="persisted", value=555)
            await db.async_update_database(new_data)
            
            # Verify in file
            content = json.loads(db_path.read_text())
            assert content["name"] == "persisted"
            assert content["value"] == 555

    @pytest.mark.asyncio
    async def test_happy_path_multiple_updates_sequential(self):
        """Multiple sequential updates work correctly."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db = JsonDatabase(
                path=Path(tmpdir) / "test.json",
                database_model=SimpleModel,
            )
            
            # First update
            data1 = SimpleModel(name="first", value=1)
            result1 = await db.async_update_database(data1)
            assert result1.name == "first"
            
            # Second update
            data2 = SimpleModel(name="second", value=2)
            result2 = await db.async_update_database(data2)
            assert result2.name == "second"
            
            # Verify final state
            final = await db.async_get_database()
            assert final.name == "second"
            assert final.value == 2

    @pytest.mark.asyncio
    async def test_edge_case_returns_copy_not_reference(self):
        """Async update returns deep copy to prevent mutations."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db = JsonDatabase(
                path=Path(tmpdir) / "test.json",
                database_model=ModelWithDefaults,
            )
            
            new_data = ModelWithDefaults(tags=["original"])
            result = await db.async_update_database(new_data)
            
            # Mutate returned copy
            result.tags.append("mutated")
            
            # Database should not be affected
            stored = await db.async_get_database()
            assert stored.tags == ["original"]

    @pytest.mark.asyncio
    async def test_edge_case_concurrent_updates_with_lock(self):
        """Concurrent updates are serialized by lock (last write wins)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db = JsonDatabase(
                path=Path(tmpdir) / "test.json",
                database_model=SimpleModel,
            )
            
            # Create concurrent update tasks
            tasks = [
                db.async_update_database(SimpleModel(name=f"update_{i}", value=i))
                for i in range(3)
            ]
            
            results = await asyncio.gather(*tasks)
            
            # All should complete without error
            assert len(results) == 3
            for result in results:
                assert isinstance(result, SimpleModel)
            
            # Final state should be last update to complete
            final = await db.async_get_database()
            assert final.name in ["update_0", "update_1", "update_2"]

    @pytest.mark.asyncio
    async def test_edge_case_complex_model_update(self):
        """Async update works with complex model types."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db = JsonDatabase(
                path=Path(tmpdir) / "test.json",
                database_model=ModelWithDefaults,
            )
            
            new_data = ModelWithDefaults(
                title="async_complex",
                count=42,
                tags=["async", "test", "complex"],
                metadata={"async": True, "version": "2.0"}
            )
            
            result = await db.async_update_database(new_data)
            
            assert result.title == "async_complex"
            assert result.count == 42
            assert result.tags == ["async", "test", "complex"]
            assert result.metadata == {"async": True, "version": "2.0"}

    @pytest.mark.asyncio
    async def test_error_case_invalid_type(self):
        """Async update with wrong type is handled."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db = JsonDatabase(
                path=Path(tmpdir) / "test.json",
                database_model=SimpleModel,
            )
            
            # Attempting to update with wrong type should raise or fail gracefully
            with pytest.raises((TypeError, AttributeError, ValidationError)):
                await db.async_update_database("not a model")  # type: ignore

    @pytest.mark.asyncio
    async def test_error_case_none_value(self):
        """Async update with None raises error."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db = JsonDatabase(
                path=Path(tmpdir) / "test.json",
                database_model=SimpleModel,
            )
            
            with pytest.raises((TypeError, AttributeError, ValidationError)):
                await db.async_update_database(None)  # type: ignore


class TestAsyncIntegration:
    """Integration tests for async operations."""

    @pytest.mark.asyncio
    async def test_async_workflow_get_then_update(self):
        """Complete workflow: async get, modify in-memory, async update."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db = JsonDatabase(
                path=Path(tmpdir) / "test.json",
                database_model=SimpleModel,
            )
            
            # Initial data
            initial = SimpleModel(name="initial", value=10, active=True)
            await db.async_update_database(initial)
            
            # Get current
            current = await db.async_get_database()
            assert current.name == "initial"
            
            # Modify and update
            current.name = "modified"
            current.value = 20
            result = await db.async_update_database(current)
            
            assert result.name == "modified"
            assert result.value == 20

    @pytest.mark.asyncio
    async def test_async_mixed_with_sync(self):
        """Async and sync methods can be used together safely."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db = JsonDatabase(
                path=Path(tmpdir) / "test.json",
                database_model=SimpleModel,
            )
            
            # Sync write
            sync_data = SimpleModel(name="sync", value=1)
            db.write(sync_data)
            
            # Async get
            async_result = await db.async_get_database()
            assert async_result.name == "sync"
            
            # Async update
            new_data = SimpleModel(name="async_update", value=2)
            await db.async_update_database(new_data)
            
            # Sync read to verify
            sync_check = db.get_database()
            assert sync_check.name == "async_update"

    @pytest.mark.asyncio
    async def test_async_concurrent_get_and_update(self):
        """Concurrent get and update operations are thread-safe."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db = JsonDatabase(
                path=Path(tmpdir) / "test.json",
                database_model=SimpleModel,
            )
            
            # Mix of concurrent gets and updates
            tasks = [
                db.async_get_database(),
                db.async_update_database(SimpleModel(name="update_1", value=1)),
                db.async_get_database(),
                db.async_update_database(SimpleModel(name="update_2", value=2)),
                db.async_get_database(),
            ]
            
            results = await asyncio.gather(*tasks)
            
            # All should complete successfully
            assert len(results) == 5
            assert all(isinstance(r, SimpleModel) for r in results)
