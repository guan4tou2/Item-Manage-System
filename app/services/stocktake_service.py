"""庫存盤點服務模組"""
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime

from app.repositories import stocktake_repo


def create_session(
    name: str,
    created_by: str,
    notes: Optional[str] = None,
) -> Tuple[bool, str, Any]:
    """建立盤點作業並自動填入現有庫存明細

    Returns:
        (success, message, session_id)
    """
    if not name or not name.strip():
        return False, "盤點名稱不可為空", None

    session_id = stocktake_repo.create_session(
        name=name.strip(),
        created_by=created_by,
        notes=notes,
    )
    stocktake_repo.populate_session(session_id)
    return True, "盤點作業已建立", session_id


def start_session(session_id: Any) -> Tuple[bool, str]:
    """開始盤點（draft → in_progress）"""
    sess = stocktake_repo.get_session(session_id)
    if not sess:
        return False, "找不到盤點作業"
    if sess["status"] != "draft":
        return False, f"目前狀態 {sess['status']} 無法開始盤點"
    ok = stocktake_repo.update_session_status(session_id, "in_progress")
    if ok:
        return True, "盤點作業已開始"
    return False, "狀態更新失敗"


def record_count(
    session_id: Any,
    item_id: str,
    actual_qty: Any,
    counted_by: str,
) -> Tuple[bool, str]:
    """記錄實際盤點數量"""
    sess = stocktake_repo.get_session(session_id)
    if not sess:
        return False, "找不到盤點作業"
    if sess["status"] not in ("in_progress",):
        return False, "盤點作業不在進行中狀態"

    try:
        qty = int(actual_qty)
        if qty < 0:
            return False, "數量不可為負數"
    except (TypeError, ValueError):
        return False, "數量格式錯誤"

    ok = stocktake_repo.record_count(
        session_id=session_id,
        item_id=item_id,
        actual_qty=qty,
        counted_by=counted_by,
    )
    if ok:
        return True, "盤點記錄已儲存"
    return False, "找不到對應的盤點明細"


def complete_counting(session_id: Any) -> Tuple[bool, str]:
    """完成盤點（in_progress → review），標記差異"""
    sess = stocktake_repo.get_session(session_id)
    if not sess:
        return False, "找不到盤點作業"
    if sess["status"] != "in_progress":
        return False, f"目前狀態 {sess['status']} 無法完成盤點"
    stocktake_repo.mark_discrepancies(session_id)
    ok = stocktake_repo.update_session_status(session_id, "review")
    if ok:
        return True, "盤點已完成，請審核差異"
    return False, "狀態更新失敗"


def commit_session(session_id: Any) -> Tuple[bool, str]:
    """提交盤點（review → committed），將實際數量寫回庫存"""
    sess = stocktake_repo.get_session(session_id)
    if not sess:
        return False, "找不到盤點作業"
    if sess["status"] != "review":
        return False, f"目前狀態 {sess['status']} 無法提交"
    updated = stocktake_repo.apply_counts_to_inventory(session_id)
    now = datetime.utcnow()
    ok = stocktake_repo.update_session_status(session_id, "committed", committed_at=now)
    if ok:
        return True, f"盤點已提交，共更新 {updated} 筆庫存數量"
    return False, "狀態更新失敗"


def get_session_detail(session_id: Any) -> Optional[Dict]:
    """取得盤點作業完整資訊（含明細與摘要）"""
    sess = stocktake_repo.get_session(session_id)
    if not sess:
        return None
    sess["summary"] = stocktake_repo.get_session_summary(session_id)
    return sess


def list_sessions() -> List[Dict]:
    """取得所有盤點作業列表"""
    return stocktake_repo.list_sessions()
