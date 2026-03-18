"""物品借出藍圖路由"""
from flask import Blueprint, render_template, request, jsonify, session

from app.services import loan_service
from app.repositories import loan_repo
from app.utils.auth import login_required, admin_required, get_current_user

bp = Blueprint("loans", __name__)


@bp.route("/loans")
@login_required
def loan_list():
    """借出管理頁面"""
    user = get_current_user()
    active_loans = loan_service.get_active_loans()
    overdue_count = loan_service.get_overdue_count()
    active_count = loan_repo.count_active_loans()
    return render_template(
        "loans.html",
        User=user,
        active_loans=active_loans,
        active_count=active_count,
        overdue_count=overdue_count,
    )


@bp.route("/api/loans/lend", methods=["POST"])
@admin_required
def api_lend():
    """API: 建立借出記錄"""
    data = request.get_json() or {}
    user = get_current_user()
    lent_by = user.get("User", "")

    item_id = str(data.get("item_id", "")).strip()
    item_name = str(data.get("item_name", "")).strip()
    borrower = str(data.get("borrower", "")).strip()
    borrower_contact = data.get("borrower_contact", "")
    lent_date = data.get("lent_date", "")
    expected_return = data.get("expected_return", "")
    notes = data.get("notes", "")

    if not item_id or not borrower:
        return jsonify({"success": False, "message": "物品 ID 與借用人不可為空"}), 400

    # Pass borrower_contact via notes if present (stored in data dict passed to service)
    ok, msg, loan_id = loan_service.lend_item(
        item_id=item_id,
        item_name=item_name,
        borrower=borrower,
        lent_date=lent_date,
        expected_return=expected_return,
        notes=notes or None,
        lent_by=lent_by,
    )

    if ok:
        return jsonify({"success": True, "message": msg, "loan_id": loan_id})
    return jsonify({"success": False, "message": msg}), 400


@bp.route("/api/loans/return/<int:loan_id>", methods=["POST"])
@admin_required
def api_return_loan(loan_id: int):
    """API: 標記物品已歸還"""
    ok, msg = loan_service.return_item(loan_id)
    if ok:
        return jsonify({"success": True, "message": msg})
    return jsonify({"success": False, "message": msg}), 404


@bp.route("/api/loans/item/<item_id>")
@login_required
def api_item_loans(item_id: str):
    """API: 取得物品的借出記錄"""
    loans = loan_service.get_item_loans(item_id)
    return jsonify(loans)
