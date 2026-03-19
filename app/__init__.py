"""物品管理系統主模組"""
import os
import secrets
from pathlib import Path
from typing import Literal

from flask import Flask
from sqlalchemy import inspect, text
from flask_pymongo import PyMongo
from flask_wtf.csrf import CSRFProtect
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_sqlalchemy import SQLAlchemy
from flask_caching import Cache
from flask_babel import Babel

mongo = PyMongo()
db = SQLAlchemy()
cache = Cache()
csrf = CSRFProtect()
babel = Babel()
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[],
    storage_uri=os.environ.get("REDIS_URL", "redis://localhost:6379/0"),
)

DBType = Literal["mongo", "postgres"]


def get_db_type() -> DBType:
    """獲取當前使用的資料庫類型"""
    db_type = os.environ.get("DB_TYPE", "postgres").lower()
    return "postgres" if db_type in ("postgres", "postgresql") else "mongo"


def ensure_upload_folder(app: Flask) -> None:
    upload_path = Path(app.config["UPLOAD_FOLDER"])
    upload_path.mkdir(parents=True, exist_ok=True)


def _ensure_default_admin() -> None:
    """確保預設管理員帳號存在"""
    from werkzeug.security import generate_password_hash

    db_type = get_db_type()
    hashed_password = generate_password_hash("admin")

    if db_type == "postgres":
        from app.models import User

        existing_admin = User.query.filter_by(User="admin").first()
        if not existing_admin:
            admin = User(
                User="admin",
                Password=hashed_password,
                admin=True,
                password_changed=False
            )
            db.session.add(admin)
            db.session.commit()
            print("✅ 已建立預設管理員帳號: admin / admin (首次登入請修改密碼)")
    else:
        existing_admin = mongo.db.user.find_one({"User": "admin"})
        if not existing_admin:
            mongo.db.user.insert_one({
                "User": "admin",
                "Password": hashed_password,
                "admin": True,
                "password_changed": False
            })
            print("✅ 已建立預設管理員帳號: admin / admin (首次登入請修改密碼)")


def _ensure_item_maintenance_columns() -> None:
    """補齊 items 表缺少的保養欄位，避免舊資料庫在重構後直接失敗。"""
    if get_db_type() != "postgres":
        return

    try:
        inspector = inspect(db.engine)
    except RuntimeError:
        # 測試環境會 monkeypatch db.init_app/create_all，此時不需要真的補欄位。
        return
    if not inspector.has_table("items"):
        return

    existing_columns = {column["name"] for column in inspector.get_columns("items")}
    alter_statements = []
    if "MaintenanceCategory" not in existing_columns:
        alter_statements.append('ALTER TABLE items ADD COLUMN "MaintenanceCategory" VARCHAR(50) DEFAULT \'\';')
    if "MaintenanceIntervalDays" not in existing_columns:
        alter_statements.append('ALTER TABLE items ADD COLUMN "MaintenanceIntervalDays" INTEGER;')
    if "LastMaintenanceDate" not in existing_columns:
        alter_statements.append('ALTER TABLE items ADD COLUMN "LastMaintenanceDate" DATE;')

    for statement in alter_statements:
        db.session.execute(text(statement))

    if alter_statements:
        db.session.commit()


def _ensure_user_profile_columns() -> None:
    """補齊 users 表缺少的個人設定欄位，避免舊資料庫在重構後直接失敗。"""
    if get_db_type() != "postgres":
        return

    try:
        inspector = inspect(db.engine)
    except RuntimeError:
        return
    if not inspector.has_table("users"):
        return

    existing_columns = {column["name"] for column in inspector.get_columns("users")}
    alter_statements = []
    if "display_name" not in existing_columns:
        alter_statements.append('ALTER TABLE users ADD COLUMN display_name VARCHAR(100);')
    if "theme_preference" not in existing_columns:
        alter_statements.append("ALTER TABLE users ADD COLUMN theme_preference VARCHAR(20) DEFAULT 'light';")
    if "language" not in existing_columns:
        alter_statements.append("ALTER TABLE users ADD COLUMN language VARCHAR(10) DEFAULT 'zh_TW';")

    for statement in alter_statements:
        db.session.execute(text(statement))

    if alter_statements:
        db.session.commit()


def _ensure_type_parent_column() -> None:
    """補齊 item_types 表缺少的 parent_id 欄位，支援子分類階層結構。"""
    if get_db_type() != "postgres":
        return

    try:
        inspector = inspect(db.engine)
    except RuntimeError:
        return
    if not inspector.has_table("item_types"):
        return

    existing_columns = {column["name"] for column in inspector.get_columns("item_types")}
    if "parent_id" not in existing_columns:
        db.session.execute(text(
            'ALTER TABLE item_types ADD COLUMN parent_id INTEGER REFERENCES item_types(id) ON DELETE SET NULL;'
        ))
        db.session.commit()


def _ensure_fulltext_extensions() -> None:
    """Install pg_trgm extension for fuzzy full-text search.

    Wrapped in try/except because the connected user may not have superuser
    privileges; in that case full-text search gracefully falls back to ILIKE.
    """
    if get_db_type() != "postgres":
        return
    try:
        db.session.execute(text("CREATE EXTENSION IF NOT EXISTS pg_trgm"))
        db.session.commit()
    except Exception:
        db.session.rollback()


def create_app() -> Flask:
    app = Flask(
        __name__,
        template_folder="../templates",
        static_folder="../static",
    )

    secret_key = os.environ.get("SECRET_KEY")
    if not secret_key:
        if os.environ.get("FLASK_ENV") == "production":
            raise RuntimeError("SECRET_KEY 環境變數未設定，生產環境中必須設定此值")
        secret_key = secrets.token_hex(32)
        print("⚠️  警告：未設定 SECRET_KEY 環境變數，使用隨機值（不建議用於生產環境）")

    db_type = get_db_type()
    
    app.config.from_mapping(
        # 資料庫設定
        DB_TYPE=db_type,
        MONGO_URI=os.environ.get("MONGO_URI", "mongodb://localhost:27017/myDB"),
        SQLALCHEMY_DATABASE_URI=os.environ.get(
            "DATABASE_URL",
            "postgresql://itemman:itemman_pass@localhost:5432/itemman"
        ),
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        SECRET_KEY=secret_key,
        UPLOAD_FOLDER=os.environ.get(
            "UPLOAD_FOLDER",
            str(Path(__file__).resolve().parent.parent / "static" / "uploads"),
        ),
        MAX_CONTENT_LENGTH=16 * 1024 * 1024,
        ALLOWED_EXTENSIONS={"png", "jpg", "jpeg", "gif"},
        SESSION_COOKIE_SECURE=os.environ.get("FLASK_ENV") == "production",
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        WTF_CSRF_ENABLED=True,
        WTF_CSRF_TIME_LIMIT=3600,
        LINE_CHANNEL_SECRET=os.environ.get("LINE_CHANNEL_SECRET", ""),
        LINE_CHANNEL_ACCESS_TOKEN=os.environ.get("LINE_CHANNEL_ACCESS_TOKEN", ""),
        LINE_LIFF_ID=os.environ.get("LINE_LIFF_ID", ""),
        LINE_BOT_URL=os.environ.get("LINE_BOT_URL", ""),
        TELEGRAM_BOT_TOKEN=os.environ.get("TELEGRAM_BOT_TOKEN", ""),
        TELEGRAM_BOT_USERNAME=os.environ.get("TELEGRAM_BOT_USERNAME", ""),
        TELEGRAM_WEBHOOK_SECRET=os.environ.get("TELEGRAM_WEBHOOK_SECRET", ""),
    )

    ensure_upload_folder(app)
    
    # 根據資料庫類型初始化
    if db_type == "postgres":
        db.init_app(app)
        with app.app_context():
            db.create_all()
            _ensure_item_maintenance_columns()
            _ensure_user_profile_columns()
            _ensure_type_parent_column()
            _ensure_fulltext_extensions()
    else:
        mongo.init_app(app)
    
    csrf.init_app(app)
    limiter.init_app(app)

    # i18n 設定
    app.config["BABEL_DEFAULT_LOCALE"] = "zh_TW"
    app.config["BABEL_DEFAULT_TIMEZONE"] = "Asia/Taipei"
    app.config["BABEL_TRANSLATION_DIRECTORIES"] = "translations"

    def get_locale():
        from flask import session as _sess
        # 優先使用使用者設定的語言
        user_lang = _sess.get("language")
        if user_lang in ("zh_TW", "en"):
            return user_lang
        from flask import request as _req
        return _req.accept_languages.best_match(["zh_TW", "en"], default="zh_TW")

    babel.init_app(app, locale_selector=get_locale)

    cache_config = {
        "CACHE_TYPE": "RedisCache",
        "CACHE_REDIS_URL": os.environ.get("REDIS_URL", "redis://localhost:6379/0"),
        "CACHE_DEFAULT_TIMEOUT": 300
    }
    cache.init_app(app, config=cache_config)

    # Initialize structured logging
    from app.utils.logging import init_flask_logging

    logger = init_flask_logging(app)

    # Load and validate configuration
    from app.config.validation import AppConfig

    try:
        cfg = AppConfig.load()
        config_result = {"valid": True, "config": cfg}
        logger.info("configuration_validation_passed")
    except Exception as e:
        logger.warning("configuration_validation_warning", error=str(e))
        config_result = {"valid": False, "errors": str(e), "config": None}

    with app.app_context():
        if os.environ.get("TEST_MODE") != "true":
            _ensure_default_admin()

        # 只在明確啟用 scheduler 的進程中初始化（避免多 worker 重複執行）
        if os.environ.get("ENABLE_SCHEDULER") == "true":
            from app.utils import scheduler
            scheduler.init_scheduler()

        # 初始化全局錯誤處理器
        from app.utils.error_handler import init_error_handlers
        init_error_handlers(app)

    # Blueprint 註冊
    from app.auth.routes import bp as auth_bp
    from app.items.routes import bp as items_bp
    from app.types.routes import bp as types_bp
    from app.locations.routes import bp as locations_bp
    from app.notifications.routes import bp as notifications_bp
    from app.health.routes import bp as health_bp
    from app.routes.import_routes import bp as import_bp
    from app.api.routes import bp as api_bp
    from app.travel.routes import bp as travel_bp, shopping_bp
    from app.line.routes import bp as line_bp
    from app.telegram.routes import bp as telegram_bp
    from app.profile.routes import bp as profile_bp
    from app.loans.routes import bp as loans_bp
    from app.stocktake.routes import bp as stocktake_bp
    from app.custom_fields.routes import bp as custom_fields_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(items_bp)
    app.register_blueprint(types_bp)
    app.register_blueprint(locations_bp)
    app.register_blueprint(notifications_bp)
    app.register_blueprint(health_bp)
    app.register_blueprint(import_bp)
    app.register_blueprint(api_bp)
    app.register_blueprint(travel_bp)
    app.register_blueprint(shopping_bp)
    app.register_blueprint(line_bp)
    app.register_blueprint(telegram_bp)
    app.register_blueprint(profile_bp)
    app.register_blueprint(loans_bp)
    app.register_blueprint(stocktake_bp)
    app.register_blueprint(custom_fields_bp)

    # 註冊自定義過濾器
    import re
    from markupsafe import Markup, escape
    
    @app.template_filter('highlight')
    def highlight_filter(text, query):
        if not query or not text:
            return text
        
        text = str(text)
        text = str(escape(text))
        pattern = re.compile(f'({re.escape(query)})', re.IGNORECASE)
        result = pattern.sub(r'<span class="search-highlight">\1</span>', text)
        
        return Markup(result)
    
    @app.template_filter('datetime_format')
    def datetime_format_filter(value, format='%Y-%m-%d %H:%M'):
        if not value:
            return ''
        if isinstance(value, str):
            return value
        return value.strftime(format)

    return app
