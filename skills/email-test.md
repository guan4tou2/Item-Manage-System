# Email Testing Skill

## Description
Email notification testing and debugging for Item Management System.

## Trigger Phrases
- "test email"
- "email notification"
- "debug mail"

## When to Use
When you need to:
- Test email notification functionality
- Debug email delivery issues
- Verify email content and formatting
- Test notification scheduling
- Configure email settings
- Debug SMTP connection issues

## Available Tools
- Bash (for email testing)
- Read (for reviewing email code)
- Grep (for finding email-related code)
- Librarian agent (for email best practices)

## MUST DO
1. Test email configuration before deployment
2. Use test email addresses (not production)
3. Verify SMTP connection and authentication
4. Test email content rendering (HTML and plain text)
5. Check spam score and deliverability
6. Test with various email providers (Gmail, Outlook, etc.)
7. Verify email templates display correctly
8. Test notification scheduling
9. Log all email attempts (success/failure)
10. Test internationalization if applicable

## MUST NOT DO
- Do NOT send emails to real users during testing
- Do NOT use production SMTP credentials in development
- Do NOT hardcode passwords in code
- Do NOT ignore email errors
- Do NOT send sensitive data in test emails
- Do NOT test with production database

## Context
- Flask-Mail for email sending
- Email notifications for:
  - Item expiry reminders
  - Warranty expiry reminders
  - System alerts
  - User notifications
- Supports both HTML and plain text emails
- Uses APScheduler for scheduled notifications
- SMTP configuration via environment variables

## Email Configuration

### Environment Variables
```bash
# .env
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USE_TLS=True
MAIL_USERNAME=your-email@gmail.com
MAIL_PASSWORD=your-app-password
MAIL_DEFAULT_SENDER=noreply@example.com
MAIL_DEBUG=True  # Enable email debugging
```

### Flask-Mail Setup
```python
from flask import Flask
from flask_mail import Mail, Message

app = Flask(__name__)

app.config.update(
    MAIL_SERVER=os.getenv('MAIL_SERVER'),
    MAIL_PORT=int(os.getenv('MAIL_PORT', 587)),
    MAIL_USE_TLS=os.getenv('MAIL_USE_TLS', 'True').lower() == 'true',
    MAIL_USERNAME=os.getenv('MAIL_USERNAME'),
    MAIL_PASSWORD=os.getenv('MAIL_PASSWORD'),
    MAIL_DEFAULT_SENDER=os.getenv('MAIL_DEFAULT_SENDER'),
    MAIL_DEBUG=os.getenv('MAIL_DEBUG', 'False').lower() == 'true'
)

mail = Mail(app)
```

## Email Testing

### 1. Test SMTP Connection
```python
def test_smtp_connection():
    """Test SMTP connection and authentication"""
    import smtplib
    from email.mime.text import MIMEText

    try:
        server = smtplib.SMTP(app.config['MAIL_SERVER'], app.config['MAIL_PORT'])

        if app.config['MAIL_USE_TLS']:
            server.starttls()

        server.login(
            app.config['MAIL_USERNAME'],
            app.config['MAIL_PASSWORD']
        )

        print("SMTP connection successful!")
        server.quit()

    except Exception as e:
        print(f"SMTP connection failed: {e}")
        raise
```

### 2. Test Send Simple Email
```python
def send_test_email(to_email, subject="Test Email"):
    """Send a simple test email"""
    msg = Message(
        subject=subject,
        recipients=[to_email],
        sender=app.config['MAIL_DEFAULT_SENDER']
    )

    msg.body = "This is a test email from Item Management System."
    msg.html = """
    <html>
        <body>
            <h1>Test Email</h1>
            <p>This is a test email from Item Management System.</p>
        </body>
    </html>
    """

    try:
        mail.send(msg)
        print(f"Test email sent to {to_email}")
        return True
    except Exception as e:
        print(f"Failed to send email: {e}")
        return False
```

### 3. Test Email Template
```python
def send_test_notification(to_email):
    """Send a notification test with template"""
    msg = Message(
        subject="Test Notification: Item Expiring Soon",
        recipients=[to_email],
        sender=app.config['MAIL_DEFAULT_SENDER']
    )

    # Load template
    msg.html = render_template('email/notification.html',
        item_name='Test Item',
        expiry_date='2024-02-01',
        days_remaining=7,
        app_url='http://localhost:8080'
    )

    # Plain text version
    msg.body = render_template('email/notification.txt',
        item_name='Test Item',
        expiry_date='2024-02-01',
        days_remaining=7,
        app_url='http://localhost:8080'
    )

    try:
        mail.send(msg)
        print(f"Notification test sent to {to_email}")
        return True
    except Exception as e:
        print(f"Failed to send notification: {e}")
        return False
```

## Email Templates

### HTML Template Example
```html
<!-- templates/email/notification.html -->
<!DOCTYPE html>
<html>
<head>
    <style>
        body { font-family: Arial, sans-serif; }
        .container { max-width: 600px; margin: 0 auto; padding: 20px; }
        .header { background-color: #007bff; color: white; padding: 20px; text-align: center; }
        .content { padding: 20px; background-color: #f8f9fa; }
        .button { display: inline-block; padding: 12px 24px; background-color: #007bff; color: white; text-decoration: none; border-radius: 5px; }
        .footer { margin-top: 20px; padding: 20px; text-align: center; font-size: 12px; color: #6c757d; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Item Management System</h1>
        </div>

        <div class="content">
            <h2>Item Expiring Soon</h2>

            <p>Hello,</p>

            <p>The following item is expiring soon:</p>

            <ul>
                <li><strong>Item Name:</strong> {{ item_name }}</li>
                <li><strong>Expiry Date:</strong> {{ expiry_date }}</li>
                <li><strong>Days Remaining:</strong> {{ days_remaining }}</li>
            </ul>

            <p style="text-align: center; margin: 30px 0;">
                <a href="{{ app_url }}/items" class="button">View Items</a>
            </p>

            <p>Please update the item or renew its expiry date.</p>
        </div>

        <div class="footer">
            <p>This is an automated email. Please do not reply.</p>
            <p>&copy; 2024 Item Management System</p>
        </div>
    </div>
</body>
</html>
```

### Plain Text Template Example
```text
<!-- templates/email/notification.txt -->
Item Management System - Item Expiring Soon

Hello,

The following item is expiring soon:

Item Name: {{ item_name }}
Expiry Date: {{ expiry_date }}
Days Remaining: {{ days_remaining }}

Please update the item or renew its expiry date.

View Items: {{ app_url }}/items

---
This is an automated email. Please do not reply.
© 2024 Item Management System
```

## Email Testing Tools

### MailHog (Local Email Testing)
```yaml
# docker-compose.yml
services:
  mailhog:
    image: mailhog/mailhog
    ports:
      - "1025:1025"  # SMTP
      - "8025:8025"  # Web UI
```

**Usage:**
```bash
# Update .env to use MailHog
MAIL_SERVER=mailhog
MAIL_PORT=1025
MAIL_USE_TLS=False
MAIL_DEBUG=True

# Test emails are captured at http://localhost:8025
```

### Mailtrap (Email Testing Service)
```bash
# Update .env with Mailtrap credentials
MAIL_SERVER=sandbox.smtp.mailtrap.io
MAIL_PORT=2525
MAIL_USERNAME=your_mailtrap_username
MAIL_PASSWORD=your_mailtrap_password
MAIL_USE_TLS=False
```

**Usage:** View emails at https://mailtrap.io

### Email on Acid (Email Testing)
1. Register at https://www.emailonacid.com
2. Get test email address
3. Send test email to that address
4. View results and check rendering across clients

### Gmail SMTP Testing
```bash
# Enable 2FA on Gmail account
# Generate App Password: https://myaccount.google.com/apppasswords

# Update .env
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USE_TLS=True
MAIL_USERNAME=your-email@gmail.com
MAIL_PASSWORD=your-16-char-app-password
```

## Email Debugging

### Enable SMTP Debugging
```python
import smtplib

server = smtplib.SMTP(app.config['MAIL_SERVER'], app.config['MAIL_PORT'])
server.set_debuglevel(1)  # Enable debug output
```

### Log Email Attempts
```python
def send_email_with_logging(msg):
    """Send email with detailed logging"""
    try:
        result = mail.send(msg)
        app.logger.info(
            f"Email sent successfully to {msg.recipients}",
            extra={'email_to': msg.recipients}
        )
        return True
    except smtplib.SMTPException as e:
        app.logger.error(
            f"SMTP error: {str(e)}",
            extra={'email_to': msg.recipients, 'error': str(e)}
        )
        return False
    except Exception as e:
        app.logger.error(
            f"Email sending failed: {str(e)}",
            extra={'email_to': msg.recipients, 'error': str(e)},
            exc_info=True
        )
        return False
```

### Test Email Deliverability
```python
def test_email_deliverability(to_email):
    """Test if email is deliverable"""
    import dns.resolver

    try:
        # Get MX records
        domain = to_email.split('@')[1]
        mx_records = dns.resolver.resolve(domain, 'MX')

        print(f"MX records for {domain}:")
        for mx in mx_records:
            print(f"  {mx.exchange}")

        # Check for common email providers
        if any(str(mx.exchange).lower().find(prov) >= 0
               for mx in mx_records
               for prov in ['gmail', 'outlook', 'yahoo', 'hotmail']):
            print(f"Email provider detected: {domain}")

        return True

    except Exception as e:
        print(f"Deliverability check failed: {e}")
        return False
```

## Common Email Issues

### Issue: "Authentication failed"
**Solution:**
- Verify username and password are correct
- For Gmail: Use App Password, not account password
- Enable 2FA and generate App Password

### Issue: "Connection timeout"
**Solution:**
- Check firewall settings
- Verify SMTP server address and port
- Try different port (587 vs 465)

### Issue: Email goes to spam
**Solution:**
- Check SPF, DKIM, and DMARC records
- Verify sender domain reputation
- Avoid spam trigger words
- Test spam score with Mail Tester

### Issue: HTML not rendering
**Solution:**
- Test with different email clients
- Avoid inline styles (use inline styles instead)
- Test with Mail Tester or Email on Acid

## Email Testing Checklist
- [ ] SMTP connection successful
- [ ] Authentication successful
- [ ] Test email sent successfully
- [ ] HTML template renders correctly
- [ ] Plain text template renders correctly
- [ ] Email not marked as spam
- [ ] Links in email work
- [ ] Email displays on mobile
- [ ] Subject line is clear
- [ ] From address is correct
- [ ] Reply-to address set (if needed)
- [ ] Footer includes unsubscribe info
- [ ] Email logged in database
- [ ] Notification scheduler working
- [ ] Error handling tested

## Email Testing Tools
- **MailHog** - Local email testing
- **Mailtrap** - Email testing service
- **Email on Acid** - Email rendering testing
- **Mail Tester** - Spam score checking
- **Gmx** - Email deliverability testing
- **Litmus** - Advanced email testing

## Testing Commands
```bash
# Test SMTP connection
python3 test_smtp_connection.py

# Send test email
python3 test_send_email.py test@example.com

# Test notification template
python3 test_notification.py test@example.com

# Test with MailHog
docker compose up mailhog
curl -X POST http://localhost:8025/api/v1/messages
```
