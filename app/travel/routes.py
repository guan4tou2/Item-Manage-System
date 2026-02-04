from datetime import datetime
from io import StringIO
import csv
import uuid

from flask import Blueprint, jsonify, request, Response, redirect, url_for, session, render_template, flash, abort

from app import db, csrf
from app.models import Travel, TravelGroup, TravelItem, ShoppingList, ShoppingItem

bp = Blueprint("travel", __name__, url_prefix="/travel")
shopping_bp = Blueprint("shopping", __name__, url_prefix="/shopping")



def _require_auth():
    if "UserID" not in session:
        return False, redirect(url_for("auth.signin"))
    return True, None


def _get_travel_or_403(travel_id: int):
    travel = Travel.query.get_or_404(travel_id)
    if travel.owner and travel.owner != session.get("UserID"):
        abort(403)
    return travel


@bp.route("/", methods=["GET"])
def list_page():
    ok, redirect_resp = _require_auth()
    if not ok:
        return redirect_resp
    owner = session.get("UserID")
    travels = Travel.query.filter((Travel.owner == owner) | (Travel.owner.is_(None))).all()
    items_counts = {t.id: TravelItem.query.filter_by(travel_id=t.id).count() for t in travels}
    for t in travels:
        t.item_count = items_counts.get(t.id, 0)
    return render_template("travel.html", travels=travels, User={"name": owner, "admin": False})


@bp.route("/create", methods=["POST"])
@csrf.exempt
def create_travel_form():
    ok, redirect_resp = _require_auth()
    if not ok:
        return redirect_resp
    name = request.form.get("name")
    if not name:
        return redirect(url_for("travel.list_page"))
    travel = Travel(
        name=name,
        owner=session.get("UserID"),
        start_date=request.form.get("start_date") or None,
        end_date=request.form.get("end_date") or None,
        note=request.form.get("note"),
    )
    db.session.add(travel)
    db.session.flush()
    default_group_name = request.form.get("default_group") or "未分組"
    db.session.add(TravelGroup(travel_id=travel.id, name=default_group_name, sort_order=0))
    db.session.commit()
    return redirect(url_for("travel.detail", travel_id=travel.id))


@bp.route("/<int:travel_id>", methods=["GET"])
def detail(travel_id: int):
    ok, redirect_resp = _require_auth()
    if not ok:
        return redirect_resp
    travel = _get_travel_or_403(travel_id)
    groups = TravelGroup.query.filter_by(travel_id=travel_id).order_by(TravelGroup.sort_order).all()
    items = TravelItem.query.filter_by(travel_id=travel_id).all()
    shopping = ShoppingList.query.filter_by(travel_id=travel_id, list_type="travel").first()
    if not shopping:
        shopping = ShoppingList(
            travel_id=travel_id,
            list_type="travel",
            title=f"購買清單-{travel.name}",
            owner=session.get("UserID"),
        )
        db.session.add(shopping)
        db.session.commit()
    shopping_items = ShoppingItem.query.filter_by(list_id=shopping.id).all()
    return render_template(
        "travel_detail.html",
        travel=travel,
        groups=groups,
        items=items,
        shopping=shopping,
        shopping_items=shopping_items,
        User={"name": session.get("UserID"), "admin": False},
    )


@bp.route("/<int:travel_id>/group", methods=["POST"])
@csrf.exempt
def add_group_form(travel_id: int):
    ok, redirect_resp = _require_auth()
    if not ok:
        return redirect_resp
    _get_travel_or_403(travel_id)
    name = request.form.get("name") or "未命名"
    sort_order = int(request.form.get("sort_order", 0))
    db.session.add(TravelGroup(travel_id=travel_id, name=name, sort_order=sort_order))
    db.session.commit()
    return redirect(url_for("travel.detail", travel_id=travel_id))


@bp.route("/<int:travel_id>/item", methods=["POST"])
@csrf.exempt
def add_item_form(travel_id: int):
    ok, redirect_resp = _require_auth()
    if not ok:
        return redirect_resp
    _get_travel_or_403(travel_id)
    name = request.form.get("name")
    if not name:
        flash("請輸入物品名稱", "warning")
        return redirect(url_for("travel.detail", travel_id=travel_id))
    item = TravelItem(
        travel_id=travel_id,
        group_id=request.form.get("group_id") or None,
        source_type=request.form.get("source_type", "temp"),
        source_ref=request.form.get("source_ref") or None,
        name=name,
        qty_required=int(request.form.get("qty_required", 1)),
        qty_packed=int(request.form.get("qty_packed", 0)),
        carried=bool(request.form.get("carried")),
        note=request.form.get("note"),
        is_temp=True,
    )
    db.session.add(item)
    db.session.commit()
    return redirect(url_for("travel.detail", travel_id=travel_id))


@bp.route("/<int:travel_id>/items/<int:item_id>/update", methods=["POST"])
@csrf.exempt
def update_item_form(travel_id: int, item_id: int):
    ok, redirect_resp = _require_auth()
    if not ok:
        return redirect_resp
    _get_travel_or_403(travel_id)
    item = TravelItem.query.get_or_404(item_id)
    if item.travel_id != travel_id:
        abort(404)
    if "toggle_carried" in request.form:
        item.carried = not item.carried
    if "qty_packed" in request.form:
        item.qty_packed = int(request.form.get("qty_packed", item.qty_packed))
    if "qty_required" in request.form:
        item.qty_required = int(request.form.get("qty_required", item.qty_required))
    db.session.commit()
    return redirect(url_for("travel.detail", travel_id=travel_id))


@bp.route("/<int:travel_id>/items/<int:item_id>/delete", methods=["POST"])
@csrf.exempt
def delete_item_form(travel_id: int, item_id: int):
    ok, redirect_resp = _require_auth()
    if not ok:
        return redirect_resp
    _get_travel_or_403(travel_id)
    item = TravelItem.query.get_or_404(item_id)
    if item.travel_id != travel_id:
        abort(404)
    db.session.delete(item)
    db.session.commit()
    return redirect(url_for("travel.detail", travel_id=travel_id))


def _serialize_travel(travel: Travel):
    return {
        "id": travel.id,
        "name": travel.name,
        "owner": travel.owner,
        "start_date": travel.start_date.isoformat() if travel.start_date else None,
        "end_date": travel.end_date.isoformat() if travel.end_date else None,
        "note": travel.note,
        "shared": travel.shared or {},
        "groups": [
            {"id": g.id, "name": g.name, "sort_order": g.sort_order}
            for g in sorted(travel.groups, key=lambda x: x.sort_order)
        ],
    }


def _serialize_travel_item(item: TravelItem):
    return {
        "id": item.id,
        "travel_id": item.travel_id,
        "group_id": item.group_id,
        "source_type": item.source_type,
        "source_ref": item.source_ref,
        "name": item.name,
        "qty_required": item.qty_required,
        "qty_packed": item.qty_packed,
        "carried": item.carried,
        "note": item.note,
        "size_notes": item.size_notes or {},
        "is_temp": item.is_temp,
    }


@bp.route("/api", methods=["GET"])
def list_travels():
    ok, redirect_resp = _require_auth()
    if not ok:
        return redirect_resp
    owner = session.get("UserID")
    travels = Travel.query.filter((Travel.owner == owner) | (Travel.owner.is_(None))).all()
    return jsonify({"items": [_serialize_travel(t) for t in travels]})


@bp.route("/api", methods=["POST"])
@csrf.exempt
def create_travel():
    ok, redirect_resp = _require_auth()
    if not ok:
        return redirect_resp
    data = request.get_json(force=True) or {}
    name = data.get("name")
    if not name:
        return jsonify({"error": "name_required"}), 400
    travel = Travel(
        name=name,
        owner=session.get("UserID"),
        start_date=data.get("start_date"),
        end_date=data.get("end_date"),
        note=data.get("note"),
    )
    db.session.add(travel)
    db.session.flush()
    default_group = TravelGroup(travel_id=travel.id, name=data.get("default_group", "未分組"), sort_order=0)
    db.session.add(default_group)
    db.session.commit()
    return jsonify({"success": True, "travel": _serialize_travel(travel)})


@bp.route("/api/<int:travel_id>/groups", methods=["POST"])
@csrf.exempt
def create_group(travel_id: int):
    ok, redirect_resp = _require_auth()
    if not ok:
        return redirect_resp
    data = request.get_json(force=True) or {}
    name = data.get("name")
    if not name:
        return jsonify({"error": "name_required"}), 400
    sort_order = int(data.get("sort_order", 0))
    group = TravelGroup(travel_id=travel_id, name=name, sort_order=sort_order)
    db.session.add(group)
    db.session.commit()
    return jsonify({"success": True, "group": {"id": group.id, "name": group.name, "sort_order": group.sort_order}})


@bp.route("/api/<int:travel_id>/items", methods=["GET"])
def list_items(travel_id: int):
    ok, redirect_resp = _require_auth()
    if not ok:
        return redirect_resp
    items = TravelItem.query.filter_by(travel_id=travel_id).all()
    return jsonify({"items": [_serialize_travel_item(i) for i in items]})


@bp.route("/api/<int:travel_id>/items", methods=["POST"])
@csrf.exempt
def add_item(travel_id: int):
    ok, redirect_resp = _require_auth()
    if not ok:
        return redirect_resp
    data = request.get_json(force=True) or {}
    name = data.get("name")
    if not name:
        return jsonify({"error": "name_required"}), 400
    item = TravelItem(
        travel_id=travel_id,
        group_id=data.get("group_id"),
        source_type=data.get("source_type", "temp"),
        source_ref=data.get("source_ref"),
        name=name,
        qty_required=int(data.get("qty_required", 1)),
        qty_packed=int(data.get("qty_packed", 0)),
        carried=bool(data.get("carried", False)),
        note=data.get("note"),
        size_notes=data.get("size_notes") or {},
        is_temp=bool(data.get("is_temp", data.get("source_type", "temp") == "temp")),
    )
    db.session.add(item)
    db.session.commit()
    return jsonify({"success": True, "item": _serialize_travel_item(item)})


@bp.route("/api/items/<int:item_id>", methods=["PATCH"])
@csrf.exempt
def update_item(item_id: int):
    ok, redirect_resp = _require_auth()
    if not ok:
        return redirect_resp
    data = request.get_json(force=True) or {}
    item = TravelItem.query.get_or_404(item_id)
    if "qty_packed" in data:
        item.qty_packed = int(data.get("qty_packed", item.qty_packed))
    if "qty_required" in data:
        item.qty_required = int(data.get("qty_required", item.qty_required))
    if "carried" in data:
        item.carried = bool(data.get("carried"))
    if "note" in data:
        item.note = data.get("note")
    if "size_notes" in data:
        item.size_notes = data.get("size_notes") or {}
    db.session.commit()
    return jsonify({"success": True, "item": _serialize_travel_item(item)})


@bp.route("/api/<int:travel_id>/export", methods=["GET"])
def export_travel(travel_id: int):
    ok, redirect_resp = _require_auth()
    if not ok:
        return redirect_resp
    items = TravelItem.query.filter_by(travel_id=travel_id).all()
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(["name", "group_id", "qty_required", "qty_packed", "carried", "note"])
    for i in items:
        writer.writerow([
            i.name,
            i.group_id or "",
            i.qty_required,
            i.qty_packed,
            "yes" if i.carried else "no",
            i.note or "",
        ])
    csv_data = output.getvalue()
    return Response(csv_data, mimetype="text/csv", headers={"Content-Disposition": f"attachment; filename=travel_{travel_id}.csv"})


@bp.route("/api/<int:travel_id>/reminder", methods=["GET"])
def travel_reminder(travel_id: int):
    ok, redirect_resp = _require_auth()
    if not ok:
        return redirect_resp
    items = TravelItem.query.filter_by(travel_id=travel_id).all()
    total = len(items)
    pending = sum(1 for i in items if not i.carried or i.qty_packed < i.qty_required)
    return jsonify({"travel_id": travel_id, "pending": pending, "total": total})


@bp.route("/api/<int:travel_id>/export/pdf", methods=["GET"])
def export_travel_pdf(travel_id: int):
    ok, redirect_resp = _require_auth()
    if not ok:
        return redirect_resp
    items = TravelItem.query.filter_by(travel_id=travel_id).all()
    lines = ["旅旅行清單"]
    for i in items:
        lines.append(f"- {i.name} {i.qty_packed}/{i.qty_required} {'✔' if i.carried else '✘'}")
    pdf_like = "\n".join(lines)
    return Response(pdf_like, mimetype="application/pdf", headers={"Content-Disposition": f"attachment; filename=travel_{travel_id}.pdf"})


def _serialize_shopping_item(item: ShoppingItem):
    return {
        "id": item.id,
        "list_id": item.list_id,
        "name": item.name,
        "qty": item.qty,
        "budget": float(item.budget) if item.budget is not None else None,
        "price": float(item.price) if item.price is not None else None,
        "store": item.store,
        "link": item.link,
        "priority": item.priority,
        "note": item.note,
        "size_notes": item.size_notes or {},
        "status": item.status,
    }


def _serialize_shopping_list(lst: ShoppingList):
    return {
        "id": lst.id,
        "title": lst.title,
        "list_type": lst.list_type,
        "travel_id": lst.travel_id,
        "owner": lst.owner,
        "note": lst.note,
        "shared": lst.shared or {},
        "items": [_serialize_shopping_item(i) for i in lst.items],
    }


@shopping_bp.route("/api/lists", methods=["GET"])
def list_lists():
    ok, redirect_resp = _require_auth()
    if not ok:
        return redirect_resp
    owner = session.get("UserID")
    lists = ShoppingList.query.filter((ShoppingList.owner == owner) | (ShoppingList.owner.is_(None))).all()
    return jsonify({"items": [_serialize_shopping_list(l) for l in lists]})


@shopping_bp.route("/api", methods=["POST"])
@csrf.exempt
def create_list():
    ok, redirect_resp = _require_auth()
    if not ok:
        return redirect_resp
    data = request.get_json(force=True) or {}
    title = data.get("title") or "購買清單"
    lst = ShoppingList(
        title=title,
        list_type=data.get("list_type", "general"),
        travel_id=data.get("travel_id"),
        owner=session.get("UserID"),
        note=data.get("note"),
    )
    db.session.add(lst)
    db.session.commit()
    return jsonify({"success": True, "list": _serialize_shopping_list(lst)})


@shopping_bp.route("/api/<int:list_id>/items", methods=["POST"])
@csrf.exempt
def add_shopping_item(list_id: int):
    ok, redirect_resp = _require_auth()
    if not ok:
        return redirect_resp
    lst = ShoppingList.query.get_or_404(list_id)
    if request.is_json:
        data = request.get_json(force=True) or {}
    else:
        data = request.form.to_dict() or {}
    name = data.get("name")
    if not name:
        if request.is_json:
            return jsonify({"error": "name_required"}), 400
        flash("請輸入品名", "warning")
        return redirect(url_for("travel.detail", travel_id=lst.travel_id))
    item = ShoppingItem(
        list_id=list_id,
        name=name,
        qty=int(data.get("qty", 1)),
        budget=data.get("budget"),
        price=data.get("price"),
        store=data.get("store"),
        link=data.get("link"),
        priority=int(data.get("priority", 0)),
        note=data.get("note"),
        size_notes=data.get("size_notes") or {},
        status=data.get("status", "todo"),
    )
    db.session.add(item)
    db.session.commit()
    if request.is_json:
        return jsonify({"success": True, "item": _serialize_shopping_item(item)})
    return redirect(url_for("travel.detail", travel_id=lst.travel_id))


@shopping_bp.route("/api/items/<int:item_id>", methods=["PATCH"])
@csrf.exempt
def update_shopping_item(item_id: int):
    ok, redirect_resp = _require_auth()
    if not ok:
        return redirect_resp
    data = request.get_json(force=True) or {}
    item = ShoppingItem.query.get_or_404(item_id)
    if "qty" in data:
        item.qty = int(data.get("qty", item.qty))
    if "budget" in data:
        item.budget = data.get("budget")
    if "price" in data:
        item.price = data.get("price")
    if "store" in data:
        item.store = data.get("store")
    if "link" in data:
        item.link = data.get("link")
    if "priority" in data:
        item.priority = int(data.get("priority", item.priority))
    if "note" in data:
        item.note = data.get("note")
    if "size_notes" in data:
        item.size_notes = data.get("size_notes") or {}
    if "status" in data:
        item.status = data.get("status", item.status)
    db.session.commit()
    return jsonify({"success": True, "item": _serialize_shopping_item(item)})


@shopping_bp.route("/api/<int:list_id>/export", methods=["GET"])
def export_shopping(list_id: int):
    ok, redirect_resp = _require_auth()
    if not ok:
        return redirect_resp
    items = ShoppingItem.query.filter_by(list_id=list_id).all()
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(["name", "qty", "budget", "price", "store", "priority", "status"])
    for i in items:
        writer.writerow([
            i.name,
            i.qty,
            float(i.budget) if i.budget is not None else "",
            float(i.price) if i.price is not None else "",
            i.store or "",
            i.priority,
            i.status,
        ])
    csv_data = output.getvalue()
    return Response(csv_data, mimetype="text/csv", headers={"Content-Disposition": f"attachment; filename=shopping_{list_id}.csv"})


@shopping_bp.route("/api/<int:list_id>/summary", methods=["GET"])
def shopping_summary(list_id: int):
    ok, redirect_resp = _require_auth()
    if not ok:
        return redirect_resp
    items = ShoppingItem.query.filter_by(list_id=list_id).all()
    todo = sum(1 for i in items if i.status != "done")
    done = sum(1 for i in items if i.status == "done")
    return jsonify({"list_id": list_id, "todo": todo, "done": done, "total": len(items)})
