import os
import sys
from pathlib import Path

# Add app to path
sys.path.append(os.getcwd())

from app import create_app, mongo
from app.services import user_service, item_service
from app.utils import storage

def test_resource_cleanup():
    print("\n--- Testing Resource Cleanup ---")
    app = create_app()
    with app.app_context():
        # 1. Create a dummy file
        filename = "test_cleanup.jpg"
        filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
        Path(filepath).touch()
        print(f"Created dummy file: {filepath}")
        
        # 2. Test deletion utility
        success = storage.delete_file(filename)
        print(f"Delete file utility success: {success}")
        if not os.path.exists(filepath):
            print("✅ File successfully deleted from disk.")
        else:
            print("❌ File still exists on disk.")

def test_validation_hardening():
    print("\n--- Testing Validation Hardening ---")
    app = create_app()
    with app.app_context():
        # 1. Test short password
        ok, msg = user_service.validate_new_password("123456")
        print(f"Short password (123456): {ok}, {msg}")
        
        # 2. Test password without letters
        ok, msg = user_service.validate_new_password("12345678")
        print(f"No letters password (12345678): {ok}, {msg}")
        
        # 3. Test valid password
        ok, msg = user_service.validate_new_password("Admin123")
        print(f"Valid password (Admin123): {ok}, {msg}")
        
        # 4. Test case-insensitive username
        # Assuming 'admin' exists from _ensure_default_admin
        exists = user_service.get_user("admin")
        print(f"Admin exists: {bool(exists)}")
        
        # Try to create 'Admin'
        # This will use the new check in create_user
        created = user_service.create_user("Admin", "AnotherPass123")
        print(f"Creating 'Admin' (conflict with 'admin'): {created}")
        if not created:
            print("✅ Case-insensitive username conflict detected.")
        else:
            print("❌ Case-insensitive username conflict NOT detected.")

def test_security_logging():
    print("\n--- Testing Security Logging ---")
    app = create_app()
    with app.app_context():
        # Clear logs first? Or just look for the latest
        # Try to trigger a lockout (simulated or real call)
        user_service.authenticate("admin", "WrongPass")
        user_service.authenticate("admin", "WrongPass")
        user_service.authenticate("admin", "WrongPass")
        user_service.authenticate("admin", "WrongPass")
        user_service.authenticate("admin", "WrongPass")
        user_service.authenticate("admin", "WrongPass") # Should lock
        
        from app.services import log_service
        logs = log_service.get_recent_logs(limit=5)
        print("Recent logs:")
        for log in logs:
            print(f"- {log.get('action')}: {log.get('details', {}).get('message')}")
        
        if any(log.get('action') == 'security' for log in logs):
            print("✅ Security event logged.")
        else:
            print("❌ Security event NOT found in logs.")

if __name__ == "__main__":
    if not os.path.exists("venv"):
        print("Please run in venv")
        sys.exit(1)
    
    test_resource_cleanup()
    test_validation_hardening()
    test_security_logging()
