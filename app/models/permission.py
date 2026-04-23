"""
Permission Model - Role-Based Access Control (RBAC)
=================================================
"""

from enum import Enum
from functools import wraps
from flask import abort
from flask_login import current_user


class Role(Enum):
    """User roles"""
    ADMIN = 'admin'      # 系統管理員
    EDITOR = 'editor'    # 可編輯
    VIEWER = 'viewer'    # 僅檢視


class Permission(Enum):
    """System permissions"""
    # Item permissions
    ITEM_CREATE = 'item:create'
    ITEM_EDIT = 'item:edit'
    ITEM_DELETE = 'item:delete'
    ITEM_VIEW = 'item:view'
    
    # Location permissions
    LOCATION_CREATE = 'location:create'
    LOCATION_EDIT = 'location:edit'
    LOCATION_DELETE = 'location:delete'
    
    # Type permissions
    TYPE_CREATE = 'type:create'
    TYPE_EDIT = 'type:edit'
    TYPE_DELETE = 'type:delete'
    
    # User permissions
    USER_CREATE = 'user:create'
    USER_EDIT = 'user:edit'
    USER_DELETE = 'user:delete'
    USER_VIEW = 'user:view'
    
    # System permissions
    BACKUP = 'system:backup'
    SETTINGS = 'system:settings'
    EXPORT = 'system:export'
    IMPORT = 'system:import'


# Role-Permission mapping
ROLE_PERMISSIONS = {
    Role.ADMIN: list(Permission),  # All permissions
    Role.EDITOR: [
        Permission.ITEM_CREATE,
        Permission.ITEM_EDIT,
        Permission.ITEM_VIEW,
        Permission.LOCATION_CREATE,
        Permission.LOCATION_EDIT,
        Permission.TYPE_CREATE,
        Permission.TYPE_EDIT,
        Permission.EXPORT,
        Permission.IMPORT,
    ],
    Role.VIEWER: [
        Permission.ITEM_VIEW,
    ],
}


def get_user_role(user) -> Role:
    """Get user's role"""
    if not user or not user.is_authenticated:
        return Role.VIEWER
    
    if user.admin:
        return Role.ADMIN
    
    # Check for editor role (custom field or attribute)
    if getattr(user, 'role', None) == 'editor':
        return Role.EDITOR
    
    return Role.VIEWER


def has_permission(user, permission: Permission) -> bool:
    """Check if user has specific permission"""
    if not user or not user.is_authenticated:
        return False
    
    role = get_user_role(user)
    role_perms = ROLE_PERMISSIONS.get(role, [])
    
    return permission in role_perms


def has_any_permission(user, permissions: list) -> bool:
    """Check if user has any of the permissions"""
    return any(has_permission(user, p) for p in permissions)


def has_all_permissions(user, permissions: list) -> bool:
    """Check if user has all permissions"""
    return all(has_permission(user, p) for p in permissions)


def require_permission(permission: Permission):
    """Decorator to require permission for route"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                abort(401)
            
            if not has_permission(current_user, permission):
                abort(403)
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def require_role(role: Role):
    """Decorator to require role for route"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                abort(401)
            
            if get_user_role(current_user) != role:
                abort(403)
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator


# Permission check functions for templates
def can_create_items():
    """Check if current user can create items"""
    return current_user.is_authenticated and has_permission(
        current_user, Permission.ITEM_CREATE
    )


def can_edit_items():
    """Check if current user can edit items"""
    return current_user.is_authenticated and has_permission(
        current_user, Permission.ITEM_EDIT
    )


def can_delete_items():
    """Check if current user can delete items"""
    return current_user.is_authenticated and has_permission(
        current_user, Permission.ITEM_DELETE
    )


def can_manage_users():
    """Check if current user can manage users"""
    return current_user.is_authenticated and has_permission(
        current_user, Permission.USER_EDIT
    )


def can_manage_system():
    """Check if current user can manage system"""
    return current_user.is_authenticated and has_permission(
        current_user, Permission.SETTINGS
    )