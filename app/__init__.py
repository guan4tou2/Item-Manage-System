"""物品管理系統主模組"""
import os
import secrets
from pathlib import Path

from flask import Flask
from flask_pymongo import PyMongo
from flask_wtf.csrf import CSRFProtect
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

mongo = PyMongo()
csrf = CSRFProtect()
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"],
    storage_uri="memory://",
)


def ensure_upload_folder(app: Flask) -> None:
    """Create upload folder if missing."""
    upload_path = Path(app.config["UPLOAD_FOLDER"])
    upload_path.mkdir(parents=True, exist_ok=True)


def create_app() -> Flask:
    app = Flask(
        __name__,
        template_folder="../templates",
        static_folder="../static",
    )

    # 基本設定
    # SECRET_KEY 必須設定環境變數，否則使用隨機值（開發用）
    secret_key = os.environ.get("SECRET_KEY")
    if not secret_key:
        # 開發環境使用固定的隨機 key，避免重啟後 session 失效
        secret_key = secrets.token_hex(32)
        print("⚠️  警告：未設定 SECRET_KEY 環境變數，使用隨機值（不建議用於生產環境）")

    app.config.from_mapping(
        MONGO_URI=os.environ.get("MONGO_URI", "mongodb://localhost:27017/myDB"),
        SECRET_KEY=secret_key,
        UPLOAD_FOLDER=os.environ.get(
            "UPLOAD_FOLDER",
            str(Path(__file__).resolve().parent.parent / "static" / "uploads"),
        ),
        MAX_CONTENT_LENGTH=16 * 1024 * 1024,  # 16MB
        ALLOWED_EXTENSIONS={"png", "jpg", "jpeg", "gif"},
        # Session 安全設定
        SESSION_COOKIE_SECURE=os.environ.get("FLASK_ENV") == "production",
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        # WTF CSRF 設定
        WTF_CSRF_ENABLED=True,
        WTF_CSRF_TIME_LIMIT=3600,  # 1 小時
    )

    ensure_upload_folder(app)
    
    # 初始化擴充套件
    mongo.init_app(app)
    csrf.init_app(app)
    limiter.init_app(app)

    # Blueprint 註冊
    from app.auth.routes import bp as auth_bp
    from app.items.routes import bp as items_bp
    from app.types.routes import bp as types_bp
    from app.locations.routes import bp as locations_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(items_bp)
    app.register_blueprint(types_bp)
    app.register_blueprint(locations_bp)

    return app
