import base64
import io
import os
import uuid
from typing import Optional, Tuple

import requests
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


def download_and_save_image(url: str) -> Optional[Tuple[str, str]]:
    """Download image from URL, save to uploads folder, return (filename, thumb_filename).

    Validates content type is image. Max 16 MB. Timeout 10 s.
    Returns None on any failure.
    """
    try:
        response = requests.get(url, timeout=10, stream=True)
        response.raise_for_status()

        content_type = response.headers.get("Content-Type", "")
        if not content_type.startswith("image/"):
            current_app.logger.warning(
                f"download_and_save_image: non-image content type '{content_type}' for {url}"
            )
            return None

        # Read up to 16 MB
        max_bytes = 16 * 1024 * 1024
        data = b""
        for chunk in response.iter_content(chunk_size=8192):
            data += chunk
            if len(data) > max_bytes:
                current_app.logger.warning(
                    f"download_and_save_image: image exceeds 16 MB limit for {url}"
                )
                return None

        # Derive extension from content type (fallback to jpg)
        ext_map = {
            "image/jpeg": "jpg",
            "image/png": "png",
            "image/gif": "gif",
            "image/webp": "webp",
        }
        ext = ext_map.get(content_type.split(";")[0].strip(), "jpg")

        filename = f"{uuid.uuid4().hex}.{ext}"
        upload_folder = current_app.config["UPLOAD_FOLDER"]
        save_path = os.path.join(upload_folder, filename)

        with open(save_path, "wb") as f:
            f.write(data)

        # Compress and thumbnail
        final_filename = compress_image(filename) or filename
        thumb_filename = create_thumbnail(final_filename)

        return (final_filename, thumb_filename)
    except Exception as e:
        current_app.logger.error(f"download_and_save_image failed for {url}: {e}")
        return None


def decode_base64_image(data: str) -> Optional[Tuple[str, str]]:
    """Decode base64 image data (with or without data URI prefix), save to uploads.

    Supports:
      - data:image/jpeg;base64,<payload>
      - raw base64 string

    Returns (filename, thumb_filename) or None on failure.
    """
    try:
        ext = "jpg"
        payload = data.strip()

        if payload.startswith("data:"):
            # data URI format: data:<mime>;base64,<payload>
            header, _, b64_payload = payload.partition(",")
            mime = header.split(";")[0].replace("data:", "").strip()
            ext_map = {
                "image/jpeg": "jpg",
                "image/png": "png",
                "image/gif": "gif",
                "image/webp": "webp",
            }
            ext = ext_map.get(mime, "jpg")
            payload = b64_payload

        image_bytes = base64.b64decode(payload)

        # Verify it's a valid image
        img_check = Image.open(io.BytesIO(image_bytes))
        img_check.verify()

        filename = f"{uuid.uuid4().hex}.{ext}"
        upload_folder = current_app.config["UPLOAD_FOLDER"]
        save_path = os.path.join(upload_folder, filename)

        with open(save_path, "wb") as f:
            f.write(image_bytes)

        # Compress and thumbnail
        final_filename = compress_image(filename) or filename
        thumb_filename = create_thumbnail(final_filename)

        return (final_filename, thumb_filename)
    except Exception as e:
        current_app.logger.error(f"decode_base64_image failed: {e}")
        return None
