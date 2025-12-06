import os
from typing import Optional

from PIL import Image
from flask import current_app


def create_thumbnail(filename: str) -> Optional[str]:
    """Create thumbnail for given filename; returns thumbnail filename."""
    upload_folder = current_app.config["UPLOAD_FOLDER"]
    src_path = os.path.join(upload_folder, filename)
    if not os.path.exists(src_path):
        return None

    thumb_name = f"thumb_{filename}"
    thumb_path = os.path.join(upload_folder, thumb_name)
    try:
        with Image.open(src_path) as img:
            img.thumbnail((300, 300))
            img.save(thumb_path)
        return thumb_name
    except Exception:
        return None

