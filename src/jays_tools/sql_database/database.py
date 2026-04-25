import json
from pathlib import Path
from typing import Any, Type, TypeVar, Union

import aiosqlite

from .filters import ComparisonFilter, Filter
from .models import MigratableSQLModel

T = TypeVar("T", bound=MigratableSQLModel)

class SQLDatabase:
    # TODO: support other databases like Postgres, MySQL, for now just support SQLite
    
    def __init__(
        self, 
        sqlite_database_path: str | Path,
        schemas: list[Type[MigratableSQLModel]],
    ) -> None:
    
        self.sqlite_database_path = Path(sqlite_database_path)
        self.schemas = schemas
        self.initialized = False

    @staticmethod
    def _get_sql_type_from_json_value(value: Any) -> str:
        """Determine SQLite type from an actual JSON value (after model_dump)."""
        if value is None:
            return "TEXT"  # NULL columns default to TEXT for new rows
        elif isinstance(value, bool):
            return "INTEGER"
        elif isinstance(value, int):
            return "INTEGER"
        elif isinstance(value, float):
            return "REAL"
        elif isinstance(value, str):
            return "TEXT"
        elif isinstance(value, (list, dict)):
            return "JSON"
        else:
            return "JSON"  # Safe default for anything Pydantic serialized
    
    @staticmethod
    def python_type_to_sqlite_type(python_type: Type[Any]) -> str:
        """Map Python types to SQLite types (for testing/backwards compatibility)."""
        # Simple mapping for type objects
        type_map = {
            int: "INTEGER",
            float: "REAL",
            str: "TEXT",
            bool: "INTEGER",
            bytes: "BLOB",
            type(None): "NULL",
            list: "JSON",
            dict: "JSON",
            set: "JSON",
            tuple: "JSON",
        }
        
        if python_type in type_map:
            return type_map[python_type]
        
        # Handle special types
        try:
            from datetime import datetime, date
            if python_type is datetime:
                return "TIMESTAMP"
            elif python_type is date:
                return "DATE"
        except (ImportError, NameError):
            pass
        
        # For unknown types, raise ValueError to maintain test compatibility
        raise ValueError(f"Unsupported Python type: {python_type}")
    
    async def initialize(self) -> None:
        """Initialize the database by creating tables for each schema."""
        if self.initialized:
            return
        
        async with aiosqlite.connect(self.sqlite_database_path) as db:
            for schema in self.schemas:
                table_name = schema.get_table_name()
                existing_columns = await self._get_table_columns(db, table_name)
                
                if not existing_columns:
                    # Create new table
                    await self._create_table(db, schema)
                else:
                    # Add any missing columns for schema evolution
                    await self._migrate_schema(db, schema, existing_columns)
         
            await db.commit()
        
        self.initialized = True
    
    @staticmethod
    def _serialize_for_db(value: Any) -> Any:
        """Serialize complex types to JSON for SQLite storage."""
        return json.dumps(value) if isinstance(value, (dict, list)) else value
    
    @staticmethod
    def _deserialize_from_db(row_dict: dict[str, Any]) -> dict[str, Any]:
        """Deserialize data from database, converting JSON strings back to Python objects."""
        result = {}
        for field_name, field_value in row_dict.items():
            if field_value is None or not isinstance(field_value, str):
                result[field_name] = field_value
                continue
            
            # Try to deserialize JSON strings (stored list/dict values)
            try:
                result[field_name] = json.loads(field_value)
            except (json.JSONDecodeError, TypeError):
                # Not JSON, keep as string
                result[field_name] = field_value
        
        return result
    
    async def _get_table_columns(self, db: aiosqlite.Connection, table_name: str) -> set[str]:
        """Get existing column names for a table."""
        try:
            cursor = await db.execute(f"PRAGMA table_info({table_name})")
            rows = await cursor.fetchall()
            await cursor.close()
            return {row[1] for row in rows}  # row[1] is the column name
        except Exception:
            return set()
    
    async def _create_table(self, db: aiosqlite.Connection, schema: Type[MigratableSQLModel]) -> None:
        """Create a new table for the given schema."""
        columns = ["id INTEGER PRIMARY KEY AUTOINCREMENT", "model_version INTEGER DEFAULT 1"]
        
        # Dump an instance to see actual JSON values
        instance = schema.from_migration({})
        dumped = instance.model_dump(mode="json")
        
        for field_name in schema.get_fields().keys():
            if field_name in ('id', 'model_version'):
                continue  # Already added above
            
            # Get the actual JSON value to determine column type
            value = dumped.get(field_name)
            sqlite_type = self._get_sql_type_from_json_value(value)
            columns.append(f"{field_name} {sqlite_type}")
        
        columns_sql = ", ".join(columns)
        create_table_sql = f"CREATE TABLE IF NOT EXISTS {schema.get_table_name()} ({columns_sql})"
        await db.execute(create_table_sql)
    
    async def _migrate_schema(self, db: aiosqlite.Connection, schema: Type[MigratableSQLModel], existing_columns: set[str]) -> None:
        """Add any missing columns to an existing table for schema evolution."""
        table_name = schema.get_table_name()
        
        # Dump an instance to see actual JSON values
        instance = schema.from_migration({})
        dumped = instance.model_dump(mode="json")
        
        for field_name in schema.get_fields().keys():
            if field_name in ('id', 'model_version') or field_name in existing_columns:
                continue  # Skip ID, model_version, and existing columns
            
            # Get the actual JSON value to determine column type
            value = dumped.get(field_name)
            sqlite_type = self._get_sql_type_from_json_value(value)
            
            # Use the actual default value from the JSON dump
            if value is not None:
                if isinstance(value, str):
                    default_value = f"'{value}'"
                elif isinstance(value, bool):
                    default_value = "1" if value else "0"
                else:
                    default_value = str(value)
            else:
                default_value = "NULL"
            
            alter_sql = f"ALTER TABLE {table_name} ADD COLUMN {field_name} {sqlite_type} DEFAULT {default_value}"
            await db.execute(alter_sql)
    
    async def find(self, schema: Type[T], where: Union[dict[str, Any], Filter, None] = None) -> list[T]:
        """Find entries in the database matching filters or criteria.
        
        Args:
            schema: The model class to find
            where: Filter object, dict of field->value pairs for equality, or None for all
        
        Returns:
            List of model instances matching the criteria
            
        Examples:
            # Using Filter objects (recommended)
            age = Field("age")
            results = await db.find(UserV1, age >= 30)
            
            # Using dict (backwards compatible)
            results = await db.find(UserV1, {"name": "Alice"})
            
            # No filters
            results = await db.find(UserV1)
        """
        await self.initialize()
        
        table_name = schema.get_table_name()
        where_sql = "1"
        values = []
        
        # Convert where to Filter if needed
        if where is None:
            # No filters, fetch all
            pass
        elif isinstance(where, Filter):
            # Use Filter object
            where_sql, values = where.to_sql()
        elif isinstance(where, dict):
            # Convert dict to equality filters (backwards compatibility)
            where_clauses = []
            for field_name, field_value in where.items():
                where_clauses.append(f"{field_name} = ?")
                values.append(field_value)
            where_sql = " AND ".join(where_clauses) if where_clauses else "1"
        else:
            raise TypeError(f"where must be Filter, dict, or None, got {type(where)}")
        
        query_sql = f"SELECT * FROM {table_name} WHERE {where_sql}"
        
        async with aiosqlite.connect(self.sqlite_database_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(query_sql, values)
            rows = await cursor.fetchall()
            await cursor.close()
        
        results = []
        for row in rows:
            row_dict = dict(row)
            # Deserialize JSON values from database
            deserialized = self._deserialize_from_db(row_dict)
            results.append(schema.model_validate(deserialized))
        return results

    async def insert(self, entry: T) -> T:
        """Insert a new entry into the database."""
        await self.initialize()
        
        table_name = entry.get_table_name()
        data = entry.model_dump(mode="json")
        fields = [f for f in data.keys() if f != 'id']  # Exclude auto-increment ID
        values = [self._serialize_for_db(data[field]) for field in fields]
        
        fields_sql = ", ".join(fields)
        placeholders_sql = ", ".join(["?"] * len(fields))
        insert_sql = f"INSERT INTO {table_name} ({fields_sql}) VALUES ({placeholders_sql})"
        
        async with aiosqlite.connect(self.sqlite_database_path) as db:
            cursor = await db.execute(insert_sql, values)
            entry.id = cursor.lastrowid
            await cursor.close()
            await db.commit()
        
        return entry

    async def update(self, entry: T) -> T:
        """Update an existing entry in the database by ID."""
        await self.initialize()
        
        if entry.id is None:
            raise ValueError("Cannot update entry without an ID")
        
        table_name = entry.get_table_name()
        data = entry.model_dump(mode="json")
        fields = [f for f in data.keys() if f not in ('id', 'model_version')]
        values = [self._serialize_for_db(data[field]) for field in fields]
        values.append(entry.id)  # Add ID for WHERE clause
        
        set_clauses = ", ".join([f"{field} = ?" for field in fields])
        update_sql = f"UPDATE {table_name} SET {set_clauses} WHERE id = ?"
        
        async with aiosqlite.connect(self.sqlite_database_path) as db:
            await db.execute(update_sql, values)
            await db.commit()
        
        return entry

    async def delete(self, entry: T) -> T:
        """Delete an entry from the database by ID."""
        await self.initialize()
        
        if entry.id is None:
            raise ValueError("Cannot delete entry without an ID")
        
        table_name = entry.get_table_name()
        delete_sql = f"DELETE FROM {table_name} WHERE id = ?"
        
        async with aiosqlite.connect(self.sqlite_database_path) as db:
            await db.execute(delete_sql, [entry.id])
            await db.commit()
        
        return entry
    
    async def batch_insert(self, entries: list[T]) -> list[T]:
        """Insert multiple entries into the database in batch.
        
        More efficient than calling insert() multiple times as it
        reuses the database connection.
        
        Args:
            entries: List of model instances to insert
            
        Returns:
            List of inserted entries with auto-generated IDs
            
        Example:
            users = [UserV1(name=f"user_{i}") for i in range(1000)]
            inserted = await db.batch_insert(users)
            print(inserted[0].id)  # 1
        """
        if not entries:
            return []
        
        await self.initialize()
        
        # All entries must be same type
        first_schema = type(entries[0])
        if not all(isinstance(e, first_schema) for e in entries):
            raise ValueError("All entries must be the same model type")
        
        results = []
        async with aiosqlite.connect(self.sqlite_database_path) as db:
            for entry in entries:
                result = await self._insert_with_connection(db, entry)
                results.append(result)
            await db.commit()
        
        return results
    
    async def batch_update(self, entries: list[T]) -> list[T]:
        """Update multiple entries in the database in batch.
        
        More efficient than calling update() multiple times as it
        reuses the database connection.
        
        Args:
            entries: List of model instances to update (must have IDs)
            
        Returns:
            List of updated entries
            
        Example:
            users = [UserV1(id=1, name="Alice"), UserV1(id=2, name="Bob")]
            updated = await db.batch_update(users)
        """
        if not entries:
            return []
        
        await self.initialize()
        
        # All entries must be same type
        first_schema = type(entries[0])
        if not all(isinstance(e, first_schema) for e in entries):
            raise ValueError("All entries must be the same model type")
        
        # All entries must have IDs
        if any(e.id is None for e in entries):
            raise ValueError("All entries must have IDs for batch update")
        
        results = []
        async with aiosqlite.connect(self.sqlite_database_path) as db:
            for entry in entries:
                result = await self._update_with_connection(db, entry)
                results.append(result)
            await db.commit()
        
        return results
    
    async def _insert_with_connection(
        self, 
        db: aiosqlite.Connection, 
        entry: T
    ) -> T:
        """Insert entry using existing connection (for batch operations)."""
        table_name = entry.get_table_name()
        
        # Serialize entry to dict
        data = entry.model_dump(mode="json")
        
        # Serialize complex types
        for key, value in data.items():
            data[key] = self._serialize_for_db(value)
        
        # Build INSERT statement
        columns = ", ".join(data.keys())
        placeholders = ", ".join(["?" for _ in data])
        insert_sql = f"INSERT INTO {table_name} ({columns}) VALUES ({placeholders})"
        
        cursor = await db.execute(insert_sql, list(data.values()))
        # Get the auto-increment ID
        entry.id = cursor.lastrowid
        await cursor.close()
        
        return entry
    
    async def _update_with_connection(
        self, 
        db: aiosqlite.Connection, 
        entry: T
    ) -> T:
        """Update entry using existing connection (for batch operations)."""
        if entry.id is None:
            raise ValueError("Cannot update entry without an ID")
        
        table_name = entry.get_table_name()
        
        # Serialize entry to dict
        data = entry.model_dump(mode="json")
        
        # Serialize complex types
        for key, value in data.items():
            data[key] = self._serialize_for_db(value)
        
        # Remove id from update (it's in WHERE clause)
        entry_id = data.pop("id")
        
        # Build UPDATE statement
        set_clause = ", ".join([f"{k} = ?" for k in data.keys()])
        update_sql = f"UPDATE {table_name} SET {set_clause} WHERE id = ?"
        
        values = list(data.values()) + [entry_id]
        await db.execute(update_sql, values)
        
        return entry
