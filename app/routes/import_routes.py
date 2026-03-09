"""Routes for bulk import operations."""
import csv
import io
import json
import uuid
from datetime import datetime
from typing import List, Dict, Any

from flask import Blueprint, render_template, request, jsonify

from app.repositories import item_repo
from app.services import location_service
from app.utils.auth import login_required, get_current_user

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
        'ItemName', 'ItemType', 'Location', 'PhotoPath',
        'WarrantyExpiry', 'UsageExpiry', 'Notes'
    ]

    # Create CSV content
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=headers)
    writer.writeheader()

    # Add example rows
    writer.writerow({
        'ItemName': 'Example Item 1',
        'ItemType': 'Electronics',
        'Location': '1F/RoomA/Shelf1',
        'PhotoPath': '',
        'WarrantyExpiry': '2025-12-31',
        'UsageExpiry': '2026-06-30',
        'Notes': 'Example notes'
    })
    writer.writerow({
        'ItemName': 'Example Item 2',
        'ItemType': 'Office Supplies',
        'Location': '2F/RoomB/Drawer1',
        'PhotoPath': '',
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


def _normalize_import_item(item_data: Dict[str, Any], index: int) -> Dict[str, Any]:
    raw_location, floor, room, zone = _split_location(item_data.get("Location"))
    item_id = str(item_data.get("ItemID", "")).strip() or _generate_item_id()

    return {
        "ItemID": item_id,
        "ItemName": item_data["ItemName"].strip(),
        "ItemType": item_data.get("ItemType") or "",
        "ItemDesc": item_data.get("Notes") or "",
        "ItemPic": item_data.get("PhotoPath") or "",
        "ItemThumb": "",
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
