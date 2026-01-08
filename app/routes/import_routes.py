"""Routes for bulk import operations."""
import csv
import io
import json
from datetime import datetime
from typing import List, Dict, Any

from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for, current_app
from flask_login import login_required, current_user

from app.utils.logging import get_logger

bp = Blueprint('import', __name__, url_prefix='/import')
logger = get_logger(__name__)


@bp.route('/')
@login_required
def index():
    """Render bulk import page."""
    return render_template('import_items.html')


@bp.route('/upload', methods=['POST'])
@login_required
def upload():
    """
    Handle file upload and bulk import.

    Supports CSV and JSON formats.
    Returns import results with success/failure counts and error details.
    """
    if 'file' not in request.files:
        flash('No file uploaded', 'error')
        return redirect(url_for('import.index'))

    file = request.files['file']
    if file.filename == '':
        flash('No file selected', 'error')
        return redirect(url_for('import.index'))

    # Validate file type
    if not allowed_file(file.filename):
        flash('Invalid file type. Please upload CSV or JSON files only.', 'error')
        return redirect(url_for('import.index'))

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
            user_id=current_user.id if hasattr(current_user, 'id') else 'unknown',
            file_name=file.filename,
            total_items=len(items),
            successful=result['success_count'],
            failed=result['failed_count'],
            errors=result['errors'][:5]  # Log first 5 errors
        )

        flash(
            f"Import completed: {result['success_count']} items imported, "
            f"{result['failed_count']} items failed.",
            'success' if result['failed_count'] == 0 else 'warning'
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
        flash(f'Error importing file: {str(e)}', 'error')
        return redirect(url_for('import.index'))


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
    from app.repositories import get_item_repository
    from app.services.item_service import insert_item

    item_repo = get_item_repository()

    result = {
        'success_count': 0,
        'failed_count': 0,
        'errors': []
    }

    for index, item_data in enumerate(items, start=1):
        try:
            # Insert item
            item_id = insert_item(
                item_name=item_data['ItemName'],
                item_type=item_data.get('ItemType'),
                location=item_data.get('Location'),
                photo_path=item_data.get('PhotoPath'),
                warranty_expiry=item_data.get('WarrantyExpiry'),
                usage_expiry=item_data.get('UsageExpiry'),
                notes=item_data.get('Notes')
            )

            if item_id:
                result['success_count'] += 1
            else:
                result['failed_count'] += 1
                result['errors'].append({
                    'row': index,
                    'item': item_data['ItemName'],
                    'error': 'Failed to insert item'
                })

        except Exception as e:
            result['failed_count'] += 1
            result['errors'].append({
                'row': index,
                'item': item_data['ItemName'],
                'error': str(e)
            })

    return result
