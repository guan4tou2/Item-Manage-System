# 🏗️ Architecture Documentation

System architecture and design patterns for the Item Management System.

## 📋 Table of Contents

- [System Overview](#system-overview)
- [Architecture Layers](#architecture-layers)
- [Database Strategy](#database-strategy)
- [Authentication Flow](#authentication-flow)
- [Notification System](#notification-system)
- [Caching Strategy](#caching-strategy)
- [File Upload Handling](#file-upload-handling)
- [Technology Stack](#technology-stack)
- [Design Patterns](#design-patterns)
- [Security Architecture](#security-architecture)

---

## 🎯 System Overview

The Item Management System is a full-stack web application built with Flask that helps users track and manage physical items, their locations, expiration dates, and warranties.

### Key Features
- Multi-database support (PostgreSQL/MongoDB)
- Session-based authentication
- Scheduled notifications (email)
- Photo management
- QR/Barcode generation
- Travel packing lists
- Shopping lists
- RESTful API

### Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                         Client Layer                         │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │  Web Browser │  │  Mobile PWA  │  │  API Client  │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                     Presentation Layer                       │
│  ┌──────────────────────────────────────────────────────┐  │
│  │              Flask Routes (Blueprints)                │  │
│  │  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌──────────┐  │  │
│  │  │  Auth   │ │  Items  │ │  Types  │ │  Travel  │  │  │
│  │  └─────────┘ └─────────┘ └─────────┘ └──────────┘  │  │
│  │  ┌─────────┐ ┌──────────┐ ┌──────────┐ ┌─────────┐│  │
│  │  │Location │ │  Notify  │ │  Import  │ │  Health │ │  │
│  │  └─────────┘ └──────────┘ └──────────┘ └─────────┘│  │
│  └──────────────────────────────────────────────────────┘  │
│                              │                               │
│  ┌──────────────────────────────────────────────────────┐  │
│  │           Middleware & Extensions                     │  │
│  │  • CSRF Protection      • Rate Limiting               │  │
│  │  • Session Management   • Caching (Redis)             │  │
│  │  • Error Handlers       • Logging (structlog)         │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                      Business Logic Layer                    │
│  ┌──────────────────────────────────────────────────────┐  │
│  │                   Services Layer                      │  │
│  │  ┌────────────┐ ┌────────────┐ ┌────────────┐       │  │
│  │  │    Item    │ │    User    │ │   Type     │       │  │
│  │  │  Service   │ │  Service   │ │  Service   │       │  │
│  │  └────────────┘ └────────────┘ └────────────┘       │  │
│  │  ┌────────────┐ ┌────────────┐ ┌────────────┐       │  │
│  │  │  Location  │ │   Email    │ │Notification│       │  │
│  │  │  Service   │ │  Service   │ │  Service   │       │  │
│  │  └────────────┘ └────────────┘ └────────────┘       │  │
│  │  ┌────────────┐ ┌────────────┐                      │  │
│  │  │    Log     │ │  Scheduler │                      │  │
│  │  │  Service   │ │  (APSched) │                      │  │
│  │  └────────────┘ └────────────┘                      │  │
│  └──────────────────────────────────────────────────────┘  │
│                              │                               │
│  ┌──────────────────────────────────────────────────────┐  │
│  │                 Validators Layer                      │  │
│  │  • Form Validation (Flask-WTF)                        │  │
│  │  • Input Sanitization                                 │  │
│  │  • Pydantic Models (Config validation)               │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    Data Access Layer                         │
│  ┌──────────────────────────────────────────────────────┐  │
│  │               Repository Pattern                      │  │
│  │  ┌────────────┐ ┌────────────┐ ┌────────────┐       │  │
│  │  │    Item    │ │    User    │ │   Type     │       │  │
│  │  │    Repo    │ │    Repo    │ │    Repo    │       │  │
│  │  └────────────┘ └────────────┘ └────────────┘       │  │
│  │  ┌────────────┐ ┌────────────┐                      │  │
│  │  │  Location  │ │    Log     │                      │  │
│  │  │    Repo    │ │    Repo    │                      │  │
│  │  └────────────┘ └────────────┘                      │  │
│  │                                                       │  │
│  │  ┌───────────────────────────────────────────────┐  │  │
│  │  │         Repository Factory                     │  │  │
│  │  │    (Strategy Pattern for DB Selection)        │  │  │
│  │  │  ┌──────────────┐    ┌──────────────┐        │  │  │
│  │  │  │  Postgres    │    │   MongoDB    │        │  │  │
│  │  │  │Implementation│    │Implementation│        │  │  │
│  │  │  └──────────────┘    └──────────────┘        │  │  │
│  │  └───────────────────────────────────────────────┘  │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                       Data Layer                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │  PostgreSQL  │  │   MongoDB    │  │    Redis     │      │
│  │   (Primary)  │  │   (Legacy)   │  │   (Cache)    │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
│  ┌──────────────┐  ┌──────────────┐                        │
│  │  File System │  │     Email    │                        │
│  │  (Uploads)   │  │  (SMTP/API)  │                        │
│  └──────────────┘  └──────────────┘                        │
└─────────────────────────────────────────────────────────────┘
```

---

## 🏛️ Architecture Layers

### 1. Presentation Layer (Routes)

**Location:** `app/<module>/routes.py`

**Responsibility:**
- Handle HTTP requests and responses
- Render templates
- Validate session authentication
- Return JSON for API endpoints

**Blueprints:**
```python
app/
├── auth/routes.py        # Authentication endpoints
├── items/routes.py       # Item management
├── types/routes.py       # Item type management
├── locations/routes.py   # Location management
├── notifications/routes.py  # Notification settings
├── travel/routes.py      # Travel & shopping lists
├── health/routes.py      # Health checks
└── routes/import_routes.py  # Bulk import
```

**Example Flow:**
```python
# User Request
GET /home?type=電器&page=1

# Route Handler (items/routes.py)
@bp.route("/home")
@login_required
def home():
    filters = extract_filters(request.args)
    result = item_service.list_items(filters, page=1)
    return render_template("home.html", items=result["items"])
```

---

### 2. Business Logic Layer (Services)

**Location:** `app/services/`

**Responsibility:**
- Implement business rules
- Coordinate between repositories
- Handle complex operations
- Process data transformations

**Services:**
```python
app/services/
├── item_service.py          # Item CRUD & search logic
├── user_service.py          # User auth & management
├── type_service.py          # Type management
├── location_service.py      # Location management
├── notification_service.py  # Notification logic
├── email_service.py         # Email sending
└── log_service.py           # Activity logging
```

**Example:**
```python
# item_service.py
def list_items(filters: dict, page: int = 1) -> dict:
    """
    List items with filters and pagination
    
    Business logic:
    1. Apply filters
    2. Add expiry annotations
    3. Apply sorting
    4. Paginate results
    """
    items = item_repo.find_with_filters(filters)
    items = add_expiry_status(items)
    items = apply_sorting(items, filters.get('sort'))
    return paginate(items, page)
```

---

### 3. Data Access Layer (Repositories)

**Location:** `app/repositories/`

**Responsibility:**
- Abstract database operations
- Provide consistent interface across databases
- Handle database-specific queries

**Structure:**
```python
app/repositories/
├── base.py              # Base repository interface
├── factory.py           # Repository factory (Strategy pattern)
├── postgres_impl.py     # PostgreSQL implementation
├── mongo_impl.py        # MongoDB implementation
├── item_repo.py         # Item repository
├── user_repo.py         # User repository
├── type_repo.py         # Type repository
├── location_repo.py     # Location repository
└── log_repo.py          # Log repository
```

**Example:**
```python
# Factory pattern selects implementation
def get_item_repository():
    db_type = get_db_type()
    if db_type == "postgres":
        return PostgresItemRepository()
    else:
        return MongoItemRepository()
```

---

### 4. Model Layer

**Location:** `app/models/`

**Responsibility:**
- Define data structures
- Map to database schemas
- Provide data validation

**Models:**
```python
app/models/
├── __init__.py
├── item.py          # Item model
├── item_type.py     # ItemType model
├── location.py      # Location model
├── user.py          # User model
├── log.py           # Log model
└── travel.py        # Travel, TravelGroup, TravelItem, ShoppingList
```

**SQLAlchemy Models:**
```python
# app/models/item.py
class Item(db.Model):
    __tablename__ = "items"
    
    id = db.Column(db.Integer, primary_key=True)
    item_id = db.Column(db.String(100), unique=True, nullable=False)
    name = db.Column(db.String(200), nullable=False)
    type = db.Column(db.String(100))
    # ... other fields
```

---

## 🗄️ Database Strategy

### Strategy Pattern Implementation

The system uses the **Strategy Pattern** to support multiple databases:

```python
# app/repositories/factory.py
class RepositoryFactory:
    @staticmethod
    def get_item_repo():
        if get_db_type() == "postgres":
            return PostgresItemRepository()
        return MongoItemRepository()
```

### Database Selection

**Environment Variable:**
```bash
DB_TYPE=postgres  # or mongo
```

### PostgreSQL (Primary - Recommended)

**Connection:**
```python
DATABASE_URL=postgresql://user:pass@localhost:5432/itemman
```

**Features:**
- ACID transactions
- Referential integrity
- Advanced indexing
- Better query optimization
- Type safety

**Schema:**
```sql
-- Items table
CREATE TABLE items (
    id SERIAL PRIMARY KEY,
    item_id VARCHAR(100) UNIQUE NOT NULL,
    name VARCHAR(200) NOT NULL,
    type VARCHAR(100),
    store_place VARCHAR(200),
    floor VARCHAR(100),
    room VARCHAR(100),
    zone VARCHAR(100),
    warranty_expiry DATE,
    usage_expiry DATE,
    photo VARCHAR(500),
    description TEXT,
    owner VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_items_name ON items(name);
CREATE INDEX idx_items_type ON items(type);
CREATE INDEX idx_items_warranty ON items(warranty_expiry);
CREATE INDEX idx_items_usage ON items(usage_expiry);
```

### MongoDB (Legacy Support)

**Connection:**
```python
MONGO_URI=mongodb://localhost:27017/myDB
```

**Collections:**
- `items` - Item documents
- `user` - User documents
- `itemtype` - Type documents
- `location` - Location documents
- `log` - Activity log documents

### Migration Path

**From MongoDB to PostgreSQL:**

1. Export MongoDB data:
```bash
mongoexport --db myDB --collection items --out items.json
```

2. Use migration script (future enhancement)
3. Validate data integrity
4. Switch `DB_TYPE` to `postgres`

---

## 🔐 Authentication Flow

### Session-Based Authentication

```
┌─────────┐         ┌─────────┐         ┌─────────┐
│ Browser │         │  Flask  │         │Database │
└────┬────┘         └────┬────┘         └────┬────┘
     │                   │                   │
     │  POST /signin     │                   │
     ├──────────────────>│                   │
     │                   │                   │
     │                   │ Check credentials │
     │                   ├──────────────────>│
     │                   │                   │
     │                   │ User data         │
     │                   │<──────────────────┤
     │                   │                   │
     │                   │ Create session    │
     │                   │ (Flask session)   │
     │                   │                   │
     │  Set-Cookie: sid  │                   │
     │<──────────────────┤                   │
     │  Redirect: /home  │                   │
     │                   │                   │
     │  GET /home        │                   │
     │  Cookie: sid      │                   │
     ├──────────────────>│                   │
     │                   │                   │
     │                   │ Validate session  │
     │                   │ (check session["UserID"]) │
     │                   │                   │
     │  HTML response    │                   │
     │<──────────────────┤                   │
     │                   │                   │
```

### Authentication Decorators

```python
# app/utils/auth.py

def login_required(f):
    """Require authentication for endpoint"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "UserID" not in session:
            return redirect(url_for("auth.signin"))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    """Require admin privileges"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "UserID" not in session:
            return redirect(url_for("auth.signin"))
        
        user = user_repo.find_by_username(session["UserID"])
        if not user or not user.get("admin"):
            flash("需要管理員權限", "danger")
            return redirect(url_for("items.home"))
        
        return f(*args, **kwargs)
    return decorated_function
```

### Password Security

```python
# app/services/user_service.py

def hash_password(password: str) -> str:
    """Hash password using bcrypt"""
    from werkzeug.security import generate_password_hash
    return generate_password_hash(password)

def verify_password(password: str, hashed: str) -> bool:
    """Verify password against hash"""
    from werkzeug.security import check_password_hash
    return check_password_hash(hashed, password)
```

**Features:**
- Bcrypt password hashing
- Auto-upgrade from plaintext to hashed
- Failed login attempt tracking
- Force password change on first login

---

## 🔔 Notification System

### Architecture

```
┌─────────────────────────────────────────────────────┐
│              Notification System                     │
└─────────────────────────────────────────────────────┘
                      │
         ┌────────────┴────────────┐
         │                         │
         ▼                         ▼
┌─────────────────┐      ┌─────────────────┐
│   APScheduler   │      │  Manual Trigger │
│   (Cron Job)    │      │  (User Button)  │
└────────┬────────┘      └────────┬────────┘
         │                         │
         └────────────┬────────────┘
                      │
                      ▼
         ┌────────────────────────┐
         │ Notification Service   │
         │                        │
         │ 1. Get user settings   │
         │ 2. Find expiring items │
         │ 3. Group by category   │
         │ 4. Check send cooldown │
         └────────┬───────────────┘
                  │
                  ▼
         ┌────────────────────────┐
         │    Email Service       │
         │                        │
         │ 1. Build email content │
         │ 2. Render template     │
         │ 3. Send via SMTP       │
         │ 4. Log result          │
         └────────────────────────┘
```

### Scheduled Notifications

**Configuration:**
```python
# app/utils/scheduler.py
from apscheduler.schedulers.background import BackgroundScheduler

scheduler = BackgroundScheduler()

def init_scheduler():
    # Daily notification check at 9:00 AM
    scheduler.add_job(
        func=send_all_notifications,
        trigger="cron",
        hour=9,
        minute=0,
        id="daily_notification"
    )
    scheduler.start()
```

### Notification Logic

```python
# app/services/notification_service.py

def should_send_notification(user: dict, items: list) -> bool:
    """
    Check if notification should be sent
    
    Rules:
    1. User has email configured
    2. Notifications enabled
    3. Has expiring items
    4. Not sent recently (cooldown period)
    """
    settings = user.get("notification_settings", {})
    
    if not settings.get("notify_enabled"):
        return False
    
    if not settings.get("email"):
        return False
    
    if not items:
        return False
    
    last_sent = settings.get("last_notification_sent")
    if last_sent and is_within_cooldown(last_sent):
        return False
    
    return True
```

### Email Template

```
Subject: 🔔 物品到期提醒 - 2026-01-24

親愛的用戶，

您有以下物品即將到期或已過期：

⚠️ 已過期物品 (2 項)
━━━━━━━━━━━━━━━━━━━━
• 牛奶 - 使用期限: 2026-01-20
• 面包 - 使用期限: 2026-01-22

⏰ 即將到期物品 (5 項)
━━━━━━━━━━━━━━━━━━━━
• 雞蛋 - 使用期限: 2026-01-30
• 優格 - 使用期限: 2026-02-01
• 沙拉 - 使用期限: 2026-02-05

請登入系統查看詳情並進行處理。

[登入系統]

─────────────────────
Item Management System
```

---

## 💾 Caching Strategy

### Redis Cache

**Configuration:**
```python
# app/__init__.py
cache_config = {
    "CACHE_TYPE": "RedisCache",
    "CACHE_REDIS_URL": "redis://localhost:6379/0",
    "CACHE_DEFAULT_TIMEOUT": 300  # 5 minutes
}
cache.init_app(app, config=cache_config)
```

### Cache Usage

```python
from app import cache

# Cache expensive query results
@cache.memoize(timeout=300)
def get_item_statistics():
    """Cache stats for 5 minutes"""
    return {
        "total_items": item_repo.count_all(),
        "items_with_photo": item_repo.count_with_photos(),
        # ... more stats
    }

# Invalidate cache on updates
def update_item(item_id, data):
    result = item_repo.update(item_id, data)
    cache.delete_memoized(get_item_statistics)
    return result
```

### Cached Data

- Item statistics
- Type lists
- Location lists
- User session data

---

## 📁 File Upload Handling

### Upload Flow

```
┌─────────┐         ┌─────────┐         ┌──────────┐
│ Browser │         │  Flask  │         │   Disk   │
└────┬────┘         └────┬────┘         └────┬─────┘
     │                   │                   │
     │  POST /additem    │                   │
     │  (multipart/form) │                   │
     ├──────────────────>│                   │
     │                   │                   │
     │                   │ 1. Validate file  │
     │                   │    - Size < 16MB  │
     │                   │    - Type: JPG/PNG│
     │                   │                   │
     │                   │ 2. Generate UUID  │
     │                   │    filename       │
     │                   │                   │
     │                   │ 3. Save file      │
     │                   ├──────────────────>│
     │                   │                   │
     │                   │ 4. Create         │
     │                   │    thumbnail      │
     │                   ├──────────────────>│
     │                   │                   │
     │                   │ 5. Save DB record │
     │                   │    with filename  │
     │                   │                   │
     │  Success response │                   │
     │<──────────────────┤                   │
     │                   │                   │
```

### Storage Configuration

```python
# app/__init__.py
app.config.update(
    UPLOAD_FOLDER="static/uploads",
    MAX_CONTENT_LENGTH=16 * 1024 * 1024,  # 16MB
    ALLOWED_EXTENSIONS={"png", "jpg", "jpeg", "gif"}
)
```

### File Processing

```python
# app/utils/storage.py

def save_upload_file(file, filename: str) -> str:
    """
    Save uploaded file with UUID filename
    
    1. Generate unique filename
    2. Validate file type
    3. Save original
    4. Generate thumbnail (optional)
    """
    unique_filename = f"{uuid.uuid4()}_{secure_filename(filename)}"
    filepath = os.path.join(app.config["UPLOAD_FOLDER"], unique_filename)
    
    file.save(filepath)
    
    # Create thumbnail if image
    if is_image(filepath):
        create_thumbnail(filepath)
    
    return unique_filename
```

---

## 🛠️ Technology Stack

### Backend
```
Flask 3.1+              - Web framework
SQLAlchemy 2.0+         - ORM (PostgreSQL)
PyMongo                 - MongoDB driver
APScheduler 3.11+       - Job scheduling
Flask-Mail              - Email sending
Flask-Login             - User sessions
Flask-WTF               - Form validation & CSRF
Flask-Limiter           - Rate limiting
Flask-Caching           - Redis caching
Pydantic 2.0+           - Config validation
structlog               - Structured logging
Pillow                  - Image processing
qrcode                  - QR code generation
python-barcode          - Barcode generation
Werkzeug                - WSGI utilities
```

### Frontend
```
Bootstrap 5             - UI framework
Font Awesome            - Icons
JavaScript (ES6+)       - Interactivity
Jinja2                  - Template engine
```

### Database & Cache
```
PostgreSQL 16+          - Primary database
MongoDB 7+              - Legacy support
Redis 7+                - Caching & rate limiting
```

### DevOps
```
Docker                  - Containerization
Docker Compose          - Multi-container orchestration
Gunicorn                - WSGI server
Nginx (recommended)     - Reverse proxy
```

---

## 🎨 Design Patterns

### 1. Repository Pattern

**Purpose:** Abstract data access logic

**Implementation:**
```python
# Base interface
class BaseRepository(ABC):
    @abstractmethod
    def find_all(self) -> List[dict]:
        pass
    
    @abstractmethod
    def find_by_id(self, id: str) -> Optional[dict]:
        pass

# Concrete implementations
class PostgresItemRepository(BaseRepository):
    def find_all(self):
        return Item.query.all()

class MongoItemRepository(BaseRepository):
    def find_all(self):
        return list(mongo.db.items.find())
```

### 2. Strategy Pattern

**Purpose:** Select database implementation at runtime

**Implementation:**
```python
class RepositoryFactory:
    @staticmethod
    def create(entity_type: str):
        db_type = get_db_type()
        
        if entity_type == "item":
            return PostgresItemRepo() if db_type == "postgres" else MongoItemRepo()
```

### 3. Factory Pattern

**Purpose:** Create repository instances

**Usage:** Combined with Strategy pattern for database selection

### 4. Decorator Pattern

**Purpose:** Add functionality to routes (auth, caching, rate limiting)

**Implementation:**
```python
@bp.route("/admin")
@login_required
@admin_required
@limiter.limit("10 per minute")
@cache.cached(timeout=60)
def admin_panel():
    pass
```

### 5. Template Method Pattern

**Purpose:** Define skeleton of notification process

**Implementation:**
```python
class BaseNotificationService:
    def send_notification(self, user, items):
        # Template method
        if not self.should_send(user, items):
            return
        
        content = self.prepare_content(items)
        self.deliver(user, content)
        self.log_sent(user)
    
    @abstractmethod
    def deliver(self, user, content):
        pass
```

---

## 🔒 Security Architecture

### CSRF Protection

```python
# Enabled globally
from flask_wtf.csrf import CSRFProtect
csrf = CSRFProtect(app)

# Exempt API endpoints
@bp.route("/api/endpoint", methods=["POST"])
@csrf.exempt
def api_endpoint():
    pass
```

### Rate Limiting

```python
from flask_limiter import Limiter

limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"],
    storage_uri="redis://localhost:6379/0"
)

# Per-endpoint limits
@bp.route("/login", methods=["POST"])
@limiter.limit("5 per minute")
def login():
    pass
```

### Input Validation

```python
# Form validation
from flask_wtf import FlaskForm
from wtforms import StringField, validators

class ItemForm(FlaskForm):
    name = StringField('Name', [
        validators.DataRequired(),
        validators.Length(min=1, max=200)
    ])

# Pydantic validation
from pydantic import BaseModel, validator

class CreateItemRequest(BaseModel):
    name: str
    item_id: str
    
    @validator('name')
    def validate_name(cls, v):
        if not v.strip():
            raise ValueError('Name cannot be empty')
        return v.strip()
```

### Session Security

```python
app.config.update(
    SESSION_COOKIE_SECURE=True,      # HTTPS only
    SESSION_COOKIE_HTTPONLY=True,    # No JS access
    SESSION_COOKIE_SAMESITE='Lax',   # CSRF protection
    PERMANENT_SESSION_LIFETIME=3600  # 1 hour timeout
)
```

### SQL Injection Prevention

```python
# Using SQLAlchemy ORM (parameterized queries)
items = Item.query.filter(
    Item.name.ilike(f"%{search_query}%")
).all()

# Never use raw SQL with string formatting
```

### File Upload Security

```python
def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def secure_filename_upload(file):
    if not allowed_file(file.filename):
        raise ValueError("Invalid file type")
    
    if file.content_length > MAX_CONTENT_LENGTH:
        raise ValueError("File too large")
    
    # Use UUID to prevent path traversal
    filename = f"{uuid.uuid4()}_{secure_filename(file.filename)}"
    return filename
```

---

## 📚 Additional Resources

- [API Documentation](./API.md)
- [Development Guide](./DEVELOPMENT.md)
- [Testing Documentation](../TESTING.md)
- [Deployment Guide](../Deployment_Guide_zh-TW.md)

---

**Last Updated:** 2026-01-24  
**Version:** 1.0.0
