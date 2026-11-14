"""備份匯入（Phase 29）。

兩段式：`build_plan` 為純讀（dry-run 即零寫入；含驗證／名稱匹配／id-map／對帳），
`apply_plan`（T1.3/T1.4）依 plan 寫入。plan 內先配發 UUID，apply 具決定性。

歧異決策見 `docs/plans/2026-10-17-phase29-backup-restore.md` 盤點定案。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Any, Literal, Optional
from uuid import UUID, uuid4

from pydantic import ValidationError
from sqlalchemy import delete, func, insert, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.category import Category
from app.models.customization import CustomField, ItemCustomValue, ItemTemplate, ItemType
from app.models.group import Group, GroupMember
from app.models.item import Item
from app.models.item_batch import ItemBatch
from app.models.item_history import ItemVersion, QuantityLog
from app.models.list import List as UserList, ListEntry
from app.models.loan import ItemLoan
from app.models.location import Location
from app.models.notification_preference import NotificationPreference
from app.models.stocktake import Stocktake, StocktakeItem
from app.models.tag import Tag, item_tags
from app.models.user import User
from app.models.warehouse import Warehouse
from app.models.webhook import Webhook, WebhookDelivery
from app.schemas.backup import (
    BackupImportEntitySummary,
    BackupImportError,
    BackupImportResult,
    BackupReconciliationItem,
)
from app.schemas.location import PlanRegion
from app.schemas.preferences import currency_from_raw
from app.services import audit_service
from app.services.backup_service import FORMAT_VERSION

#: 上傳大小上限（nginx `client_max_body_size 32m` 之下）
MAX_BACKUP_BYTES = 20 * 1024 * 1024
#: replace 非 dry-run 的確認字串（UI 與 API 雙重防誤用）
CONFIRM_PHRASE = "REPLACE"
#: 回應中列出的錯誤上限（`errors_total` 仍為總數）
MAX_ERRORS = 100

ENTITY_KEYS: tuple[str, ...] = (
    "items",
    "categories",
    "locations",
    "tags",
    "warehouses",
    "item_types",
    "custom_fields",
    "item_templates",
    "item_custom_values",
    "item_batches",
    "loans",
    "quantity_logs",
    "item_versions",
    "lists",
    "stocktakes",
    "webhooks",
    "notification_preferences",
    "groups_owned",
    "preferences",
)

STOCKTAKE_STATUSES = ("open", "completed", "cancelled")


class BackupFormatError(Exception):
    """檔案層級的硬錯誤（route 轉 400）。"""

    def __init__(self, detail: str) -> None:
        super().__init__(detail)
        self.detail = detail


class _RowError(Exception):
    """單列驗證錯誤（列入 errors、不中斷整檔）。"""


# ---------------------------------------------------------------------------
# 驗證小工具
# ---------------------------------------------------------------------------


def _str_(
    row: dict[str, Any],
    key: str,
    *,
    required: bool = False,
    max_len: int | None = None,
    default: str | None = None,
) -> str | None:
    value = row.get(key, default)
    if value is None:
        if required:
            raise _RowError(f"{key} 為必填")
        return None
    if not isinstance(value, str):
        raise _RowError(f"{key} 必須為字串")
    if required and not value.strip():
        raise _RowError(f"{key} 不可為空")
    if max_len is not None and len(value) > max_len:
        raise _RowError(f"{key} 超過 {max_len} 字元")
    return value


def _int_(
    row: dict[str, Any],
    key: str,
    *,
    required: bool = False,
    default: int | None = None,
    min_value: int | None = None,
    max_value: int | None = None,
) -> int | None:
    value = row.get(key, default)
    if value is None:
        if required:
            raise _RowError(f"{key} 為必填")
        return None
    if isinstance(value, bool):
        raise _RowError(f"{key} 必須為整數")
    if isinstance(value, str):
        try:
            value = int(value)
        except ValueError as exc:
            raise _RowError(f"{key} 必須為整數") from exc
    if not isinstance(value, int):
        raise _RowError(f"{key} 必須為整數")
    if min_value is not None and value < min_value:
        raise _RowError(f"{key} 必須 ≥ {min_value}")
    if max_value is not None and value > max_value:
        raise _RowError(f"{key} 必須 ≤ {max_value}")
    return value


def _bool_(row: dict[str, Any], key: str, *, default: bool = False) -> bool:
    value = row.get(key)
    if value is None:
        return default
    if not isinstance(value, bool):
        raise _RowError(f"{key} 必須為布林值")
    return value


def _decimal_(row: dict[str, Any], key: str, *, max_digits: int = 12) -> Decimal | None:
    value = row.get(key)
    if value is None:
        return None
    if isinstance(value, bool):
        raise _RowError(f"{key} 必須為數字")
    try:
        number = Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise _RowError(f"{key} 必須為數字") from exc
    if not number.is_finite() or number < 0:
        raise _RowError(f"{key} 必須為 ≥ 0 的數字")
    try:
        number = number.quantize(Decimal("0.01"))
    except InvalidOperation as exc:
        raise _RowError(f"{key} 數字超出範圍") from exc
    if len(number.as_tuple().digits) > max_digits:
        raise _RowError(f"{key} 數字超出範圍")
    return number


def _dt_(row: dict[str, Any], key: str, *, default: datetime | None = None) -> datetime | None:
    value = row.get(key)
    if value is None:
        return default
    if not isinstance(value, str):
        raise _RowError(f"{key} 必須為 ISO 時間字串")
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise _RowError(f"{key} 時間格式錯誤") from exc


def _date_(row: dict[str, Any], key: str) -> date | None:
    value = row.get(key)
    if value is None:
        return None
    if not isinstance(value, str):
        raise _RowError(f"{key} 必須為 YYYY-MM-DD 字串")
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise _RowError(f"{key} 日期格式錯誤") from exc


def _str_list(row: dict[str, Any], key: str, *, max_items: int, max_len: int) -> list[str]:
    value = row.get(key)
    if value is None:
        return []
    if not isinstance(value, list) or any(not isinstance(v, str) for v in value):
        raise _RowError(f"{key} 必須為字串陣列")
    if len(value) > max_items:
        raise _RowError(f"{key} 最多 {max_items} 項")
    for item in value:
        if len(item) > max_len:
            raise _RowError(f"{key} 內含超過 {max_len} 字元的項目")
    # 去重且保序
    return list(dict.fromkeys(value))


# ---------------------------------------------------------------------------
# plan 結構
# ---------------------------------------------------------------------------


@dataclass
class RowError:
    entity: str
    index: int
    name: Optional[str]
    message: str


@dataclass
class Summary:
    entity: str
    existing: int = 0
    imported: int = 0
    created: int = 0
    reused: int = 0
    renamed: int = 0
    skipped: int = 0
    errors: int = 0


@dataclass
class Plan:
    mode: str
    format_version: int
    summaries: dict[str, Summary]
    records: dict[str, list[dict[str, Any]]]
    errors: list[RowError]
    warnings: list[str]
    reconciliation: list[dict[str, Any]]
    deleted_total: int
    existing_currency: str
    backup_currency: str
    #: create_only 沿用既有列時，apply 需要的名稱→既有 id 對照
    existing_name_ids: dict[str, dict[str, int]] = field(default_factory=dict)


class _Ctx:
    def __init__(self, mode: str) -> None:
        self.mode = mode
        self.summaries: dict[str, Summary] = {k: Summary(k) for k in ENTITY_KEYS}
        self.records: dict[str, list[dict[str, Any]]] = {k: [] for k in ENTITY_KEYS}
        self.errors: list[RowError] = []
        self.reconciliation: list[dict[str, Any]] = []
        self._warn_counts: dict[str, int] = {}
        self._warn_texts: list[str] = []

    @property
    def reuse_enabled(self) -> bool:
        # replace 先清空帳號，比對既有列已無意義 → 一律新建。
        return self.mode == "create_only"

    def error(self, entity: str, index: int, name: Optional[str], message: str) -> None:
        self.summaries[entity].errors += 1
        self.errors.append(RowError(entity=entity, index=index, name=name, message=message))

    def count(self, key: str, amount: int = 1) -> None:
        self._warn_counts[key] = self._warn_counts.get(key, 0) + amount

    def text(self, text: str) -> None:
        if text not in self._warn_texts:
            self._warn_texts.append(text)

    def warnings(self, backup_currency: str, existing_currency: str) -> list[str]:
        out: list[str] = []
        c = self._warn_counts
        if self.mode == "create_only":
            out.append(
                f"幣別偏好僅於「取代」模式還原（目前 {existing_currency}，備份為 {backup_currency}）"
            )
        if c.get("images"):
            out.append(f"{c['images']} 件物品的圖片不還原（image 二進位檔不在備份內）")
        if c.get("unknown_parent"):
            out.append(
                f"{c['unknown_parent']} 個分類或位置的上一層不存在，已置於最上層"
            )
        if c.get("unknown_refs"):
            out.append(
                f"{c['unknown_refs']} 筆物品的分類／位置／倉庫參照不存在，已設為空"
            )
        if c.get("borrowers"):
            out.append(f"{c['borrowers']} 筆借還記錄的借用人不存在，已改為標籤")
        if c.get("groups"):
            out.append(f"{c['groups']} 個群組僅還原群組本身，成員不還原")
        if c.get("webhooks"):
            out.append(f"{c['webhooks']} 個 Webhook 已以停用狀態還原")
        if c.get("prefs_skipped"):
            out.append(f"{c['prefs_skipped']} 筆通知偏好與現有設定重疊，未覆蓋")
        if c.get("reconcile"):
            out.append(f"{c['reconcile']} 件物品的數量與未耗盡批次總和不一致")
        out.extend(self._warn_texts)
        return out


# ---------------------------------------------------------------------------
# 既有資料盤點／清空範圍
# ---------------------------------------------------------------------------


def _owned_item_ids(owner_id: UUID):
    """帳號所有物品（含軟刪除；清空範圍用）。"""
    return select(Item.id).where(Item.owner_id == owner_id)


async def existing_counts(session: AsyncSession, owner_id: UUID) -> dict[str, int]:
    """各實體目前列數（顯示「現有」用）。"""
    not_deleted_item_ids = select(Item.id).where(
        Item.owner_id == owner_id, Item.is_deleted.is_(False)
    )

    async def count(stmt) -> int:
        return int((await session.execute(stmt)).scalar_one())

    return {
        "items": await count(
            select(func.count()).select_from(Item).where(
                Item.owner_id == owner_id, Item.is_deleted.is_(False)
            )
        ),
        "categories": await count(
            select(func.count()).select_from(Category).where(Category.owner_id == owner_id)
        ),
        "locations": await count(
            select(func.count()).select_from(Location).where(Location.owner_id == owner_id)
        ),
        "tags": await count(
            select(func.count()).select_from(Tag).where(Tag.owner_id == owner_id)
        ),
        "warehouses": await count(
            select(func.count()).select_from(Warehouse).where(Warehouse.owner_id == owner_id)
        ),
        "item_types": await count(
            select(func.count()).select_from(ItemType).where(ItemType.owner_id == owner_id)
        ),
        "custom_fields": await count(
            select(func.count()).select_from(CustomField).where(CustomField.owner_id == owner_id)
        ),
        "item_templates": await count(
            select(func.count()).select_from(ItemTemplate).where(ItemTemplate.owner_id == owner_id)
        ),
        "item_custom_values": await count(
            select(func.count()).select_from(ItemCustomValue).where(
                ItemCustomValue.item_id.in_(not_deleted_item_ids)
            )
        ),
        "item_batches": await count(
            select(func.count()).select_from(ItemBatch).where(
                ItemBatch.item_id.in_(not_deleted_item_ids)
            )
        ),
        "loans": await count(
            select(func.count()).select_from(ItemLoan).where(
                ItemLoan.item_id.in_(not_deleted_item_ids)
            )
        ),
        "quantity_logs": await count(
            select(func.count()).select_from(QuantityLog).where(
                QuantityLog.item_id.in_(not_deleted_item_ids)
            )
        ),
        "item_versions": await count(
            select(func.count()).select_from(ItemVersion).where(
                ItemVersion.item_id.in_(not_deleted_item_ids)
            )
        ),
        "lists": await count(
            select(func.count()).select_from(UserList).where(UserList.owner_id == owner_id)
        ),
        "stocktakes": await count(
            select(func.count()).select_from(Stocktake).where(Stocktake.owner_id == owner_id)
        ),
        "webhooks": await count(
            select(func.count()).select_from(Webhook).where(Webhook.owner_id == owner_id)
        ),
        "notification_preferences": await count(
            select(func.count()).select_from(NotificationPreference).where(
                NotificationPreference.user_id == owner_id
            )
        ),
        "groups_owned": await count(
            select(func.count()).select_from(Group).where(Group.owner_id == owner_id)
        ),
        "preferences": 1,
    }


def _wipe_statements(owner_id: UUID) -> list[tuple[str, Any, Any]]:
    """replace 清空語句（依賴序；items 之子表在 items 之前）。

    每項為 `(標籤, 表／模型, where 條件)`；`wipe_counts` 以此計數、
    `wipe_owner_data` 以此順序刪除。

    不清除：audit_logs、api_tokens、images、notifications、外部管道綁定、
    item_transfers、「我加入他人群組」的 group_members。
    """
    item_ids = _owned_item_ids(owner_id)
    own_lists = select(UserList.id).where(UserList.owner_id == owner_id)
    own_stocktakes = select(Stocktake.id).where(Stocktake.owner_id == owner_id)
    own_webhooks = select(Webhook.id).where(Webhook.owner_id == owner_id)
    own_tags = select(Tag.id).where(Tag.owner_id == owner_id)
    own_groups = select(Group.id).where(Group.owner_id == owner_id)

    return [
        ("item_batches", ItemBatch, ItemBatch.item_id.in_(item_ids)),
        ("item_loans", ItemLoan, ItemLoan.item_id.in_(item_ids)),
        ("quantity_logs", QuantityLog, QuantityLog.item_id.in_(item_ids)),
        ("item_versions", ItemVersion, ItemVersion.item_id.in_(item_ids)),
        ("item_custom_values", ItemCustomValue, ItemCustomValue.item_id.in_(item_ids)),
        (
            "item_tags",
            item_tags,
            or_(item_tags.c.item_id.in_(item_ids), item_tags.c.tag_id.in_(own_tags)),
        ),
        ("stocktake_items", StocktakeItem, StocktakeItem.stocktake_id.in_(own_stocktakes)),
        ("stocktakes", Stocktake, Stocktake.owner_id == owner_id),
        ("list_entries", ListEntry, ListEntry.list_id.in_(own_lists)),
        ("lists", UserList, UserList.owner_id == owner_id),
        (
            "webhook_deliveries",
            WebhookDelivery,
            WebhookDelivery.webhook_id.in_(own_webhooks),
        ),
        ("webhooks", Webhook, Webhook.owner_id == owner_id),
        ("items", Item, Item.owner_id == owner_id),
        ("categories", Category, Category.owner_id == owner_id),
        ("locations", Location, Location.owner_id == owner_id),
        ("tags", Tag, Tag.owner_id == owner_id),
        ("warehouses", Warehouse, Warehouse.owner_id == owner_id),
        ("item_types", ItemType, ItemType.owner_id == owner_id),
        ("custom_fields", CustomField, CustomField.owner_id == owner_id),
        ("item_templates", ItemTemplate, ItemTemplate.owner_id == owner_id),
        (
            "notification_preferences",
            NotificationPreference,
            NotificationPreference.user_id == owner_id,
        ),
        ("group_members", GroupMember, GroupMember.group_id.in_(own_groups)),
        ("groups_owned", Group, Group.owner_id == owner_id),
    ]


async def wipe_counts(session: AsyncSession, owner_id: UUID) -> int:
    """回傳 replace 模式將刪除的列數合計（不執行刪除）。"""
    total = 0
    for _label, target, where in _wipe_statements(owner_id):
        count_stmt = select(func.count()).select_from(target).where(where)
        total += int((await session.execute(count_stmt)).scalar_one())
    return total


async def wipe_owner_data(session: AsyncSession, owner_id: UUID) -> int:
    """執行 replace 清空（呼叫端負責交易）；回傳刪除列數合計。"""
    total = 0
    for _label, target, where in _wipe_statements(owner_id):
        result = await session.execute(delete(target).where(where))
        total += int(result.rowcount or 0)
    return total


# ---------------------------------------------------------------------------
# 名稱匹配解析器
# ---------------------------------------------------------------------------


class _NameMap:
    """名稱匹配解析器（tags／warehouses）：既有列沿用、pending 沿用、否則建立。"""

    def __init__(self, ctx: _Ctx, entity: str, existing: dict[str, int]) -> None:
        self.ctx = ctx
        self.entity = entity
        self.existing = existing
        self.pending: set[str] = set()

    def ensure(
        self, name: str, *, implicit: bool = False, extra: dict[str, Any] | None = None
    ) -> dict[str, Any] | None:
        """確保 `name` 有對應列；沿用既有／pending 時回 None（不建列）。"""
        summary = self.ctx.summaries[self.entity]
        if implicit:
            summary.imported += 1
        if self.ctx.reuse_enabled and name in self.existing:
            summary.reused += 1
            return None
        if name in self.pending:
            summary.reused += 1
            return None
        self.pending.add(name)
        summary.created += 1
        record: dict[str, Any] = {"action": "create", "name": name}
        if extra:
            record.update(extra)
        self.ctx.records[self.entity].append(record)
        return record


def _obj(raw: Any, *, label: str = "列") -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise _RowError(f"{label}必須是 JSON 物件")
    return raw


def _name_hint(raw: Any) -> Optional[str]:
    if isinstance(raw, dict):
        name = raw.get("name")
        if isinstance(name, str):
            return name
    return None


def _resolve_hierarchy(
    ctx: _Ctx,
    entity: str,
    rows: list[Any],
    *,
    parse_fn,
    existing_keys: dict[tuple, int],
) -> dict[int, tuple[str, int]]:
    """解析樹狀 taxonomy（categories／locations）並回傳 src_id → 解析結果。

    回傳值：`("existing", db_id)`（create_only 沿用）或 `("create", src_id)`。
    """
    nodes: dict[int, dict[str, Any]] = {}
    order: list[int] = []
    index_by_src: dict[int, int] = {}
    for index, raw in enumerate(rows):
        try:
            node = parse_fn(_obj(raw))
        except _RowError as exc:
            ctx.error(entity, index, _name_hint(raw), str(exc))
            continue
        src = node["src_id"]
        if src in nodes:
            ctx.error(entity, index, node["name"], f"id 重複（{src}）")
            continue
        nodes[src] = node
        order.append(src)
        index_by_src[src] = index

    # 上層鏈無法終止於根（含成環）的節點 → 錯誤列；其餘指向它們的節點再視為上層不存在。
    def unresolvable(src: int) -> bool:
        seen: set[int] = set()
        cur: Optional[int] = src
        while cur is not None:
            if cur in seen:
                return True
            seen.add(cur)
            node = nodes.get(cur)
            if node is None:
                return False
            cur = node["parent_src"]
        return False

    bad_srcs = [src for src in order if unresolvable(src)]
    for src in bad_srcs:
        node = nodes.pop(src)
        order.remove(src)
        ctx.error(entity, index_by_src[src], node["name"], "上層階層成環，無法解析")

    resolved: dict[int, tuple[str, int]] = {}
    taken: set[tuple] = set(existing_keys.keys())
    emitting: set[int] = set()

    def resolve(src: int) -> tuple[str, int]:
        if src in resolved:
            return resolved[src]
        if src in emitting:  # 防禦：成環節點已於前置檢查移除，此處理論上不觸發
            raise BackupFormatError(f"「{entity}」階層成環，無法解析")
        emitting.add(src)
        node = nodes[src]
        parent_src = node["parent_src"]
        if parent_src is not None and parent_src not in nodes:
            ctx.count("unknown_parent")
            parent_src = None
        parent_ref: Optional[tuple[str, int]] = None
        scope: Any = None
        if parent_src is not None:
            parent_res = resolve(parent_src)
            if parent_res[0] == "existing":
                parent_ref = ("existing", parent_res[1])
                scope = ("db", parent_res[1])
            else:
                parent_ref = ("src", parent_src)
                scope = ("src", parent_src)
        key = (scope, node["name"])
        if ctx.reuse_enabled and key in existing_keys:
            outcome: tuple[str, int] = ("existing", existing_keys[key])
            ctx.summaries[entity].reused += 1
        else:
            final_name = node["name"]
            renamed = False
            if key in taken:
                suffix = 2
                while (scope, f"{final_name} ({suffix})") in taken:
                    suffix += 1
                final_name = f"{final_name} ({suffix})"
                renamed = True
            taken.add((scope, final_name))
            record = {
                "action": "create",
                "src_id": src,
                "name": final_name,
                "parent": parent_ref,
                "renamed": renamed,
            }
            record.update(node.get("extra", {}))
            ctx.records[entity].append(record)
            summary = ctx.summaries[entity]
            if renamed:
                summary.renamed += 1
            else:
                summary.created += 1
            outcome = ("create", src)
        resolved[src] = outcome
        emitting.discard(src)
        return outcome

    for src in order:
        if src in nodes:
            resolve(src)
    return resolved


def _parse_category(raw: dict[str, Any]) -> dict[str, Any]:
    src = _int_(raw, "id", required=True, min_value=1)
    name = _str_(raw, "name", required=True, max_len=100)
    parent_src = _int_(raw, "parent_id", min_value=1)
    if parent_src == src:
        raise _RowError("parent_id 不可指向自己")
    return {"src_id": src, "name": name, "parent_src": parent_src}


def _parse_location(raw: dict[str, Any], ctx: _Ctx) -> dict[str, Any]:
    src = _int_(raw, "id", required=True, min_value=1)
    name = _str_(raw, "name", required=True, max_len=50)
    parent_src = _int_(raw, "parent_id", min_value=1)
    if parent_src == src:
        raise _RowError("parent_id 不可指向自己")
    region = None
    if raw.get("plan_region") is not None:
        try:
            region = PlanRegion.model_validate(raw["plan_region"]).model_dump()
        except ValidationError:
            ctx.text(f"位置「{name}」的 plan_region 不合格，已略過區域")
    return {
        "src_id": src,
        "name": name,
        "parent_src": parent_src,
        "extra": {
            "plan_region": region,
            "kind": _str_(raw, "kind", max_len=20),
            "sort_order": _int_(raw, "sort_order", default=0, min_value=0) or 0,
        },
    }


# ---------------------------------------------------------------------------
# build_plan
# ---------------------------------------------------------------------------


def _prepare_payload(payload: Any) -> tuple[int, dict[str, list[Any]], dict[str, Any]]:
    if not isinstance(payload, dict):
        raise BackupFormatError("備份檔根層必須是 JSON 物件")
    version = payload.get("format_version")
    if isinstance(version, bool) or not isinstance(version, int):
        raise BackupFormatError("備份檔缺少有效的 format_version")
    if version < 1:
        raise BackupFormatError(f"不支援的備份格式版本（{version}）")
    if version > FORMAT_VERSION:
        raise BackupFormatError(
            f"備份檔版本（{version}）高於本系統支援的版本（{FORMAT_VERSION}）"
        )
    entity_lists: dict[str, list[Any]] = {}
    for key in ENTITY_KEYS:
        if key == "preferences":
            continue
        value = payload.get(key, [])
        if value is None:
            value = []
        if not isinstance(value, list):
            raise BackupFormatError(f"{key} 必須是陣列")
        entity_lists[key] = value
    preferences = payload.get("preferences")
    if preferences is not None and not isinstance(preferences, dict):
        raise BackupFormatError("preferences 必須是物件")
    return version, entity_lists, (preferences or {})


async def build_plan(
    session: AsyncSession, owner_id: UUID, payload: Any, *, mode: Literal["create_only", "replace"]
) -> Plan:
    if mode not in ("create_only", "replace"):
        raise BackupFormatError(f"不支援的匯入模式（{mode}）")
    version, lists, preferences = _prepare_payload(payload)

    ctx = _Ctx(mode)
    counts = await existing_counts(session, owner_id)
    for key, value in counts.items():
        ctx.summaries[key].existing = value
    for key, rows in lists.items():
        ctx.summaries[key].imported = len(rows)
    ctx.summaries["preferences"].imported = 1

    # ---- categories / locations（樹狀，名稱匹配）----
    cat_rows = (await session.execute(
        select(Category.id, Category.parent_id, Category.name).where(
            Category.owner_id == owner_id
        )
    )).all()
    existing_cat_keys = {
        ((("db", row.parent_id) if row.parent_id is not None else None), row.name): row.id
        for row in cat_rows
    }
    resolved_categories = _resolve_hierarchy(
        ctx, "categories", lists["categories"], parse_fn=_parse_category,
        existing_keys=existing_cat_keys,
    )

    loc_rows = (await session.execute(
        select(Location.id, Location.parent_id, Location.name).where(
            Location.owner_id == owner_id
        )
    )).all()
    existing_loc_keys = {
        ((("db", row.parent_id) if row.parent_id is not None else None), row.name): row.id
        for row in loc_rows
    }
    resolved_locations = _resolve_hierarchy(
        ctx, "locations", lists["locations"], parse_fn=lambda raw: _parse_location(raw, ctx),
        existing_keys=existing_loc_keys,
    )

    # ---- tags / warehouses（名稱匹配）----
    tag_rows = (await session.execute(
        select(Tag.name, Tag.id).where(Tag.owner_id == owner_id)
    )).all()
    tag_map = _NameMap(ctx, "tags", {row.name: row.id for row in tag_rows})
    for index, raw in enumerate(lists["tags"]):
        try:
            name = _str_(_obj(raw), "name", required=True, max_len=50)
        except _RowError as exc:
            ctx.error("tags", index, _name_hint(raw), str(exc))
            continue
        tag_map.ensure(name)

    wh_rows = (await session.execute(
        select(Warehouse.name, Warehouse.id).where(Warehouse.owner_id == owner_id)
    )).all()
    warehouse_map = _NameMap(ctx, "warehouses", {row.name: row.id for row in wh_rows})
    #: 匯出檔內庫房 id → 名稱（物品以 warehouse_id 參照）
    wh_src_name: dict[int, str] = {}
    for index, raw in enumerate(lists["warehouses"]):
        try:
            row = _obj(raw)
            name = _str_(row, "name", required=True, max_len=100)
            description = _str_(row, "description")
            src = _int_(row, "id", min_value=1)
        except _RowError as exc:
            ctx.error("warehouses", index, _name_hint(raw), str(exc))
            continue
        if src is not None:
            wh_src_name[src] = name
        warehouse_map.ensure(name, extra={"description": description})

    # ---- item_types / custom_fields / item_templates（一律新建，重名加後綴）----
    it_existing = {
        row.name for row in (await session.execute(
            select(ItemType.name).where(ItemType.owner_id == owner_id)
        )).all()
    }
    it_taken = set(it_existing) if ctx.reuse_enabled else set()
    for index, raw in enumerate(lists["item_types"]):
        try:
            row = _obj(raw)
            name = _str_(row, "name", required=True, max_len=100)
            icon = _str_(row, "icon", max_len=50)
        except _RowError as exc:
            ctx.error("item_types", index, _name_hint(raw), str(exc))
            continue
        final = name
        renamed = False
        if final in it_taken:
            suffix = 2
            while f"{name} ({suffix})" in it_taken:
                suffix += 1
            final = f"{name} ({suffix})"
            renamed = True
        it_taken.add(final)
        if renamed:
            ctx.summaries["item_types"].renamed += 1
        else:
            ctx.summaries["item_types"].created += 1
        ctx.records["item_types"].append(
            {"action": "create", "name": final, "icon": icon, "renamed": renamed}
        )

    cf_existing = {
        row.name for row in (await session.execute(
            select(CustomField.name).where(CustomField.owner_id == owner_id)
        )).all()
    }
    cf_taken = set(cf_existing) if ctx.reuse_enabled else set()
    field_srcs: set[int] = set()
    for index, raw in enumerate(lists["custom_fields"]):
        try:
            row = _obj(raw)
            src = _int_(row, "id", required=True, min_value=1)
            name = _str_(row, "name", required=True, max_len=80)
            field_type = _str_(row, "field_type", required=True, max_len=20)
        except _RowError as exc:
            ctx.error("custom_fields", index, _name_hint(raw), str(exc))
            continue
        if src in field_srcs:
            ctx.error("custom_fields", index, name, f"id 重複（{src}）")
            continue
        final = name
        renamed = False
        if final in cf_taken:
            suffix = 2
            while f"{name} ({suffix})" in cf_taken:
                suffix += 1
            final = f"{name} ({suffix})"
            renamed = True
        cf_taken.add(final)
        if renamed:
            ctx.summaries["custom_fields"].renamed += 1
        else:
            ctx.summaries["custom_fields"].created += 1
        field_srcs.add(src)
        ctx.records["custom_fields"].append(
            {
                "action": "create",
                "src_id": src,
                "name": final,
                "field_type": field_type,
                "renamed": renamed,
            }
        )

    tpl_existing = {
        row.name for row in (await session.execute(
            select(ItemTemplate.name).where(ItemTemplate.owner_id == owner_id)
        )).all()
    }
    tpl_taken = set(tpl_existing) if ctx.reuse_enabled else set()
    for index, raw in enumerate(lists["item_templates"]):
        try:
            row = _obj(raw)
            name = _str_(row, "name", required=True, max_len=100)
            payload_value = row.get("payload")
            if not isinstance(payload_value, dict):
                raise _RowError("payload 必須是 JSON 物件")
        except _RowError as exc:
            ctx.error("item_templates", index, _name_hint(raw), str(exc))
            continue
        final = name
        renamed = False
        if final in tpl_taken:
            suffix = 2
            while f"{name} ({suffix})" in tpl_taken:
                suffix += 1
            final = f"{name} ({suffix})"
            renamed = True
        tpl_taken.add(final)
        if renamed:
            ctx.summaries["item_templates"].renamed += 1
        else:
            ctx.summaries["item_templates"].created += 1
        ctx.records["item_templates"].append(
            {
                "action": "create",
                "name": final,
                "payload": payload_value,
                "renamed": renamed,
            }
        )

    # ---- items ----
    now = datetime.now(timezone.utc)
    valid_item_srcs: set[str] = set()
    for index, raw in enumerate(lists["items"]):
        try:
            row = _obj(raw, label="物品列")
            src = _str_(row, "id", required=True)
            name = _str_(row, "name", required=True, max_len=200)
            description = _str_(row, "description")
            notes = _str_(row, "notes")
            barcode = _str_(row, "barcode", max_len=32)
            quantity = _int_(row, "quantity", default=1, min_value=0)
            min_quantity = _int_(row, "min_quantity", min_value=0)
            cost = _decimal_(row, "cost")
            track_batches = _bool_(row, "track_batches", default=False)
            is_favorite = _bool_(row, "is_favorite", default=False)
            tag_names = _str_list(row, "tag_names", max_items=50, max_len=50)
            if row.get("image_id") is not None:
                ctx.count("images")

            cat_ref: Optional[tuple[str, int]] = None
            cat_src = _int_(row, "category_id", min_value=1)
            if cat_src is not None:
                got = resolved_categories.get(cat_src)
                if got is None:
                    ctx.count("unknown_refs")
                else:
                    cat_ref = got
            loc_ref: Optional[tuple[str, int]] = None
            loc_src = _int_(row, "location_id", min_value=1)
            if loc_src is not None:
                got = resolved_locations.get(loc_src)
                if got is None:
                    ctx.count("unknown_refs")
                else:
                    loc_ref = got
            warehouse_name: Optional[str] = None
            wh_id = _int_(row, "warehouse_id", min_value=1)
            if wh_id is not None:
                warehouse_name = wh_src_name.get(wh_id)
                if warehouse_name is None:
                    ctx.count("unknown_refs")

            created_at = _dt_(row, "created_at", default=now)
            updated_at = _dt_(row, "updated_at", default=created_at)
        except _RowError as exc:
            ctx.error("items", index, _name_hint(raw), str(exc))
            continue
        if src in valid_item_srcs:
            ctx.error("items", index, name, "id 重複")
            continue
        valid_item_srcs.add(src)
        ctx.summaries["items"].created += 1
        ctx.records["items"].append(
            {
                "action": "create",
                "src_id": src,
                "new_id": uuid4(),
                "name": name,
                "description": description,
                "barcode": barcode,
                "quantity": quantity if quantity is not None else 1,
                "min_quantity": min_quantity,
                "cost": cost,
                "track_batches": track_batches,
                "notes": notes,
                "is_favorite": is_favorite,
                "category_ref": cat_ref,
                "location_ref": loc_ref,
                "warehouse_name": warehouse_name,
                "tag_names": tag_names,
                "created_at": created_at,
                "updated_at": updated_at,
            }
        )
        for tag_name in tag_names:
            tag_map.ensure(tag_name, implicit=True)

    # ---- item_custom_values ----
    seen_values: set[tuple[str, int]] = set()
    for index, raw in enumerate(lists["item_custom_values"]):
        try:
            row = _obj(raw)
            item_src = _str_(row, "item_id", required=True)
            if item_src not in valid_item_srcs:
                raise _RowError("參照的物品不存在於備份檔內")
            field_src = _int_(row, "custom_field_id", required=True, min_value=1)
            if field_src not in field_srcs:
                raise _RowError("參照的自訂欄位不存在於備份檔內")
            if (item_src, field_src) in seen_values:
                raise _RowError("同一物品的同自訂欄位值重複")
            value = row.get("value")
        except _RowError as exc:
            ctx.error("item_custom_values", index, None, str(exc))
            continue
        seen_values.add((item_src, field_src))
        ctx.summaries["item_custom_values"].created += 1
        ctx.records["item_custom_values"].append(
            {
                "action": "create",
                "item_src": item_src,
                "field_src": field_src,
                "value": value,
            }
        )

    # ---- item_batches ----
    tracked_item_srcs: set[str] = set()
    for index, raw in enumerate(lists["item_batches"]):
        try:
            row = _obj(raw)
            item_src = _str_(row, "item_id", required=True)
            if item_src not in valid_item_srcs:
                raise _RowError("參照的物品不存在於備份檔內")
            quantity = _int_(row, "quantity", required=True, min_value=0)
            expiry_date = _date_(row, "expiry_date")
            received_at = _date_(row, "received_at")
            unit_cost = _decimal_(row, "unit_cost")
            note = _str_(row, "note")
            is_depleted = _bool_(row, "is_depleted", default=False)
            created_at = _dt_(row, "created_at", default=now)
        except _RowError as exc:
            ctx.error("item_batches", index, None, str(exc))
            continue
        tracked_item_srcs.add(item_src)
        ctx.summaries["item_batches"].created += 1
        ctx.records["item_batches"].append(
            {
                "action": "create",
                "item_src": item_src,
                "quantity": quantity,
                "expiry_date": expiry_date,
                "received_at": received_at,
                "unit_cost": unit_cost,
                "note": note,
                "is_depleted": is_depleted,
                "created_at": created_at,
            }
        )
    # 有批次列的物品一律標記為批次追蹤（舊檔可能缺 track_batches 欄位）
    for item_rec in ctx.records["items"]:
        if item_rec["src_id"] in tracked_item_srcs:
            item_rec["track_batches"] = True

    # ---- loans / quantity_logs / item_versions（user 參照統一存在性檢查）----
    user_id_strs: set[str] = set()
    pending_loans: list[dict[str, Any]] = []
    active_loan_items: set[str] = set()
    for index, raw in enumerate(lists["loans"]):
        try:
            row = _obj(raw)
            item_src = _str_(row, "item_id", required=True)
            if item_src not in valid_item_srcs:
                raise _RowError("參照的物品不存在於備份檔內")
            borrower_user_id = _str_(row, "borrower_user_id")
            if borrower_user_id is not None:
                try:
                    UUID(borrower_user_id)
                except ValueError as exc:
                    raise _RowError("borrower_user_id 格式錯誤") from exc
                user_id_strs.add(borrower_user_id)
            borrower_label = _str_(row, "borrower_label", max_len=200)
            lent_at = _dt_(row, "lent_at", default=now)
            expected_return = _date_(row, "expected_return")
            returned_at = _dt_(row, "returned_at")
            notes = _str_(row, "notes")
            if returned_at is None:
                if item_src in active_loan_items:
                    raise _RowError("同一物品有多筆未歸還的借還記錄")
                active_loan_items.add(item_src)
        except _RowError as exc:
            ctx.error("loans", index, None, str(exc))
            continue
        pending_loans.append(
            {
                "item_src": item_src,
                "borrower_user_id": borrower_user_id,
                "borrower_label": borrower_label,
                "lent_at": lent_at,
                "expected_return": expected_return,
                "returned_at": returned_at,
                "notes": notes,
            }
        )

    pending_logs: list[dict[str, Any]] = []
    for index, raw in enumerate(lists["quantity_logs"]):
        try:
            row = _obj(raw)
            item_src = _str_(row, "item_id", required=True)
            if item_src not in valid_item_srcs:
                raise _RowError("參照的物品不存在於備份檔內")
            user_id = _str_(row, "user_id")
            if user_id is not None:
                try:
                    UUID(user_id)
                except ValueError as exc:
                    raise _RowError("user_id 格式錯誤") from exc
                user_id_strs.add(user_id)
            old_quantity = _int_(row, "old_quantity", required=True, min_value=0)
            new_quantity = _int_(row, "new_quantity", required=True, min_value=0)
            reason = _str_(row, "reason")
            created_at = _dt_(row, "created_at", default=now)
        except _RowError as exc:
            ctx.error("quantity_logs", index, None, str(exc))
            continue
        pending_logs.append(
            {
                "item_src": item_src,
                "user_id": user_id,
                "old_quantity": old_quantity,
                "new_quantity": new_quantity,
                "reason": reason,
                "created_at": created_at,
            }
        )

    pending_versions: list[dict[str, Any]] = []
    for index, raw in enumerate(lists["item_versions"]):
        try:
            row = _obj(raw)
            item_src = _str_(row, "item_id", required=True)
            if item_src not in valid_item_srcs:
                raise _RowError("參照的物品不存在於備份檔內")
            user_id = _str_(row, "user_id")
            if user_id is not None:
                try:
                    UUID(user_id)
                except ValueError as exc:
                    raise _RowError("user_id 格式錯誤") from exc
                user_id_strs.add(user_id)
            snapshot = row.get("snapshot")
            if not isinstance(snapshot, dict):
                raise _RowError("snapshot 必須是 JSON 物件")
            created_at = _dt_(row, "created_at", default=now)
        except _RowError as exc:
            ctx.error("item_versions", index, None, str(exc))
            continue
        pending_versions.append(
            {
                "item_src": item_src,
                "user_id": user_id,
                "snapshot": snapshot,
                "created_at": created_at,
            }
        )

    existing_user_ids: set[str] = set()
    if user_id_strs:
        user_uuid_rows = (await session.execute(
            select(User.id).where(User.id.in_([UUID(x) for x in user_id_strs]))
        )).scalars().all()
        existing_user_ids = {str(u) for u in user_uuid_rows}

    for loan in pending_loans:
        borrower_user_id = loan["borrower_user_id"]
        if borrower_user_id is not None and borrower_user_id not in existing_user_ids:
            ctx.count("borrowers")
            borrower_user_id = None
        label = loan["borrower_label"]
        if not label and borrower_user_id is None:
            label = "（原借用人不存在）" if loan["borrower_user_id"] else "（未命名借用人）"
        ctx.summaries["loans"].created += 1
        ctx.records["loans"].append(
            {**loan, "borrower_user_id": borrower_user_id, "borrower_label": label}
        )

    for log in pending_logs:
        user_id = log["user_id"]
        if user_id is not None and user_id not in existing_user_ids:
            user_id = None
        ctx.summaries["quantity_logs"].created += 1
        ctx.records["quantity_logs"].append({**log, "user_id": user_id})

    for version_rec in pending_versions:
        user_id = version_rec["user_id"]
        if user_id is not None and user_id not in existing_user_ids:
            user_id = None
        ctx.summaries["item_versions"].created += 1
        ctx.records["item_versions"].append({**version_rec, "user_id": user_id})

    # ---- lists ----
    for index, raw in enumerate(lists["lists"]):
        try:
            row = _obj(raw, label="清單列")
            kind = _str_(row, "kind", required=True, max_len=20)
            title = _str_(row, "title", required=True, max_len=120)
            description = _str_(row, "description")
            start_date = _date_(row, "start_date")
            end_date = _date_(row, "end_date")
            budget = _decimal_(row, "budget")
            created_at = _dt_(row, "created_at", default=now)
            updated_at = _dt_(row, "updated_at", default=created_at)
            entries_raw = row.get("entries") or []
            if not isinstance(entries_raw, list):
                raise _RowError("entries 必須是陣列")
            entries: list[dict[str, Any]] = []
            for entry_raw in entries_raw:
                entry = _obj(entry_raw, label="清單項目")
                entries.append(
                    {
                        "position": _int_(entry, "position", default=0, min_value=0),
                        "name": _str_(entry, "name", required=True, max_len=200),
                        "quantity": _int_(entry, "quantity", min_value=1),
                        "note": _str_(entry, "note"),
                        "price": _decimal_(entry, "price"),
                        "link": _str_(entry, "link", max_len=500),
                        "is_done": _bool_(entry, "is_done", default=False),
                        "created_at": _dt_(entry, "created_at", default=now),
                    }
                )
        except _RowError as exc:
            ctx.error("lists", index, None, str(exc))
            continue
        ctx.summaries["lists"].created += 1
        ctx.records["lists"].append(
            {
                "action": "create",
                "kind": kind,
                "title": title,
                "description": description,
                "start_date": start_date,
                "end_date": end_date,
                "budget": budget,
                "entries": entries,
                "created_at": created_at,
                "updated_at": updated_at,
            }
        )

    # ---- stocktakes ----
    for index, raw in enumerate(lists["stocktakes"]):
        try:
            row = _obj(raw, label="盤點列")
            name = _str_(row, "name", required=True, max_len=120)
            status = _str_(row, "status", default="open", max_len=20)
            if status not in STOCKTAKE_STATUSES:
                raise _RowError("status 必須是 open／completed／cancelled")
            started_at = _dt_(row, "started_at", default=now)
            completed_at = _dt_(row, "completed_at")
            items_raw = row.get("items") or []
            if not isinstance(items_raw, list):
                raise _RowError("items 必須是陣列")
            items: list[dict[str, Any]] = []
            for position, item_raw in enumerate(items_raw, start=1):
                item = _obj(item_raw, label="盤點項目")
                item_src = _str_(item, "item_id", required=True)
                if item_src not in valid_item_srcs:
                    raise _RowError(f"第 {position} 個盤點項目參照的物品不存在於備份檔內")
                items.append(
                    {
                        "item_src": item_src,
                        "expected_quantity": _int_(
                            item, "expected_quantity", required=True, min_value=0
                        ),
                        "actual_quantity": _int_(
                            item, "actual_quantity", required=True, min_value=0
                        ),
                        "note": _str_(item, "note"),
                        "scanned_at": _dt_(item, "scanned_at", default=now),
                    }
                )
        except _RowError as exc:
            ctx.error("stocktakes", index, _name_hint(raw), str(exc))
            continue
        ctx.summaries["stocktakes"].created += 1
        ctx.records["stocktakes"].append(
            {
                "action": "create",
                "name": name,
                "status": status,
                "started_at": started_at,
                "completed_at": completed_at,
                "items": items,
            }
        )

    # ---- webhooks（一律停用還原）----
    for index, raw in enumerate(lists["webhooks"]):
        try:
            row = _obj(raw)
            name = _str_(row, "name", required=True, max_len=100)
            url = _str_(row, "url", required=True)
            secret = _str_(row, "secret", max_len=200)
            events = _str_list(row, "events", max_items=50, max_len=60)
        except _RowError as exc:
            ctx.error("webhooks", index, _name_hint(raw), str(exc))
            continue
        ctx.summaries["webhooks"].created += 1
        ctx.records["webhooks"].append(
            {
                "action": "create",
                "name": name,
                "url": url,
                "secret": secret,
                "events": events,
                "is_active": False,
            }
        )
    if ctx.summaries["webhooks"].created:
        ctx.count("webhooks", ctx.summaries["webhooks"].created)

    # ---- notification_preferences（create_only：既有格不覆蓋）----
    pref_rows = (await session.execute(
        select(NotificationPreference.type, NotificationPreference.channel).where(
            NotificationPreference.user_id == owner_id
        )
    )).all()
    existing_cells = {(row.type, row.channel) for row in pref_rows}
    seen_cells: set[tuple[str, str]] = set()
    for index, raw in enumerate(lists["notification_preferences"]):
        try:
            row = _obj(raw)
            pref_type = _str_(row, "type", required=True, max_len=40)
            channel = _str_(row, "channel", required=True, max_len=20)
            if row.get("enabled") is None:
                raise _RowError("enabled 為必填")
            enabled = _bool_(row, "enabled")
            if (pref_type, channel) in seen_cells:
                raise _RowError("重複的通知偏好設定")
        except _RowError as exc:
            ctx.error("notification_preferences", index, None, str(exc))
            continue
        seen_cells.add((pref_type, channel))
        if ctx.reuse_enabled and (pref_type, channel) in existing_cells:
            ctx.summaries["notification_preferences"].skipped += 1
            ctx.count("prefs_skipped")
            continue
        ctx.summaries["notification_preferences"].created += 1
        ctx.records["notification_preferences"].append(
            {"action": "create", "type": pref_type, "channel": channel, "enabled": enabled}
        )

    # ---- groups_owned（僅群組殼，成員不還原）----
    for index, raw in enumerate(lists["groups_owned"]):
        try:
            row = _obj(raw)
            name = _str_(row, "name", required=True, max_len=100)
        except _RowError as exc:
            ctx.error("groups_owned", index, _name_hint(raw), str(exc))
            continue
        ctx.summaries["groups_owned"].created += 1
        ctx.records["groups_owned"].append({"action": "create", "name": name})
        ctx.count("groups")

    # ---- preferences（幣別僅 replace 還原）----
    backup_currency = currency_from_raw(preferences)
    current_raw = (await session.execute(
        select(User.preferences).where(User.id == owner_id)
    )).scalar_one_or_none() or {}
    existing_currency = currency_from_raw(current_raw)
    if ctx.reuse_enabled:
        ctx.summaries["preferences"].skipped = 1
    else:
        ctx.summaries["preferences"].created = 1
        ctx.records["preferences"].append({"action": "create", "currency": backup_currency})

    # ---- 對帳：track_batches 物品 quantity == Σ 未耗盡批次 ----
    batch_totals: dict[str, int] = {}
    for batch_rec in ctx.records["item_batches"]:
        if not batch_rec["is_depleted"]:
            batch_totals[batch_rec["item_src"]] = (
                batch_totals.get(batch_rec["item_src"], 0) + batch_rec["quantity"]
            )
    for item_rec in ctx.records["items"]:
        if not item_rec["track_batches"]:
            continue
        total = batch_totals.get(item_rec["src_id"], 0)
        if item_rec["quantity"] != total:
            ctx.reconciliation.append(
                {
                    "item_id": item_rec["new_id"],
                    "name": item_rec["name"],
                    "quantity": item_rec["quantity"],
                    "batch_total": total,
                }
            )
    if ctx.reconciliation:
        ctx.count("reconcile", len(ctx.reconciliation))

    deleted_total = await wipe_counts(session, owner_id) if mode == "replace" else 0

    return Plan(
        mode=mode,
        format_version=version,
        summaries=ctx.summaries,
        records=ctx.records,
        errors=ctx.errors,
        warnings=ctx.warnings(
            backup_currency=backup_currency, existing_currency=existing_currency
        ),
        reconciliation=ctx.reconciliation,
        deleted_total=deleted_total,
        existing_currency=existing_currency,
        backup_currency=backup_currency,
        existing_name_ids={
            "tags": tag_map.existing,
            "warehouses": warehouse_map.existing,
        },
    )


def to_result(plan: Plan, *, dry_run: bool) -> BackupImportResult:
    """把 plan（或 apply 後的 plan）轉為 API 結果。"""
    entities: list[BackupImportEntitySummary] = []
    for key in ENTITY_KEYS:
        summary = plan.summaries[key]
        if summary.imported or summary.existing or summary.errors:
            entities.append(
                BackupImportEntitySummary(
                    entity=key,
                    existing=summary.existing,
                    imported=summary.imported,
                    created=summary.created,
                    reused=summary.reused,
                    renamed=summary.renamed,
                    skipped=summary.skipped,
                    errors=summary.errors,
                )
            )
    valid = sum(s.created + s.reused + s.renamed for s in plan.summaries.values())
    if plan.errors:
        status: Literal["ok", "partial", "error"] = (
            "partial" if (plan.mode == "create_only" and valid > 0) else "error"
        )
    else:
        status = "ok"
    return BackupImportResult(
        format_version=plan.format_version,
        mode=plan.mode,  # type: ignore[arg-type]
        dry_run=dry_run,
        status=status,
        deleted_total=plan.deleted_total,
        entities=entities,
        errors=[
            BackupImportError(
                entity=row.entity, index=row.index, name=row.name, message=row.message
            )
            for row in plan.errors[:MAX_ERRORS]
        ],
        errors_total=len(plan.errors),
        warnings=plan.warnings,
        reconciliation=[BackupReconciliationItem(**row) for row in plan.reconciliation],
    )

# ---------------------------------------------------------------------------
# apply（T1.3 create_only／T1.4 replace 共用）
# ---------------------------------------------------------------------------


def _resolve_ref(ref: Optional[tuple[str, int]], id_by_src: dict[int, int]) -> Optional[int]:
    if ref is None:
        return None
    kind, value = ref
    return value if kind == "existing" else id_by_src.get(value)


async def _insert_hierarchy(
    session: AsyncSession, owner_id: UUID, records: list[dict[str, Any]], model: Any
) -> dict[int, int]:
    """依依賴序（父先於子）建立 categories／locations；回傳 src id → 新 id。"""
    id_by_src: dict[int, int] = {}
    for rec in records:
        parent_ref = rec["parent"]
        parent_id: Optional[int]
        if parent_ref is None:
            parent_id = None
        elif parent_ref[0] == "existing":
            parent_id = parent_ref[1]
        else:
            parent_id = id_by_src.get(parent_ref[1])
        kwargs: dict[str, Any] = {
            "owner_id": owner_id,
            "name": rec["name"],
            "parent_id": parent_id,
        }
        for key in ("kind", "sort_order", "plan_region"):
            if key in rec:
                kwargs[key] = rec[key]
        row = model(**kwargs)
        session.add(row)
        await session.flush()
        id_by_src[rec["src_id"]] = row.id
    return id_by_src


async def _insert_catalogs(
    session: AsyncSession, owner_id: UUID, plan: Plan
) -> tuple[dict[int, int], dict[str, int], dict[str, int]]:
    """建立 item_types／custom_fields／item_templates／tags／warehouses。

    回傳 (custom_field src→id、tag name→id、warehouse name→id)。create_only 時
    tags／warehouses 的既有名稱沿用 `plan.existing_name_ids`；replace 已清空，
    一律用本檔建立的列。
    """
    records = plan.records
    for rec in records["item_types"]:
        session.add(ItemType(owner_id=owner_id, name=rec["name"], icon=rec["icon"]))
    cf_id_by_src: dict[int, int] = {}
    for rec in records["custom_fields"]:
        cf_row = CustomField(owner_id=owner_id, name=rec["name"], field_type=rec["field_type"])
        session.add(cf_row)
        await session.flush()
        cf_id_by_src[rec["src_id"]] = cf_row.id
    for rec in records["item_templates"]:
        session.add(
            ItemTemplate(owner_id=owner_id, name=rec["name"], payload=rec["payload"])
        )

    reuse = plan.mode == "create_only"
    tag_id_by_name: dict[str, int] = dict(plan.existing_name_ids.get("tags", {})) if reuse else {}
    for rec in records["tags"]:
        tag_row = Tag(owner_id=owner_id, name=rec["name"])
        session.add(tag_row)
        await session.flush()
        tag_id_by_name[rec["name"]] = tag_row.id
    warehouse_id_by_name: dict[str, int] = (
        dict(plan.existing_name_ids.get("warehouses", {})) if reuse else {}
    )
    for rec in records["warehouses"]:
        wh_row = Warehouse(
            owner_id=owner_id, name=rec["name"], description=rec.get("description")
        )
        session.add(wh_row)
        await session.flush()
        warehouse_id_by_name[rec["name"]] = wh_row.id
    return cf_id_by_src, tag_id_by_name, warehouse_id_by_name


async def _insert_items(
    session: AsyncSession,
    owner_id: UUID,
    plan: Plan,
    category_id_by_src: dict[int, int],
    location_id_by_src: dict[int, int],
    warehouse_id_by_name: dict[str, int],
    tag_id_by_name: dict[str, int],
) -> dict[str, UUID]:
    item_id_by_src: dict[str, UUID] = {}
    for rec in plan.records["items"]:
        warehouse_name = rec["warehouse_name"]
        row = Item(
            id=rec["new_id"],
            owner_id=owner_id,
            name=rec["name"],
            description=rec["description"],
            barcode=rec["barcode"],
            category_id=_resolve_ref(rec["category_ref"], category_id_by_src),
            location_id=_resolve_ref(rec["location_ref"], location_id_by_src),
            warehouse_id=warehouse_id_by_name.get(warehouse_name) if warehouse_name else None,
            quantity=rec["quantity"],
            min_quantity=rec["min_quantity"],
            cost=rec["cost"],
            track_batches=rec["track_batches"],
            notes=rec["notes"],
            is_favorite=rec["is_favorite"],
            image_id=None,
            created_at=rec["created_at"],
            updated_at=rec["updated_at"],
        )
        session.add(row)
        item_id_by_src[rec["src_id"]] = rec["new_id"]
    await session.flush()
    for rec in plan.records["items"]:
        for tag_name in rec["tag_names"]:
            tag_id = tag_id_by_name.get(tag_name)
            if tag_id is None:
                continue
            await session.execute(
                insert(item_tags).values(item_id=rec["new_id"], tag_id=tag_id)
            )
    return item_id_by_src


async def _insert_item_children(
    session: AsyncSession,
    plan: Plan,
    item_id_by_src: dict[str, UUID],
    cf_id_by_src: dict[int, int],
) -> None:
    records = plan.records
    for rec in records["item_custom_values"]:
        session.add(
            ItemCustomValue(
                item_id=item_id_by_src[rec["item_src"]],
                custom_field_id=cf_id_by_src[rec["field_src"]],
                value=rec["value"],
            )
        )
    for rec in records["item_batches"]:
        session.add(
            ItemBatch(
                item_id=item_id_by_src[rec["item_src"]],
                quantity=rec["quantity"],
                expiry_date=rec["expiry_date"],
                received_at=rec["received_at"],
                unit_cost=rec["unit_cost"],
                note=rec["note"],
                is_depleted=rec["is_depleted"],
                created_at=rec["created_at"],
            )
        )
    for rec in records["loans"]:
        borrower_user_id = rec["borrower_user_id"]
        session.add(
            ItemLoan(
                item_id=item_id_by_src[rec["item_src"]],
                borrower_user_id=UUID(borrower_user_id) if borrower_user_id else None,
                borrower_label=rec["borrower_label"],
                lent_at=rec["lent_at"],
                expected_return=rec["expected_return"],
                returned_at=rec["returned_at"],
                notes=rec["notes"],
            )
        )
    for rec in records["quantity_logs"]:
        user_id = rec["user_id"]
        session.add(
            QuantityLog(
                item_id=item_id_by_src[rec["item_src"]],
                user_id=UUID(user_id) if user_id else None,
                old_quantity=rec["old_quantity"],
                new_quantity=rec["new_quantity"],
                reason=rec["reason"],
                created_at=rec["created_at"],
            )
        )
    for rec in records["item_versions"]:
        user_id = rec["user_id"]
        session.add(
            ItemVersion(
                item_id=item_id_by_src[rec["item_src"]],
                user_id=UUID(user_id) if user_id else None,
                snapshot=rec["snapshot"],
                created_at=rec["created_at"],
            )
        )
    await session.flush()


async def _insert_lists(session: AsyncSession, owner_id: UUID, plan: Plan) -> None:
    for rec in plan.records["lists"]:
        lst_row = UserList(
            owner_id=owner_id,
            kind=rec["kind"],
            title=rec["title"],
            description=rec["description"],
            start_date=rec["start_date"],
            end_date=rec["end_date"],
            budget=rec["budget"],
            created_at=rec["created_at"],
            updated_at=rec["updated_at"],
        )
        session.add(lst_row)
        await session.flush()
        for entry in rec["entries"]:
            session.add(
                ListEntry(
                    list_id=lst_row.id,
                    position=entry["position"],
                    name=entry["name"],
                    quantity=entry["quantity"],
                    note=entry["note"],
                    price=entry["price"],
                    link=entry["link"],
                    is_done=entry["is_done"],
                    created_at=entry["created_at"],
                )
            )
    await session.flush()


async def _insert_stocktakes(
    session: AsyncSession, owner_id: UUID, plan: Plan, item_id_by_src: dict[str, UUID]
) -> None:
    for rec in plan.records["stocktakes"]:
        st_row = Stocktake(
            owner_id=owner_id,
            name=rec["name"],
            status=rec["status"],
            started_at=rec["started_at"],
            completed_at=rec["completed_at"],
        )
        session.add(st_row)
        await session.flush()
        for scan in rec["items"]:
            session.add(
                StocktakeItem(
                    stocktake_id=st_row.id,
                    item_id=item_id_by_src[scan["item_src"]],
                    expected_quantity=scan["expected_quantity"],
                    actual_quantity=scan["actual_quantity"],
                    note=scan["note"],
                    scanned_at=scan["scanned_at"],
                )
            )
    await session.flush()


async def _insert_webhooks(session: AsyncSession, owner_id: UUID, plan: Plan) -> None:
    for rec in plan.records["webhooks"]:
        session.add(
            Webhook(
                owner_id=owner_id,
                name=rec["name"],
                url=rec["url"],
                secret=rec["secret"],
                events=rec["events"],
                is_active=False,
            )
        )
    await session.flush()


async def _insert_preferences(session: AsyncSession, owner_id: UUID, plan: Plan) -> None:
    for rec in plan.records["notification_preferences"]:
        session.add(
            NotificationPreference(
                user_id=owner_id,
                type=rec["type"],
                channel=rec["channel"],
                enabled=rec["enabled"],
            )
        )
    for rec in plan.records["groups_owned"]:
        session.add(Group(owner_id=owner_id, name=rec["name"]))
    if plan.records["preferences"]:
        user = (await session.execute(select(User).where(User.id == owner_id))).scalar_one()
        prefs = dict(user.preferences or {})
        prefs["currency"] = plan.records["preferences"][0]["currency"]
        user.preferences = prefs
    await session.flush()


async def apply_plan(session: AsyncSession, owner_id: UUID, plan: Plan) -> int:
    """依 plan 寫入（單一交易）；回傳 replace 的實際刪除列數。

    任何例外 → `rollback()` 後重新拋出（route 轉 500）；`backup.import` 稽核
    於 commit 之後寫入（稽核服務自帶 commit）。
    """
    try:
        if plan.mode == "replace":
            plan.deleted_total = await wipe_owner_data(session, owner_id)
        category_id_by_src = await _insert_hierarchy(
            session, owner_id, plan.records["categories"], Category
        )
        location_id_by_src = await _insert_hierarchy(
            session, owner_id, plan.records["locations"], Location
        )
        cf_id_by_src, tag_id_by_name, wh_id_by_name = await _insert_catalogs(
            session, owner_id, plan
        )
        item_id_by_src = await _insert_items(
            session,
            owner_id,
            plan,
            category_id_by_src,
            location_id_by_src,
            wh_id_by_name,
            tag_id_by_name,
        )
        await _insert_item_children(session, plan, item_id_by_src, cf_id_by_src)
        await _insert_lists(session, owner_id, plan)
        await _insert_stocktakes(session, owner_id, plan, item_id_by_src)
        await _insert_webhooks(session, owner_id, plan)
        await _insert_preferences(session, owner_id, plan)
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    await audit_service.log(
        session,
        user_id=owner_id,
        action="backup.import",
        resource_type="backup",
        resource_id=None,
        meta={
            "mode": plan.mode,
            "format_version": plan.format_version,
            "created": {key: plan.summaries[key].created for key in ENTITY_KEYS},
            "deleted_total": plan.deleted_total,
            "errors_total": len(plan.errors),
        },
    )
    return plan.deleted_total
