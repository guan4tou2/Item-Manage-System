"""群組服務模組"""
from typing import Any, Dict, List, Optional, Tuple

from app.repositories import group_repo


def create_group(name: str, owner: str) -> Tuple[bool, str, Any]:
    """建立群組，擁有者自動成為 admin 成員。回傳 (success, message, group_id)"""
    name = name.strip()
    if not name:
        return False, "群組名稱不可為空", None

    group_id = group_repo.create_group(name, owner)
    # 擁有者自動加入為 admin
    group_repo.add_member(group_id, owner, role="admin")
    return True, "群組建立成功", group_id


def get_user_groups(username: str) -> List[Dict[str, Any]]:
    """取得使用者所有群組"""
    return group_repo.list_user_groups(username)


def invite_member(
    group_id: int,
    username: str,
    role: str,
    inviter: str,
) -> Tuple[bool, str]:
    """邀請成員加入群組"""
    username = username.strip()
    if not username:
        return False, "使用者名稱不可為空"

    valid_roles = {"admin", "member", "viewer"}
    if role not in valid_roles:
        role = "member"

    # 檢查邀請者是否有管理員權限
    members = group_repo.get_group_members(group_id)
    inviter_member = next((m for m in members if m["username"] == inviter), None)
    group = group_repo.get_group(group_id)
    is_owner = group and group.get("owner") == inviter
    is_admin = inviter_member and inviter_member.get("role") == "admin"

    if not is_owner and not is_admin:
        return False, "只有管理員可以邀請成員"

    # 檢查是否已為成員
    if group_repo.is_member(group_id, username):
        return False, f"{username} 已是群組成員"

    group_repo.add_member(group_id, username, role)
    return True, f"已成功邀請 {username} 加入群組"


def remove_member(
    group_id: int,
    username: str,
    remover: str,
) -> Tuple[bool, str]:
    """從群組移除成員"""
    group = group_repo.get_group(group_id)
    if not group:
        return False, "群組不存在"

    # 擁有者不可被移除
    if group.get("owner") == username:
        return False, "無法移除群組擁有者"

    # 只有擁有者或 admin 可移除成員
    members = group_repo.get_group_members(group_id)
    remover_member = next((m for m in members if m["username"] == remover), None)
    is_owner = group.get("owner") == remover
    is_admin = remover_member and remover_member.get("role") == "admin"

    if not is_owner and not is_admin:
        return False, "只有管理員可以移除成員"

    success = group_repo.remove_member(group_id, username)
    if success:
        return True, f"已移除成員 {username}"
    return False, f"找不到成員 {username}"


def get_user_group_member_ids(username: str) -> set:
    """回傳與 username 同群組的所有成員 username 集合（含自身）"""
    return group_repo.get_user_group_member_ids(username)


def get_group_detail(group_id: int) -> Optional[Dict[str, Any]]:
    """取得群組詳細資訊，包含成員列表"""
    group = group_repo.get_group(group_id)
    if not group:
        return None
    members = group_repo.get_group_members(group_id)
    group["members"] = members
    group["member_count"] = len(members)
    return group
