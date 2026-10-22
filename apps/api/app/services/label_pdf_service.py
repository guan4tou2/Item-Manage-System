"""Phase 41：伺服器端物品標籤 PDF（A4、3×7、QR＋Code128）。

- 版面固定（63.5 × 38.1 mm × 21 格），不依瀏覽器縮放
- 字型使用內附的 Noto Sans TC 子集（OFL；PDF 只嵌入用到的字形）→ 不依賴檢視器/印表機的系統字型
- QR 沿用 `labels_service.render_qr_png`（與既有 QR 同一口徑）
- Code128 由 `python-barcode` 產生 PNG；不可編碼時只省略條碼，不影響整批
"""
from __future__ import annotations

import io
import re
from collections.abc import Sequence
from pathlib import Path
from typing import Any, Optional

import barcode
from barcode.writer import ImageWriter
from PIL import Image
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

from app.services.labels_service import render_qr_png

# --- 版面（mm） -------------------------------------------------------------

LABEL_COLS = 3
LABEL_ROWS = 7
LABELS_PER_PAGE = LABEL_COLS * LABEL_ROWS

LABEL_W = 63.5 * mm
LABEL_H = 38.1 * mm
PAGE_W, PAGE_H = A4
MARGIN_X = (PAGE_W - LABEL_COLS * LABEL_W) / 2  # 9.75 mm
MARGIN_Y = (PAGE_H - LABEL_ROWS * LABEL_H) / 2  # 15.15 mm

PADDING = 1.8 * mm
QR_SIZE = 19 * mm
QR_GAP = 1.6 * mm
BARCODE_H = 8 * mm
BARCODE_TEXT_AREA = 4.2 * mm
BARCODE_DPI = 300

FONT_NAME = "NotoSansTC"
FONT_PATH = Path(__file__).resolve().parents[1] / "assets" / "fonts" / "NotoSansTC-Regular.ttf"
FONT_READY = False

CODE128_PATTERN = re.compile(r"^[\x20-\x7e]+$")
#: 與 `items.barcode` schema 上限一致；超過會讓條碼太密而掃不到
CODE128_MAX_LEN = 32


def _ensure_font() -> None:
    global FONT_READY
    if not FONT_READY:
        pdfmetrics.registerFont(TTFont(FONT_NAME, str(FONT_PATH)))
        FONT_READY = True


def is_code128_encodable(value: Optional[str]) -> bool:
    """Code128 僅能編碼可列印 ASCII；空白字串視為不可編碼。"""
    text = (value or "").strip()
    return (
        bool(text)
        and len(text) <= CODE128_MAX_LEN
        and CODE128_PATTERN.fullmatch(text) is not None
    )


def _wrap_text(
    text: str,
    *,
    font: str,
    size: float,
    max_width: float,
    max_lines: int,
) -> list[str]:
    """以字元為單位換行（CJK 無空白可斷）；超出 `max_lines` 以 `…` 截斷。"""
    _ensure_font()
    lines: list[str] = []
    current = ""
    index = 0

    while index < len(text):
        ch = text[index]
        candidate = current + ch
        if current and pdfmetrics.stringWidth(candidate, font, size) > max_width:
            lines.append(current)
            current = ""
            if len(lines) == max_lines:
                break
            continue
        current = candidate
        index += 1

    if len(lines) < max_lines and current:
        lines.append(current)
        current = ""
        index = len(text)

    if index < len(text):
        last = lines[-1]
        while last and pdfmetrics.stringWidth(last + "…", font, size) > max_width:
            last = last[:-1]
        lines[-1] = last + "…"

    return lines


def _code128_png(value: str) -> Optional[tuple[bytes, float, float]]:
    """回傳 (PNG bytes, 寬 mm, 高 mm)；不可編碼或套件錯誤時回傳 None。"""
    if not is_code128_encodable(value):
        return None
    options = {
        "write_text": False,
        "module_width": 0.25,
        "module_height": 8.0,
        "quiet_zone": 1.0,
        "dpi": BARCODE_DPI,
    }
    try:
        buf = io.BytesIO()
        barcode.get("code128", value.strip(), writer=ImageWriter()).write(buf, options=options)
        png = buf.getvalue()
        with Image.open(io.BytesIO(png)) as image:
            px_w, px_h = image.size
    except Exception:  # pragma: no cover - 防禦性；正常值已由 is_code128_encodable 擋掉
        return None
    return png, px_w / BARCODE_DPI * 25.4, px_h / BARCODE_DPI * 25.4


def _slot_rect(slot: int) -> tuple[float, float]:
    col = slot % LABEL_COLS
    row = slot // LABEL_COLS
    x = MARGIN_X + col * LABEL_W
    y = PAGE_H - MARGIN_Y - (row + 1) * LABEL_H
    return x, y


def _draw_cut_guide(c: canvas.Canvas, x: float, y: float) -> None:
    c.saveState()
    c.setStrokeGray(0.85)
    c.setLineWidth(0.3)
    c.rect(x, y, LABEL_W, LABEL_H, stroke=1, fill=0)
    c.restoreState()


def _draw_label(c: canvas.Canvas, label: dict[str, Any], slot: int) -> None:
    x, y = _slot_rect(slot)
    top = y + LABEL_H

    # QR（左上）
    qr_png = render_qr_png(label["deep_link"])
    c.drawImage(
        ImageReader(io.BytesIO(qr_png)),
        x + PADDING,
        top - PADDING - QR_SIZE,
        QR_SIZE,
        QR_SIZE,
    )

    # 右側文字
    text_x = x + PADDING + QR_SIZE + QR_GAP
    text_w = x + LABEL_W - PADDING - text_x
    lines = _wrap_text(
        str(label["name"]),
        font=FONT_NAME,
        size=8.5,
        max_width=text_w,
        max_lines=2,
    )
    c.setFillGray(0)
    c.setFont(FONT_NAME, 8.5)
    for index, line in enumerate(lines):
        c.drawString(text_x, top - PADDING - 3.2 * mm - index * 3.6 * mm, line)

    short_id = str(label["item_id"])[:8]
    c.setFillGray(0.35)
    c.setFont(FONT_NAME, 6.5)
    c.drawString(
        text_x,
        top - PADDING - QR_SIZE + 2.5 * mm,
        f"#{short_id} · x{label['quantity']}",
    )

    # 底部條碼（可選）
    code = label.get("barcode")
    rendered = _code128_png(code) if code else None
    if rendered is None:
        if code:
            # 不可編碼（例如中文）→ 仍以文字呈現，供手動輸入，不讓整批失敗
            c.setFillGray(0.15)
            c.setFont(FONT_NAME, 6)
            c.drawCentredString(
                x + LABEL_W / 2,
                y + 2.0 * mm,
                _wrap_text(
                    str(code).strip(),
                    font=FONT_NAME,
                    size=6,
                    max_width=LABEL_W - 2 * PADDING,
                    max_lines=1,
                )[0],
            )
            c.setFillGray(0)
        return

    png, natural_w_mm, natural_h_mm = rendered
    available_w = LABEL_W - 2 * PADDING
    width = min(natural_w_mm * mm, available_w)
    scale = width / (natural_w_mm * mm)
    height = min(natural_h_mm * mm * scale, BARCODE_H)
    bx = x + (LABEL_W - width) / 2
    by = y + BARCODE_TEXT_AREA
    c.drawImage(ImageReader(io.BytesIO(png)), bx, by, width, height)

    c.setFillGray(0.15)
    c.setFont(FONT_NAME, 6)
    c.drawCentredString(x + LABEL_W / 2, y + 2.0 * mm, str(code).strip())
    c.setFillGray(0)


def render_item_labels_pdf(
    labels: Sequence[dict[str, Any]], *, start: int = 0
) -> bytes:
    """把物品標籤畫成 A4 PDF（每頁 21 格；`start` 跳過前 N 格）。"""
    if start < 0 or start >= LABELS_PER_PAGE:
        raise ValueError("start must be within 0..20")

    _ensure_font()
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    c.setTitle("Item labels")

    total = start + len(labels)
    pages = max(1, (total + LABELS_PER_PAGE - 1) // LABELS_PER_PAGE)

    for page in range(pages):
        for slot in range(LABELS_PER_PAGE):
            x, y = _slot_rect(slot)
            _draw_cut_guide(c, x, y)
            index = page * LABELS_PER_PAGE + slot - start
            if 0 <= index < len(labels):
                _draw_label(c, labels[index], slot)
        c.showPage()

    c.save()
    return buf.getvalue()
