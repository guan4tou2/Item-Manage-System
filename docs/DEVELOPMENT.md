# 👨‍💻 Developer Guide

Complete guide for developers contributing to the Item Management System.

## 📋 Table of Contents

- [Getting Started](#getting-started)
- [Project Structure](#project-structure)
- [Development Workflow](#development-workflow)
- [Coding Standards](#coding-standards)
- [Adding New Features](#adding-new-features)
- [Database Operations](#database-operations)
- [Testing](#testing)
- [Debugging](#debugging)
- [Common Tasks](#common-tasks)
- [Troubleshooting](#troubleshooting)

---

## 🚀 Getting Started

### Prerequisites

- **Python 3.13+** (3.11+ also supported)
- **PostgreSQL 16+** or **MongoDB 7+**
- **Redis 7+** (for caching and rate limiting)
- **Git**
- **Docker & Docker Compose** (optional, for containerized development)
- **uv** or **pip** (Python package manager)

### Initial Setup

#### 1. Clone the Repository

```bash
git clone <repository-url>
cd Item-Manage-System
```

#### 2. Set Up Virtual Environment

**Using uv (Recommended - Faster):**
```bash
# Install uv if not already installed
curl -LsSf https://astral.sh/uv/install.sh | sh

# Create virtual environment
uv venv .venv

# Activate virtual environment
source .venv/bin/activate  # Linux/Mac
# or
.venv\Scripts\activate  # Windows

# Install dependencies
uv pip install -r requirements.txt
uv pip install -e ".[test]"  # Install with test dependencies
```

**Using pip:**
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -e ".[test]"
```

#### 3. Set Up Database

**Option A: PostgreSQL (Recommended)**

```bash
# macOS
brew install postgresql@16
brew services start postgresql@16
createdb itemman

# Ubuntu/Debian
sudo apt install postgresql-16
sudo systemctl start postgresql
sudo -u postgres createdb itemman
```

**Option B: MongoDB**

```bash
# macOS
brew tap mongodb/brew
brew install mongodb-community
brew services start mongodb-community

# Ubuntu/Debian
sudo apt install mongodb
sudo systemctl start mongod
```

**Option C: Docker (Easiest)**

```bash
# Start all services (database, cache, app)
docker-compose up -d postgres redis
```

#### 4. Configure Environment

```bash
# Copy example configuration
cp .env.example .env

# Edit configuration
vim .env
```

**Minimal .env for development:**
```env
# Database
DB_TYPE=postgres
DATABASE_URL=postgresql://localhost:5432/itemman

# Flask
SECRET_KEY=dev-secret-key-change-in-production
FLASK_ENV=development

# Redis (optional for caching)
REDIS_URL=redis://localhost:6379/0

# Email (optional for notifications)
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USE_TLS=true
MAIL_USERNAME=your-email@gmail.com
MAIL_PASSWORD=your-app-password
```

#### 5. Run the Application

```bash
# Development server
python run.py

# Or using Flask CLI
export FLASK_APP=app:create_app
flask run --port 8080 --debug

# Access application
open http://localhost:8080

# Default credentials
# Username: admin
# Password: admin
```

---

## 📁 Project Structure

### Directory Layout

```
Item-Manage-System/
├── app/                          # Main application package
│   ├── __init__.py               # App factory and initialization
│   ├── models/                   # Database models (SQLAlchemy/MongoDB)
│   │   ├── __init__.py
│   │   ├── item.py               # Item model
│   │   ├── item_type.py          # ItemType model
│   │   ├── location.py           # Location model
│   │   ├── user.py               # User model
│   │   ├── log.py                # Log model
│   │   └── travel.py             # Travel models
│   ├── repositories/             # Data access layer
│   │   ├── __init__.py
│   │   ├── base.py               # Base repository interface
│   │   ├── factory.py            # Repository factory (Strategy pattern)
│   │   ├── postgres_impl.py      # PostgreSQL implementation
│   │   ├── mongo_impl.py         # MongoDB implementation
│   │   ├── item_repo.py          # Item repository
│   │   ├── user_repo.py          # User repository
│   │   ├── type_repo.py          # Type repository
│   │   ├── location_repo.py      # Location repository
│   │   └── log_repo.py           # Log repository
│   ├── services/                 # Business logic layer
│   │   ├── __init__.py
│   │   ├── item_service.py       # Item business logic
│   │   ├── user_service.py       # User business logic
│   │   ├── type_service.py       # Type business logic
│   │   ├── location_service.py   # Location business logic
│   │   ├── notification_service.py  # Notification logic
│   │   ├── email_service.py      # Email sending
│   │   └── log_service.py        # Logging logic
│   ├── auth/                     # Authentication blueprint
│   │   ├── __init__.py
│   │   └── routes.py             # Auth routes (/signin, /signup, etc.)
│   ├── items/                    # Items blueprint
│   │   ├── __init__.py
│   │   └── routes.py             # Item routes (/home, /additem, etc.)
│   ├── types/                    # Types blueprint
│   │   ├── __init__.py
│   │   └── routes.py             # Type routes
│   ├── locations/                # Locations blueprint
│   │   ├── __init__.py
│   │   └── routes.py             # Location routes
│   ├── notifications/            # Notifications blueprint
│   │   ├── __init__.py
│   │   └── routes.py             # Notification routes
│   ├── travel/                   # Travel & shopping blueprint
│   │   ├── __init__.py
│   │   └── routes.py             # Travel routes
│   ├── health/                   # Health check blueprint
│   │   ├── __init__.py
│   │   └── routes.py             # Health endpoints
│   ├── routes/                   # Additional routes
│   │   └── import_routes.py      # Import functionality
│   ├── api/                      # API blueprint (future)
│   │   ├── __init__.py
│   │   └── routes.py             # API routes with Swagger
│   ├── validators/               # Input validation
│   │   ├── __init__.py
│   │   └── items.py              # Item validators
│   ├── utils/                    # Utility modules
│   │   ├── __init__.py
│   │   ├── auth.py               # Auth decorators
│   │   ├── storage.py            # File storage utilities
│   │   ├── image.py              # Image processing
│   │   ├── scheduler.py          # APScheduler setup
│   │   ├── logging.py            # Structured logging
│   │   └── error_handler.py      # Global error handlers
│   └── config/                   # Configuration
│       └── validation.py         # Pydantic config models
├── templates/                    # Jinja2 templates
│   ├── base.html                 # Base template
│   ├── home.html                 # Home page
│   ├── additem.html              # Add item form
│   ├── edititem.html             # Edit item form
│   ├── signin.html               # Login page
│   ├── signup.html               # Registration page
│   └── ...                       # Other templates
├── static/                       # Static files
│   ├── css/                      # Stylesheets
│   ├── js/                       # JavaScript files
│   ├── uploads/                  # User uploaded files
│   └── brand/                    # Branding assets
├── tests/                        # Test suite
│   ├── __init__.py
│   ├── conftest.py               # Pytest configuration
│   ├── test_items.py             # Item service tests
│   ├── test_user_service.py      # User service tests
│   ├── test_routes.py            # Route tests
│   └── ...                       # Other tests
├── migrations/                   # Database migrations (Alembic)
│   ├── versions/                 # Migration versions
│   └── env.py                    # Migration environment
├── scripts/                      # Utility scripts
├── docs/                         # Documentation
│   ├── API.md                    # API documentation
│   ├── ARCHITECTURE.md           # Architecture docs
│   └── DEVELOPMENT.md            # This file
├── .github/                      # GitHub configuration
│   └── workflows/                # CI/CD workflows
├── docker-compose.yml            # Docker compose configuration
├── docker-compose.test.yml       # Test environment compose
├── Dockerfile                    # Application Dockerfile
├── Dockerfile.test               # Test Dockerfile
├── requirements.txt              # Python dependencies
├── pyproject.toml                # Project metadata and tool config
├── pytest.ini                    # Pytest configuration
├── .env.example                  # Environment variables example
├── .gitignore                    # Git ignore rules
├── Makefile                      # Development commands
├── README.md                     # Project README
├── GUIDE_ZH-TW.md                # Chinese user guide
├── TESTING.md                    # Testing documentation
└── run.py                        # Application entry point
```

### Key Modules

| Module | Purpose |
|--------|---------|
| `app/__init__.py` | Application factory, extensions initialization |
| `app/models/` | SQLAlchemy/MongoDB data models |
| `app/repositories/` | Data access layer (Repository pattern) |
| `app/services/` | Business logic layer |
| `app/*/routes.py` | Flask blueprints and route handlers |
| `app/utils/` | Utility functions and helpers |
| `app/validators/` | Input validation logic |

---

## 🔄 Development Workflow

### Branching Strategy

```bash
main              # Production-ready code
├── develop       # Integration branch
│   ├── feature/user-profile
│   ├── feature/advanced-search
│   ├── bugfix/login-issue
│   └── hotfix/security-patch
```

### Creating a Feature

```bash
# 1. Create feature branch from develop
git checkout develop
git pull origin develop
git checkout -b feature/item-favorites

# 2. Develop feature
# - Write code
# - Write tests
# - Update documentation

# 3. Run tests and linting
make test
make lint

# 4. Commit changes
git add .
git commit -m "feat: add item favorites functionality"

# 5. Push and create PR
git push origin feature/item-favorites
# Open Pull Request on GitHub
```

### Commit Message Convention

Follow [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <description>

[optional body]

[optional footer]
```

**Types:**
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting)
- `refactor`: Code refactoring
- `test`: Adding or updating tests
- `chore`: Maintenance tasks

**Examples:**
```bash
feat(items): add bulk delete functionality
fix(auth): resolve session expiration issue
docs(api): update API endpoint documentation
test(services): add tests for notification service
refactor(repos): simplify query logic in item repository
```

---

## 📏 Coding Standards

### Python Style Guide

Follow [PEP 8](https://pep8.org/) with these specifics:

**Line Length:**
```python
# Maximum 100 characters (PEP 8 recommends 79, we use 100)
def create_item_with_location(name: str, location: str, description: str) -> dict:
    pass
```

**Imports:**
```python
# 1. Standard library imports
import os
from datetime import datetime
from typing import Optional, List, Dict

# 2. Third-party imports
from flask import Blueprint, request, jsonify
from sqlalchemy import func

# 3. Local application imports
from app import db
from app.models import Item
from app.services import item_service
```

**Naming Conventions:**
```python
# Classes: PascalCase
class ItemService:
    pass

# Functions/methods: snake_case
def find_items_by_type(item_type: str) -> List[dict]:
    pass

# Constants: UPPER_SNAKE_CASE
MAX_UPLOAD_SIZE = 16 * 1024 * 1024
DEFAULT_PAGE_SIZE = 20

# Private methods: _leading_underscore
def _validate_internal_data(data: dict) -> bool:
    pass
```

### Type Hints

**Always use type hints for function signatures:**

```python
from typing import Optional, List, Dict, Any, Union

def search_items(
    query: Optional[str] = None,
    filters: Optional[Dict[str, Any]] = None,
    page: int = 1,
    per_page: int = 20
) -> Dict[str, Any]:
    """
    Search items with filters and pagination.
    
    Args:
        query: Search query string
        filters: Dictionary of filter conditions
        page: Page number (1-indexed)
        per_page: Items per page
    
    Returns:
        Dictionary containing items and pagination info
    """
    pass
```

### Docstrings

**Use Google style docstrings:**

```python
def calculate_expiry_status(
    item: dict,
    notify_days: int = 30
) -> Dict[str, Union[str, int]]:
    """
    Calculate item expiry status and days remaining.
    
    Determines if an item is expired, near expiry, or OK based on
    warranty and usage expiry dates.
    
    Args:
        item: Item dictionary containing expiry dates
        notify_days: Number of days before expiry to notify
    
    Returns:
        Dictionary with keys:
            - status: "expired", "near_expiry", or "ok"
            - days_remaining: Number of days until expiry (negative if expired)
            - expiry_date: The earliest expiry date
    
    Raises:
        ValueError: If item is missing required fields
    
    Example:
        >>> item = {"warranty_expiry": "2026-01-30", "usage_expiry": None}
        >>> calculate_expiry_status(item, notify_days=7)
        {"status": "near_expiry", "days_remaining": 6, "expiry_date": "2026-01-30"}
    """
    pass
```

### Error Handling

```python
# Use specific exceptions
from werkzeug.exceptions import BadRequest, NotFound, Unauthorized

def get_item_by_id(item_id: str) -> dict:
    """Get item by ID, raise NotFound if not exists."""
    item = item_repo.find_by_id(item_id)
    
    if not item:
        raise NotFound(f"Item with ID {item_id} not found")
    
    return item

# Custom exceptions
class ValidationError(Exception):
    """Raised when input validation fails"""
    pass

class DuplicateItemError(Exception):
    """Raised when attempting to create duplicate item"""
    pass
```

### Logging

```python
import structlog

logger = structlog.get_logger()

def process_item(item_id: str):
    logger.info("processing_item_started", item_id=item_id)
    
    try:
        result = do_something(item_id)
        logger.info("processing_item_completed", item_id=item_id, result=result)
        return result
    except Exception as e:
        logger.error("processing_item_failed", item_id=item_id, error=str(e))
        raise
```

---

## ➕ Adding New Features

### Step-by-Step Guide

#### Example: Adding Item Tags Feature

**1. Define the Model**

```python
# app/models/tag.py
from app import db

class Tag(db.Model):
    """Item tag model"""
    __tablename__ = "tags"
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    color = db.Column(db.String(7), default="#007bff")  # Hex color
    created_at = db.Column(db.DateTime, default=db.func.now())
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "color": self.color,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }

# Add relationship to Item model
# app/models/item.py
item_tags = db.Table('item_tags',
    db.Column('item_id', db.Integer, db.ForeignKey('items.id')),
    db.Column('tag_id', db.Integer, db.ForeignKey('tags.id'))
)

class Item(db.Model):
    # ... existing fields ...
    tags = db.relationship('Tag', secondary=item_tags, backref='items')
```

**2. Create Migration**

```bash
# Generate migration
flask db migrate -m "add tags table and item_tags association"

# Review migration file in migrations/versions/

# Apply migration
flask db upgrade
```

**3. Create Repository**

```python
# app/repositories/tag_repo.py
from typing import List, Optional
from app.models.tag import Tag
from app import db

def find_all() -> List[dict]:
    """Get all tags"""
    tags = Tag.query.order_by(Tag.name).all()
    return [tag.to_dict() for tag in tags]

def find_by_name(name: str) -> Optional[dict]:
    """Find tag by name"""
    tag = Tag.query.filter_by(name=name).first()
    return tag.to_dict() if tag else None

def create(name: str, color: str = "#007bff") -> dict:
    """Create new tag"""
    tag = Tag(name=name, color=color)
    db.session.add(tag)
    db.session.commit()
    return tag.to_dict()

def delete(tag_id: int) -> bool:
    """Delete tag"""
    tag = Tag.query.get(tag_id)
    if tag:
        db.session.delete(tag)
        db.session.commit()
        return True
    return False
```

**4. Create Service**

```python
# app/services/tag_service.py
from typing import List, Optional
from app.repositories import tag_repo

def list_tags() -> List[dict]:
    """List all tags"""
    return tag_repo.find_all()

def create_tag(name: str, color: str = "#007bff") -> tuple[bool, str]:
    """
    Create new tag
    
    Returns:
        Tuple of (success: bool, message: str)
    """
    # Validate input
    if not name or len(name) > 50:
        return False, "Tag name must be 1-50 characters"
    
    # Check if exists
    existing = tag_repo.find_by_name(name)
    if existing:
        return False, "Tag already exists"
    
    # Create tag
    tag_repo.create(name, color)
    return True, "Tag created successfully"

def delete_tag(tag_id: int) -> tuple[bool, str]:
    """Delete tag"""
    if tag_repo.delete(tag_id):
        return True, "Tag deleted successfully"
    return False, "Tag not found"

def add_tag_to_item(item_id: int, tag_id: int) -> bool:
    """Add tag to item"""
    # Implementation here
    pass
```

**5. Create Routes**

```python
# app/tags/routes.py
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from app.utils.auth import login_required, admin_required
from app.services import tag_service

bp = Blueprint("tags", __name__, url_prefix="/tags")

@bp.route("/")
@login_required
def list_tags():
    """List all tags"""
    tags = tag_service.list_tags()
    return render_template("tags.html", tags=tags)

@bp.route("/add", methods=["POST"])
@admin_required
def add_tag():
    """Add new tag"""
    name = request.form.get("name", "").strip()
    color = request.form.get("color", "#007bff")
    
    success, message = tag_service.create_tag(name, color)
    
    if success:
        flash(message, "success")
    else:
        flash(message, "danger")
    
    return redirect(url_for("tags.list_tags"))

@bp.route("/delete/<int:tag_id>", methods=["POST"])
@admin_required
def delete_tag(tag_id: int):
    """Delete tag"""
    success, message = tag_service.delete_tag(tag_id)
    flash(message, "success" if success else "danger")
    return redirect(url_for("tags.list_tags"))

# API endpoint
@bp.route("/api/tags", methods=["GET"])
@login_required
def api_list_tags():
    """API: List all tags"""
    tags = tag_service.list_tags()
    return jsonify({"tags": tags})
```

**6. Register Blueprint**

```python
# app/__init__.py
def create_app():
    # ... existing code ...
    
    from app.tags.routes import bp as tags_bp
    app.register_blueprint(tags_bp)
    
    return app
```

**7. Create Template**

```html
<!-- templates/tags.html -->
{% extends "base.html" %}

{% block content %}
<div class="container mt-4">
    <h2>標籤管理</h2>
    
    <!-- Add tag form -->
    <form method="POST" action="{{ url_for('tags.add_tag') }}" class="mb-4">
        <div class="row">
            <div class="col-md-6">
                <input type="text" name="name" class="form-control" placeholder="標籤名稱" required>
            </div>
            <div class="col-md-3">
                <input type="color" name="color" class="form-control" value="#007bff">
            </div>
            <div class="col-md-3">
                <button type="submit" class="btn btn-primary">新增標籤</button>
            </div>
        </div>
    </form>
    
    <!-- Tag list -->
    <div class="row">
        {% for tag in tags %}
        <div class="col-md-3 mb-3">
            <div class="card">
                <div class="card-body" style="background-color: {{ tag.color }}20;">
                    <h5 class="card-title">{{ tag.name }}</h5>
                    <form method="POST" action="{{ url_for('tags.delete_tag', tag_id=tag.id) }}" class="d-inline">
                        <button type="submit" class="btn btn-sm btn-danger">刪除</button>
                    </form>
                </div>
            </div>
        </div>
        {% endfor %}
    </div>
</div>
{% endblock %}
```

**8. Write Tests**

```python
# tests/test_tag_service.py
import pytest
from app.services import tag_service

class TestTagService:
    def test_create_tag_success(self, app_context):
        """Test creating a new tag"""
        success, message = tag_service.create_tag("Electronics", "#FF5733")
        assert success is True
        assert "created successfully" in message
    
    def test_create_duplicate_tag(self, app_context):
        """Test creating duplicate tag fails"""
        tag_service.create_tag("Electronics", "#FF5733")
        success, message = tag_service.create_tag("Electronics", "#FF5733")
        assert success is False
        assert "already exists" in message
    
    def test_list_tags(self, app_context):
        """Test listing tags"""
        tag_service.create_tag("Electronics", "#FF5733")
        tag_service.create_tag("Food", "#00FF00")
        
        tags = tag_service.list_tags()
        assert len(tags) == 2
        assert any(t["name"] == "Electronics" for t in tags)
```

**9. Update Documentation**

- Add to API.md
- Update ARCHITECTURE.md if needed
- Add usage examples to README.md

---

## 💾 Database Operations

### Working with PostgreSQL

**Create Migration:**
```bash
flask db migrate -m "description"
flask db upgrade
```

**Rollback Migration:**
```bash
flask db downgrade
```

**Adding Indexes:**
```python
# In migration file
def upgrade():
    op.create_index('idx_items_name', 'items', ['name'])
    op.create_index('idx_items_expiry', 'items', ['usage_expiry'])
```

### Working with MongoDB

**Direct Access:**
```python
from app import mongo

# Insert
mongo.db.items.insert_one({"name": "Test", "type": "Food"})

# Find
items = list(mongo.db.items.find({"type": "Food"}))

# Update
mongo.db.items.update_one({"_id": item_id}, {"$set": {"name": "New Name"}})

# Delete
mongo.db.items.delete_one({"_id": item_id})
```

---

## 🧪 Testing

See [TESTING.md](../TESTING.md) for complete testing guide.

**Quick Reference:**

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_items.py

# Run with coverage
pytest --cov=app --cov-report=html

# Watch mode
pytest-watch

# Using Makefile
make test
make test-cov
make test-watch
```

---

## 🐛 Debugging

### Using Flask Debug Mode

```bash
# Enable debug mode
export FLASK_ENV=development
export FLASK_DEBUG=1
flask run
```

### Using Python Debugger

```python
# Add breakpoint
import pdb; pdb.set_trace()

# Or use breakpoint() (Python 3.7+)
breakpoint()
```

### Logging

```python
import structlog

logger = structlog.get_logger()

def problematic_function():
    logger.debug("entering_function", param1=value1)
    # ... code ...
    logger.debug("intermediate_state", state=current_state)
    # ... more code ...
```

### VSCode Debug Configuration

```json
// .vscode/launch.json
{
    "version": "0.2.0",
    "configurations": [
        {
            "name": "Flask",
            "type": "python",
            "request": "launch",
            "module": "flask",
            "env": {
                "FLASK_APP": "run.py",
                "FLASK_ENV": "development"
            },
            "args": [
                "run",
                "--port=8080",
                "--debug"
            ],
            "jinja": true
        }
    ]
}
```

---

## 🛠️ Common Tasks

### Adding a New Blueprint

```python
# 1. Create directory
mkdir -p app/newfeature

# 2. Create __init__.py
touch app/newfeature/__init__.py

# 3. Create routes.py
cat > app/newfeature/routes.py << 'EOF'
from flask import Blueprint

bp = Blueprint("newfeature", __name__, url_prefix="/newfeature")

@bp.route("/")
def index():
    return "New Feature"
EOF

# 4. Register in app/__init__.py
# Add this line in create_app():
# from app.newfeature.routes import bp as newfeature_bp
# app.register_blueprint(newfeature_bp)
```

### Adding Environment Variable

```python
# 1. Add to .env.example
echo "NEW_VARIABLE=default_value" >> .env.example

# 2. Add to app/config/validation.py
class AppConfig(BaseModel):
    new_variable: str = Field(default="default_value")
    
    @classmethod
    def load(cls):
        return cls(
            new_variable=os.getenv("NEW_VARIABLE", "default_value")
        )

# 3. Use in code
from app.config.validation import AppConfig
config = AppConfig.load()
value = config.new_variable
```

### Adding Scheduled Task

```python
# app/utils/scheduler.py
from apscheduler.schedulers.background import BackgroundScheduler

def my_scheduled_task():
    """Task to run on schedule"""
    logger.info("running_scheduled_task")
    # Do work
    
def init_scheduler():
    scheduler = BackgroundScheduler()
    
    # Run daily at 10:00 AM
    scheduler.add_job(
        my_scheduled_task,
        trigger="cron",
        hour=10,
        minute=0,
        id="my_task"
    )
    
    scheduler.start()
```

---

## 🔧 Troubleshooting

### Common Issues

**1. ImportError: No module named 'flask'**
```bash
# Solution: Activate virtual environment
source .venv/bin/activate
pip install -r requirements.txt
```

**2. Database connection refused**
```bash
# PostgreSQL
brew services start postgresql@16
# or
docker-compose up -d postgres

# MongoDB
brew services start mongodb-community
# or
docker-compose up -d mongo
```

**3. Port 8080 already in use**
```bash
# Find process using port
lsof -i :8080

# Kill process
kill -9 <PID>

# Or use different port
flask run --port 8081
```

**4. CSRF token missing**
```python
# Ensure CSRF protection is initialized
from app import csrf
csrf.init_app(app)

# In forms, add CSRF token
<form method="POST">
    {{ csrf_token() }}
    <!-- form fields -->
</form>
```

**5. Static files not loading**
```bash
# Check file permissions
chmod -R 755 static/

# Clear browser cache
# Or use Ctrl+Shift+R (hard reload)
```

---

## 📚 Additional Resources

- [API Documentation](./API.md)
- [Architecture Documentation](./ARCHITECTURE.md)
- [Testing Guide](../TESTING.md)
- [User Guide](../GUIDE_ZH-TW.md)
- [Flask Documentation](https://flask.palletsprojects.com/)
- [SQLAlchemy Documentation](https://docs.sqlalchemy.org/)

---

## 💬 Getting Help

- **Issues:** [GitHub Issues](../../issues)
- **Discussions:** [GitHub Discussions](../../discussions)
- **Email:** support@example.com

---

**Last Updated:** 2026-01-24  
**Version:** 1.0.0
