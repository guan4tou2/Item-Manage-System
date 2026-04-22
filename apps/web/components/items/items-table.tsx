"use client"

import Link from "next/link"
import { useTranslations } from "next-intl"

import { Badge } from "@/components/ui/badge"
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from "@/components/ui/table"
import type { ItemRead } from "@/lib/api/items"

export function ItemsTable({ items }: { items: ItemRead[] }) {
  const t = useTranslations()
  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>{t("items.list.columnName")}</TableHead>
          <TableHead>{t("items.list.columnCategory")}</TableHead>
          <TableHead>{t("items.list.columnLocation")}</TableHead>
          <TableHead className="text-right">{t("items.list.columnQuantity")}</TableHead>
          <TableHead>{t("items.list.columnTags")}</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {items.map((i) => (
          <TableRow key={i.id}>
            <TableCell>
              <Link className="font-medium underline-offset-2 hover:underline" href={`/items/${i.id}`}>
                {i.name}
              </Link>
            </TableCell>
            <TableCell>{i.category?.name ?? "—"}</TableCell>
            <TableCell>
              {i.location ? [i.location.floor, i.location.room, i.location.zone].filter(Boolean).join(" / ") : "—"}
            </TableCell>
            <TableCell className="text-right tabular-nums">{i.quantity}</TableCell>
            <TableCell className="space-x-1">
              {i.tags.map((tag) => <Badge key={tag.id} variant="secondary">{tag.name}</Badge>)}
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  )
}
