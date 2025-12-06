import os
from pathlib import Path

from flask import Flask
from flask_pymongo import PyMongo

mongo = PyMongo()


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
    app.config.from_mapping(
        MONGO_URI=os.environ.get("MONGO_URI", "mongodb://localhost:27017/myDB"),
        SECRET_KEY=os.environ.get("SECRET_KEY", os.urandom(16)),
        UPLOAD_FOLDER=os.environ.get(
            "UPLOAD_FOLDER",
            str(Path(__file__).resolve().parent.parent / "static" / "uploads"),
        ),
        MAX_CONTENT_LENGTH=16 * 1024 * 1024,  # 16MB
        ALLOWED_EXTENSIONS={"png", "jpg", "jpeg", "gif"},
    )

    ensure_upload_folder(app)
    mongo.init_app(app)

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

