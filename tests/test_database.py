"""Tests for SQLDatabase async ORM functionality."""

import pytest
import asyncio
import tempfile
from pathlib import Path
from datetime import datetime, date
from pydantic import Field
from jays_tools.sql_database.models import MigratableSQLModel
from src.jays_tools.sql_database.database import SQLDatabase


@pytest.fixture
def temp_db_path():
    """Create temporary database file path for testing."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=True) as f:
        path = Path(f.name)
    # Ensure file doesn't exist at start of test
    if path.exists():
        path.unlink()
    yield path
    # Cleanup
    if path.exists():
        path.unlink()


class TestSQLDatabaseTypeMapping:
    """Test suite for Python type to SQLite type conversion."""

    def test_python_type_to_sqlite_type_int(self):
        """int maps to INTEGER."""
        result = SQLDatabase.python_type_to_sqlite_type(int)
        assert result == "INTEGER"

    def test_python_type_to_sqlite_type_float(self):
        """float maps to REAL."""
        result = SQLDatabase.python_type_to_sqlite_type(float)
        assert result == "REAL"

    def test_python_type_to_sqlite_type_str(self):
        """str maps to TEXT."""
        result = SQLDatabase.python_type_to_sqlite_type(str)
        assert result == "TEXT"

    def test_python_type_to_sqlite_type_bool(self):
        """bool maps to INTEGER."""
        result = SQLDatabase.python_type_to_sqlite_type(bool)
        assert result == "INTEGER"

    def test_python_type_to_sqlite_type_datetime(self):
        """datetime maps to TIMESTAMP."""
        result = SQLDatabase.python_type_to_sqlite_type(datetime)
        assert result == "TIMESTAMP"

    def test_python_type_to_sqlite_type_date(self):
        """date maps to DATE."""
        result = SQLDatabase.python_type_to_sqlite_type(date)
        assert result == "DATE"

    def test_python_type_to_sqlite_type_bytes(self):
        """bytes maps to BLOB."""
        result = SQLDatabase.python_type_to_sqlite_type(bytes)
        assert result == "BLOB"

    def test_python_type_to_sqlite_type_none(self):
        """NoneType maps to NULL."""
        result = SQLDatabase.python_type_to_sqlite_type(type(None))
        assert result == "NULL"

    def test_python_type_to_sqlite_type_list(self):
        """list maps to JSON."""
        result = SQLDatabase.python_type_to_sqlite_type(list)
        assert result == "JSON"

    def test_python_type_to_sqlite_type_dict(self):
        """dict maps to JSON."""
        result = SQLDatabase.python_type_to_sqlite_type(dict)
        assert result == "JSON"

    def test_python_type_to_sqlite_type_set(self):
        """set maps to JSON."""
        result = SQLDatabase.python_type_to_sqlite_type(set)
        assert result == "JSON"

    def test_python_type_to_sqlite_type_tuple(self):
        """tuple maps to JSON."""
        result = SQLDatabase.python_type_to_sqlite_type(tuple)
        assert result == "JSON"

    def test_python_type_to_sqlite_type_unsupported_raises(self):
        """Unsupported type raises ValueError."""
        class CustomType:
            pass

        with pytest.raises(ValueError, match="Unsupported Python type"):
            SQLDatabase.python_type_to_sqlite_type(CustomType)


class TestSQLDatabaseSerialization:
    """Test suite for _serialize_for_db method."""

    def test_serialize_for_db_dict_to_json(self):
        """dict is JSON-encoded."""
        data = {"key": "value", "number": 42}
        result = SQLDatabase._serialize_for_db(data)
        assert isinstance(result, str)
        assert "key" in result

    def test_serialize_for_db_list_to_json(self):
        """list is JSON-encoded."""
        data = [1, 2, 3, "test"]
        result = SQLDatabase._serialize_for_db(data)
        assert isinstance(result, str)
        assert "[1, 2, 3" in result

    def test_serialize_for_db_string_unchanged(self):
        """str is returned as-is."""
        data = "hello world"
        result = SQLDatabase._serialize_for_db(data)
        assert result == "hello world"

    def test_serialize_for_db_int_unchanged(self):
        """int is returned as-is."""
        data = 42
        result = SQLDatabase._serialize_for_db(data)
        assert result == 42

    def test_serialize_for_db_float_unchanged(self):
        """float is returned as-is."""
        data = 3.14
        result = SQLDatabase._serialize_for_db(data)
        assert result == 3.14

    def test_serialize_for_db_none_unchanged(self):
        """None is returned as-is."""
        result = SQLDatabase._serialize_for_db(None)
        assert result is None

    def test_serialize_for_db_nested_dict(self):
        """Nested dict is properly JSON-encoded."""
        data = {"user": {"name": "Alice", "age": 30}}
        result = SQLDatabase._serialize_for_db(data)
        assert isinstance(result, str)
        assert "Alice" in result


class TestSQLDatabaseInitialization:
    """Test suite for database initialization."""

    @pytest.mark.asyncio
    async def test_initialize_creates_database_file(self, temp_db_path):
        """initialize() creates the database file."""
        class UserV1(MigratableSQLModel, table=True):
            name: str = ""

        db = SQLDatabase(temp_db_path, [UserV1])
        assert not temp_db_path.exists()

        await db.initialize()

        assert temp_db_path.exists()

    @pytest.mark.asyncio
    async def test_initialize_sets_initialized_flag(self, temp_db_path):
        """initialize() sets initialized flag to True."""
        class UserV1(MigratableSQLModel, table=True):
            name: str = ""

        db = SQLDatabase(temp_db_path, [UserV1])
        assert db.initialized is False

        await db.initialize()

        assert db.initialized is True

    @pytest.mark.asyncio
    async def test_initialize_idempotent(self, temp_db_path):
        """initialize() is idempotent - can be called multiple times."""
        class UserV1(MigratableSQLModel, table=True):
            name: str = ""

        db = SQLDatabase(temp_db_path, [UserV1])
        await db.initialize()
        await db.initialize()  # Second call should not error
        assert db.initialized is True

    @pytest.mark.asyncio
    async def test_initialize_creates_table_with_all_columns(self, temp_db_path):
        """initialize() creates table with id, model_version, and model fields."""
        class ProductV1(MigratableSQLModel, table=True):
            name: str = ""
            price: float = 0.0
            in_stock: bool = False

        db = SQLDatabase(temp_db_path, [ProductV1])
        await db.initialize()

        # Verify by inserting and reading
        product = ProductV1(name="Laptop", price=999.99, in_stock=True)
        inserted = await db.insert(product)
        assert inserted.id is not None

    @pytest.mark.asyncio
    async def test_initialize_multiple_schemas(self, temp_db_path):
        """initialize() creates tables for all schemas."""
        class UserV1(MigratableSQLModel, table=True):
            username: str = ""

        class PostV1(MigratableSQLModel, table=True):
            title: str = ""

        db = SQLDatabase(temp_db_path, [UserV1, PostV1])
        await db.initialize()

        user = UserV1(username="alice")
        post = PostV1(title="First Post")

        inserted_user = await db.insert(user)
        inserted_post = await db.insert(post)

        assert inserted_user.id is not None
        assert inserted_post.id is not None


class TestSQLDatabaseCRUD:
    """Test suite for Create, Read, Update, Delete operations."""

    @pytest.mark.asyncio
    async def test_insert_sets_auto_increment_id(self, temp_db_path):
        """insert() sets id to auto-incremented value."""
        class ItemV1(MigratableSQLModel, table=True):
            name: str = ""

        db = SQLDatabase(temp_db_path, [ItemV1])
        item = ItemV1(name="Widget")

        inserted = await db.insert(item)

        assert inserted.id is not None
        assert inserted.id > 0
        assert isinstance(inserted.id, int)

    @pytest.mark.asyncio
    async def test_insert_sequential_ids(self, temp_db_path):
        """insert() assigns sequential IDs."""
        class ItemV1(MigratableSQLModel, table=True):
            name: str = ""

        db = SQLDatabase(temp_db_path, [ItemV1])
        item1 = await db.insert(ItemV1(name="First"))
        item2 = await db.insert(ItemV1(name="Second"))
        item3 = await db.insert(ItemV1(name="Third"))

        assert item1.id == 1
        assert item2.id == 2
        assert item3.id == 3

    @pytest.mark.asyncio
    async def test_insert_multiple_fields(self, temp_db_path):
        """insert() stores all model fields."""
        class UserV1(MigratableSQLModel, table=True):
            username: str = ""
            email: str = ""
            age: int = 0

        db = SQLDatabase(temp_db_path, [UserV1])
        user = UserV1(username="bob", email="bob@example.com", age=30)

        inserted = await db.insert(user)

        results = await db.find(UserV1, {"id": inserted.id})
        assert len(results) == 1
        assert results[0].username == "bob"
        assert results[0].email == "bob@example.com"
        assert results[0].age == 30

    @pytest.mark.asyncio
    async def test_find_empty_results(self, temp_db_path):
        """find() returns empty list when no matches."""
        class UserV1(MigratableSQLModel, table=True):
            username: str = ""

        db = SQLDatabase(temp_db_path, [UserV1])
        results = await db.find(UserV1, {"username": "nonexistent"})

        assert results == []

    @pytest.mark.asyncio
    async def test_find_single_match(self, temp_db_path):
        """find() returns matching entry."""
        class UserV1(MigratableSQLModel, table=True):
            username: str = ""

        db = SQLDatabase(temp_db_path, [UserV1])
        await db.insert(UserV1(username="alice"))

        results = await db.find(UserV1, {"username": "alice"})

        assert len(results) == 1
        assert results[0].username == "alice"

    @pytest.mark.asyncio
    async def test_find_multiple_matches(self, temp_db_path):
        """find() returns all matching entries."""
        class TagV1(MigratableSQLModel, table=True):
            category: str = ""
            label: str = ""

        db = SQLDatabase(temp_db_path, [TagV1])
        await db.insert(TagV1(category="color", label="red"))
        await db.insert(TagV1(category="color", label="blue"))
        await db.insert(TagV1(category="size", label="large"))

        results = await db.find(TagV1, {"category": "color"})

        assert len(results) == 2

    @pytest.mark.asyncio
    async def test_find_by_id(self, temp_db_path):
        """find() can filter by id."""
        class ItemV1(MigratableSQLModel, table=True):
            name: str = ""

        db = SQLDatabase(temp_db_path, [ItemV1])
        item = await db.insert(ItemV1(name="Widget"))

        results = await db.find(ItemV1, {"id": item.id})

        assert len(results) == 1
        assert results[0].id == item.id

    @pytest.mark.asyncio
    async def test_find_empty_where_dict(self, temp_db_path):
        """find() with empty where dict returns all entries."""
        class DocV1(MigratableSQLModel, table=True):
            title: str = ""

        db = SQLDatabase(temp_db_path, [DocV1])
        await db.insert(DocV1(title="Doc1"))
        await db.insert(DocV1(title="Doc2"))

        results = await db.find(DocV1, {})

        assert len(results) == 2

    @pytest.mark.asyncio
    async def test_update_modifies_entry(self, temp_db_path):
        """update() modifies entry in database."""
        class UserV1(MigratableSQLModel, table=True):
            name: str = ""
            email: str = ""

        db = SQLDatabase(temp_db_path, [UserV1])
        user = await db.insert(UserV1(name="Alice", email="alice@old.com"))

        user.email = "alice@new.com"
        updated = await db.update(user)

        assert updated.email == "alice@new.com"

        results = await db.find(UserV1, {"id": user.id})
        assert results[0].email == "alice@new.com"

    @pytest.mark.asyncio
    async def test_update_without_id_raises(self, temp_db_path):
        """update() without id raises ValueError."""
        class UserV1(MigratableSQLModel, table=True):
            name: str = ""

        db = SQLDatabase(temp_db_path, [UserV1])
        user = UserV1(name="Bob")  # No ID

        with pytest.raises(ValueError, match="Cannot update entry without an ID"):
            await db.update(user)

    @pytest.mark.asyncio
    async def test_update_preserves_other_entries(self, temp_db_path):
        """update() doesn't affect other entries."""
        class ItemV1(MigratableSQLModel, table=True):
            name: str = ""
            quantity: int = 0

        db = SQLDatabase(temp_db_path, [ItemV1])
        item1 = await db.insert(ItemV1(name="A", quantity=1))
        item2 = await db.insert(ItemV1(name="B", quantity=2))

        item1.quantity = 10
        await db.update(item1)

        results = await db.find(ItemV1, {"id": item2.id})
        assert results[0].quantity == 2

    @pytest.mark.asyncio
    async def test_delete_removes_entry(self, temp_db_path):
        """delete() removes entry from database."""
        class ItemV1(MigratableSQLModel, table=True):
            name: str = ""

        db = SQLDatabase(temp_db_path, [ItemV1])
        item = await db.insert(ItemV1(name="ToDelete"))

        await db.delete(item)

        results = await db.find(ItemV1, {"id": item.id})
        assert len(results) == 0

    @pytest.mark.asyncio
    async def test_delete_without_id_raises(self, temp_db_path):
        """delete() without id raises ValueError."""
        class ItemV1(MigratableSQLModel, table=True):
            name: str = ""

        db = SQLDatabase(temp_db_path, [ItemV1])
        item = ItemV1(name="NoID")  # No ID

        with pytest.raises(ValueError, match="Cannot delete entry without an ID"):
            await db.delete(item)

    @pytest.mark.asyncio
    async def test_delete_preserves_other_entries(self, temp_db_path):
        """delete() doesn't affect other entries."""
        class ItemV1(MigratableSQLModel, table=True):
            name: str = ""

        db = SQLDatabase(temp_db_path, [ItemV1])
        item1 = await db.insert(ItemV1(name="Keep"))
        item2 = await db.insert(ItemV1(name="Delete"))

        await db.delete(item2)

        results = await db.find(ItemV1, {})
        assert len(results) == 1
        assert results[0].id == item1.id


class TestSQLDatabaseDataTypes:
    """Test suite for various data types in models."""

    @pytest.mark.asyncio
    async def test_insert_and_retrieve_string(self, temp_db_path):
        """String fields are stored and retrieved correctly."""
        class DocV1(MigratableSQLModel, table=True):
            content: str = ""

        db = SQLDatabase(temp_db_path, [DocV1])
        doc = DocV1(content="Hello, World!")
        inserted = await db.insert(doc)

        results = await db.find(DocV1, {"id": inserted.id})
        assert results[0].content == "Hello, World!"

    @pytest.mark.asyncio
    async def test_insert_and_retrieve_integer(self, temp_db_path):
        """Integer fields are stored and retrieved correctly."""
        class CounterV1(MigratableSQLModel, table=True):
            value: int = 0

        db = SQLDatabase(temp_db_path, [CounterV1])
        counter = CounterV1(value=42)
        inserted = await db.insert(counter)

        results = await db.find(CounterV1, {"id": inserted.id})
        assert results[0].value == 42

    @pytest.mark.asyncio
    async def test_insert_and_retrieve_float(self, temp_db_path):
        """Float fields are stored and retrieved correctly."""
        class MeasureV1(MigratableSQLModel, table=True):
            distance: float = 0.0

        db = SQLDatabase(temp_db_path, [MeasureV1])
        measure = MeasureV1(distance=3.14159)
        inserted = await db.insert(measure)

        results = await db.find(MeasureV1, {"id": inserted.id})
        assert abs(results[0].distance - 3.14159) < 0.00001

    @pytest.mark.asyncio
    async def test_insert_and_retrieve_list(self, temp_db_path):
        """List fields are JSON-encoded and deserialized."""
        class ConfigV1(MigratableSQLModel, table=True):
            options: list[str] = Field(default_factory=list)

        db = SQLDatabase(temp_db_path, [ConfigV1])
        config = ConfigV1(options=["a", "b", "c"])
        inserted = await db.insert(config)

        results = await db.find(ConfigV1, {"id": inserted.id})
        assert results[0].options == ["a", "b", "c"]

    @pytest.mark.asyncio
    async def test_insert_and_retrieve_dict(self, temp_db_path):
        """Dict fields are JSON-encoded and deserialized."""
        class SettingV1(MigratableSQLModel, table=True):
            config: dict = Field(default_factory=dict)

        db = SQLDatabase(temp_db_path, [SettingV1])
        setting = SettingV1(config={"theme": "dark", "language": "en"})
        inserted = await db.insert(setting)

        results = await db.find(SettingV1, {"id": inserted.id})
        assert results[0].config == {"theme": "dark", "language": "en"}

    @pytest.mark.asyncio
    async def test_insert_and_retrieve_bool(self, temp_db_path):
        """Bool fields are stored as INTEGER and retrieved as bool."""
        class FeatureV1(MigratableSQLModel, table=True):
            enabled: bool = False

        db = SQLDatabase(temp_db_path, [FeatureV1])
        feature = FeatureV1(enabled=True)
        inserted = await db.insert(feature)

        results = await db.find(FeatureV1, {"id": inserted.id})
        assert results[0].enabled is True

    @pytest.mark.asyncio
    async def test_insert_and_retrieve_optional_field(self, temp_db_path):
        """Optional fields can be None."""
        class ProfileV1(MigratableSQLModel, table=True):
            name: str = ""
            bio: str | None = None

        db = SQLDatabase(temp_db_path, [ProfileV1])
        profile = ProfileV1(name="Charlie")
        inserted = await db.insert(profile)

        results = await db.find(ProfileV1, {"id": inserted.id})
        assert results[0].bio is None


class TestSQLDatabaseSchemaEvolution:
    """Test suite for schema evolution (ALTER TABLE)."""

    @pytest.mark.asyncio
    async def test_schema_evolution_add_column(self, temp_db_path):
        """Schema evolution adds new column with ALTER TABLE."""
        class UserV1(MigratableSQLModel, table=True):
            name: str = ""

        db1 = SQLDatabase(temp_db_path, [UserV1])
        user1 = await db1.insert(UserV1(name="Alice"))
        user1_id = user1.id

        # Now redefine with V2
        class UserV2(MigratableSQLModel, table=True, previous_model=UserV1):
            name: str = ""
            email: str = "default@example.com"

            @classmethod
            def migrate(cls, previous: UserV1) -> "UserV2":
                data = previous.model_dump()
                data["email"] = "default@example.com"
                return cls.from_migration(data)

        # Re-initialize with new schema
        db2 = SQLDatabase(temp_db_path, [UserV2])
        db2.initialized = False  # Reset so it re-initializes
        await db2.initialize()

        # Verify old data still accessible
        results = await db2.find(UserV2, {"id": user1_id})
        assert len(results) == 1
        assert results[0].name == "Alice"

    @pytest.mark.asyncio
    async def test_schema_evolution_insert_new_version(self, temp_db_path):
        """After schema evolution, can insert new version."""
        class ItemV1(MigratableSQLModel, table=True):
            name: str = ""

        db1 = SQLDatabase(temp_db_path, [ItemV1])
        await db1.initialize()

        class ItemV2(MigratableSQLModel, table=True, previous_model=ItemV1):
            name: str = ""
            price: float = 0.0

            @classmethod
            def migrate(cls, previous: ItemV1) -> "ItemV2":
                data = previous.model_dump()
                data["price"] = 0.0
                return cls.from_migration(data)

        db2 = SQLDatabase(temp_db_path, [ItemV2])
        db2.initialized = False
        await db2.initialize()

        # Insert new item with V2 fields
        item = ItemV2(name="Laptop", price=999.99)
        inserted = await db2.insert(item)

        results = await db2.find(ItemV2, {"id": inserted.id})
        assert results[0].price == 999.99
