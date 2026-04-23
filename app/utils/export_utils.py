"""
匯出工具：將物品列表輸出為 CSV / Excel / PDF / JSON。

設計原則：
- 任何選用套件（openpyxl、reportlab）都採延遲匯入，缺套件時優雅降級為 CSV/JSON。
- 所有函式皆回傳 ``bytes``，方便直接做為 Flask `send_file` 的內容。
"""

from __future__ import annotations

import csv
import io
import json
from datetime import date, datetime
from io import BytesIO
from typing import Iterable, List, Optional, Sequence, Tuple

try:  # pragma: no cover - 依賴於執行環境
    from flask import current_app
except Exception:  # pragma: no cover
    current_app = None  # type: ignore[assignment]


Column = Tuple[str, str]
ItemDict = dict


DEFAULT_COLUMNS: List[Column] = [
    ("ItemID", "ID"),
    ("ItemName", "名稱"),
    ("ItemStorePlace", "放置地點"),
    ("ItemFloor", "樓層"),
    ("ItemRoom", "房間"),
    ("ItemZone", "區域"),
    ("ItemType", "類型"),
    ("ItemQuantity", "數量"),
    ("ItemDesc", "描述"),
    ("ItemGetDate", "取得日期"),
    ("WarrantyExpiry", "保固截止"),
    ("UsageExpiry", "使用期限"),
    ("ItemStoreMin", "安全庫存"),
    ("ItemStoreReorder", "補貨門檻"),
]


def _format_value(value):
    """將日期/None 等值正規化成字串。"""
    if value is None:
        return ""
    if isinstance(value, (datetime,)):
        return value.strftime("%Y-%m-%d %H:%M")
    if isinstance(value, date):
        return value.strftime("%Y-%m-%d")
    return value


def _resolve_columns(columns: Optional[Sequence[Column]]) -> List[Column]:
    return list(columns) if columns else list(DEFAULT_COLUMNS)


def _log_warning(message: str) -> None:
    if current_app is not None:
        try:
            current_app.logger.warning(message)
            return
        except Exception:
            pass
    # fallback to stderr
    import sys
    print(message, file=sys.stderr)


def export_to_csv(items: Iterable[ItemDict], columns: Optional[Sequence[Column]] = None) -> bytes:
    """匯出為 CSV（UTF-8 with BOM 以利 Excel 直接開啟）。"""
    cols = _resolve_columns(columns)
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([label for _, label in cols])
    for item in items:
        writer.writerow([str(_format_value(item.get(key, ""))) for key, _ in cols])
    # 加上 BOM，避免 Excel 開啟亂碼
    return ("\ufeff" + output.getvalue()).encode("utf-8")


def export_to_json(items: Iterable[ItemDict]) -> bytes:
    """匯出為 JSON。"""
    return json.dumps(list(items), ensure_ascii=False, indent=2, default=str).encode("utf-8")


def export_to_excel(items: Iterable[ItemDict], columns: Optional[Sequence[Column]] = None) -> bytes:
    """匯出為 .xlsx。若 openpyxl 未安裝則降級為 CSV。"""
    try:
        from openpyxl import Workbook
        from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
        from openpyxl.utils import get_column_letter
    except ImportError:
        _log_warning("openpyxl 未安裝，自動降級為 CSV 匯出。")
        return export_to_csv(items, columns)

    cols = _resolve_columns(columns)
    wb = Workbook()
    ws = wb.active
    ws.title = "Items"

    header_fill = PatternFill(start_color="2f658f", end_color="2f658f", fill_type="solid")
    header_font = Font(bold=True, color="FFFFFF", size=11)
    header_align = Alignment(horizontal="center", vertical="center")
    thin = Side(style="thin")
    border = Border(left=thin, right=thin, top=thin, bottom=thin)

    for col_idx, (_, label) in enumerate(cols, 1):
        cell = ws.cell(row=1, column=col_idx, value=label)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = header_align
        cell.border = border

    for row_idx, item in enumerate(items, 2):
        for col_idx, (key, _) in enumerate(cols, 1):
            cell = ws.cell(row=row_idx, column=col_idx, value=_format_value(item.get(key, "")))
            cell.border = border

    for col_idx in range(1, len(cols) + 1):
        ws.column_dimensions[get_column_letter(col_idx)].width = 18

    buffer = BytesIO()
    wb.save(buffer)
    return buffer.getvalue()


def export_to_pdf(items: Iterable[ItemDict], title: str = "物品清單") -> bytes:
    """匯出為 PDF。若 reportlab 未安裝則回傳純文字訊息。"""
    try:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.lib.units import mm
        from reportlab.platypus import (
            Paragraph,
            SimpleDocTemplate,
            Spacer,
            Table,
            TableStyle,
        )
    except ImportError:
        _log_warning("reportlab 未安裝，無法產生 PDF。")
        return b"PDF export requires the reportlab package to be installed."

    items_list = list(items)
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=15 * mm,
        leftMargin=15 * mm,
        topMargin=15 * mm,
        bottomMargin=15 * mm,
    )
    styles = getSampleStyleSheet()
    elements = [Paragraph(title, styles["Title"]), Spacer(1, 6 * mm)]

    headers = ["#", "名稱", "位置", "類型", "數量", "保固截止", "使用期限"]
    rows = [headers]
    for idx, item in enumerate(items_list, 1):
        rows.append([
            str(idx),
            str(_format_value(item.get("ItemName", ""))),
            str(_format_value(item.get("ItemStorePlace", ""))),
            str(_format_value(item.get("ItemType", ""))),
            str(_format_value(item.get("ItemQuantity", ""))),
            str(_format_value(item.get("WarrantyExpiry", ""))),
            str(_format_value(item.get("UsageExpiry", ""))),
        ])

    table = Table(rows, repeatRows=1)
    table.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.Color(0.18, 0.4, 0.56)),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 0), 10),
            ("BOTTOMPADDING", (0, 0), (-1, 0), 8),
            ("BACKGROUND", (0, 1), (-1, -1), colors.white),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("FONTSIZE", (0, 1), (-1, -1), 8),
        ])
    )
    elements.append(table)
    doc.build(elements)
    return buffer.getvalue()
