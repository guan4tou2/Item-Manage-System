# Backup & Restore Skill

## Description
Database backup and restore procedures for Item Management System (PostgreSQL & MongoDB).

## Trigger Phrases
- "backup"
- "restore"
- "database backup"

## When to Use
When you need to:
- Create database backups
- Restore from backup
- Schedule automated backups
- Migrate data between environments
- Recover from data loss

## Available Tools
- Bash (for backup commands)
- PostgreSQL MCP (if available)
- MongoDB MCP (if available)
- Cron/scheduler (for automated backups)

## MUST DO
1. Check current database type before backup
2. ALWAYS backup before any migration or critical change
3. Verify backup integrity
4. Test restore procedures regularly
5. Store backups in multiple locations
6. Encrypt sensitive backups
7. Compress backups to save space
8. Document backup/restore procedures
9. Schedule automated backups
10. Monitor backup success/failure

## MUST NOT DO
- Do NOT delete old backups without confirmation
- Do NOT skip testing restore procedures
- Do NOT rely on a single backup location
- Do NOT ignore backup failures
- Do NOT store unencrypted backups in public locations
- Do NOT overwrite recent backups without verification

## Context
- Dual database support: PostgreSQL (primary) and MongoDB (legacy)
- PostgreSQL used for production
- MongoDB used for backward compatibility
- Data includes:
  - Users and authentication
  - Items with metadata
  - Photos and attachments
  - Audit logs
  - Notification settings
- Application data in `uploads/` directory

## Backup Procedures

### PostgreSQL Backup

#### 1. pg_dump (Full Database)
```bash
# Backup structure and data
docker compose exec -T db pg_dump \
  -U user \
  -d itemman \
  --clean \
  --if-exists \
  --format=plain \
  > backups/postgres_full_$(date +%Y%m%d_%H%M%S).sql

# Compressed backup
docker compose exec -T db pg_dump \
  -U user \
  -d itemman \
  --clean \
  --if-exists \
  | gzip > backups/postgres_full_$(date +%Y%m%d_%H%M%S).sql.gz
```

#### 2. pg_dump (Schema Only)
```bash
docker compose exec -T db pg_dump \
  -U user \
  -d itemman \
  --schema-only \
  > backups/postgres_schema_$(date +%Y%m%d_%H%M%S).sql
```

#### 3. pg_dump (Data Only)
```bash
docker compose exec -T db pg_dump \
  -U user \
  -d itemman \
  --data-only \
  > backups/postgres_data_$(date +%Y%m%d_%H%M%S).sql
```

#### 4. pg_dump (Specific Tables)
```bash
docker compose exec -T db pg_dump \
  -U user \
  -d itemman \
  -t users \
  -t items \
  > backups/postgres_tables_$(date +%Y%m%d_%H%M%S).sql
```

### MongoDB Backup

#### 1. mongodump (Full Database)
```bash
# Backup all databases
docker compose exec -T mongo mongodump \
  --uri "mongodb://user:password@localhost:27017" \
  --out backups/mongo_$(date +%Y%m%d_%H%M%S)

# Backup specific database
docker compose exec -T mongo mongodump \
  --uri "mongodb://user:password@localhost:27017" \
  --db myDB \
  --out backups/mongo_mydb_$(date +%Y%m%d_%H%M%S)

# Compressed backup
docker compose exec -T mongo mongodump \
  --uri "mongodb://user:password@localhost:27017" \
  --archive=- \
  | gzip > backups/mongo_$(date +%Y%m%d_%H%M%S).gz
```

#### 2. mongodump (Specific Collections)
```bash
docker compose exec -T mongo mongodump \
  --uri "mongodb://user:password@localhost:27017/myDB" \
  --collection items \
  --out backups/mongo_items_$(date +%Y%m%d_%H%M%S)
```

### Application Data Backup
```bash
# Backup uploaded files
tar -czf backups/uploads_$(date +%Y%m%d_%H%M%S).tar.gz \
  uploads/

# Backup static files
tar -czf backups/static_$(date +%Y%m%d_%H%M%S).tar.gz \
  static/

# Backup configuration
tar -czf backups/config_$(date +%Y%m%d_%H%M%S).tar.gz \
  .env app/config.py
```

## Restore Procedures

### PostgreSQL Restore

#### 1. Restore from SQL File
```bash
# Stop application
docker compose stop web

# Restore database
docker compose exec -T db psql \
  -U user \
  -d itemman \
  < backups/postgres_full_20240101_120000.sql

# Restore from compressed file
gunzip -c backups/postgres_full_20240101_120000.sql.gz | \
  docker compose exec -T db psql -U user -d itemman

# Restart application
docker compose start web
```

#### 2. Restore Specific Tables
```bash
# Drop existing tables
docker compose exec db psql -U user -d itemman \
  -c "DROP TABLE IF EXISTS items CASCADE;"

# Restore from backup
docker compose exec -T db psql -U user -d itemman \
  < backups/postgres_tables_20240101.sql
```

### MongoDB Restore

#### 1. Restore from mongodump
```bash
# Stop application
docker compose stop web

# Restore from directory
docker compose exec mongo mongorestore \
  --uri "mongodb://user:password@localhost:27017" \
  --db myDB \
  backups/mongo_20240101_120000/myDB

# Restore from archive
gunzip -c backups/mongo_20240101_120000.gz | \
  docker compose exec -T mongo mongorestore \
    --uri "mongodb://user:password@localhost:27017" \
    --archive=-

# Restart application
docker compose start web
```

#### 2. Restore Specific Collection
```bash
docker compose exec mongo mongorestore \
  --uri "mongodb://user:password@localhost:27017/myDB" \
  --collection items \
  --db myDB \
  backups/mongo_items_20240101/myDB/items.bson
```

## Automated Backups

### Cron Jobs
```bash
# Edit crontab
crontab -e

# Daily PostgreSQL backup at 2 AM
0 2 * * * cd /path/to/Item-Manage-System && \
  docker compose exec -T db pg_dump -U user -d itemman | \
  gzip > /backups/postgres_daily_$(date +\%Y\%m\%d).sql.gz

# Daily MongoDB backup at 2:30 AM
30 2 * * * cd /path/to/Item-Manage-System && \
  docker compose exec -T mongo mongodump --archive=- | \
  gzip > /backups/mongo_daily_$(date +\%Y\%m\%d).gz

# Weekly full backup (Sunday at 3 AM)
0 3 * * 0 cd /path/to/Item-Manage-System && \
  tar -czf /backups/full_backup_$(date +\%Y\%m\%d).tar.gz \
    uploads/ .env app/config.py

# Delete backups older than 30 days
0 4 * * * find /backups -name "*.sql.gz" -mtime +30 -delete
```

### Python Backup Script
```python
#!/usr/bin/env python3
import os
import subprocess
import datetime
from pathlib import Path

BACKUP_DIR = Path("/backups")
BACKUP_DIR.mkdir(exist_ok=True)
timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

def backup_postgres():
    """Backup PostgreSQL database"""
    filename = BACKUP_DIR / f"postgres_{timestamp}.sql.gz"

    cmd = f"""
    docker compose exec -T db pg_dump \
      -U user \
      -d itemman \
      | gzip > {filename}
    """

    subprocess.run(cmd, shell=True, check=True)
    print(f"PostgreSQL backup: {filename}")

def backup_mongodb():
    """Backup MongoDB database"""
    filename = BACKUP_DIR / f"mongo_{timestamp}.gz"

    cmd = f"""
    docker compose exec -T mongo mongodump \
      --uri "mongodb://user:password@localhost:27017" \
      --archive=- \
      | gzip > {filename}
    """

    subprocess.run(cmd, shell=True, check=True)
    print(f"MongoDB backup: {filename}")

def backup_uploads():
    """Backup uploaded files"""
    filename = BACKUP_DIR / f"uploads_{timestamp}.tar.gz"

    cmd = f"tar -czf {filename} uploads/"
    subprocess.run(cmd, shell=True, check=True)
    print(f"Uploads backup: {filename}")

def cleanup_old_backups(days=30):
    """Delete backups older than specified days"""
    for backup in BACKUP_DIR.glob("*"):
        # Check file age
        age = datetime.datetime.now() - datetime.datetime.fromtimestamp(
            backup.stat().st_mtime
        )

        if age.days > days:
            backup.unlink()
            print(f"Deleted old backup: {backup}")

if __name__ == "__main__":
    try:
        backup_postgres()
        backup_mongodb()
        backup_uploads()
        cleanup_old_backups()
        print("Backup completed successfully")
    except Exception as e:
        print(f"Backup failed: {e}")
        exit(1)
```

## Backup Verification

### Verify PostgreSQL Backup
```bash
# Check SQL file integrity
docker compose exec -T db psql \
  -U user \
  -d itemman \
  -f backups/postgres_full_20240101.sql

# Or restore to test database
docker compose exec -T db psql \
  -U user \
  -d itemman_test \
  < backups/postgres_full_20240101.sql

# Verify data count
docker compose exec db psql -U user -d itemman_test \
  -c "SELECT COUNT(*) FROM items;"
```

### Verify MongoDB Backup
```bash
# Check BSON files
docker compose exec mongo bsondump \
  backups/mongo_20240101/myDB/items.bson

# Restore to test database
docker compose exec mongo mongorestore \
  --uri "mongodb://user:password@localhost:27017" \
  --db myDB_test \
  backups/mongo_20240101/myDB

# Verify data count
docker compose exec mongo mongosh \
  --eval "db=db.getSiblingDB('myDB_test'); db.items.count();"
```

## Disaster Recovery Plan

### 1. Identify Failure
```bash
# Check database connectivity
docker compose exec db pg_isready -U user -d itemman
docker compose exec mongo mongosh --eval "db.serverStatus()"

# Check logs
docker compose logs db
docker compose logs mongo
```

### 2. Assess Impact
```bash
# Check data integrity
docker compose exec db psql -U user -d itemman \
  -c "SELECT COUNT(*) FROM items;"
docker compose exec mongo mongosh myDB \
  --eval "db.items.count();"

# Check recent logs
docker compose logs --tail 100 web
```

### 3. Restore from Backup
```bash
# Stop application
docker compose down

# Choose appropriate backup
ls -lt backups/

# Restore database (see Restore Procedures section)

# Restore application data
tar -xzf backups/uploads_20240101_120000.tar.gz

# Restart services
docker compose up -d
```

### 4. Verify Recovery
```bash
# Test application
curl http://localhost:8080/health

# Test authentication
curl -X POST http://localhost:8080/api/auth/login \
  -d '{"username":"admin","password":"admin"}'

# Test data access
curl http://localhost:8080/api/items
```

## Backup Retention Policy

| Type | Frequency | Retention | Location |
|------|-----------|------------|----------|
| Full DB | Daily | 7 days | Local |
| Full DB | Weekly | 4 weeks | Local + Cloud |
| Full DB | Monthly | 12 months | Cloud |
| Uploads | Daily | 7 days | Local |
| Uploads | Weekly | 4 weeks | Cloud |
| Config | On change | Permanent | Version control |

## Backup Checklist
- [ ] Database backup completed
- [ ] Uploads backup completed
- [ ] Configuration backup completed
- [ ] Backup integrity verified
- [ ] Backup stored in multiple locations
- [ ] Backup encrypted (if sensitive)
- [ ] Backup compressed
- [ ] Restore procedure tested
- [ ] Backup documented
- [ ] Automated backups scheduled
- [ ] Backup monitoring configured
