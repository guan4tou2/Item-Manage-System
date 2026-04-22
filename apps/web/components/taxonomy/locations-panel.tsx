"use client"

import { Trash2 } from "lucide-react"
import { useTranslations } from "next-intl"
import { useState } from "react"
import { toast } from "sonner"

import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import {
  useCreateLocation, useDeleteLocation, useLocations,
} from "@/lib/hooks/use-locations"

export function LocationsPanel() {
  const t = useTranslations()
  const locs = useLocations()
  const create = useCreateLocation()
  const del = useDeleteLocation()
  const [floor, setFloor] = useState("")
  const [room, setRoom] = useState("")
  const [zone, setZone] = useState("")

  async function handleAdd() {
    if (!floor.trim()) return
    try {
      await create.mutateAsync({
        floor: floor.trim(),
        room: room.trim() || null,
        zone: zone.trim() || null,
      })
      setFloor(""); setRoom(""); setZone("")
    } catch {
      toast.error(t("items.toast.saveFailed"))
    }
  }

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-1 sm:grid-cols-4 gap-2">
        <Input value={floor} onChange={(e) => setFloor(e.target.value)}
               placeholder={t("taxonomy.locations.floor")} aria-label={t("taxonomy.locations.floor")} />
        <Input value={room} onChange={(e) => setRoom(e.target.value)}
               placeholder={t("taxonomy.locations.room")} aria-label={t("taxonomy.locations.room")} />
        <Input value={zone} onChange={(e) => setZone(e.target.value)}
               placeholder={t("taxonomy.locations.zone")} aria-label={t("taxonomy.locations.zone")} />
        <Button onClick={handleAdd} disabled={create.isPending || !floor.trim()}>
          {t("taxonomy.locations.add")}
        </Button>
      </div>

      {(locs.data ?? []).length === 0 ? (
        <p className="text-muted-foreground">{t("taxonomy.locations.empty")}</p>
      ) : (
        <ul className="space-y-1">
          {(locs.data ?? []).map((l) => (
            <li key={l.id} className="flex items-center justify-between border rounded px-3 py-2">
              <span>{[l.floor, l.room, l.zone].filter(Boolean).join(" / ")}</span>
              <Button
                variant="ghost" size="sm"
                onClick={() => {
                  if (confirm(t("taxonomy.locations.confirmDelete"))) {
                    del.mutate(l.id)
                  }
                }}
                aria-label={t("taxonomy.locations.delete")}
              >
                <Trash2 className="h-4 w-4" />
                <span className="sr-only">{t("taxonomy.locations.delete")}</span>
              </Button>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
