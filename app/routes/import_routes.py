"""Routes for bulk import operations."""
import csv
import io
import json
import uuid
from datetime import datetime
from typing import List, Dict, Any

from flask import Blueprint, render_template, request, jsonify

from app.repositories import item_repo
from app.services import item_service, location_service
from app.utils.auth import login_required, get_current_user
from app.utils.image import download_and_save_image, decode_base64_image

from app.utils.logging import get_logger

bp = Blueprint('import', __name__, url_prefix='/import')
logger = get_logger(__name__)


@bp.route('/')
@login_required
def index():
    """Render bulk import page."""
    return render_template('import_items.html', User=get_current_user())


@bp.route('/upload', methods=['POST'])
@login_required
def upload():
    """
    Handle file upload and bulk import.

    Supports CSV and JSON formats.
    Returns import results with success/failure counts and error details.
    """
    if 'file' not in request.files:
        return jsonify({'success': False, 'error': '請選擇要上傳的檔案'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'success': False, 'error': '請選擇要上傳的檔案'}), 400

    # Validate file type
    if not allowed_file(file.filename):
        return jsonify({'success': False, 'error': '僅支援 CSV 或 JSON 檔案'}), 400

    try:
        # Read file content
        content = file.read().decode('utf-8')

        # Process based on file type
        if file.filename.endswith('.csv'):
            items = parse_csv(content)
        elif file.filename.endswith('.json'):
            items = parse_json(content)
        else:
            raise ValueError('Unsupported file format')

        # Import items
        result = import_items(items)

        # Log import results
        logger.info(
            "bulk_import_completed",
            user_id=(get_current_user() or {}).get("User", "unknown"),
            file_name=file.filename,
            total_items=len(items),
            successful=result['success_count'],
            failed=result['failed_count'],
            errors=result['errors'][:5]  # Log first 5 errors
        )

        # Store result for display on page
        return jsonify({
            'success': True,
            'result': result
        })

    except Exception as e:
        logger.error(
            "bulk_import_failed",
            error=str(e),
            file_name=file.filename,
            exc_info=True
        )
        return jsonify({'success': False, 'error': f'導入失敗：{str(e)}'}), 400


@bp.route('/template', methods=['GET'])
@login_required
def template():
    """
    Download CSV template for bulk import.

    Returns a CSV file with headers that matches the expected format.
    """
    # Define CSV headers
    headers = [
        'ItemID', 'ItemName', 'ItemType', 'Location', 'PhotoPath',
        'Quantity', 'SafetyStock', 'ReorderLevel',
        'MaintenanceCategory', 'MaintenanceIntervalDays', 'LastMaintenanceDate',
        'WarrantyExpiry', 'UsageExpiry', 'Notes'
    ]

    # Create CSV content
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=headers)
    writer.writeheader()

    # Add example rows
    # PhotoPath supports: plain filename, URL (http/https), or Base64 data URI
    writer.writerow({
        'ItemID': '',
        'ItemName': 'Example Item 1',
        'ItemType': 'Electronics',
        'Location': '1F/RoomA/Shelf1',
        'PhotoPath': 'https://example.com/photo.jpg',
        'Quantity': 1,
        'SafetyStock': 1,
        'ReorderLevel': 1,
        'MaintenanceCategory': '充電保養',
        'MaintenanceIntervalDays': 60,
        'LastMaintenanceDate': '2025-12-01',
        'WarrantyExpiry': '2025-12-31',
        'UsageExpiry': '2026-06-30',
        'Notes': 'PhotoPath accepts URL / Base64 / filename'
    })
    writer.writerow({
        'ItemID': 'ITEM-123456-ABCDEF',
        'ItemName': 'Example Item 2',
        'ItemType': 'Office Supplies',
        'Location': '2F/RoomB/Drawer1',
        'PhotoPath': '',
        'Quantity': 6,
        'SafetyStock': 2,
        'ReorderLevel': 1,
        'MaintenanceCategory': '濾芯更換',
        'MaintenanceIntervalDays': 180,
        'LastMaintenanceDate': '2025-01-15',
        'WarrantyExpiry': '',
        'UsageExpiry': '2025-08-15',
        'Notes': ''
    })

    # Reset pointer to beginning
    output.seek(0)

    # Return CSV file
    from flask import Response
    response = Response(
        output.getvalue(),
        mimetype='text/csv',
        headers={
            'Content-Disposition': 'attachment; filename=import_template.csv'
        }
    )
    return response


def allowed_file(filename: str) -> bool:
    """Check if file extension is allowed."""
    return filename.lower().endswith(('.csv', '.json'))


def parse_csv(content: str) -> List[Dict[str, Any]]:
    """
    Parse CSV content into list of dictionaries.

    Args:
        content: CSV file content as string

    Returns:
        List of item dictionaries

    Raises:
        ValueError: If CSV parsing fails
    """
    try:
        reader = csv.DictReader(io.StringIO(content))
        items = []
        for row_num, row in enumerate(reader, start=2):  # Start at 2 (header is row 1)
            # Validate required fields
            if not row.get('ItemName'):
                raise ValueError(f"Row {row_num}: Missing required field 'ItemName'")

            items.append({
                'ItemName': row['ItemName'].strip(),
                'ItemType': row.get('ItemType', '').strip() or None,
                'Location': row.get('Location', '').strip() or None,
                'PhotoPath': row.get('PhotoPath', '').strip() or None,
                'MaintenanceCategory': row.get('MaintenanceCategory', '').strip() or None,
                'MaintenanceIntervalDays': parse_int(row.get('MaintenanceIntervalDays', '').strip()),
                'LastMaintenanceDate': parse_date(row.get('LastMaintenanceDate', '').strip()),
                'WarrantyExpiry': parse_date(row.get('WarrantyExpiry', '').strip()),
                'UsageExpiry': parse_date(row.get('UsageExpiry', '').strip()),
                'Notes': row.get('Notes', '').strip() or None
            })
        return items
    except Exception as e:
        raise ValueError(f"CSV parsing error: {str(e)}")


def parse_json(content: str) -> List[Dict[str, Any]]:
    """
    Parse JSON content into list of dictionaries.

    Args:
        content: JSON file content as string

    Returns:
        List of item dictionaries

    Raises:
        ValueError: If JSON parsing fails
    """
    try:
        data = json.loads(content)

        # Validate that it's a list
        if not isinstance(data, list):
            raise ValueError("JSON must be an array of objects")

        items = []
        for index, item in enumerate(data, start=1):
            # Validate required fields
            if not isinstance(item, dict):
                raise ValueError(f"Item {index}: Must be an object")

            if 'ItemName' not in item or not item['ItemName']:
                raise ValueError(f"Item {index}: Missing required field 'ItemName'")

            items.append({
                'ItemName': str(item['ItemName']).strip(),
                'ItemType': item.get('ItemType') and str(item['ItemType']).strip() or None,
                'Location': item.get('Location') and str(item['Location']).strip() or None,
                'PhotoPath': item.get('PhotoPath') and str(item['PhotoPath']).strip() or None,
                'MaintenanceCategory': item.get('MaintenanceCategory') and str(item['MaintenanceCategory']).strip() or None,
                'MaintenanceIntervalDays': parse_int(item.get('MaintenanceIntervalDays')),
                'LastMaintenanceDate': parse_date(item.get('LastMaintenanceDate')),
                'WarrantyExpiry': parse_date(item.get('WarrantyExpiry')),
                'UsageExpiry': parse_date(item.get('UsageExpiry')),
                'Notes': item.get('Notes') and str(item['Notes']).strip() or None
            })
        return items
    except json.JSONDecodeError as e:
        raise ValueError(f"JSON parsing error: {str(e)}")
    except Exception as e:
        raise ValueError(f"JSON validation error: {str(e)}")


def parse_date(date_str: str) -> datetime.date or None:
    """
    Parse date string into date object.

    Args:
        date_str: Date string in YYYY-MM-DD format

    Returns:
        Date object or None if empty string

    Raises:
        ValueError: If date format is invalid
    """
    if not date_str or not date_str.strip():
        return None

    try:
        # Try YYYY-MM-DD format
        return datetime.strptime(date_str.strip(), '%Y-%m-%d').date()
    except ValueError:
        # Try other common formats
        for fmt in ['%d/%m/%Y', '%m/%d/%Y', '%Y/%m/%d', '%d-%m-%Y']:
            try:
                return datetime.strptime(date_str.strip(), fmt).date()
            except ValueError:
                continue
        raise ValueError(f"Invalid date format: {date_str}. Expected YYYY-MM-DD")


def parse_int(value: Any) -> int | None:
    if value in (None, ""):
        return None
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        raise ValueError(f"Invalid integer value: {value}")


def import_items(items: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Import items into the database.

    Args:
        items: List of item dictionaries to import

    Returns:
        Dictionary with import results including:
            - success_count: Number of successfully imported items
            - failed_count: Number of failed items
            - errors: List of error messages
    """
    result = {
        'success_count': 0,
        'failed_count': 0,
        'errors': []
    }

    for index, item_data in enumerate(items, start=1):
        try:
            normalized = _normalize_import_item(item_data, index)
            existing = item_repo.find_item_by_id(normalized["ItemID"])
            if existing:
                item_repo.update_item_by_id(normalized["ItemID"], normalized)
            else:
                item_repo.insert_item(normalized)
            # Note: 使用 item_repo 而非 item_service 因為匯入資料已經過
            # _normalize_import_item 驗證，不需要重複走完整的 service 驗證流程
            _ensure_location_choice(
                normalized.get("ItemFloor", ""),
                normalized.get("ItemRoom", ""),
                normalized.get("ItemZone", ""),
            )
            result['success_count'] += 1

        except Exception as e:
            result['failed_count'] += 1
            result['errors'].append({
                'row': index,
                'item': item_data['ItemName'],
                'error': str(e)
            })

    return result


def _generate_item_id() -> str:
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    random_part = uuid.uuid4().hex[:6].upper()
    return f"ITEM-{timestamp[-6:]}-{random_part}"


def _split_location(location: str | None) -> tuple[str, str, str, str]:
    raw_location = (location or "").strip()
    if not raw_location:
        return "", "", "", ""

    parts = [part.strip() for part in raw_location.split("/") if part.strip()]
    floor = parts[0] if len(parts) > 0 else ""
    room = parts[1] if len(parts) > 1 else ""
    zone = "/".join(parts[2:]) if len(parts) > 2 else ""
    return raw_location, floor, room, zone


def _resolve_photo(photo_path: str | None) -> tuple[str, str]:
    """Resolve PhotoPath to (ItemPic, ItemThumb).

    - URL (http/https) → download and save
    - data:image or long base64 string → decode and save
    - plain filename or empty → leave as-is
    """
    if not photo_path:
        return "", ""

    photo_path = photo_path.strip()

    if photo_path.startswith("http://") or photo_path.startswith("https://"):
        result = download_and_save_image(photo_path)
        if result:
            return result[0], result[1] or ""
        # Fall through: keep original URL string as-is so data isn't lost
        return photo_path, ""

    if photo_path.startswith("data:image"):
        result = decode_base64_image(photo_path)
        if result:
            return result[0], result[1] or ""
        return "", ""

    # Heuristic: raw base64 — long alphanumeric string with no path separators
    if len(photo_path) > 64 and "/" not in photo_path and "." not in photo_path:
        result = decode_base64_image(photo_path)
        if result:
            return result[0], result[1] or ""
        return "", ""

    # Plain filename or anything else — keep as-is
    return photo_path, ""


def _normalize_import_item(item_data: Dict[str, Any], index: int) -> Dict[str, Any]:
    raw_location, floor, room, zone = _split_location(item_data.get("Location"))
    item_id = str(item_data.get("ItemID", "")).strip() or _generate_item_id()

    item_pic, item_thumb = _resolve_photo(item_data.get("PhotoPath"))

    return {
        "ItemID": item_id,
        "ItemName": item_data["ItemName"].strip(),
        "ItemType": item_data.get("ItemType") or "",
        "ItemDesc": item_data.get("Notes") or "",
        "ItemPic": item_pic,
        "ItemThumb": item_thumb,
        "ItemPics": [],
        "ItemStorePlace": raw_location,
        "ItemOwner": (get_current_user() or {}).get("User", ""),
        "ItemGetDate": datetime.now().strftime("%Y-%m-%d"),
        "ItemFloor": floor,
        "ItemRoom": room,
        "ItemZone": zone,
        "visibility": "private",
        "shared_with": [],
        "Quantity": int(item_data.get("Quantity", 0) or 0),
        "SafetyStock": int(item_data.get("SafetyStock", 0) or 0),
        "ReorderLevel": int(item_data.get("ReorderLevel", 0) or 0),
        "MaintenanceCategory": item_data.get("MaintenanceCategory") or "",
        "MaintenanceIntervalDays": item_data.get("MaintenanceIntervalDays"),
        "LastMaintenanceDate": item_data.get("LastMaintenanceDate"),
        "WarrantyExpiry": item_data.get("WarrantyExpiry"),
        "UsageExpiry": item_data.get("UsageExpiry"),
        "move_history": [],
        "favorites": [],
        "related_items": [],
        "size_notes": {},
    }


def _ensure_location_choice(floor: str, room: str, zone: str) -> None:
    if not any([floor, room, zone]):
        return
    location_service.create_location({"floor": floor, "room": room, "zone": zone})
