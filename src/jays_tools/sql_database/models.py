import re
from typing import Any, ClassVar, Self, Type

from pydantic import BaseModel, Field, model_validator
from pydantic.fields import FieldInfo


VERSION_REGEX = re.compile(r".*[vV](?P<model_number>\d*)$")


class MigratableSQLModel(BaseModel):
    id: int | None = Field(default=None, description="Auto-increment database ID")
    model_version: int = 1

    __table_name__: ClassVar[str]
    __model_version__: ClassVar[int] = 1  # Private class var for version tracking
    __previous_model__: ClassVar[Type['MigratableSQLModel'] | None] = None

    def __init_subclass__(
        cls, 
        previous_model: Type['MigratableSQLModel'] | None = None, 
        **kwargs
    ):
        if "table" in kwargs:
            del kwargs["table"]
        
        super().__init_subclass__(**kwargs)

        match = VERSION_REGEX.match(cls.__name__)
        if not match:
            raise ValueError(
                "Class name must end with a version number, e.g. ProfileV1"
            )

        version = int(match.group("model_number"))
        cls.__model_version__ = version
        cls.model_version = version
        cls.__table_name__ = re.sub(r"[vV]\d+$", "", cls.__name__)
        
        # Enforce that all fields have defaults (except id and model_version)
        fields_without_defaults = []
        for field_name in cls.__annotations__:
            if field_name not in ('id', 'model_version'):
                # Check if this field has a default value
                if not hasattr(cls, field_name):
                    fields_without_defaults.append(field_name)
        
        if fields_without_defaults:
            raise ValueError(
                f"{cls.__name__} fields must have defaults (required for SQL table schema inference). "
                f"Fields without defaults: {', '.join(fields_without_defaults)}\n"
                f"Example: {fields_without_defaults[0]}: str = \"\""
            )
        
        if previous_model is None:
            cls.__previous_model__ = None
            return

        if not issubclass(previous_model, MigratableSQLModel):
            raise ValueError("previous_model must be a subclass of MigratableSQLModel")
        
        if previous_model.__table_name__ != cls.__table_name__:
            raise ValueError(
                f"previous_model must have the same table name as the current model. "
                f"Expected {cls.__table_name__}, got {previous_model.__table_name__}"
            )
        
        # Use __model_version__ to avoid Pydantic field descriptor issues
        valid_model_increment = (cls.__model_version__ - previous_model.__model_version__) == 1
        if not valid_model_increment:
            raise ValueError(
                f"Model version must increment by 1 from the previous model. "
                f"Expected {previous_model.__model_version__ + 1}, got {cls.__model_version__}"
            )
        
        # Check if migrate() has been implemented (exists in cls.__dict__, not inherited)
        if previous_model is not None and "migrate" not in cls.__dict__:
            raise TypeError(
                f"{cls.__name__} must implement migrate() classmethod since previous_model={previous_model.__name__}"
            )

        cls.__previous_model__ = previous_model

    @classmethod
    def get_model_from_version(cls, version: int) -> Type['MigratableSQLModel'] | None:
        current_model = cls
        while current_model is not None:
            if current_model.__model_version__ == version:
                return current_model
            current_model = current_model.__previous_model__
        
        return None

    @model_validator(mode="before")
    @classmethod
    def run_migrations(cls, data: Any) -> Any:
        if not isinstance(data, dict) or not data:
            return data

        # Check if we're already in a migration (skip if so)
        if data.get("__skip_migrations__", False):
            data.pop("__skip_migrations__", None)
            return data

        # Get model_version from data, but only proceed with migrations if explicitly provided
        # If model_version isn't in the original data, this is a new instance, don't migrate
        if "model_version" not in data:
            # New instance being created, don't run migrations
            data["model_version"] = cls.__model_version__
            return data

        old_model_version = data.get("model_version", cls.__model_version__)
        current_model_version = cls.__model_version__
        
        # If already at current version, no migration needed
        if old_model_version == current_model_version:
            return data

        while old_model_version < current_model_version:
            old_model = cls.get_model_from_version(old_model_version)
            next_model = cls.get_model_from_version(old_model_version + 1)
            
            if old_model is None:
                raise ValueError(
                    f"No model found for version {old_model_version} during migration. "
                    f"Cannot migrate to version {current_model_version}"
                )
            
            if next_model is None:
                raise ValueError(
                    f"No model found for version {old_model_version + 1} during migration. "
                    f"Cannot migrate to version {current_model_version}"
                )
            
            # Use from_migration to bypass validators and avoid recursion
            old_instance = old_model.from_migration(data)
            # Call the NEXT model's migrate method to move from old to next version
            migrated_instance = next_model.migrate(old_instance)
            data = migrated_instance.model_dump()
            # Explicitly set model_version for current migration step
            data["model_version"] = old_model_version + 1
            # Set flag to prevent re-triggering migration in nested calls
            data["__skip_migrations__"] = True
            old_model_version += 1
            
        data.pop("__skip_migrations__", None)
        return data
    
    @classmethod
    def from_migration(cls, data: dict[str, Any]) -> Self:
        """
        Construct an instance from migration data, bypassing validators.
        
        This is used internally during migrations to avoid triggering recursive
        validators when constructing intermediate model instances.
        """
        return cls.model_construct(**data)

    @classmethod
    def migrate(cls, previous: 'MigratableSQLModel') -> 'MigratableSQLModel':
        """Convert from previous model to current model. Must be implemented if there is a previous model."""
        raise NotImplementedError(
            f"{cls.__name__} must implement migrate() to migrate from {previous.__class__.__name__}"
        )

    @classmethod
    def get_table_name(cls) -> str:
        return cls.__table_name__

    @classmethod
    def get_fields(cls) -> dict[str, FieldInfo]:
        """Get model fields from the class (non-deprecated way)."""
        return cls.model_fields
