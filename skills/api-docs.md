# API Documentation Skill

## Description
Generate OpenAPI/Swagger documentation from Flask routes for Item Management System.

## Trigger Phrases
- "generate api docs"
- "swagger"
- "openapi"
- "api documentation"
- "document api"

## When to Use
When you need to:
- Generate API documentation from existing routes
- Update API documentation after route changes
- Create interactive API documentation (Swagger UI)
- Document request/response formats
- Document authentication requirements
- Document error responses

## Available Tools
- Bash (for running documentation generation)
- Grep (for finding route definitions)
- Read (for reading route files)
- Write (for creating documentation files)
- Glob (for finding all route files)

## MUST DO
1. Scan all route files in `app/routes/` directory
2. Document every route with:
   - HTTP method (GET, POST, PUT, DELETE)
   - URL path
   - Request parameters (query, path, body)
   - Request body schema
   - Response format
   - Status codes (success and error)
   - Authentication requirements
   - Rate limiting (if applicable)
3. Generate OpenAPI 3.0 specification
4. Create interactive Swagger UI
5. Keep documentation in sync with code
6. Document all error responses
7. Include example requests/responses

## MUST NOT DO
- Do NOT document routes that don't exist
- Do NOT skip authentication requirements
- Do NOT omit error responses
- Do NOT use unclear or ambiguous descriptions
- Do NOT generate docs without verifying routes work

## Context
- Flask application with Blueprint routing
- Routes organized in `app/routes/`:
  - `auth/` - Authentication routes (login, logout, change password)
  - `items/` - Item management CRUD
  - `types/` - Item type management
  - `locations/` - Location management
  - `notifications/` - Notification settings
- Uses Flask-Login for authentication
- Uses Flask-Limiter for rate limiting
- JSON request/response format
- Supports both PostgreSQL and MongoDB

## API Documentation Structure

### OpenAPI 3.0 Specification
```yaml
openapi: 3.0.0
info:
  title: Item Management System API
  version: 1.0.0
  description: API for managing items, users, and locations

servers:
  - url: http://localhost:8080/api
    description: Development server

components:
  securitySchemes:
    sessionAuth:
      type: apiKey
      in: cookie
      name: session

paths:
  # Route definitions here
```

### Route Documentation Template
```yaml
/items:
  get:
    summary: List all items
    description: Retrieve a paginated list of items with optional filtering
    security:
      - sessionAuth: []
    parameters:
      - name: page
        in: query
        schema:
          type: integer
          default: 1
      - name: per_page
        in: query
        schema:
          type: integer
          default: 20
      - name: search
        in: query
        schema:
          type: string
    responses:
      '200':
        description: Successful response
        content:
          application/json:
            schema:
              type: array
              items:
                $ref: '#/components/schemas/Item'
      '401':
        description: Unauthorized
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/Error'
```

## Workflow

### 1. Scan Routes
```bash
# Find all route files
find app/routes -name "*.py"

# Extract route definitions
grep -r "@.*\.route" app/routes/
```

### 2. Parse Route Metadata
For each route, document:
- Method (GET, POST, PUT, DELETE, PATCH)
- URL pattern (including parameters)
- Authentication requirement (login_required)
- Rate limits (if any)
- Request parameters
- Request body schema
- Response structure
- Status codes
- Error handling

### 3. Generate Documentation
Create file: `docs/openapi.yaml` or `docs/swagger.json`

### 4. Setup Swagger UI
Create file: `static/swagger-ui.html` or integrate with Flask

```html
<!DOCTYPE html>
<html>
<head>
  <link rel="stylesheet" type="text/css" href="https://unpkg.com/swagger-ui-dist/swagger-ui.css">
</head>
<body>
  <div id="swagger-ui"></div>
  <script src="https://unpkg.com/swagger-ui-dist/swagger-ui-bundle.js"></script>
  <script>
    SwaggerUIBundle({
      url: '/static/openapi.yaml',
      dom_id: '#swagger-ui'
    });
  </script>
</body>
</html>
```

### 5. Add Documentation Route
```python
# app/routes/docs.py
from flask import Blueprint, render_template, send_from_directory

docs_bp = Blueprint('docs', __name__)

@docs_bp.route('/swagger')
def swagger_ui():
    return render_template('swagger.html')

@docs_bp.route('/openapi.yaml')
def openapi_spec():
    return send_from_directory('static', 'openapi.yaml')
```

## Key Routes to Document

### Authentication
- POST `/auth/login` - User login
- POST `/auth/logout` - User logout
- POST `/auth/change_password` - Change password
- POST `/auth/force_change_password` - First-time password change

### Items
- GET `/items` - List items with pagination
- GET `/items/<item_id>` - Get single item
- POST `/items` - Create new item
- PUT `/items/<item_id>` - Update item
- DELETE `/items/<item_id>` - Delete item
- POST `/items/<item_id>/favorite` - Toggle favorite
- POST `/items/<item_id>/related` - Add related item
- DELETE `/items/<item_id>/related/<related_id>` - Remove related item

### Types
- GET `/types` - List item types
- POST `/types` - Create type
- DELETE `/types/<name>` - Delete type

### Locations
- GET `/locations` - List locations
- POST `/locations` - Create location
- PUT `/locations/<id>` - Update location
- DELETE `/locations/<id>` - Delete location
- GET `/locations/choices` - Get unique floors/rooms/zones

### Notifications
- GET `/notifications/settings` - Get notification settings
- PUT `/notifications/settings` - Update notification settings

## Schema Definitions

### Item Schema
```yaml
components:
  schemas:
    Item:
      type: object
      properties:
        ItemID:
          type: string
          description: Unique item identifier
        ItemName:
          type: string
          description: Item name
        ItemDesc:
          type: string
          description: Item description
        ItemType:
          type: string
          description: Item type/category
        ItemOwner:
          type: string
          description: Item owner
        ItemFloor:
          type: string
          description: Floor location
        ItemRoom:
          type: string
          description: Room location
        ItemZone:
          type: string
          description: Zone location
        WarrantyExpiry:
          type: string
          format: date
          description: Warranty expiry date
        UsageExpiry:
          type: string
          format: date
          description: Usage expiry date
        favorites:
          type: array
          items:
            type: string
          description: User IDs who favorited this item
        related_items:
          type: array
          items:
            type: object
          description: Related items
        move_history:
          type: array
          items:
            type: object
          description: Movement history
      required:
        - ItemID
        - ItemName
```

### Error Schema
```yaml
components:
  schemas:
    Error:
      type: object
      properties:
        error:
          type: string
          description: Error message
        code:
          type: integer
          description: HTTP status code
```

## Documentation Checklist
- [ ] All routes documented
- [ ] Authentication requirements specified
- [ ] Request parameters documented
- [ ] Request body schemas defined
- [ ] Response formats documented
- [ ] Status codes documented
- [ ] Error responses documented
- [ ] Example requests/responses provided
- [ ] Swagger UI configured
- [ ] Documentation accessible via `/docs` route

## Tools and Libraries
- **Flasgger** - Swagger UI integration for Flask
- **Sphinx** - Documentation generation
- **ReDoc** - Alternative to Swagger UI

## Example: Using Flasgger
```python
from flask import Flask
from flasgger import Swagger

app = Flask(__name__)
swagger = Swagger(app)

@app.route('/items')
@swag_from({
    'responses': {
        200: {
            'description': 'List of items',
            'schema': {
                'type': 'array',
                'items': {'$ref': '#/definitions/Item'}
            }
        }
    }
})
def list_items():
    pass
```

## Maintenance
- Update documentation when routes change
- Regenerate OpenAPI spec after updates
- Keep examples current with actual API behavior
- Add changelog to documentation version history
