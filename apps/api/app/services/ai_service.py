from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Optional
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.schemas.ai import AiSuggestResponse
from app.services.images_service import get_visible as get_visible_image

logger = logging.getLogger(__name__)


_PROMPT = """You are an inventory cataloguing assistant for a home item management app.
Given the image of a single household item, return a JSON object describing it.
The user may also supply a short hint to disambiguate.

Output STRICT JSON (no prose, no markdown fences) with these fields:
- name (string, required): short product name in Traditional Chinese (zh-TW), ≤ 40 chars
- description (string or null): one-sentence description in zh-TW, ≤ 100 chars
- category_suggestion (string or null): a broad category label in zh-TW (e.g., 「廚房用品」, 「衣物」, 「電器」)
- tag_suggestions (array of strings): up to 5 short tag words in zh-TW

Example:
{"name":"咖啡濾杯","description":"陶瓷手沖濾杯，適合 1-2 杯","category_suggestion":"廚房用品","tag_suggestions":["咖啡","陶瓷","手沖"]}
"""


async def suggest_from_image(
    session: AsyncSession,
    viewer_id: UUID,
    image_id: UUID,
    hint: Optional[str] = None,
) -> AiSuggestResponse:
    settings = get_settings()
    if not settings.gemini_api_key:
        raise HTTPException(status_code=503, detail="AI disabled (GEMINI_API_KEY not set)")

    image = await get_visible_image(session, viewer_id, image_id)
    if image is None:
        raise HTTPException(status_code=404, detail="image not found")
    image_path = Path(image.storage_path)
    if not image_path.exists():
        raise HTTPException(status_code=404, detail="file missing on disk")

    try:
        from google import genai
        from google.genai import types as genai_types
    except ImportError as exc:
        raise HTTPException(status_code=503, detail=f"AI SDK not installed: {exc}")

    image_bytes = image_path.read_bytes()
    client = genai.Client(api_key=settings.gemini_api_key)

    parts = [_PROMPT]
    if hint:
        parts.append(f"Hint from user: {hint}")
    parts.append(
        genai_types.Part.from_bytes(data=image_bytes, mime_type=image.mime_type)
    )

    try:
        result = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=parts,
            config=genai_types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=0.2,
            ),
        )
    except Exception as exc:
        logger.warning("gemini call failed", exc_info=True)
        raise HTTPException(status_code=502, detail=f"upstream AI error: {exc}") from exc

    text = (result.text or "").strip()
    if not text:
        raise HTTPException(status_code=502, detail="empty AI response")
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        logger.warning("gemini returned non-JSON: %s", text[:200])
        raise HTTPException(status_code=502, detail="AI returned invalid JSON") from exc

    return AiSuggestResponse(
        name=str(payload.get("name") or "未命名物品")[:200],
        description=(payload.get("description") or None),
        category_suggestion=(payload.get("category_suggestion") or None),
        tag_suggestions=[str(t)[:40] for t in (payload.get("tag_suggestions") or [])[:5]],
    )
