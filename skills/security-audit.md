# Security Audit Skill

## Description
Security vulnerability scanning and remediation for Item Management System.

## Trigger Phrases
- "security scan"
- "vulnerability"
- "security audit"

## When to Use
When you need to:
- Scan for security vulnerabilities
- Audit authentication/authorization
- Check for common security issues
- Review code for security flaws
- Implement security best practices
- Test for XSS, CSRF, SQL injection

## Available Tools
- Bash (for security scanning tools)
- Grep (for finding security issues)
- Read (for reviewing code)
- Librarian/Explore agents (for security best practices)

## MUST DO
1. Scan dependencies for known vulnerabilities
2. Check authentication implementation
3. Validate input sanitization
4. Review authorization checks
5. Test for common OWASP vulnerabilities
6. Verify HTTPS enforcement
7. Check secret management
8. Review logging for security events
9. Test rate limiting
10. Validate CORS configuration

## MUST NOT DO
- Do NOT skip security scans before deployment
- Do NOT ignore low-severity vulnerabilities
- Do NOT assume input is safe
- Do NOT hardcode secrets
- Do NOT disable security features
- Do NOT roll your own crypto
- Do NOT ignore authentication on any route

## Context
- Flask web application
- User authentication with Flask-Login
- Database access with SQLAlchemy/PyMongo
- File upload functionality (photos)
- Email notifications
- PWA support
- Supports both PostgreSQL and MongoDB

## Security Checklist

### OWASP Top 10
- [ ] Injection (SQL, NoSQL, command)
- [ ] Broken authentication
- [ ] Sensitive data exposure
- [ ] XML external entities (XXE)
- [ ] Broken access control
- [ ] Security misconfiguration
- [ ] Cross-site scripting (XSS)
- [ ] Insecure deserialization
- [ ] Using components with known vulnerabilities
- [ ] Insufficient logging & monitoring

## Security Scanning

### 1. Dependency Scanning
```bash
# pip-audit: Check for vulnerable dependencies
pip install pip-audit
pip-audit

# Safety: Check for security issues
pip install safety
safety check

# Snyk: Advanced vulnerability scanner
npm install -g snyk
snyk test
```

### 2. Code Security Analysis
```bash
# Bandit: Python security linter
pip install bandit
bandit -r app/

# Semgrep: Fast security scanning
pip install semgrep
semgrep scan --config auto

# PyT: Python vulnerability scanner
pip install pyt
pyt app/
```

### 3. Authentication Audit
```python
# Check for authentication on all routes
from flask import current_app

@current_app.before_request
def check_auth():
    # Public routes
    public_routes = ['/auth/login', '/static', '/api/docs']

    if request.path not in public_routes:
        if not current_user.is_authenticated:
            return jsonify({'error': 'Unauthorized'}), 401
```

### 4. Input Validation
```python
# Validate all inputs
from wtforms import validators

class ItemForm(FlaskForm):
    ItemName = StringField('Name', [
        validators.DataRequired(),
        validators.Length(min=1, max=100),
        validators.Regexp(r'^[a-zA-Z0-9\s\-_\.]+$')
    ])
    ItemID = StringField('ID', [
        validators.DataRequired(),
        validators.Regexp(r'^[A-Z]{2}\d{8}$')  # Format: AB12345678
    ])
```

### 5. SQL Injection Prevention
```python
# GOOD: Use parameterized queries
from app import db
item = Item.query.filter_by(ItemID=item_id).first()

# BAD: String concatenation (vulnerable)
# query = f"SELECT * FROM items WHERE ItemID = '{item_id}'"
```

### 6. XSS Prevention
```python
from markupsafe import escape

# Escape user input before rendering
item_name = escape(request.form['ItemName'])

# Or use Flask's auto-escaping in templates
# {{ item_name }} is auto-escaped
# {{ item_name|safe }} disables escaping (use carefully!)
```

### 7. CSRF Protection
```python
from flask_wtf.csrf import CSRFProtect

app = Flask(__name__)
csrf = CSRFProtect(app)

# All POST/PUT/DELETE routes now protected
# Include CSRF token in forms:
# <input type="hidden" name="csrf_token" value="{{ csrf_token() }}">
```

### 8. File Upload Security
```python
import os
from werkzeug.utils import secure_filename

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/upload', methods=['POST'])
def upload_file():
    file = request.files['file']

    # Validate file type
    if not allowed_file(file.filename):
        return jsonify({'error': 'Invalid file type'}), 400

    # Secure filename
    filename = secure_filename(file.filename)

    # Generate unique filename
    import uuid
    unique_filename = f"{uuid.uuid4()}_{filename}"

    # Save file
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
    file.save(filepath)

    return jsonify({'path': filepath})
```

### 9. Rate Limiting
```python
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

limiter = Limiter(
    app,
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"]
)

@app.route('/api/items')
@limiter.limit("100 per hour")
def list_items():
    pass
```

### 10. Secure Headers
```python
from flask import Flask
from flask_talisman import Talisman

app = Flask(__name__)
Talisman(app, force_https=True)

# Or manually set headers
@app.after_request
def security_headers(response):
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    return response
```

## Secret Management

### .env Example
```bash
# Database
DATABASE_URL=postgresql://user:${DB_PASSWORD}@localhost:5432/itemman
MONGO_URI=mongodb://user:${DB_PASSWORD}@localhost:27017/myDB

# Email
MAIL_SERVER=${SMTP_SERVER}
MAIL_PORT=${SMTP_PORT}
MAIL_USERNAME=${SMTP_USER}
MAIL_PASSWORD=${SMTP_PASSWORD}

# Session
SECRET_KEY=${APP_SECRET_KEY}

# NEVER commit actual values to version control
```

### Using Python Keyring
```python
import keyring
import os

def get_secret(key):
    # Try environment variable first
    value = os.getenv(key)
    if value:
        return value

    # Fall back to keyring
    value = keyring.get_password("itemman", key)
    if value:
        return value

    raise ValueError(f"Secret not found for key: {key}")

# Usage
db_password = get_secret('DB_PASSWORD')
```

## Security Testing

### Manual Testing
```bash
# Test SQL injection
curl -X POST http://localhost:8080/api/items \
  -d "ItemID=' OR '1'='1"

# Test XSS
curl -X POST http://localhost:8080/api/items \
  -d "ItemName=<script>alert('XSS')</script>"

# Test CSRF (remove token)
curl -X POST http://localhost:8080/api/items \
  -H "Cookie: session=..." \
  -d "ItemID=ABC12345678"

# Test rate limiting
for i in {1..100}; do
  curl http://localhost:8080/api/items
done
```

### Automated Testing
```bash
# OWASP ZAP
docker run -t owasp/zap2docker-stable zap-baseline.py \
  -t http://localhost:8080

# Nikto
nikto -h http://localhost:8080

# SQLMap
sqlmap -u "http://localhost:8080/api/items?id=1" \
  --dbs --batch
```

## Common Vulnerabilities to Fix

### 1. Hardcoded Secrets
```python
# BAD
DATABASE_URL = "postgresql://user:password123@localhost/itemman"

# GOOD
import os
DATABASE_URL = os.getenv('DATABASE_URL')
```

### 2. Missing Authentication
```python
# BAD
@app.route('/admin/users')
def list_all_users():
    return jsonify(User.query.all())

# GOOD
@app.route('/admin/users')
@login_required
@admin_required
def list_all_users():
    return jsonify(User.query.all())
```

### 3. Information Leakage
```python
# BAD: Detailed error messages
@app.errorhandler(Exception)
def handle_error(e):
    return jsonify({'error': str(e)}), 500

# GOOD: Generic error messages
@app.errorhandler(Exception)
def handle_error(e):
    app.logger.error(f"Error: {e}")
    return jsonify({'error': 'Internal server error'}), 500
```

## Security Audit Report Template

```markdown
# Security Audit Report

## Executive Summary
- Total vulnerabilities found: X
- Critical: X
- High: X
- Medium: X
- Low: X

## Findings

### [Critical] SQL Injection in Search
- Location: app/routes/items.py:45
- Severity: Critical
- Description: User input directly concatenated into SQL query
- Remediation: Use parameterized queries

### [High] Missing CSRF Protection
- Location: app/routes/admin.py:12
- Severity: High
- Description: Admin actions not protected against CSRF
- Remediation: Add Flask-WTF CSRF protection

## Recommendations
1. Implement all security headers
2. Add rate limiting to all public APIs
3. Review and harden authentication flow
4. Implement proper logging and monitoring
```

## Security Best Practices
1. Always use HTTPS in production
2. Implement rate limiting
3. Validate all inputs
4. Use prepared statements
5. Keep dependencies updated
6. Implement proper logging
7. Use strong session security
8. Regular security audits
9. Implement security headers
10. Have an incident response plan
