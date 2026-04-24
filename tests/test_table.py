"""Tests for MigratableRow model versioning and migration system."""

import pytest
from pydantic import Field
from jays_tools.sql_database.row import MigratableRow


class TestMigratableRowClassValidation:
    """Test suite for MigratableRow class definition and validation."""

    def test_init_subclass_valid_class_name_v1(self):
        """Valid class name with V1 suffix is accepted."""
        class UserV1(MigratableRow):
            name: str = ""
            email: str = ""

        # Check class attributes that are set in __init_subclass__
        assert UserV1.__table_name__ == "User"
        assert UserV1.__previous_model__ is None

    def test_init_subclass_valid_class_name_v2(self):
        """Valid class name with V2 suffix is accepted."""
        class UserV1(MigratableRow):
            name: str = ""

        class UserV2(MigratableRow, previous_model=UserV1):
            name: str = ""
            age: int = 0

            @classmethod
            def migrate(cls, previous: MigratableRow) -> "UserV2":
                data = previous.model_dump()
                data["age"] = 0
                return cls(**data)

        # Check that class was accepted and table name is correct
        assert UserV2.__table_name__ == "User"
        assert UserV2.__previous_model__ is UserV1

    def test_init_subclass_invalid_class_name_no_version(self):
        """Class name without version number raises ValueError."""
        with pytest.raises(ValueError, match="must end with a version number"):
            class User(MigratableRow):
                name: str = ""

    def test_init_subclass_invalid_class_name_lowercase_v(self):
        """Class name with lowercase 'v' is valid."""
        class Userv1(MigratableRow):
            name: str = ""

        assert Userv1.__table_name__ == "User"

    def test_init_subclass_invalid_class_name_uppercase_v(self):
        """Class name with uppercase 'V' is valid."""
        class UserV1(MigratableRow):
            name: str = ""

        assert UserV1.__table_name__ == "User"

    def test_init_subclass_previous_model_not_subclass_raises(self):
        """previous_model that isn't MigratableRow raises ValueError."""
        class NotMigratableRow:
            pass

        with pytest.raises(ValueError, match="must be a subclass of MigratableRow"):
            class UserV2(MigratableRow, previous_model=NotMigratableRow):
                name: str = ""

    def test_init_subclass_previous_model_different_table_name_raises(self):
        """previous_model with different table name raises ValueError."""
        class UserV1(MigratableRow):
            name: str = ""

        with pytest.raises(ValueError, match="same table name"):
            class ProfileV2(MigratableRow, previous_model=UserV1):
                name: str = ""

                @classmethod
                def migrate(cls, previous: MigratableRow) -> "ProfileV2":
                    return cls(**previous.model_dump())

    def test_init_subclass_version_not_incremented_by_one_raises(self):
        """Version increment not by 1 raises ValueError."""
        class UserV1(MigratableRow):
            name: str = ""

        with pytest.raises(ValueError, match="increment by 1"):
            class UserV3(MigratableRow, previous_model=UserV1):
                name: str = ""

                @classmethod
                def migrate(cls, previous: MigratableRow) -> "UserV3":
                    return cls(**previous.model_dump())

    def test_init_subclass_missing_migrate_raises_type_error(self):
        """previous_model without migrate() implementation raises TypeError."""
        class UserV1(MigratableRow):
            name: str = ""

        with pytest.raises(TypeError, match="must implement migrate"):
            class UserV2(MigratableRow, previous_model=UserV1):
                name: str = ""
                # Missing migrate() method

    def test_init_subclass_field_without_default_raises_value_error(self):
        """Field without default value raises ValueError."""
        with pytest.raises(ValueError, match="fields must have defaults"):
            class UserV1(MigratableRow):
                name: str  # No default value!

    def test_init_subclass_field_without_default_error_message_is_helpful(self):
        """Error message for missing defaults is specific and helpful."""
        with pytest.raises(ValueError) as exc_info:
            class UserV1(MigratableRow):
                email: str  # No default
        
        error_msg = str(exc_info.value)
        assert "email" in error_msg
        assert "required for SQL table schema inference" in error_msg
        assert "Example:" in error_msg

    def test_init_subclass_multiple_fields_without_defaults_lists_all(self):
        """All fields without defaults are listed in error message."""
        with pytest.raises(ValueError) as exc_info:
            class UserV1(MigratableRow):
                username: str  # No default
                email: str     # No default
        
        error_msg = str(exc_info.value)
        assert "username" in error_msg
        assert "email" in error_msg

    def test_init_subclass_id_field_exempt_from_default_requirement(self):
        """id field is exempt from default requirement (already has default)."""
        # Should not raise - id has a default
        class UserV1(MigratableRow):
            name: str = ""
        
        assert UserV1.__table_name__ == "User"

    def test_init_subclass_model_version_exempt_from_default_requirement(self):
        """model_version field is exempt from default requirement (already has default)."""
        # Should not raise - model_version has a default
        class UserV1(MigratableRow):
            name: str = ""
        
        assert UserV1.__table_name__ == "User"

    def test_init_subclass_all_fields_with_defaults_succeeds(self):
        """Class with all fields having defaults is accepted."""
        class UserV1(MigratableRow):
            name: str = ""
            age: int = 0
            email: str = "default@example.com"
            tags: list[str] = Field(default_factory=list)
        
        assert UserV1.__table_name__ == "User"
        assert UserV1.__model_version__ == 1

    def test_init_subclass_optional_field_with_none_default_is_valid(self):
        """Optional field with None default is valid."""
        class UserV1(MigratableRow):
            name: str = ""
            bio: str | None = None
        
        assert UserV1.__table_name__ == "User"


class TestMigratableRowBasicMethods:
    """Test suite for basic MigratableRow methods."""

    def test_get_table_name(self):
        """get_table_name returns table name without version suffix."""
        class ProfileV1(MigratableRow):
            username: str = ""

        assert ProfileV1.get_table_name() == "Profile"

    def test_get_table_name_multiple_versions(self):
        """get_table_name returns same name across versions."""
        class ProductV1(MigratableRow):
            name: str = ""

        class ProductV2(MigratableRow, previous_model=ProductV1):
            name: str = ""
            price: float = 0.0

            @classmethod
            def migrate(cls, previous: MigratableRow) -> "ProductV2":
                data = previous.model_dump()
                data["price"] = 0.0
                return cls(**data)

        assert ProductV1.get_table_name() == ProductV2.get_table_name()

    def test_get_fields_returns_model_fields(self):
        """get_fields returns model field info."""
        class PersonV1(MigratableRow):
            first_name: str = ""
            age: int = 0

        fields = PersonV1.get_fields()
        assert "first_name" in fields
        assert "age" in fields
        assert "id" in fields
        assert "model_version" in fields

    def test_id_field_auto_increment(self):
        """id field defaults to None and is optional."""
        class ItemV1(MigratableRow):
            name: str = ""

        item = ItemV1(name="test")
        assert item.id is None

    def test_id_field_set_manually(self):
        """id field can be set manually."""
        class ItemV1(MigratableRow):
            name: str = ""

        item = ItemV1(name="test", id=42)
        assert item.id == 42

    def test_model_version_defaults_to_one(self):
        """model_version defaults to 1."""
        class DocV1(MigratableRow):
            title: str = ""

        doc = DocV1(title="test")
        assert doc.model_version == 1


class TestMigratableRowGetModelFromVersion:
    """Test suite for get_model_from_version traversal."""

    def test_get_model_from_version_same_version(self):
        """get_model_from_version returns self when version matches."""
        class ArticleV1(MigratableRow):
            title: str = ""

        result = ArticleV1.get_model_from_version(1)
        assert result is ArticleV1

    def test_get_model_from_version_previous_model(self):
        """get_model_from_version traverses to previous model."""
        class ArticleV1(MigratableRow):
            title: str = ""

        class ArticleV2(MigratableRow, previous_model=ArticleV1):
            title: str = ""
            author: str = ""

            @classmethod
            def migrate(cls, previous: MigratableRow) -> "ArticleV2":
                data = previous.model_dump()
                data["author"] = "Unknown"
                return cls(**data)

        result = ArticleV2.get_model_from_version(1)
        assert result is ArticleV1

    def test_get_model_from_version_long_chain(self):
        """get_model_from_version traverses long version chain."""
        class EventV1(MigratableRow):
            name: str = ""

        class EventV2(MigratableRow, previous_model=EventV1):
            name: str = ""
            date: str = ""

            @classmethod
            def migrate(cls, previous: MigratableRow) -> "EventV2":
                data = previous.model_dump()
                data["date"] = ""
                return cls(**data)

        class EventV3(MigratableRow, previous_model=EventV2):
            name: str = ""
            date: str = ""
            location: str = ""

            @classmethod
            def migrate(cls, previous: MigratableRow) -> "EventV3":
                data = previous.model_dump()
                data["location"] = ""
                return cls(**data)

        assert EventV3.get_model_from_version(1) is EventV1
        assert EventV3.get_model_from_version(2) is EventV2
        assert EventV3.get_model_from_version(3) is EventV3

    def test_get_model_from_version_not_found_returns_none(self):
        """get_model_from_version returns None if version doesn't exist."""
        class CommentV1(MigratableRow):
            text: str = ""

        result = CommentV1.get_model_from_version(99)
        assert result is None


class TestMigratableRowMigration:
    """Test suite for model migration via validator."""

    def test_run_migrations_no_migration_needed(self):
        """Data with current version passes through unchanged."""
        class TagV1(MigratableRow):
            label: str = ""

        data = {"label": "python", "model_version": 1}
        result = TagV1.model_validate(data)
        assert result.label == "python"
        assert result.model_version == 1

    def test_run_migrations_single_version_gap(self):
        """Data from V1 migrates to V2 successfully."""
        class CategoryV1(MigratableRow):
            name: str = ""

        class CategoryV2(MigratableRow, previous_model=CategoryV1):
            name: str = ""
            icon: str = ""

            @classmethod
            def migrate(cls, previous: CategoryV1) -> "CategoryV2":
                data = previous.model_dump()
                data["icon"] = "default"
                return cls.from_migration(data)

        old_data = {"name": "Tech", "model_version": 1}
        result = CategoryV2.model_validate(old_data)
        assert result.name == "Tech"
        assert result.icon == "default"
        assert result.model_version == 2

    def test_run_migrations_multi_version_gap(self):
        """Data from V1 migrates through V2, V3 chain."""
        class TagV1(MigratableRow):
            name: str = ""

        class TagV2(MigratableRow, previous_model=TagV1):
            name: str = ""
            color: str = ""

            @classmethod
            def migrate(cls, previous: TagV1) -> "TagV2":
                data = previous.model_dump()
                data["color"] = "gray"
                return cls.from_migration(data)

        class TagV3(MigratableRow, previous_model=TagV2):
            name: str = ""
            color: str = ""
            active: bool = False

            @classmethod
            def migrate(cls, previous: TagV2) -> "TagV3":
                data = previous.model_dump()
                data["active"] = True
                return cls.from_migration(data)

        old_data = {"name": "Python", "model_version": 1}
        result = TagV3.model_validate(old_data)
        assert result.name == "Python"
        assert result.color == "gray"
        assert result.active is True

    def test_run_migrations_missing_model_version_raises(self):
        """Data with gap to non-existent version raises ValueError."""
        class ItemV2(MigratableRow):
            name: str = ""

        with pytest.raises(ValueError, match="No model found for version"):
            ItemV2.model_validate({"name": "test", "model_version": 1})

    def test_run_migrations_with_custom_validation(self):
        """Migration works with field validation and defaults."""
        class UserV1(MigratableRow):
            username: str = Field(min_length=1)

        class UserV2(MigratableRow, previous_model=UserV1):
            username: str = Field(min_length=1)
            email: str = Field(default="noemail@example.com")

            @classmethod
            def migrate(cls, previous: UserV1) -> "UserV2":
                # Use model_construct to avoid re-triggering validator
                return cls.model_construct(**previous.model_dump())

        result = UserV2.model_validate({"username": "alice", "model_version": 1})
        assert result.username == "alice"
        assert result.email == "noemail@example.com"


class TestMigratableRowEdgeCases:
    """Test suite for edge cases and special scenarios."""

    def test_multiple_independent_models(self):
        """Multiple independent versioned models can coexist."""
        class UserV1(MigratableRow):
            name: str = ""

        class PostV1(MigratableRow):
            title: str = ""

        assert UserV1.get_table_name() == "User"
        assert PostV1.get_table_name() == "Post"

    def test_model_version_in_serialization(self):
        """model_version is included in model_dump."""
        class DocV1(MigratableRow):
            content: str = ""

        doc = DocV1(content="test", id=1)
        dumped = doc.model_dump()
        assert dumped["model_version"] == 1
        assert dumped["id"] == 1
        assert dumped["content"] == "test"

    def test_id_none_in_serialization(self):
        """id=None is included in model_dump."""
        class DocV1(MigratableRow):
            content: str = ""

        doc = DocV1(content="test")
        dumped = doc.model_dump()
        assert dumped["id"] is None

    def test_complex_type_fields(self):
        """Complex field types work with MigratableRow."""
        from datetime import datetime

        class EventV1(MigratableRow):
            title: str = ""
            timestamp: datetime = Field(default_factory=lambda: datetime(2024, 1, 1))
            tags: list[str] = Field(default_factory=list)

        event = EventV1(
            title="Meeting",
            timestamp=datetime(2024, 1, 1, 12, 0),
            tags=["work", "important"],
        )
        assert event.title == "Meeting"
        assert len(event.tags) == 2

    def test_optional_fields(self):
        """Optional fields work correctly."""
        class ProfileV1(MigratableRow):
            name: str = ""
            bio: str | None = None

        profile = ProfileV1(name="Alice")
        assert profile.bio is None

        profile2 = ProfileV1(name="Bob", bio="Developer")
        assert profile2.bio == "Developer"
