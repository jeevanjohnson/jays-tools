"""Tests for the JsonCollection module."""

import asyncio
import tempfile
from pathlib import Path
from typing import Any

import pytest
from pydantic import Field

from jays_tools.json_collection import JsonCollection
from jays_tools.json_database.models import MigratableModel


class SimpleCollectionModel(MigratableModel):
    """Simple test model for collection tests."""

    id: str = ""
    name: str = "default"
    value: int = 0
    active: bool = True


class CollectionModelWithDefaults(MigratableModel):
    """Collection model with various default types."""

    title: str = ""
    count: int = 0
    tags: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class TestJsonCollectionInitialization:
    """Tests for JsonCollection initialization."""

    def test_init_with_valid_model(self):
        """Should create instance with valid model."""
        with tempfile.TemporaryDirectory() as tmpdir:
            collection = JsonCollection(
                path=tmpdir,
                model=SimpleCollectionModel,
            )
            assert collection.private_model == SimpleCollectionModel
            assert collection.private_path == Path(tmpdir)

    def test_init_with_path_string(self):
        """Should accept path as string and convert to Path."""
        with tempfile.TemporaryDirectory() as tmpdir:
            collection = JsonCollection(
                path=tmpdir,
                model=SimpleCollectionModel,
            )
            assert isinstance(collection.private_path, Path)

    def test_init_with_path_object(self):
        """Should accept path as Path object."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir)
            collection = JsonCollection(
                path=path,
                model=SimpleCollectionModel,
            )
            assert collection.private_path == path


class TestJsonCollectionGetOperation:
    """Tests for get() method."""

    def test_get_creates_directory_if_not_exists(self):
        """Should create directory if it doesn't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            collection = JsonCollection(
                path=Path(tmpdir) / "new_collection",
                model=SimpleCollectionModel,
            )
            assert not collection.private_path.exists()
            collection.get("test_key")
            assert collection.private_path.exists()

    def test_get_returns_json_database(self):
        """Should return a JsonDatabase instance."""
        with tempfile.TemporaryDirectory() as tmpdir:
            collection = JsonCollection(
                path=tmpdir,
                model=SimpleCollectionModel,
            )
            db = collection.get("test_key")
            assert hasattr(db, "get_database")
            assert hasattr(db, "update_database")

    def test_get_creates_file_at_correct_path(self):
        """Should create file with correct path pattern."""
        with tempfile.TemporaryDirectory() as tmpdir:
            collection = JsonCollection(
                path=tmpdir,
                model=SimpleCollectionModel,
            )
            db = collection.get("test_key")
            data = db.get_database()
            db.update_database(data)
            expected_file = Path(tmpdir) / "test_key.json"
            assert expected_file.exists()

    def test_get_multiple_keys(self):
        """Should handle multiple different keys."""
        with tempfile.TemporaryDirectory() as tmpdir:
            collection = JsonCollection(
                path=tmpdir,
                model=SimpleCollectionModel,
            )
            db1 = collection.get("key1")
            db2 = collection.get("key2")
            # Both should be valid databases
            assert db1.get_database()
            assert db2.get_database()


class TestJsonCollectionDelete:
    """Tests for delete() method."""

    def test_delete_removes_file(self):
        """Should delete the file for given key."""
        with tempfile.TemporaryDirectory() as tmpdir:
            collection = JsonCollection(
                path=tmpdir,
                model=SimpleCollectionModel,
            )
            # Create a file
            db = collection.get("to_delete")
            data = db.get_database()
            db.update_database(data)
            assert (Path(tmpdir) / "to_delete.json").exists()

            # Delete it
            collection.delete("to_delete")
            assert not (Path(tmpdir) / "to_delete.json").exists()

    def test_delete_nonexistent_key_does_not_raise(self):
        """Should not raise error when deleting non-existent key."""
        with tempfile.TemporaryDirectory() as tmpdir:
            collection = JsonCollection(
                path=tmpdir,
                model=SimpleCollectionModel,
            )
            # Should not raise
            collection.delete("nonexistent")

    def test_delete_only_deletes_specified_key(self):
        """Should only delete the specified key, not others."""
        with tempfile.TemporaryDirectory() as tmpdir:
            collection = JsonCollection(
                path=tmpdir,
                model=SimpleCollectionModel,
            )
            # Create multiple files
            for key in ["key1", "key2", "key3"]:
                db = collection.get(key)
                db.update_database(db.get_database())

            # Delete one
            collection.delete("key2")
            assert (Path(tmpdir) / "key1.json").exists()
            assert not (Path(tmpdir) / "key2.json").exists()
            assert (Path(tmpdir) / "key3.json").exists()


class TestJsonCollectionExists:
    """Tests for exists() method."""

    def test_exists_returns_true_for_existing_key(self):
        """Should return True when file exists."""
        with tempfile.TemporaryDirectory() as tmpdir:
            collection = JsonCollection(
                path=tmpdir,
                model=SimpleCollectionModel,
            )
            db = collection.get("exists_key")
            db.update_database(db.get_database())
            assert collection.exists("exists_key") is True

    def test_exists_returns_false_for_nonexistent_key(self):
        """Should return False when file doesn't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            collection = JsonCollection(
                path=tmpdir,
                model=SimpleCollectionModel,
            )
            assert collection.exists("nonexistent") is False

    def test_exists_returns_false_before_directory_created(self):
        """Should return False when collection directory doesn't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            collection = JsonCollection(
                path=Path(tmpdir) / "nonexistent_dir",
                model=SimpleCollectionModel,
            )
            assert collection.exists("any_key") is False


class TestJsonCollectionListKeys:
    """Tests for list_keys() method."""

    def test_list_keys_empty_collection(self):
        """Should return empty list for empty collection."""
        with tempfile.TemporaryDirectory() as tmpdir:
            collection = JsonCollection(
                path=tmpdir,
                model=SimpleCollectionModel,
            )
            assert collection.list_keys() == []

    def test_list_keys_returns_all_keys(self):
        """Should return list of all keys in collection."""
        with tempfile.TemporaryDirectory() as tmpdir:
            collection = JsonCollection(
                path=tmpdir,
                model=SimpleCollectionModel,
            )
            keys_to_create = ["key1", "key2", "key3"]
            for key in keys_to_create:
                db = collection.get(key)
                db.update_database(db.get_database())

            assert sorted(collection.list_keys()) == sorted(keys_to_create)

    def test_list_keys_excludes_non_json_files(self):
        """Should only list .json files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            collection = JsonCollection(
                path=tmpdir,
                model=SimpleCollectionModel,
            )
            # Create a json file
            db = collection.get("valid_key")
            db.update_database(db.get_database())

            # Create a non-json file
            Path(tmpdir, "invalid_file.txt").write_text("test")

            keys = collection.list_keys()
            assert "valid_key" in keys
            assert "invalid_file" not in keys

    def test_list_keys_empty_when_directory_not_exists(self):
        """Should return empty list if directory doesn't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            collection = JsonCollection(
                path=Path(tmpdir) / "nonexistent",
                model=SimpleCollectionModel,
            )
            assert collection.list_keys() == []


class TestJsonCollectionClear:
    """Tests for clear() method."""

    def test_clear_removes_all_files(self):
        """Should remove all .json files in collection."""
        with tempfile.TemporaryDirectory() as tmpdir:
            collection = JsonCollection(
                path=tmpdir,
                model=SimpleCollectionModel,
            )
            # Create multiple files
            for key in ["key1", "key2", "key3"]:
                db = collection.get(key)
                db.update_database(db.get_database())

            collection.clear()
            assert collection.list_keys() == []

    def test_clear_does_not_remove_directory(self):
        """Should remove files but not the directory itself."""
        with tempfile.TemporaryDirectory() as tmpdir:
            collection = JsonCollection(
                path=tmpdir,
                model=SimpleCollectionModel,
            )
            db = collection.get("key1")
            db.update_database(db.get_database())

            collection.clear()
            assert collection.private_path.exists()

    def test_clear_on_nonexistent_directory_does_not_raise(self):
        """Should not raise error if directory doesn't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            collection = JsonCollection(
                path=Path(tmpdir) / "nonexistent",
                model=SimpleCollectionModel,
            )
            # Should not raise
            collection.clear()

    def test_clear_ignores_non_json_files(self):
        """Should only clear .json files, leave others."""
        with tempfile.TemporaryDirectory() as tmpdir:
            collection = JsonCollection(
                path=tmpdir,
                model=SimpleCollectionModel,
            )
            # Create json file
            db = collection.get("key1")
            db.update_database(db.get_database())

            # Create non-json file
            txt_file = Path(tmpdir) / "keep.txt"
            txt_file.write_text("preserve me")

            collection.clear()
            assert not (Path(tmpdir) / "key1.json").exists()
            assert txt_file.exists()


class TestJsonCollectionCreate:
    """Tests for create() method."""

    def test_create_new_key(self):
        """Should create a new entity with the given key."""
        with tempfile.TemporaryDirectory() as tmpdir:
            collection = JsonCollection(
                path=tmpdir,
                model=SimpleCollectionModel,
            )
            data = SimpleCollectionModel(name="created", value=99)
            result = collection.create("new_key", data)

            assert result.name == "created"
            assert result.value == 99
            assert collection.exists("new_key")

    def test_create_raises_on_existing_key(self):
        """Should raise ValueError if key already exists."""
        with tempfile.TemporaryDirectory() as tmpdir:
            collection = JsonCollection(
                path=tmpdir,
                model=SimpleCollectionModel,
            )
            # Create first entity
            data1 = SimpleCollectionModel(name="first", value=1)
            collection.create("existing_key", data1)

            # Try to create with same key
            data2 = SimpleCollectionModel(name="second", value=2)
            with pytest.raises(ValueError, match="already exists"):
                collection.create("existing_key", data2)

    def test_create_persists_file(self):
        """Should persist created entity to file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            collection = JsonCollection(
                path=tmpdir,
                model=SimpleCollectionModel,
            )
            data = SimpleCollectionModel(name="persisted", value=42)
            collection.create("persist_key", data)

            file_path = Path(tmpdir) / "persist_key.json"
            assert file_path.exists()


class TestJsonCollectionUpdate:
    """Tests for update() method."""

    def test_update_persists_data(self):
        """Should persist updated data to file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            collection = JsonCollection(
                path=tmpdir,
                model=SimpleCollectionModel,
            )
            # Create and update
            data = SimpleCollectionModel(name="updated", value=42)
            result = collection.update("key1", data)

            # Verify data was persisted
            assert result.name == "updated"
            assert result.value == 42

    def test_update_returns_updated_data(self):
        """Should return the updated data."""
        with tempfile.TemporaryDirectory() as tmpdir:
            collection = JsonCollection(
                path=tmpdir,
                model=SimpleCollectionModel,
            )
            data = SimpleCollectionModel(name="test", value=10)
            result = collection.update("key1", data)

            assert isinstance(result, SimpleCollectionModel)
            assert result.name == "test"
            assert result.value == 10

    def test_update_creates_file_if_not_exists(self):
        """Should create file if it doesn't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            collection = JsonCollection(
                path=tmpdir,
                model=SimpleCollectionModel,
            )
            file_path = Path(tmpdir) / "new_key.json"
            assert not file_path.exists()

            data = SimpleCollectionModel(name="new")
            collection.update("new_key", data)

            assert file_path.exists()

    def test_update_overwrites_existing_data(self):
        """Should overwrite existing data."""
        with tempfile.TemporaryDirectory() as tmpdir:
            collection = JsonCollection(
                path=tmpdir,
                model=SimpleCollectionModel,
            )
            # Create initial
            data1 = SimpleCollectionModel(name="first", value=1)
            collection.update("key1", data1)

            # Update with different data
            data2 = SimpleCollectionModel(name="second", value=2)
            result = collection.update("key1", data2)

            assert result.name == "second"
            assert result.value == 2


class TestJsonCollectionGetAll:
    """Tests for get_all() method."""

    def test_get_all_empty_collection(self):
        """Should return empty dict for empty collection."""
        with tempfile.TemporaryDirectory() as tmpdir:
            collection = JsonCollection(
                path=tmpdir,
                model=SimpleCollectionModel,
            )
            assert collection.get_all() == {}

    def test_get_all_returns_all_entities(self):
        """Should return dict of all entities keyed by key."""
        with tempfile.TemporaryDirectory() as tmpdir:
            collection = JsonCollection(
                path=tmpdir,
                model=SimpleCollectionModel,
            )
            # Create multiple entities
            for i, key in enumerate(["key1", "key2", "key3"]):
                data = SimpleCollectionModel(name=f"entity_{i}", value=i)
                collection.update(key, data)

            result = collection.get_all()
            assert len(result) == 3
            assert "key1" in result
            assert "key2" in result
            assert "key3" in result

    def test_get_all_returns_correct_data(self):
        """Should return correct data for each key."""
        with tempfile.TemporaryDirectory() as tmpdir:
            collection = JsonCollection(
                path=tmpdir,
                model=SimpleCollectionModel,
            )
            data1 = SimpleCollectionModel(name="first", value=1)
            data2 = SimpleCollectionModel(name="second", value=2)
            collection.update("key1", data1)
            collection.update("key2", data2)

            result = collection.get_all()
            assert result["key1"].name == "first"
            assert result["key1"].value == 1
            assert result["key2"].name == "second"
            assert result["key2"].value == 2


class TestJsonCollectionUpdateAll:
    """Tests for update_all() method."""

    def test_update_all_creates_multiple_entities(self):
        """Should create multiple entities from dict."""
        with tempfile.TemporaryDirectory() as tmpdir:
            collection = JsonCollection(
                path=tmpdir,
                model=SimpleCollectionModel,
            )
            updates = {
                "key1": SimpleCollectionModel(name="first", value=1),
                "key2": SimpleCollectionModel(name="second", value=2),
                "key3": SimpleCollectionModel(name="third", value=3),
            }
            result = collection.update_all(updates)

            assert len(result) == 3
            assert "key1" in result
            assert "key2" in result
            assert "key3" in result

    def test_update_all_overwrites_existing(self):
        """Should overwrite existing entities."""
        with tempfile.TemporaryDirectory() as tmpdir:
            collection = JsonCollection(
                path=tmpdir,
                model=SimpleCollectionModel,
            )
            # Create initial
            collection.update("key1", SimpleCollectionModel(name="old", value=0))

            # Update all
            updates = {
                "key1": SimpleCollectionModel(name="new", value=1),
            }
            result = collection.update_all(updates)

            assert result["key1"].name == "new"
            assert result["key1"].value == 1

    def test_update_all_returns_all_data(self):
        """Should return dict of all updated data."""
        with tempfile.TemporaryDirectory() as tmpdir:
            collection = JsonCollection(
                path=tmpdir,
                model=SimpleCollectionModel,
            )
            updates = {
                "key1": SimpleCollectionModel(name="first", value=1),
                "key2": SimpleCollectionModel(name="second", value=2),
            }
            result = collection.update_all(updates)

            assert len(result) == 2
            assert result["key1"].name == "first"
            assert result["key2"].name == "second"


class TestJsonCollectionAsync:
    """Tests for async methods."""

    @pytest.mark.asyncio
    async def test_async_get_returns_database(self):
        """Async get should return JsonDatabase."""
        with tempfile.TemporaryDirectory() as tmpdir:
            collection = JsonCollection(
                path=tmpdir,
                model=SimpleCollectionModel,
            )
            db = await collection.async_get("async_key")
            assert hasattr(db, "get_database")

    @pytest.mark.asyncio
    async def test_async_update_persists_data(self):
        """Async update should persist data."""
        with tempfile.TemporaryDirectory() as tmpdir:
            collection = JsonCollection(
                path=tmpdir,
                model=SimpleCollectionModel,
            )
            data = SimpleCollectionModel(name="async_update", value=99)
            result = await collection.async_update("async_key", data)

            assert result.name == "async_update"
            assert result.value == 99

    @pytest.mark.asyncio
    async def test_async_delete_removes_file(self):
        """Async delete should remove file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            collection = JsonCollection(
                path=tmpdir,
                model=SimpleCollectionModel,
            )
            # Create file
            db = collection.get("to_delete")
            db.update_database(db.get_database())

            # Delete async
            await collection.async_delete("to_delete")
            assert not (Path(tmpdir) / "to_delete.json").exists()

    @pytest.mark.asyncio
    async def test_async_exists_returns_bool(self):
        """Async exists should return boolean."""
        with tempfile.TemporaryDirectory() as tmpdir:
            collection = JsonCollection(
                path=tmpdir,
                model=SimpleCollectionModel,
            )
            db = collection.get("exists_key")
            db.update_database(db.get_database())

            assert await collection.async_exists("exists_key") is True
            assert await collection.async_exists("nonexistent") is False

    @pytest.mark.asyncio
    async def test_async_clear_removes_all(self):
        """Async clear should remove all files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            collection = JsonCollection(
                path=tmpdir,
                model=SimpleCollectionModel,
            )
            # Create files
            for key in ["key1", "key2"]:
                db = collection.get(key)
                db.update_database(db.get_database())

            await collection.async_clear()
            assert collection.list_keys() == []

    @pytest.mark.asyncio
    async def test_async_list_keys_returns_keys(self):
        """Async list_keys should return list of keys."""
        with tempfile.TemporaryDirectory() as tmpdir:
            collection = JsonCollection(
                path=tmpdir,
                model=SimpleCollectionModel,
            )
            # Create files
            for key in ["key1", "key2", "key3"]:
                db = collection.get(key)
                db.update_database(db.get_database())

            keys = await collection.async_list_keys()
            assert sorted(keys) == ["key1", "key2", "key3"]

    @pytest.mark.asyncio
    async def test_async_get_all_returns_dict(self):
        """Async get_all should return dict of all entities."""
        with tempfile.TemporaryDirectory() as tmpdir:
            collection = JsonCollection(
                path=tmpdir,
                model=SimpleCollectionModel,
            )
            # Create entities
            for i, key in enumerate(["key1", "key2"]):
                data = SimpleCollectionModel(name=f"entity_{i}", value=i)
                collection.update(key, data)

            result = await collection.async_get_all()
            assert len(result) == 2
            assert "key1" in result
            assert "key2" in result

    @pytest.mark.asyncio
    async def test_async_update_all_updates_multiple(self):
        """Async update_all should update multiple entities."""
        with tempfile.TemporaryDirectory() as tmpdir:
            collection = JsonCollection(
                path=tmpdir,
                model=SimpleCollectionModel,
            )
            updates = {
                "key1": SimpleCollectionModel(name="first", value=1),
                "key2": SimpleCollectionModel(name="second", value=2),
            }
            result = await collection.async_update_all(updates)

            assert len(result) == 2
            assert result["key1"].name == "first"
            assert result["key2"].name == "second"


class TestJsonCollectionConcurrency:
    """Tests for concurrent async operations."""

    @pytest.mark.asyncio
    async def test_concurrent_updates_serialized(self):
        """Multiple concurrent updates should serialize with lock."""
        with tempfile.TemporaryDirectory() as tmpdir:
            collection = JsonCollection(
                path=tmpdir,
                model=SimpleCollectionModel,
            )

            # Concurrent updates to same key
            tasks = [
                collection.async_update(
                    "concurrent_key",
                    SimpleCollectionModel(name="update_1", value=i),
                )
                for i in range(5)
            ]
            results = await asyncio.gather(*tasks) 

            # All should complete without error
            assert len(results) == 5

    @pytest.mark.asyncio
    async def test_concurrent_reads_with_lock(self):
        """Multiple concurrent reads should be serialized."""
        with tempfile.TemporaryDirectory() as tmpdir:
            collection = JsonCollection(
                path=tmpdir,
                model=SimpleCollectionModel,
            )
            # Create data
            collection.update("key1", SimpleCollectionModel(name="test", value=1))

            # Concurrent reads
            tasks = [collection.async_get_all() for _ in range(5)]
            results = await asyncio.gather(*tasks)

            # All should complete
            assert len(results) == 5


class TestJsonCollectionEdgeCases:
    """Edge case tests for JsonCollection."""

    def test_special_characters_in_keys(self):
        """Should handle special characters in keys (as filenames)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            collection = JsonCollection(
                path=tmpdir,
                model=SimpleCollectionModel,
            )
            # Note: Some characters may not be valid in filenames
            # This tests reasonable alphanumeric+underscore keys
            key = "key_with_underscores_123"
            data = SimpleCollectionModel(name="special", value=1)
            collection.update(key, data)

            assert collection.exists(key)
            assert key in collection.list_keys()

    def test_unicode_in_data(self):
        """Should handle unicode characters in data."""
        with tempfile.TemporaryDirectory() as tmpdir:
            collection = JsonCollection(
                path=tmpdir,
                model=SimpleCollectionModel,
            )
            data = SimpleCollectionModel(name="こんにちは 世界", value=42)
            collection.update("unicode_key", data)

            result = collection.get_all()
            assert result["unicode_key"].name == "こんにちは 世界"

    def test_large_collection(self):
        """Should handle many entities."""
        with tempfile.TemporaryDirectory() as tmpdir:
            collection = JsonCollection(
                path=tmpdir,
                model=SimpleCollectionModel,
            )
            # Create many entities
            num_entities = 100
            for i in range(num_entities):
                key = f"key_{i:04d}"
                data = SimpleCollectionModel(name=f"entity_{i}", value=i)
                collection.update(key, data)

            assert len(collection.list_keys()) == num_entities

    def test_empty_string_key_raises_error(self):
        """Should raise ValueError for empty string key."""
        with tempfile.TemporaryDirectory() as tmpdir:
            collection = JsonCollection(
                path=tmpdir,
                model=SimpleCollectionModel,
            )
            data = SimpleCollectionModel(name="empty_key", value=0)
            
            with pytest.raises(ValueError, match="Key cannot be empty"):
                collection.update("", data)

    def test_whitespace_key_raises_error(self):
        """Should raise ValueError for whitespace-only key."""
        with tempfile.TemporaryDirectory() as tmpdir:
            collection = JsonCollection(
                path=tmpdir,
                model=SimpleCollectionModel,
            )
            data = SimpleCollectionModel(name="whitespace_key", value=0)
            
            with pytest.raises(ValueError, match="Key cannot be empty"):
                collection.update("   ", data)

    def test_delete_with_empty_key_raises_error(self):
        """Should raise ValueError when deleting with empty key."""
        with tempfile.TemporaryDirectory() as tmpdir:
            collection = JsonCollection(
                path=tmpdir,
                model=SimpleCollectionModel,
            )
            with pytest.raises(ValueError, match="Key cannot be empty"):
                collection.delete("")

    def test_exists_with_empty_key_raises_error(self):
        """Should raise ValueError when checking exists with empty key."""
        with tempfile.TemporaryDirectory() as tmpdir:
            collection = JsonCollection(
                path=tmpdir,
                model=SimpleCollectionModel,
            )
            with pytest.raises(ValueError, match="Key cannot be empty"):
                collection.exists("")

    def test_long_key_names(self):
        """Should handle long key names."""
        with tempfile.TemporaryDirectory() as tmpdir:
            collection = JsonCollection(
                path=tmpdir,
                model=SimpleCollectionModel,
            )
            long_key = "a" * 200  # Very long key
            data = SimpleCollectionModel(name="long_key", value=0)
            collection.update(long_key, data)

            assert collection.exists(long_key)
