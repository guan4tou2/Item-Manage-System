"""物品借出服務模組"""
from typing import Any, Dict, List, Optional, Tuple
from datetime import date, datetime

from app.repositories import loan_repo


def lend_item(
    item_id: str,
    item_name: str,
    borrower: str,
    lent_date: Any,
    expected_return: Any = None,
    notes: Optional[str] = None,
    lent_by: str = "",
) -> Tuple[bool, str, Any]:
    """建立借出記錄

    Returns:
        (success, message, loan_id)
    """
    if not item_id or not borrower:
        return False, "物品 ID 與借用人不可為空", None

    # 轉換日期
    if isinstance(lent_date, str):
        try:
            lent_date = datetime.strptime(lent_date, "%Y-%m-%d").date()
        except ValueError:
            return False, "借出日期格式錯誤", None
    if not lent_date:
        lent_date = date.today()

    if isinstance(expected_return, str) and expected_return:
        try:
            expected_return = datetime.strptime(expected_return, "%Y-%m-%d").date()
        except ValueError:
            expected_return = None
    elif not expected_return:
        expected_return = None

    data = {
        "item_id": item_id,
        "item_name": item_name,
        "borrower": borrower.strip(),
        "lent_date": lent_date,
        "expected_return": expected_return,
        "notes": notes,
        "lent_by": lent_by,
    }

    loan_id = loan_repo.create_loan(data)
    return True, "借出記錄已建立", loan_id


def return_item(loan_id: int) -> Tuple[bool, str]:
    """標記物品已歸還"""
    success = loan_repo.return_loan(loan_id)
    if success:
        return True, "已標記為歸還"
    return False, "找不到借出記錄"


def get_item_loans(item_id: str) -> List[Dict[str, Any]]:
    """取得指定物品的借出記錄"""
    return loan_repo.get_loans_by_item(item_id)


def get_active_loans() -> List[Dict[str, Any]]:
    """取得所有進行中的借出，並自動標記逾期"""
    loan_repo.mark_overdue_loans()
    return loan_repo.get_active_loans()


def get_overdue_count() -> int:
    """取得逾期借出數量"""
    return len(loan_repo.get_overdue_loans())


def get_overdue_loans() -> List[Dict[str, Any]]:
    """取得所有逾期借出（expected_return < today 且 status='active'）"""
    try:
        loan_repo.mark_overdue_loans()
        return loan_repo.get_overdue_loans()
    except Exception:
        return []


def check_and_notify_overdue() -> None:
    """檢查並記錄逾期借出（供排程器每日呼叫）。

    目前實作：標記逾期並印出摘要。若系統已整合 Email，可在此擴充發送通知。
    """
    try:
        updated = loan_repo.mark_overdue_loans()
        overdue = loan_repo.get_overdue_loans()
        if overdue:
            print(f"⚠️  逾期借出提醒：共 {len(overdue)} 筆逾期，本次標記 {updated} 筆")
            for loan in overdue:
                print(f"   - {loan.get('item_name')} 借給 {loan.get('borrower')}，預計歸還 {loan.get('expected_return')}")
    except Exception as e:
        print(f"❌ 逾期借出檢查失敗: {e}")
