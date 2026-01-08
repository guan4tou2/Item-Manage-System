# Database Migration Skill

## Description
Database schema migration tool for PostgreSQL and MongoDB in the Item Management System.

## Trigger Phrases
- "migrate"
- "database migration"
- "schema change"
- "update database"
- "db migration"

## When to Use
When you need to:
- Add new fields to existing models
- Change field types
- Add new tables/collections
- Rename fields or tables
- Add or remove indexes
- Change data relationships
- Migrate data between schemas

## Available Tools
- Bash (for running migration scripts)
- Read/Write (for creating migration files)
- Grep (for finding model definitions)
- PostgreSQL MCP (if available)
- MongoDB MCP (if available)

## MUST DO
1. **ALWAYS** check current database type (PostgreSQL vs MongoDB) via `get_db_type()`
2. Create migration scripts for BOTH databases
3. **ALWAYS** backup database before running migrations
4. Test migrations on a copy first
5. Use transactions for PostgreSQL migrations
6. Provide rollback procedures
7. Document migration changes clearly
8. Update model definitions to match new schema
9. Verify data integrity after migration
10. Test both database backends

## MUST NOT DO
- Do NOT run migrations without backup
- Do NOT migrate production data without testing
- Do NOT skip migration for one database backend
- Do NOT make destructive changes without confirmation
- Do NOT leave inconsistent data
- Do NOT break existing API contracts

## Context
- Project supports dual database: PostgreSQL (primary) and MongoDB (legacy)
- Models in `app/models/` directory:
  - `user.py` - User accounts and authentication
  - `item.py` - Items, favorites, related items, move history
  - `item_type.py` - Item types/categories
  - `log.py` - Operation logs
  - `location.py` - Location options (floor/room/zone)
- Repositories handle database operations in `app/repositories/`
- Use `get_db_type()` to determine active database

## Migration Workflow

### 1. Planning
```bash
# Check current schema
grep -r "Mapped\[" app/models/

# Identify changes needed
# Review existing migration files in migrations/ directory
```

### 2. Backup
```bash
# PostgreSQL
pg_dump -U user -d itemman > backup_pre_migration.sql

# MongoDB
mongodump --db myDB --out backup_pre_migration/
```

### 3. Create Migration Script
Create file: `migrations/YYYYMMDD_description.py`

```python
"""Migration: description of changes"""
from app import db, get_db_type, mongo
from datetime import datetime

def upgrade():
    """Apply the migration"""
    db_type = get_db_type()

    if db_type == "postgres":
        # PostgreSQL migration
        with db.session.begin_nested():
            # Example: Add new column
            from sqlalchemy import text
            db.session.execute(text("""
                ALTER TABLE items ADD COLUMN IF NOT EXISTS new_field VARCHAR(100)
            """))
            db.session.commit()
    else:
        # MongoDB migration
        # Example: Add field to all documents
        mongo.db.item.update_many(
            {"new_field": {"$exists": False}},
            {"$set": {"new_field": ""}}
        )

def downgrade():
    """Rollback the migration"""
    db_type = get_db_type()

    if db_type == "postgres":
        with db.session.begin_nested():
            from sqlalchemy import text
            db.session.execute(text("""
                ALTER TABLE items DROP COLUMN IF EXISTS new_field
            """))
            db.session.commit()
    else:
        mongo.db.item.update_many(
            {},
            {"$unset": {"new_field": ""}}
        )

def run_migration():
    """Main migration function"""
    print(f"Starting migration at {datetime.now()}")
    try:
        upgrade()
        print("Migration completed successfully")
    except Exception as e:
        print(f"Migration failed: {e}")
        print("Rolling back...")
        downgrade()
        raise

if __name__ == "__main__":
    run_migration()
```

### 4. Run Migration
```bash
# Test on development first
python3 migrations/YYYYMMDD_description.py

# Run on production after testing
python3 migrations/YYYYMMDD_description.py
```

### 5. Verify
```bash
# Check data integrity
python3 tests/test_migration_verification.py

# Verify application works
python3 run_tests.py
```

## Common Migration Patterns

### Add New Field
```python
# PostgreSQL
ALTER TABLE table_name ADD COLUMN new_field VARCHAR(100);

# MongoDB
db.collection.update_many(
    {},
    {"$set": {"new_field": default_value}}
)
```

### Rename Field
```python
# PostgreSQL
ALTER TABLE table_name RENAME COLUMN old_name TO new_name;

# MongoDB
db.collection.update_many(
    {},
    {"$rename": {"old_name": "new_name"}}
)
```

### Change Field Type
```python
# PostgreSQL (requires data conversion)
ALTER TABLE table_name ALTER COLUMN field_name TYPE new_type USING conversion_function;

# MongoDB (documents are schema-less, just convert values)
db.collection.find({}).forEach(function(doc) {
    db.collection.updateOne(
        {_id: doc._id},
        {$set: {field_name: convert(doc.field_name)}}
    )
})
```

### Add Index
```python
# PostgreSQL
CREATE INDEX idx_name ON table_name(column_name);

# MongoDB
db.collection.create_index({"field_name": 1})
```

### Drop Field
```python
# PostgreSQL
ALTER TABLE table_name DROP COLUMN field_name;

# MongoDB
db.collection.update_many(
    {},
    {"$unset": {"field_name": ""}}
)
```

## Migration Checklist
- [ ] Identified all affected models
- [ ] Created migration script for PostgreSQL
- [ ] Created migration script for MongoDB
- [ ] Backup database before migration
- [ ] Tested migration on development environment
- [ ] Verified data integrity after migration
- [ ] Updated model definitions
- [ ] Tested application functionality
- [ ] Documented migration changes
- [ ] Prepared rollback procedure
- [ ] Notified team of migration schedule

## Migration Best Practices
1. Use descriptive migration names with date prefix
2. Keep migrations idempotent (safe to run multiple times)
3. Test with realistic data volumes
4. Monitor migration performance
5. Use appropriate indexes for large data operations
6. Break large migrations into smaller steps
7. Log migration steps for debugging
8. Verify both database backends work correctly

## Emergency Rollback
If migration fails in production:
1. Stop application
2. Run downgrade() function
3. Restore from backup if downgrade fails
4. Investigate failure cause
5. Fix and re-test migration
6. Re-attempt migration after fixes
