# 📚 API Documentation

Complete API reference for the Item Management System.

## 📋 Table of Contents

- [Authentication](#authentication)
- [Items](#items)
- [Types](#types)
- [Locations](#locations)
- [Notifications](#notifications)
- [Travel & Shopping](#travel--shopping)
- [Health & Monitoring](#health--monitoring)
- [Import](#import)
- [Error Handling](#error-handling)

---

## 🔐 Authentication

All API endpoints (except `/signin`, `/signup`, `/health`, `/ready`, `/metrics`) require authentication via session cookies.

### Sign In

**Endpoint:** `POST /signin`

**Description:** Authenticate user and create session

**Request Body:**
```json
{
  "UserID": "admin",
  "Password": "password"
}
```

**Success Response (302):**
```json
Redirect to: /home
```

**Error Response (200):**
```html
Rendered signin.html with error message
```

**Example:**
```bash
curl -X POST http://localhost:8080/signin \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "UserID=admin&Password=admin" \
  -c cookies.txt
```

---

### Sign Up

**Endpoint:** `POST /signup`

**Description:** Register new user account

**Request Body:**
```json
{
  "UserID": "newuser",
  "Password": "password123",
  "ConfirmPassword": "password123"
}
```

**Validation Rules:**
- Username: minimum 3 characters
- Password: minimum 6 characters
- Passwords must match

**Success Response (302):**
```json
Redirect to: /signin
Flash message: "註冊成功！請登入"
```

**Error Response (200):**
```html
Rendered signup.html with error message
```

---

### Sign Out

**Endpoint:** `POST /signout`

**Description:** Logout user and clear session

**Success Response (302):**
```json
Redirect to: /signin
```

---

### Change Password

**Endpoint:** `POST /change-password`

**Authentication:** Required

**Request Body:**
```json
{
  "current_password": "oldpass",
  "new_password": "newpass123",
  "confirm_password": "newpass123"
}
```

**Success Response (302):**
```json
Redirect to: /home
Flash message: "密碼已更新"
```

---

## 📦 Items

### List Items (Home Page)

**Endpoint:** `GET /home`

**Authentication:** Required

**Query Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `q` | string | No | Search query (item name) |
| `place` | string | No | Filter by storage place |
| `type` | string | No | Filter by item type |
| `floor` | string | No | Filter by floor |
| `room` | string | No | Filter by room |
| `zone` | string | No | Filter by zone |
| `sort` | string | No | Sort by: `name`, `warranty`, `usage` |
| `page` | integer | No | Page number (default: 1) |

**Response:** HTML page with item list

**Example:**
```bash
curl -X GET "http://localhost:8080/home?q=laptop&type=電器&page=1" \
  -b cookies.txt
```

---

### Add Item

**Endpoint:** `POST /additem`

**Authentication:** Admin required

**Content-Type:** `multipart/form-data`

**Request Body:**
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `ItemName` | string | Yes | Item name |
| `ItemID` | string | Yes | Unique item ID |
| `ItemType` | string | No | Item type/category |
| `ItemStorePlace` | string | No | Storage location |
| `ItemFloor` | string | No | Floor level |
| `ItemRoom` | string | No | Room name |
| `ItemZone` | string | No | Zone/area |
| `ItemOwner` | string | No | Owner name |
| `ItemGetDate` | date | No | Acquisition date (YYYY-MM-DD) |
| `WarrantyExpiry` | date | No | Warranty expiry date |
| `UsageExpiry` | date | No | Usage expiry date |
| `ItemDesc` | string | No | Item description |
| `ItemPic` | file | No | Item photo (JPG/PNG/GIF, max 16MB) |

**Success Response (302):**
```json
Redirect to: /home
Flash message: "物品新增成功！"
```

**Error Response (200):**
```html
Rendered additem.html with error message
```

**Example:**
```bash
curl -X POST http://localhost:8080/additem \
  -b cookies.txt \
  -F "ItemName=Laptop" \
  -F "ItemID=ELEC-001" \
  -F "ItemType=電器" \
  -F "ItemStorePlace=書房" \
  -F "ItemPic=@laptop.jpg"
```

---

### View Item Detail

**Endpoint:** `GET /itemdetail/<item_id>`

**Authentication:** Required

**URL Parameters:**
- `item_id`: Internal database ID

**Response:** HTML page with item details

---

### Edit Item

**Endpoint:** `POST /edititem/<item_id>`

**Authentication:** Admin required

**Content-Type:** `multipart/form-data`

**Request Body:** Same as Add Item

**Success Response (302):**
```json
Redirect to: /home
Flash message: "物品已更新"
```

---

### Delete Item

**Endpoint:** `POST /deleteitem/<item_id>`

**Authentication:** Admin required

**Success Response (302):**
```json
Redirect to: /home
Flash message: "物品已刪除"
```

---

### Generate QR Code

**Endpoint:** `GET /generate_qr/<item_id>`

**Authentication:** Required

**Response:** PNG image (QR code)

**Example:**
```bash
curl -X GET http://localhost:8080/generate_qr/ELEC-001 \
  -b cookies.txt \
  -o qrcode.png
```

---

### Generate Barcode

**Endpoint:** `GET /generate_barcode/<item_id>`

**Authentication:** Required

**Response:** PNG image (barcode)

---

### Search Items

**Endpoint:** `GET /search`

**Authentication:** Required

**Query Parameters:** Same as List Items

**Response:** HTML page with search results

---

### Manage Items (Admin)

**Endpoint:** `GET /manageitem`

**Authentication:** Admin required

**Features:**
- Bulk operations
- Advanced filtering
- Item statistics

---

### Favorites

**Endpoint:** `GET /favorites`

**Authentication:** Required

**Description:** View favorited items

---

### Statistics

**Endpoint:** `GET /statistics`

**Authentication:** Required

**Response:** HTML page with item statistics
- Total items count
- Items with photos
- Items with locations
- Items by type
- Expiry statistics

---

## 🏷️ Types

### List Types

**Endpoint:** `GET /types`

**Authentication:** Required

**Response:** HTML page with all item types

---

### Add Type

**Endpoint:** `POST /types/add`

**Authentication:** Admin required

**Request Body:**
```json
{
  "TypeName": "新類型"
}
```

**Success Response (302):**
```json
Redirect to: /types
Flash message: "類型已新增"
```

---

### Delete Type

**Endpoint:** `POST /types/delete/<type_name>`

**Authentication:** Admin required

**Success Response (302):**
```json
Redirect to: /types
Flash message: "類型已刪除"
```

---

## 📍 Locations

### List Locations

**Endpoint:** `GET /locations`

**Authentication:** Required

**Response:** HTML page with all locations (floors, rooms, zones)

---

### Add Location

**Endpoint:** `POST /locations/add`

**Authentication:** Admin required

**Request Body:**
```json
{
  "floor": "1樓",
  "room": "書房",
  "zone": "書桌"
}
```

**Success Response (302):**
```json
Redirect to: /locations
Flash message: "位置已新增"
```

---

### Delete Location

**Endpoint:** `POST /locations/delete`

**Authentication:** Admin required

**Request Body:**
```json
{
  "floor": "1樓",
  "room": "書房",
  "zone": "書桌"
}
```

---

## 🔔 Notifications

### View Notifications Settings

**Endpoint:** `GET /notifications/`

**Authentication:** Required

**Response:** HTML page with notification settings

---

### Get Notification Settings (API)

**Endpoint:** `GET /notifications/api/settings`

**Authentication:** Required

**Response:**
```json
{
  "email": "user@example.com",
  "notify_enabled": true,
  "notify_days": 30,
  "notify_time": "09:00",
  "notify_channels": ["email"],
  "reminder_ladder": [7, 3, 1],
  "replacement_enabled": true,
  "replacement_intervals": [
    {"name": "牙刷", "days": 90},
    {"name": "濾心", "days": 180}
  ]
}
```

---

### Update Notification Settings

**Endpoint:** `POST /notifications/api/settings`

**Authentication:** Required

**Content-Type:** `application/json`

**Request Body:**
```json
{
  "email": "user@example.com",
  "notify_enabled": true,
  "notify_days": 14,
  "notify_time": "08:00",
  "notify_channels": ["email"],
  "reminder_ladder": [7, 3, 1],
  "replacement_enabled": true,
  "replacement_intervals": [
    {"name": "牙刷", "days": 90}
  ]
}
```

**Success Response (200):**
```json
{
  "success": true,
  "message": "設定已更新"
}
```

---

### Send Manual Notification

**Endpoint:** `POST /notifications/api/send`

**Authentication:** Required

**Description:** Manually trigger notification email

**Success Response (200):**
```json
{
  "success": true,
  "message": "通知已發送到您的 Email",
  "expired_count": 5,
  "near_count": 3
}
```

**Error Response (200):**
```json
{
  "success": false,
  "message": "尚無到期或即將到期的物品"
}
```

---

### Get Notification Summary

**Endpoint:** `GET /notifications/api/summary`

**Authentication:** Required

**Response:**
```json
{
  "settings": {
    "email": "user@example.com",
    "notify_enabled": true,
    "notify_days": 30
  },
  "expiry_info": {
    "expired_count": 5,
    "near_expiry_count": 8,
    "expired_items": [...],
    "near_expiry_items": [...]
  },
  "can_send": true
}
```

---

## 🧳 Travel & Shopping

### List Travel Plans

**Endpoint:** `GET /travel/`

**Authentication:** Required

**Response:** HTML page with all travel plans

---

### Create Travel Plan

**Endpoint:** `POST /travel/create`

**Authentication:** Required

**Request Body:**
```json
{
  "name": "日本旅遊",
  "start_date": "2026-03-01",
  "end_date": "2026-03-10",
  "note": "春季賞櫻",
  "default_group": "衣物"
}
```

**Success Response (302):**
```json
Redirect to: /travel/<travel_id>
```

---

### View Travel Detail

**Endpoint:** `GET /travel/<travel_id>`

**Authentication:** Required (must be owner)

**Response:** HTML page with travel details, groups, and items

---

### Add Travel Group

**Endpoint:** `POST /travel/<travel_id>/group`

**Authentication:** Required

**Request Body:**
```json
{
  "name": "電子產品",
  "sort_order": 1
}
```

---

### Add Travel Item

**Endpoint:** `POST /travel/<travel_id>/item`

**Authentication:** Required

**Request Body:**
```json
{
  "group_id": 1,
  "name": "充電器",
  "quantity": 2,
  "is_temp": false,
  "note": "Type-C"
}
```

---

### Update Item Packed Status

**Endpoint:** `POST /travel/<travel_id>/item/<item_id>/packed`

**Authentication:** Required

**Request Body:**
```json
{
  "packed": true
}
```

---

### Export Travel CSV

**Endpoint:** `GET /travel/<travel_id>/export_csv`

**Authentication:** Required

**Response:** CSV file download

**CSV Format:**
```csv
群組,項目,數量,已攜帶,備註
衣物,T恤,3,否,
電子產品,充電器,2,是,Type-C
```

---

### List Shopping Lists

**Endpoint:** `GET /shopping/`

**Authentication:** Required

**Response:** HTML page with shopping lists

---

### Create Shopping List

**Endpoint:** `POST /shopping/create`

**Authentication:** Required

**Request Body:**
```json
{
  "title": "每月採購",
  "list_type": "general",
  "travel_id": null
}
```

---

### Add Shopping Item

**Endpoint:** `POST /shopping/<list_id>/item`

**Authentication:** Required

**Request Body:**
```json
{
  "name": "牛奶",
  "quantity": 2,
  "unit": "瓶",
  "estimated_price": 50.0,
  "store": "全聯",
  "priority": "high",
  "size_note": "1L裝"
}
```

---

### Update Item Purchase Status

**Endpoint:** `POST /shopping/<list_id>/item/<item_id>/purchased`

**Authentication:** Required

**Request Body:**
```json
{
  "purchased": true,
  "actual_price": 48.0
}
```

---

### Get Shopping Summary

**Endpoint:** `GET /shopping/<list_id>/summary`

**Authentication:** Required

**Response:**
```json
{
  "total_items": 10,
  "purchased_items": 3,
  "pending_items": 7,
  "total_estimated": 500.0,
  "total_actual": 150.0
}
```

---

## ⚕️ Health & Monitoring

### Health Check

**Endpoint:** `GET /health`

**Authentication:** Not required

**Description:** Check application health status

**Response (200):**
```json
{
  "status": "healthy",
  "timestamp": "2026-01-24T10:00:00Z",
  "version": "1.0.0",
  "components": {
    "database": "healthy",
    "cache": "healthy"
  }
}
```

**Response (503) - Degraded:**
```json
{
  "status": "degraded",
  "timestamp": "2026-01-24T10:00:00Z",
  "version": "1.0.0",
  "components": {
    "database": "healthy",
    "cache": "unhealthy"
  }
}
```

**Checked Components:**
- Database connectivity (PostgreSQL/MongoDB)
- Redis cache connectivity

---

### Readiness Check

**Endpoint:** `GET /ready`

**Authentication:** Not required

**Description:** Check if application is ready to serve traffic

**Response (200):**
```json
{
  "ready": true,
  "timestamp": "2026-01-24T10:00:00Z",
  "checks": {
    "database": "pass",
    "cache": "pass",
    "migrations": "pass"
  }
}
```

**Response (503) - Not Ready:**
```json
{
  "ready": false,
  "timestamp": "2026-01-24T10:00:00Z",
  "checks": {
    "database": "fail",
    "cache": "pass",
    "migrations": "pass"
  }
}
```

---

### Application Metrics

**Endpoint:** `GET /metrics`

**Authentication:** Not required

**Description:** Get application metrics for monitoring

**Response (200):**
```json
{
  "timestamp": "2026-01-24T10:00:00Z",
  "application": "item-manage-system",
  "version": "1.0.0",
  "counts": {
    "total_items": 142,
    "items_with_photo": 87,
    "items_with_location": 134,
    "items_with_type": 56,
    "types": 8,
    "locations": 12,
    "users": 5
  }
}
```

---

## 📥 Import

### Import Items Page

**Endpoint:** `GET /import`

**Authentication:** Admin required

**Response:** HTML page with import interface

---

### Import Items (CSV/Excel)

**Endpoint:** `POST /import/items`

**Authentication:** Admin required

**Content-Type:** `multipart/form-data`

**Request Body:**
- `file`: CSV or Excel file

**CSV Format:**
```csv
ItemName,ItemID,ItemType,ItemStorePlace,ItemFloor,ItemRoom,ItemZone,WarrantyExpiry,UsageExpiry,ItemDesc
Laptop,ELEC-001,電器,書房,1樓,書房,書桌,2026-12-31,,工作用筆電
牛奶,FOOD-001,食物,冰箱,1樓,廚房,冷藏,2026-01-30,,全脂鮮奶
```

**Success Response (302):**
```json
Redirect to: /home
Flash message: "成功匯入 XX 個物品"
```

**Partial Success Response:**
```json
Flash message: "成功匯入 XX 個物品，失敗 YY 個"
```

---

### Bulk Import JSON

**Endpoint:** `POST /api/items/bulk`

**Authentication:** Admin required

**Content-Type:** `application/json`

**Request Body:**
```json
{
  "items": [
    {
      "ItemName": "Laptop",
      "ItemID": "ELEC-001",
      "ItemType": "電器",
      "ItemStorePlace": "書房"
    },
    {
      "ItemName": "牛奶",
      "ItemID": "FOOD-001",
      "ItemType": "食物"
    }
  ]
}
```

**Success Response (200):**
```json
{
  "success": true,
  "imported": 2,
  "failed": 0,
  "errors": []
}
```

---

## ❌ Error Handling

### Standard Error Response

All API endpoints follow a consistent error response format:

**Format:**
```json
{
  "success": false,
  "error": "Error message",
  "code": "ERROR_CODE"
}
```

### HTTP Status Codes

| Code | Description | Usage |
|------|-------------|-------|
| 200 | OK | Successful request |
| 302 | Found | Redirect (common for form submissions) |
| 400 | Bad Request | Invalid input data |
| 401 | Unauthorized | Not authenticated |
| 403 | Forbidden | Insufficient permissions |
| 404 | Not Found | Resource not found |
| 500 | Internal Server Error | Server error |
| 503 | Service Unavailable | Service temporarily unavailable |

### Common Error Codes

| Code | Description |
|------|-------------|
| `AUTH_REQUIRED` | Authentication required |
| `INVALID_CREDENTIALS` | Invalid username or password |
| `PERMISSION_DENIED` | Insufficient permissions |
| `VALIDATION_ERROR` | Input validation failed |
| `NOT_FOUND` | Resource not found |
| `DUPLICATE_ENTRY` | Duplicate item ID or username |
| `FILE_TOO_LARGE` | File size exceeds 16MB |
| `INVALID_FILE_TYPE` | Unsupported file format |
| `DATABASE_ERROR` | Database operation failed |

---

## 🔒 Rate Limiting

API endpoints are rate-limited to prevent abuse:

**Default Limits:**
- 200 requests per day
- 50 requests per hour

**Headers:**
```
X-RateLimit-Limit: 50
X-RateLimit-Remaining: 45
X-RateLimit-Reset: 1706097600
```

**Rate Limit Exceeded Response (429):**
```json
{
  "error": "Rate limit exceeded",
  "retry_after": 3600
}
```

---

## 📝 Notes

### Authentication
- Session-based authentication using Flask sessions
- CSRF protection enabled for POST requests (use `@csrf.exempt` for API endpoints)
- Session cookies are HTTP-only and secure in production

### File Uploads
- Maximum file size: 16MB
- Allowed formats: JPG, PNG, GIF
- Files are stored in `static/uploads/`

### Date Format
- Standard format: `YYYY-MM-DD` (e.g., `2026-01-24`)
- Time format: `HH:MM` (e.g., `09:00`)

### Pagination
- Default page size: 20 items
- Use `page` query parameter to navigate pages

---

## 📚 Additional Resources

- [User Guide (Chinese)](../GUIDE_ZH-TW.md)
- [Architecture Documentation](./ARCHITECTURE.md)
- [Development Guide](./DEVELOPMENT.md)
- [Testing Documentation](../TESTING.md)

---

**Last Updated:** 2026-01-24
**API Version:** 1.0.0
