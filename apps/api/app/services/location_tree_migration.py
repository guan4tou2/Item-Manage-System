"""舊平面 `locations`（floor/room/zone）→ 樹的一次性資料遷移。

- 僅用 SQLAlchemy Core `text()`（PG／SQLite 通用）；`owner_id` 原樣傳遞。
- `analyze_flat()`＝唯讀 dry-run（遷移前審查）；`migrate_flat()`＝實際寫入。
- 語義：對每個 owner 建立 canonical 節點鏈（深度 1→`floor`、2→`room`、≥3→`other`），
  把舊列的物品**重新指向**最深節點後刪除舊列 → **物品保證無孤兒**。
  `room`／`zone` 為 NULL 時只建到該深度；`floor` 為空的異常列僅移除
  （其物品明確設為未指派）。
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Sequence

import sqlalchemy as sa
from sqlalchemy.engine import Connection

KIND_BY_DEPTH = {1: "floor", 2: "room"}

_PathKey = tuple[Any, tuple[str, ...]]


@dataclass
class MigrationReport:
    """遷移報告（analyze 與 migrate 同形狀）。"""

    source_rows: int = 0
    created_nodes: int = 0
    merged_rows: int = 0
    orphan_nodes: int = 0
    unassigned_items: int = 0

    def as_dict(self) -> dict[str, int]:
        return asdict(self)


@dataclass(frozen=True)
class _PlanNode:
    owner_id: Any
    parent_path: tuple[str, ...]
    name: str
    kind: str

    @property
    def path(self) -> tuple[str, ...]:
        return (*self.parent_path, self.name)


@dataclass
class _Plan:
    nodes: list[_PlanNode]
    row_targets: dict[int, _PlanNode]
    degenerate_rows: list[int]
    report: MigrationReport


def _read_rows(conn: Connection) -> Sequence[sa.Row]:
    return conn.execute(
        sa.text(
            "SELECT id, owner_id, floor, room, zone FROM locations "
            "ORDER BY owner_id, sort_order, "
            "floor NULLS FIRST, room NULLS FIRST, zone NULLS FIRST, id"
        )
    ).all()


def _parts(floor: str | None, room: str | None, zone: str | None) -> list[str]:
    out: list[str] = []
    for value in (floor, room, zone):
        text_value = (value or "").strip()
        if text_value:
            out.append(text_value)
    return out


def _build_plan(conn: Connection) -> _Plan:
    nodes: list[_PlanNode] = []
    index: dict[_PathKey, _PlanNode] = {}
    completed_paths: set[_PathKey] = set()
    row_targets: dict[int, _PlanNode] = {}
    degenerate: list[int] = []
    report = MigrationReport()

    for row in _read_rows(conn):
        row_id = int(row.id)
        report.source_rows += 1
        parts = _parts(row.floor, row.room, row.zone)
        if not parts:
            degenerate.append(row_id)
            continue

        parent: tuple[str, ...] = ()
        target: _PlanNode | None = None
        for depth, name in enumerate(parts, start=1):
            key = (row.owner_id, (*parent, name))
            node = index.get(key)
            if node is None:
                node = _PlanNode(
                    owner_id=row.owner_id,
                    parent_path=parent,
                    name=name,
                    kind=KIND_BY_DEPTH.get(depth, "other"),
                )
                nodes.append(node)
                index[key] = node
            target = node
            parent = (*parent, name)

        assert target is not None
        row_targets[row_id] = target
        full_key = (row.owner_id, tuple(parts))
        if full_key in completed_paths:
            report.merged_rows += 1  # 同 owner 同組合的重複列 → 併入既有節點
        completed_paths.add(full_key)

    return _Plan(
        nodes=nodes, row_targets=row_targets, degenerate_rows=degenerate, report=report
    )


def _finalize_report(conn: Connection, plan: _Plan) -> MigrationReport:
    report = plan.report
    report.created_nodes = len(plan.nodes)

    item_counts = dict(
        conn.execute(
            sa.text(
                "SELECT location_id, count(*) FROM items "
                "WHERE location_id IS NOT NULL GROUP BY location_id"
            )
        ).all()
    )
    report.unassigned_items = int(
        conn.execute(
            sa.text("SELECT count(*) FROM items WHERE location_id IS NULL")
        ).scalar_one()
    )

    nodes_with_items: set[_PathKey] = set()
    for row_id, node in plan.row_targets.items():
        if item_counts.get(row_id, 0):
            nodes_with_items.add((node.owner_id, node.path))
    node_keys = {(node.owner_id, node.path) for node in plan.nodes}
    parents_with_children = {
        (node.owner_id, node.parent_path) for node in plan.nodes if node.parent_path
    }
    report.orphan_nodes = sum(
        1
        for key in node_keys
        if key not in nodes_with_items and key not in parents_with_children
    )
    return report


def analyze_flat(conn: Connection) -> MigrationReport:
    """唯讀：回傳遷移後會產生的報告（不寫入任何資料）。"""
    return _finalize_report(conn, _build_plan(conn))


def preview_paths(conn: Connection) -> list[str]:
    """唯讀：遷移後的 canonical 路徑清單（審查用）。"""
    plan = _build_plan(conn)
    return [" / ".join(node.path) for node in plan.nodes]


def _existing_node_id(
    conn: Connection, node: _PlanNode, parent_id: int | None
) -> int | None:
    if parent_id is None:
        stmt = sa.text(
            "SELECT id FROM locations WHERE owner_id = :o AND name = :n "
            "AND parent_id IS NULL"
        )
    else:
        stmt = sa.text(
            "SELECT id FROM locations WHERE owner_id = :o AND name = :n "
            "AND parent_id = :p"
        )
    params: dict[str, Any] = {"o": node.owner_id, "n": node.name}
    if parent_id is not None:
        params["p"] = parent_id
    return conn.execute(stmt, params).scalar_one_or_none()


def _insert_nodes(conn: Connection, plan: _Plan) -> dict[_PathKey, int]:
    node_ids: dict[_PathKey, int] = {}
    sibling_counters: dict[_PathKey, int] = {}

    for node in plan.nodes:
        parent_key = (node.owner_id, node.parent_path)
        parent_id = None if not node.parent_path else node_ids[parent_key]

        existing = _existing_node_id(conn, node, parent_id)
        if existing is not None:
            node_ids[(node.owner_id, node.path)] = int(existing)
            continue

        sort_order = sibling_counters.get(parent_key, 0)
        sibling_counters[parent_key] = sort_order + 1
        new_id = conn.execute(
            sa.text(
                "INSERT INTO locations (owner_id, parent_id, name, kind, sort_order) "
                "VALUES (:o, :p, :n, :k, :s) RETURNING id"
            ),
            {
                "o": node.owner_id,
                "p": parent_id,
                "n": node.name,
                "k": node.kind,
                "s": sort_order,
            },
        ).scalar_one()
        node_ids[(node.owner_id, node.path)] = int(new_id)

    return node_ids


def migrate_flat(conn: Connection) -> MigrationReport:
    """執行遷移：建 canonical 節點 → 物品重新指向 → 刪除舊列；回傳報告。"""
    plan = _build_plan(conn)
    report = _finalize_report(conn, plan)

    if plan.nodes:
        node_ids = _insert_nodes(conn, plan)

        targets: dict[_PathKey, list[int]] = {}
        for row_id, node in plan.row_targets.items():
            targets.setdefault((node.owner_id, node.path), []).append(row_id)
        for key, row_ids in targets.items():
            conn.execute(
                sa.text(
                    "UPDATE items SET location_id = :target "
                    "WHERE location_id IN :ids"
                ).bindparams(sa.bindparam("ids", expanding=True)),
                {"target": node_ids[key], "ids": row_ids},
            )

    if plan.degenerate_rows:
        conn.execute(
            sa.text(
                "UPDATE items SET location_id = NULL WHERE location_id IN :ids"
            ).bindparams(sa.bindparam("ids", expanding=True)),
            {"ids": plan.degenerate_rows},
        )

    source_ids = [*plan.row_targets.keys(), *plan.degenerate_rows]
    if source_ids:
        conn.execute(
            sa.text("DELETE FROM locations WHERE id IN :ids").bindparams(
                sa.bindparam("ids", expanding=True)
            ),
            {"ids": source_ids},
        )

    return report
