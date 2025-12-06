import os
import uuid
from pathlib import Path
from typing import Optional

from flask import current_app


def allowed_file(filename: str) -> bool:
    allowed = current_app.config.get("ALLOWED_EXTENSIONS", set())
    return "." in filename and filename.rsplit(".", 1)[1].lower() in allowed


def random_filename(original: str) -> str:
    ext = original.rsplit(".", 1)[1].lower()
    return f"{uuid.uuid4()}.{ext}"


def save_upload(file_storage) -> Optional[str]:
    """Save upload file and return stored filename."""
    if not file_storage or file_storage.filename == "":
        return None
    if not allowed_file(file_storage.filename):
        return None

    filename = random_filename(file_storage.filename)
    upload_folder = current_app.config["UPLOAD_FOLDER"]
    Path(upload_folder).mkdir(parents=True, exist_ok=True)
    filepath = os.path.join(upload_folder, filename)
    file_storage.save(filepath)
    return filename

