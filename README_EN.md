# 🏠 Item Management System

A comprehensive item management system with expiration tracking, email notifications, Docker deployment, and support for both PostgreSQL and MongoDB.

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Python](https://img.shields.io/badge/python-3.13+-green.svg)
![Flask](https://img.shields.io/badge/flask-3.1+-lightgrey.svg)

## ✨ Core Features

- 📸 **Item Management** - Add, edit, delete items
- 📍 **Location Tracking** - Floor/Room/Zone hierarchical recording
- 📧 **Photo Management** - Support for item photos
- 🔍 **Smart Search** - Fuzzy search, multi-condition filtering
- 🏷️ **Item Categorization** - Custom item types
- 📊 **Statistics Reports** - Detailed data statistics
- 📦 **QR/Barcode** - Generate labels, camera scanning
- 🍎 **Expiration Tracking** - Food, supplies validity tracking
- 🛡 **Warranty Management** - Product warranty period management
- 🔔 **Email Notifications** - Automated expiration reminders
- 📋 **Bulk Operations** - Batch delete, move items
- ⭐ **Favorites** - Quick access to frequently used items
- 📱 **PWA Support** - Install as mobile app

## 🚀 Quick Start

### Method 1: Docker Deployment (Easiest)

```bash
# 1. Clone the repository
git clone <repository-url>
cd Item-Manage-System

# 2. Start services
docker compose up --build

# 3. Access the system
# Browser: http://localhost:8080
# Default account: admin / admin
```

### Method 2: Local Development

```bash
# 1. Create virtual environment
uv venv .venv
source .venv/bin/activate

# 2. Install dependencies
uv pip install -r requirements.txt

# 3. Configure environment
cp .env.example .env
# Edit .env to configure database connection

# 4. Run the application
python run.py
```

## 📖 Complete Documentation

### Quick Navigation

- 📘 [Complete Guide (Chinese)](GUIDE_ZH-TW.md) - Recommended for new users
- 🇺🇸 [Complete Guide (English)](GUIDE_EN.md) - English version

### Detailed Documentation

| Documentation | Description |
|---------------|-------------|
| [Installation Guide](GUIDE_EN.md#installation-guide) | Detailed installation steps |
| [Quick Start](GUIDE_EN.md#quick-start) | Get started in 5 minutes |
| [User Tutorial](GUIDE_EN.md#user-tutorial) | Detailed feature usage |
| [Notification System](GUIDE_EN.md#notification-system) | Expiration notification setup |
| [Docker Deployment](GUIDE_EN.md#docker-deployment) | Containerized deployment guide |
| [API Documentation](GUIDE_EN.md#api-documentation) | API interface documentation |
| [FAQ](GUIDE_EN.md#faq) | Troubleshooting solutions |

### Other Documentation

- [Deployment Guide](Deployment_Guide_zh-TW.md) - Production environment deployment
- [User Manual](User_Manual_zh-TW.md) - Detailed user manual
- [Feature List](FEATURES.md) - Complete feature list
- [Testing Documentation](TESTING.md) - Testing instructions
- [Docker Guide](DOCKER_POSTGRES_GUIDE.md) - Docker and PostgreSQL configuration

## 🛠️ Tech Stack

### Backend

- **Flask 3.1+** - Web framework
- **SQLAlchemy 2.0+** - ORM (PostgreSQL)
- **PyMongo** - MongoDB driver
- **APScheduler 3.11+** - Scheduled tasks
- **Flask-Mail** - Email sending
- **Flask-Login** - Authentication
- **Flask-WTF** - Form validation
- **Flask-Limiter** - Rate limiting

### Frontend

- **Bootstrap 5** - UI framework
- **Font Awesome** - Icon library
- **JavaScript** - Interactive features
- **PWA** - Progressive Web App

### Database

- **PostgreSQL 16+** - Primary database (recommended)
- **MongoDB 7+** - Legacy support

### Dev Tools

- **Python 3.13+**
- **Docker & Docker Compose**
- **Git**

## 📁 Project Structure

```
Item-Manage-System/
├── app/                      # Application core
│   ├── __init__.py           # App initialization
│   ├── models/               # SQLAlchemy models
│   │   ├── user.py
│   │   ├── item.py
│   │   ├── item_type.py
│   │   └── log.py
│   ├── repositories/          # Database access layer
│   │   ├── user_repo.py
│   │   ├── item_repo.py
│   │   ├── type_repo.py
│   │   ├── location_repo.py
│   │   └── log_repo.py
│   ├── services/             # Business logic layer
│   │   ├── notification_service.py
│   │   ├── email_service.py
│   │   ├── item_service.py
│   │   └── log_service.py
│   ├── routes/               # API routes
│   │   ├── auth/
│   │   ├── items/
│   │   ├── types/
│   │   ├── locations/
│   │   └── notifications/
│   ├── utils/                # Utility modules
│   │   ├── storage.py
│   │   ├── image.py
│   │   ├── auth.py
│   │   └── scheduler.py
│   └── validators/           # Form validation
├── templates/                 # HTML templates
├── static/                   # Static resources
│   ├── css/
│   ├── js/
│   ├── uploads/              # Upload files
│   └── brand/
├── tests/                    # Test cases
├── scripts/                  # Utility scripts
├── docker-compose.yml          # Docker compose
├── Dockerfile               # Docker image
├── requirements.txt          # Python dependencies
├── .env.example            # Environment variables example
└── docs/                   # Documentation directory
```

## 🔧 Environment Configuration

### Database Configuration

```bash
# Use PostgreSQL (recommended)
export DB_TYPE=postgres
export DATABASE_URL=postgresql://user:password@localhost:5432/itemman

# Or use MongoDB
export DB_TYPE=mongo
export MONGO_URI=mongodb://localhost:27017/myDB
```

### Email Notification Configuration

```bash
export MAIL_SERVER=smtp.gmail.com
export MAIL_PORT=587
export MAIL_USE_TLS=true
export MAIL_USERNAME=your-email@gmail.com
export MAIL_PASSWORD=your-app-password
export MAIL_DEFAULT_SENDER=your-email@gmail.com
```

For complete configuration, see [`.env.example`](.env.example)

## 🧪 Testing

```bash
# Run all tests
python run_tests.py

# Test notification functionality
python test_notifications.py

# Test login
python test_login.py

# Test system
python test_system.py
```

## 📱 PWA Installation

The system supports PWA and can be installed as a mobile app:

1. Access the system on your mobile browser
2. Tap browser menu "Add to Home Screen"
3. Confirm installation

## 🚀 Production Deployment

### Recommended Configuration

1. **Use PostgreSQL** - Better performance and reliability
2. **Configure HTTPS** - Secure communication
3. **Use Nginx** - Reverse proxy and static file serving
4. **Regular Backups** - Database and upload files
5. **Monitor Logs** - Early problem detection

For detailed deployment guide, see [Deployment_Guide_zh-TW.md](Deployment_Guide_zh-TW.md)

## 🐛 Troubleshooting

### Common Issues

| Issue | Solution |
|-------|----------|
| Docker port in use | Modify port mapping in `docker-compose.yml` |
| Cannot connect to database | Check database container status and connection string |
| Email notifications not sent | Check SMTP configuration and spam folder |
| Photo upload failed | Check file size (<16MB) and format |
| Performance issues | Use PostgreSQL, add database indexes |

For more solutions, see [GUIDE_EN.md#faq](GUIDE_EN.md#faq)

## 🤝 Contributing

Contributions are welcome!

### Development Workflow

1. Fork this repository
2. Create feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to branch (`git push origin feature/AmazingFeature`)
5. Open Pull Request

### Code Standards

- Follow PEP 8 code style
- Add appropriate documentation and comments
- Write test cases
- Ensure all tests pass

## 📄 License

MIT License - See [LICENSE](LICENSE) file for details

## 🙏 Acknowledgments

- Flask Team
- Bootstrap Team
- All Contributors

---

**Thank you for using Item Management System!** 🎉

For questions or suggestions, please:
- Submit [GitHub Issue](../../issues)
- Send [Email](mailto:support@example.com)
