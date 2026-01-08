# Logging & Monitoring Skill

## Description
Application logging setup and monitoring configuration for Item Management System.

## Trigger Phrases
- "setup logging"
- "monitoring"
- "logs"
- "alerting"

## When to Use
When you need to:
- Set up structured logging
- Configure log levels
- Monitor application performance
- Set up alerts and notifications
- Track error rates
- Monitor resource usage
- Debug production issues
- Analyze user behavior

## Available Tools
- Bash (for log commands)
- Grep (for log analysis)
- PostgreSQL MCP (for log queries)
- MongoDB MCP (for log queries)

## MUST DO
1. Use structured logging (JSON format preferred)
2. Set appropriate log levels (DEBUG, INFO, WARNING, ERROR)
3. Include context in logs (user ID, request ID, timestamp)
4. Avoid logging sensitive data (passwords, tokens)
5. Configure log rotation to prevent disk full
6. Set up monitoring for critical metrics
7. Configure alerts for errors and anomalies
8. Archive old logs for compliance
9. Use unique request IDs for traceability
10. Test log output and formatting

## MUST NOT DO
- Do NOT log passwords or secrets
- Do NOT use print statements (use logger)
- Do NOT ignore errors without logging
- Do NOT log in production at DEBUG level
- Do NOT forget log rotation
- Do NOT log excessive details that hurt performance

## Context
- Flask 3.1+ web application
- Python logging framework
- Operation logs stored in database
- Supports both PostgreSQL and MongoDB
- Email notifications for alerts
- APScheduler for scheduled tasks

## Logging Configuration

### Python Logging Setup
```python
import logging
import logging.handlers
from datetime import datetime
import os

def setup_logging(app):
    """Configure application logging"""
    log_dir = 'logs'
    os.makedirs(log_dir, exist_ok=True)

    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - [%(request_id)s] - %(message)s'
    )

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    app.logger.addHandler(console_handler)

    # File handler - rotating
    file_handler = logging.handlers.RotatingFileHandler(
        os.path.join(log_dir, 'app.log'),
        maxBytes=10485760,  # 10MB
        backupCount=10
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    app.logger.addHandler(file_handler)

    # Error log handler
    error_handler = logging.handlers.RotatingFileHandler(
        os.path.join(log_dir, 'error.log'),
        maxBytes=10485760,
        backupCount=10
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(formatter)
    app.logger.addHandler(error_handler)

    # Log level from environment
    log_level = os.getenv('LOG_LEVEL', 'INFO').upper()
    app.logger.setLevel(getattr(logging, log_level))

    return app.logger
```

### Request Logging Middleware
```python
import uuid
from flask import g, request

@app.before_request
def before_request():
    """Add request ID and log request"""
    g.request_id = str(uuid.uuid4())
    app.logger.info(
        f"{request.method} {request.path}",
        extra={'request_id': g.request_id}
    )

@app.after_request
def after_request(response):
    """Log response"""
    app.logger.info(
        f"{response.status_code} {request.method} {request.path}",
        extra={'request_id': getattr(g, 'request_id', 'unknown')}
    )
    response.headers['X-Request-ID'] = getattr(g, 'request_id', 'unknown')
    return response
```

### Database Logging
```python
from sqlalchemy import event
from sqlalchemy.engine import Engine
import time

@event.listens_for(Engine, "before_cursor_execute")
def log_query(conn, cursor, statement, parameters, context, executemany):
    """Log slow queries"""
    context._query_start_time = time.time()
    context._query_statement = statement

@event.listens_for(Engine, "after_cursor_execute")
def log_query_result(conn, cursor, statement, parameters, context, executemany):
    """Log query duration"""
    duration = time.time() - context._query_start_time

    # Log queries taking longer than 1 second
    if duration > 1.0:
        app.logger.warning(
            f"Slow query ({duration:.2f}s): {statement[:100]}...",
            extra={'request_id': getattr(g, 'request_id', 'unknown')}
        )
```

## Log Levels

### DEBUG
```python
app.logger.debug("Variable value: %s", variable)
```
**When to use:** Detailed diagnostic information, development only

### INFO
```python
app.logger.info("User %s logged in", username)
```
**When to use:** Normal application flow, important events

### WARNING
```python
app.logger.warning("Disk space low: %d%%", disk_usage)
```
**When to use:** Something unexpected but not an error

### ERROR
```python
app.logger.error("Failed to save item: %s", str(e), exc_info=True)
```
**When to use:** Application error that doesn't cause termination

### CRITICAL
```python
app.logger.critical("Database connection lost!")
```
**When to use:** Serious error requiring immediate attention

## Structured Logging

### JSON Format
```python
import json
import logging

class JSONFormatter(logging.Formatter):
    def format(self, record):
        log_entry = {
            'timestamp': datetime.utcnow().isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'request_id': getattr(record, 'request_id', 'unknown'),
        }

        if record.exc_info:
            log_entry['exception'] = self.formatException(record.exc_info)

        return json.dumps(log_entry)

# Use JSON formatter for production
json_handler = logging.StreamHandler()
json_handler.setFormatter(JSONFormatter())
```

### Context-Aware Logging
```python
import logging

class ContextLogger:
    """Logger with automatic context"""

    def __init__(self, logger, context):
        self.logger = logger
        self.context = context

    def info(self, message, **kwargs):
        """Log INFO with context"""
        extra = {**self.context, **kwargs}
        self.logger.info(message, extra=extra)

    def error(self, message, **kwargs):
        """Log ERROR with context"""
        extra = {**self.context, **kwargs}
        self.logger.error(message, extra=extra, exc_info=True)

# Usage
def process_item(user_id, item_id):
    logger = ContextLogger(app.logger, {
        'user_id': user_id,
        'item_id': item_id,
        'action': 'process_item'
    })
    logger.info("Starting to process item")
```

## Monitoring Setup

### Application Metrics
```python
from prometheus_flask_exporter import PrometheusMetrics

prometheus = PrometheusMetrics(app)

# Custom metrics
item_operations = prometheus.create_counter(
    'item_operations_total',
    'Total item operations',
    ['operation', 'status']
)

@app.route('/items/<item_id>', methods=['PUT'])
def update_item(item_id):
    try:
        item_service.update_item(item_id, request.json)
        item_operations.labels(operation='update', status='success').inc()
    except Exception as e:
        item_operations.labels(operation='update', status='error').inc()
        raise
```

### Health Checks
```python
@app.route('/health')
def health_check():
    """Health check endpoint"""
    health_status = {
        'status': 'healthy',
        'timestamp': datetime.utcnow().isoformat(),
        'checks': {}
    }

    # Check database
    try:
        from app import db
        db.session.execute(db.text('SELECT 1'))
        health_status['checks']['database'] = 'healthy'
    except Exception as e:
        health_status['checks']['database'] = f'unhealthy: {str(e)}'
        health_status['status'] = 'unhealthy'

    # Check uploads directory
    import os
    if os.access(app.config['UPLOAD_FOLDER'], os.W_OK):
        health_status['checks']['uploads'] = 'healthy'
    else:
        health_status['checks']['uploads'] = 'unhealthy'
        health_status['status'] = 'unhealthy'

    # Check disk space
    disk_usage = os.statvfs(app.config['UPLOAD_FOLDER'])
    free_percent = (disk_usage.f_bavail / disk_usage.f_blocks) * 100
    health_status['checks']['disk_space'] = f'{free_percent:.1f}% free'

    if free_percent < 10:
        health_status['status'] = 'warning'

    status_code = 200 if health_status['status'] == 'healthy' else 503
    return jsonify(health_status), status_code
```

### Alerting
```python
from app.services import email_service

def send_alert(subject, message, severity='warning'):
    """Send alert via email"""
    recipients = ['admin@example.com']

    if severity == 'critical':
        subject = f"[CRITICAL] {subject}"
        email_service.send_email(
            recipients=recipients,
            subject=subject,
            body=message
        )

def check_error_rate():
    """Check if error rate exceeds threshold"""
    from app.models.log import Log
    from datetime import datetime, timedelta

    # Count errors in last hour
    one_hour_ago = datetime.now() - timedelta(hours=1)
    error_count = Log.query.filter(
        Log.action == 'error',
        Log.timestamp >= one_hour_ago.strftime("%Y-%m-%d %H:%M:%S")
    ).count()

    # Alert if more than 10 errors per hour
    if error_count > 10:
        send_alert(
            subject="High Error Rate",
            message=f"Detected {error_count} errors in the last hour",
            severity='critical'
        )

# Schedule check
from apscheduler.schedulers.background import BackgroundScheduler
scheduler = BackgroundScheduler()
scheduler.add_job(check_error_rate, 'interval', minutes=5)
scheduler.start()
```

## Log Analysis

### Using Grep
```bash
# Find all errors in last hour
find logs/ -name "*.log" -mmin -60 -exec grep -h "ERROR" {} +

# Find slow queries
grep "Slow query" logs/app.log

# Count errors per hour
grep "ERROR" logs/app.log | cut -d' ' -f1 | uniq -c

# Find requests by user
grep "user_id:123" logs/app.log

# Find 404 errors
grep "404" logs/access.log | tail -20
```

### Using PostgreSQL (Database Logs)
```python
from app.models.log import Log
from datetime import datetime, timedelta

def get_error_summary(hours=24):
    """Get error summary from database logs"""
    start_time = datetime.now() - timedelta(hours=hours)

    # Count errors by type
    error_types = db.session.query(
        Log.action,
        db.func.count(Log.id)
    ).filter(
        Log.timestamp >= start_time.strftime("%Y-%m-%d %H:%M:%S"),
        Log.action.like('%error%')
    ).group_by(Log.action).all()

    return error_types

def get_failed_logins(hours=24):
    """Get failed login attempts"""
    start_time = datetime.now() - timedelta(hours=hours)

    failed_logins = Log.query.filter(
        Log.action == 'login_failed',
        Log.timestamp >= start_time.strftime("%Y-%m-%d %H:%M:%S")
    ).all()

    return failed_logins
```

## Monitoring Tools

### 1. Prometheus + Grafana
```yaml
# docker-compose.yml
services:
  prometheus:
    image: prom/prometheus
    ports:
      - "9090:9090"
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml

  grafana:
    image: grafana/grafana
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
    volumes:
      - grafana_data:/var/lib/grafana
```

### 2. ELK Stack (Elasticsearch, Logstash, Kibana)
```yaml
services:
  elasticsearch:
    image: elasticsearch:8.12.0
    environment:
      - discovery.type=single-node
      - "ES_JAVA_OPTS=-Xms512m -Xmx512m"
    ports:
      - "9200:9200"

  logstash:
    image: logstash:8.12.0
    ports:
      - "5044:5044"
    volumes:
      - ./logstash.conf:/usr/share/logstash/pipeline/logstash.conf

  kibana:
    image: kibana:8.12.0
    ports:
      - "5601:5601"
    depends_on:
      - elasticsearch
```

### 3. Sentry (Error Tracking)
```python
import sentry_sdk
from sentry_sdk.integrations.flask import FlaskIntegration

sentry_sdk.init(
    dsn="YOUR_SENTRY_DSN",
    integrations=[FlaskIntegration()],
    traces_sample_rate=1.0,
    environment=os.getenv('FLASK_ENV', 'production')
)
```

## Monitoring Dashboard

### Key Metrics to Track
- Request rate (requests/second)
- Response time (p50, p95, p99)
- Error rate (errors/requests)
- Database query time
- Database connection pool usage
- Disk space usage
- Memory usage
- CPU usage
- Failed logins
- Email notification failures

### Alert Thresholds
- Response time > 2 seconds (p95)
- Error rate > 1%
- Database query time > 1 second
- Disk space < 20%
- Failed logins > 10 per hour
- Email failure rate > 5%

## Log Retention Policy
- DEBUG logs: 7 days
- INFO logs: 30 days
- ERROR logs: 90 days
- Database logs: 365 days

## Monitoring Checklist
- [ ] Logging configured with appropriate levels
- [ ] Structured logging implemented
- [ ] Request ID tracking enabled
- [ ] Database query logging enabled
- [ ] Health check endpoint configured
- [ ] Prometheus metrics exposed
- [ ] Grafana dashboards created
- [ ] Alerting rules configured
- [ ] Log rotation configured
- [ ] Error tracking (Sentry) configured
- [ ] Monitoring testing completed
- [ ] Documentation updated
