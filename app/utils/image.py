import os
from typing import Optional

from PIL import Image
from flask import current_app


def compress_image(
    filename: str,
    max_width: int = 1200,
    quality: int = 85,
) -> Optional[str]:
    """Compress and resize an uploaded image in-place.

    - Resizes to *max_width* while keeping aspect ratio.
    - Converts RGBA/P to RGB (drops alpha → white background).
    - Saves as JPEG at the given *quality*.
    - GIF files are skipped (animated frames).

    Returns the (possibly renamed) filename on success, None on failure.
    """
    upload_folder = current_app.config["UPLOAD_FOLDER"]
    src_path = os.path.join(upload_folder, filename)
    if not os.path.exists(src_path):
        return None

    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext == "gif":
        # Skip animated GIFs — compression would lose frames
        return filename

    try:
        with Image.open(src_path) as img:
            # Convert palette/RGBA to RGB for JPEG saving
            if img.mode in ("RGBA", "P", "LA"):
                background = Image.new("RGB", img.size, (255, 255, 255))
                if img.mode == "P":
                    img = img.convert("RGBA")
                background.paste(img, mask=img.split()[-1])
                img = background
            elif img.mode != "RGB":
                img = img.convert("RGB")

            # Resize if wider than max_width
            if img.width > max_width:
                ratio = max_width / img.width
                new_height = int(img.height * ratio)
                img = img.resize((max_width, new_height), Image.LANCZOS)

            # Always save as JPEG for consistent compression
            new_filename = filename.rsplit(".", 1)[0] + ".jpg" if ext != "jpg" else filename
            new_path = os.path.join(upload_folder, new_filename)
            img.save(new_path, "JPEG", quality=quality, optimize=True)

            # Remove original if format changed
            if new_filename != filename and os.path.exists(src_path):
                os.remove(src_path)

            return new_filename
    except Exception as e:
        current_app.logger.error(f"Image compression failed for {filename}: {e}")
        return filename  # Return original on failure


def create_thumbnail(filename: str, size: int = 300) -> Optional[str]:
    """Create thumbnail for given filename; returns thumbnail filename."""
    upload_folder = current_app.config["UPLOAD_FOLDER"]
    src_path = os.path.join(upload_folder, filename)
    if not os.path.exists(src_path):
        return None

    thumb_name = f"thumb_{filename}"
    thumb_path = os.path.join(upload_folder, thumb_name)
    try:
        with Image.open(src_path) as img:
            if img.mode in ("RGBA", "P", "LA"):
                background = Image.new("RGB", img.size, (255, 255, 255))
                if img.mode == "P":
                    img = img.convert("RGBA")
                background.paste(img, mask=img.split()[-1])
                img = background
            elif img.mode != "RGB":
                img = img.convert("RGB")

            img.thumbnail((size, size))
            img.save(thumb_path, "JPEG", quality=80, optimize=True)
        return thumb_name
    except Exception:
        return None
