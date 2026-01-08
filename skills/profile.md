# Performance Profiling Skill

## Description
Python/Flask performance profiling and optimization for Item Management System.

## Trigger Phrases
- "profile"
- "performance"
- "optimize"
- "slow query"

## When to Use
When you need to:
- Profile application performance
- Identify slow endpoints
- Optimize database queries
- Analyze memory usage
- Find CPU bottlenecks
- Optimize Python code
- Improve response times

## Available Tools
- Bash (for running profiling tools)
- Grep (for finding code patterns)
- PostgreSQL MCP (for query analysis)
- MongoDB MCP (for query analysis)

## MUST DO
1. Profile in a development environment, not production
2. Use appropriate profiling tool for the issue:
   - cProfile for CPU profiling
   - memory_profiler for memory leaks
   - flask-profiler for endpoint profiling
   - django-debug-toolbar style tools for query analysis
3. Measure before and after optimization
4. Focus on hot paths (frequently executed code)
5. Profile with realistic data volumes
6. Analyze database query plans
7. Consider caching strategies
8. Document all optimizations

## MUST NOT DO
- Do NOT profile in production without safeguards
- Do NOT optimize without profiling data
- Do NOT prematurely optimize (measure first)
- Do NOT optimize non-critical paths
- Do NOT ignore memory leaks
- Do NOT forget to revert debug code

## Context
- Flask 3.1+ web application
- SQLAlchemy 2.0+ for PostgreSQL
- PyMongo for MongoDB
- Supports dual database backends
- JSON API responses
- Uses Flask-Limiter for rate limiting
- Uses Flask-Login for authentication

## Profiling Tools

### 1. cProfile (CPU Profiling)
```python
import cProfile
import pstats
from io import StringIO

def profile_function():
    pr = cProfile.Profile()
    pr.enable()

    # Code to profile
    result = your_function()

    pr.disable()

    # Print statistics
    s = StringIO()
    ps = pstats.Stats(pr, stream=s).sort_stats('cumulative')
    ps.print_stats(20)  # Top 20 functions
    print(s.getvalue())

    return result
```

### 2. Flask Profiler
```python
from flask import Flask
from flask_profiler import Profiler

app = Flask(__name__)
profiler = Profiler(app)

# View profiling results at: http://localhost:5000/flask-profiler
```

### 3. Memory Profiler
```python
from memory_profiler import profile

@profile
def memory_intensive_function():
    data = []
    for i in range(100000):
        data.append(i)
    return data

# Run with: python -m memory_profiler script.py
```

### 4. Query Profiling (PostgreSQL)
```python
from app import db
from sqlalchemy import event
from sqlalchemy.engine import Engine
import time

@event.listens_for(Engine, "before_cursor_execute")
def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    context._query_start_time = time.time()
    context._query_statement = statement

@event.listens_for(Engine, "after_cursor_execute")
def after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    total = time.time() - context._query_start_time
    print(f"Query: {statement[:50]}...")
    print(f"Duration: {total:.3f}s")
```

## Common Performance Issues

### 1. N+1 Query Problem
```python
# BAD: N+1 queries
items = Item.query.all()
for item in items:
    print(item.ItemType)  # Additional query for each item

# GOOD: Eager loading
items = Item.query.options(db.joinedload(Item.type)).all()
for item in items:
    print(item.ItemType)
```

### 2. Missing Indexes
```python
# Find slow queries
# PostgreSQL
EXPLAIN ANALYZE SELECT * FROM items WHERE ItemName = 'Test';

# MongoDB
db.collection.find({ItemName: 'Test'}).explain()

# Add indexes
# PostgreSQL
CREATE INDEX idx_item_name ON items(ItemName);

# MongoDB
db.collection.create_index({"ItemName": 1})
```

### 3. Inefficient JSON Operations
```python
# BAD: Sequential search in JSON array
item = Item.query.filter_by(ItemID=id).first()
if user_id in item.favorites:  # Slow for large lists

# GOOD: Use JSON containment (PostgreSQL)
from sqlalchemy import text
Item.query.filter(
    Item.favorites.op('@>')(f'["{user_id}"]')
).first()
```

### 4. Loading Unnecessary Data
```python
# BAD: Select all columns
items = Item.query.all()

# GOOD: Select only needed columns
items = Item.query.with_entities(Item.ItemID, Item.ItemName).all()
```

## Optimization Strategies

### 1. Database Query Optimization
```python
# Use indexes
class Item(db.Model):
    __tablename__ = 'items'
    ItemName = db.Column(db.String(100), index=True)
    ItemID = db.Column(db.String(50), unique=True, index=True)

# Use lazy loading
class User(db.Model):
    items = db.relationship('Item', lazy='dynamic')

# Use pagination
items = Item.query.paginate(page=1, per_page=20)

# Use raw SQL for complex queries
from sqlalchemy import text
result = db.session.execute(text("""
    SELECT * FROM items
    WHERE JSONB_ARRAY_LENGTH(favorites) > 0
"""))
```

### 2. Caching
```python
from flask_caching import Cache
cache = Cache(app, config={'CACHE_TYPE': 'simple'})

@cache.memoize(timeout=60)
def get_item_types():
    return Type.query.all()

# Cache expensive queries
@cache.cached(timeout=300, key_prefix='all_items')
def list_items():
    return Item.query.all()
```

### 3. Async Operations
```python
import asyncio
from concurrent.futures import ThreadPoolExecutor

async def async_fetch(item_id):
    loop = asyncio.get_event_loop()
    with ThreadPoolExecutor() as pool:
        result = await loop.run_in_executor(pool, fetch_item, item_id)
    return result

async def fetch_multiple_items(item_ids):
    tasks = [async_fetch(id) for id in item_ids]
    return await asyncio.gather(*tasks)
```

### 4. Connection Pooling
```python
# SQLAlchemy connection pool
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    'pool_size': 20,
    'max_overflow': 10,
    'pool_timeout': 30,
    'pool_recycle': 3600,
    'pool_pre_ping': True
}
```

## Profiling Workflow

### 1. Identify Slow Endpoints
```python
from flask import Flask
import time

@app.before_request
def before_request():
    g.start_time = time.time()

@app.after_request
def after_request(response):
    duration = time.time() - g.start_time
    if duration > 1.0:  # Log slow requests
        app.logger.warning(f"Slow request: {request.path} took {duration:.2f}s")
    return response
```

### 2. Profile Specific Endpoint
```python
@app.route('/items/<item_id>')
@profile  # Decorator from memory_profiler
def get_item(item_id):
    item = Item.query.filter_by(ItemID=item_id).first()
    return jsonify(item.to_dict())
```

### 3. Analyze Database Queries
```bash
# PostgreSQL: Enable slow query logging
docker compose exec db psql -U user -d itemman -c "
ALTER SYSTEM SET log_min_duration_statement = 100;
SELECT pg_reload_conf();
"

# MongoDB: Enable profiler
docker compose exec mongo mongosh --eval "
db.setProfilingLevel(1, {slowms: 100})
"
```

### 4. Generate Flamegraph
```bash
# Install flamegraph
pip install flamegraph

# Run and generate
python -m flamegraph -o flamegraph.svg run.py
```

## Performance Checklist
- [ ] Identified slow endpoints
- [ ] Profiled CPU usage
- [ ] Profiled memory usage
- [ ] Analyzed database queries
- [ ] Added necessary indexes
- [ ] Optimized N+1 queries
- [ ] Implemented caching where appropriate
- [ ] Optimized JSON operations
- [ ] Configured connection pooling
- [ ] Reduced unnecessary data loading
- [ ] Tested optimizations
- [ ] Measured improvement (before/after)

## Tools
- **cProfile** - Built-in Python profiler
- **py-spy** - Sampling profiler (no code modification)
- **memory_profiler** - Memory usage profiling
- **flask-profiler** - Flask endpoint profiling
- **django-debug-toolbar** - Query profiling (adapt for Flask)
- **pgBadger** - PostgreSQL log analysis
- **MongoDB Profiler** - Built-in MongoDB profiler
- **pyflame** - Flamegraph generation
- **line_profiler** - Line-by-line profiling

## Benchmarking
```python
import timeit

def benchmark():
    iterations = 1000
    old_time = timeit.timeit(old_implementation, number=iterations)
    new_time = timeit.timeit(new_implementation, number=iterations)
    improvement = (old_time - new_time) / old_time * 100
    print(f"Improvement: {improvement:.2f}%")
```
