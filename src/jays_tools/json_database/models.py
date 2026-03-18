import functools
from typing import Any, ClassVar, TypeVar

from pydantic import BaseModel, model_validator

T = TypeVar("T", bound=dict[str, Any])

class MigratableModel(BaseModel):
    """Base model with linear migrations using previous_model + migrate_from_previous.

    When creating a new version, declare the previous version using `previous_model=`:
        class UserV2(MigratableModel, previous_model=UserV1):
    
    Then implement the staticmethod `migrate_from_previous(previous_data)` to transform old data:
        @staticmethod
        def migrate_from_previous(previous_data: dict[str, Any]) -> dict[str, Any]:
            # Transform data from UserV1 format to UserV2 format
            previous_data["email"] = ""
            return previous_data

    Example:
        class UserV1(MigratableModel):
            name: str = ""

        class UserV2(MigratableModel, previous_model=UserV1):
            name: str = ""
            email: str = ""

            @staticmethod
            def migrate_from_previous(previous_data: dict[str, Any]) -> dict[str, Any]:
                previous_data["email"] = ""
                return previous_data
    """

    _previous_model: ClassVar[type["MigratableModel"] | None] = None

    def __init_subclass__(
        cls,
        previous_model: type["MigratableModel"] | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init_subclass__(**kwargs)

        if "model_version" in cls.__dict__ or "model_version" in cls.__annotations__:
            raise TypeError(
                f"{cls.__name__} cannot define model_version; it is auto-managed by MigratableModel"
            )

        if previous_model is not None and not issubclass(previous_model, MigratableModel):
            raise TypeError(
                f"{cls.__name__} previous_model must inherit from MigratableModel"
            )

        cls._previous_model = previous_model

        if previous_model is not None and "migrate_from_previous" not in cls.__dict__:
            raise TypeError(
                f"{cls.__name__} must define a staticmethod:\n"
                f"  @staticmethod\n"
                f"  def migrate_from_previous(previous_data: dict[str, Any]) -> dict[str, Any]:\n"
                f"      # Transform previous_data from previous version format\n"
                f"      return previous_data"
            )

    # Auto-managed version field. Users do not need to set/increment this manually.
    model_version: int = 1

    @classmethod
    @functools.cache
    def get_version_chain(cls) -> tuple[type["MigratableModel"], ...]:
        chain: list[type["MigratableModel"]] = []
        current: type[MigratableModel] | None = cls
        visited: set[type["MigratableModel"]] = set()

        while current is not None:
            if current in visited:
                # Detect and prevent cycles in the migration chain (including self-references).
                raise TypeError(
                    "Detected a cycle in the MigratableModel version chain involving "
                    f"{current.__name__}. Ensure 'previous_model' creates a linear, "
                    "acyclic chain of model versions."
                )
            visited.add(current)
            chain.append(current)
            current = current._previous_model

        chain.reverse()
        return tuple(chain)

    @classmethod
    @functools.cache
    def get_model_version(cls) -> int:
        return len(cls.get_version_chain())

    @model_validator(mode="before")
    @classmethod
    def run_migrations(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data

        # Happens during _JsonDatabase init model validation.
        if not data:
            return data

        chain = cls.get_version_chain()
        latest_version = len(chain)

        file_version = data.get("model_version", 1)
        # Validation to prevent invalid version numbers that could cause issues in migration logic below.
        if not isinstance(file_version, int) or file_version < 1:
            raise ValueError(
                "model_version must be a positive integer in persisted data"
            )

        # Prevents being on V5 of a code base, going back to V3 code but keeping V5 data and
        # trying to run V3 code against V5 data.
        if file_version > latest_version:
            raise ValueError(
                f"Data model_version {file_version} is newer than supported version {latest_version} "
                f"for model {cls.__name__}"
            )

        for next_index in range(file_version, latest_version):
            model_for_step = chain[next_index]
            migrate_func = getattr(model_for_step, "migrate_from_previous", None)

            if migrate_func is None:
                raise ValueError(
                    f"Missing migrate_from_previous on {model_for_step.__name__} "
                    "for a required migration step"
                )

            data = migrate_func(data)

        # Ensure serialized data always contains the current auto-managed version.
        data["model_version"] = cls.get_model_version()

        return data

    # Prevents model_version from staying at the default value
    # It increments the version based off the length of the model chain, 
    # so it will always be in sync with the current version of the model.
    def model_post_init(self, __context: Any) -> None:
        # Keep instance version in sync with class chain depth.
        self.model_version = type(self).get_model_version()