"""物品管理系統主模組"""
import os
import secrets
from pathlib import Path
from typing import Literal

from flask import Flask
from flask_pymongo import PyMongo
from flask_wtf.csrf import CSRFProtect
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_sqlalchemy import SQLAlchemy
from flask_caching import Cache

mongo = PyMongo()
db = SQLAlchemy()
cache = Cache()
csrf = CSRFProtect()
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"],
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
    db_type = get_db_type()
    
    if db_type == "postgres":
        from app.models import User
        
        existing_admin = User.query.filter_by(User="admin").first()
        if not existing_admin:
            admin = User(
                User="admin",
                Password="admin",
                admin=True
            )
            db.session.add(admin)
            db.session.commit()
            print("✅ 已建立預設管理員帳號: admin / admin")
    else:
        existing_admin = mongo.db.user.find_one({"User": "admin"})
        if not existing_admin:
            mongo.db.user.insert_one({
                "User": "admin",
                "Password": "admin",
                "admin": True
            })
            print("✅ 已建立預設管理員帳號: admin / admin")


def create_app() -> Flask:
    app = Flask(
        __name__,
        template_folder="../templates",
        static_folder="../static",
    )

    secret_key = os.environ.get("SECRET_KEY")
    if not secret_key:
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
    )

    ensure_upload_folder(app)
    
    # 根據資料庫類型初始化
    if db_type == "postgres":
        db.init_app(app)
        with app.app_context():
            db.create_all()
    else:
        mongo.init_app(app)
    
    csrf.init_app(app)
    limiter.init_app(app)

    cache_config = {
        "CACHE_TYPE": "RedisCache",
        "CACHE_REDIS_URL": os.environ.get("REDIS_URL", "redis://localhost:6379/0"),
        "CACHE_DEFAULT_TIMEOUT": 300
    }
    cache.init_app(app, config=cache_config)

    # Load and validate configuration
    from app.config.validation import AppConfig

    try:
        config_result = AppConfig.load()
        if not config_result["valid"]:
            print(f"⚠️  配置驗證失敗:")
            for error in config_result["errors"]:
                print(f"  - {error}")
            print("⚠️  使用默認配置，某些功能可能無法正常工作")
        else:
            print("✅ 配置驗證通過")
    except Exception as e:
        print(f"⚠️  配置加載失敗: {e}")

    # Replace direct environment access with validated config
    config = config_result.get("config", AppConfig.load())
    secret_key = config.secret_key

    csrf.init_app(app)
    limiter.init_app(app)

    with app.app_context():
        _ensure_default_admin()

        # 只在web进程（非worker）中初始化scheduler
        if os.environ.get("WORKER_MODE") != "scheduler":
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

    app.register_blueprint(auth_bp)
    app.register_blueprint(items_bp)
    app.register_blueprint(types_bp)
    app.register_blueprint(locations_bp)
    app.register_blueprint(notifications_bp)
    app.register_blueprint(health_bp)
    
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
