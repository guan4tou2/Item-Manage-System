"use client"

import Link from "next/link"
import { useRef, useState, type PointerEvent } from "react"
import { useTranslations } from "next-intl"
import { toast } from "sonner"

import { AuthImage } from "@/components/common/auth-image"
import { Button } from "@/components/ui/button"
import { Skeleton } from "@/components/ui/skeleton"
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog"
import { uploadImage } from "@/lib/api/images"
import type { LocationUpdate } from "@/lib/api/locations"
import { useAccessToken } from "@/lib/auth/use-auth"
import { useReadOnly } from "@/lib/auth/use-readonly"
import { useLocationTree, useUpdateFloorPlan } from "@/lib/hooks/use-locations"
import {
  adjustRegion,
  dragRegion,
  findPlanNode,
  totalItems,
  type PlanRegion,
  type Point,
} from "@/lib/locations/floor-plan"
import { cn } from "@/lib/utils"

const regionStyle = (r: PlanRegion) => ({
  left: `${r.x * 100}%`,
  top: `${r.y * 100}%`,
  width: `${r.w * 100}%`,
  height: `${r.h * 100}%`,
})

export function FloorPlan({ locationId }: { locationId: number }) {
  const t = useTranslations("locations.plan")
  const tree = useLocationTree()
  const mutation = useUpdateFloorPlan()
  const readOnly = useReadOnly()
  const token = useAccessToken()
  const [editing, setEditing] = useState(false)
  const [selected, setSelected] = useState<number | null>(null)
  const [removeOpen, setRemoveOpen] = useState(false)
  const [uploading, setUploading] = useState(false)
  const [retry, setRetry] = useState(0)
  const [loadedImage, setLoadedImage] = useState<string | null>(null)
  const [preview, setPreview] = useState<PlanRegion | null>(null)
  const drag = useRef<{ start: Point; pointerId: number } | null>(null)
  const fileInput = useRef<HTMLInputElement>(null)
  const node = findPlanNode(tree.data ?? [], locationId)
  const children = node?.children ?? []
  const imageKey = `${node?.floor_plan_image_id}:${retry}`
  const ready = loadedImage === imageKey
  const edit = editing && !readOnly
  const busy = mutation.isPending || uploading

  const save = async (id: number, body: LocationUpdate) => {
    try {
      await mutation.mutateAsync({ id, body })
      return true
    } catch {
      toast.error(t("saveError"))
      return false
    }
  }
  const upload = async (file: File) => {
    if (readOnly || busy) return
    if (
      file.size > 10 * 1024 * 1024 ||
      !["image/png", "image/jpeg", "image/webp", "image/gif"].includes(file.type)
    ) {
      toast.error(t("uploadError"))
      return
    }
    setUploading(true)
    try {
      const image = await uploadImage(file, token)
      await save(locationId, { floor_plan_image_id: image.id })
    } catch {
      toast.error(t("uploadError"))
    } finally {
      setUploading(false)
    }
  }
  const point = (event: PointerEvent<HTMLDivElement>): Point => {
    const bounds = event.currentTarget.getBoundingClientRect()
    return {
      x: (event.clientX - bounds.left) / bounds.width,
      y: (event.clientY - bounds.top) / bounds.height,
    }
  }
  const stopDrag = () => {
    drag.current = null
    setPreview(null)
  }
  const imageError = (
    <div role="alert" className="space-y-3 rounded-sm border p-4">
      <p>{t("loadError")}</p>
      <Button
        variant="outline"
        className="min-h-11"
        onClick={() => {
          stopDrag()
          setRetry((n) => n + 1)
        }}
      >
        {t("retry")}
      </Button>
    </div>
  )
  const skeleton = <Skeleton className="aspect-video w-full" />
  const back = (
    <Link
      className="text-primary inline-flex min-h-11 items-center text-sm underline"
      href="/locations"
    >
      {t("back")}
    </Link>
  )

  return (
    <section className="min-w-0 space-y-6 p-4 sm:p-6">
      {back}
      <h1 className="break-words text-2xl font-semibold">
        {node ? `${node.name} · ${t("title")}` : t("title")}
      </h1>
      {tree.isLoading || tree.isPending ? (
        <div role="status" aria-label={t("loading")} className="space-y-4">
          {skeleton}
          <Skeleton className="h-11 w-full" />
          <Skeleton className="h-11 w-full" />
        </div>
      ) : tree.isError && !node ? (
        <div role="alert">
          <p>{t("treeError")}</p>
          <Button className="min-h-11" onClick={() => void tree.refetch()}>
            {t("retry")}
          </Button>
        </div>
      ) : !node ? (
        <p role="alert">{t("notFound")}</p>
      ) : (
        <>
          {tree.isError && (
            <div role="alert">
              <p>{t("treeError")}</p>
              <Button variant="outline" className="min-h-11" onClick={() => void tree.refetch()}>
                {t("retry")}
              </Button>
            </div>
          )}
          {!readOnly && (
            <div className="flex flex-wrap gap-2">
              {/* 用原生 input：Input 元件自帶 w-full，與 sr-only 疊加會讓頁面水平溢出 */}
              <input
                ref={fileInput}
                type="file"
                accept="image/png,image/jpeg,image/webp,image/gif"
                className="sr-only"
                tabIndex={-1}
                aria-label={t("upload")}
                onChange={(event) => {
                  const file = event.target.files?.[0]
                  if (file) void upload(file)
                  event.target.value = ""
                }}
              />
              <Button
                className="min-h-11"
                disabled={busy}
                onClick={() => fileInput.current?.click()}
              >
                {uploading ? t("uploading") : node.floor_plan_image_id ? t("replace") : t("upload")}
              </Button>
              {node.floor_plan_image_id && (
                <>
                  <Button
                    variant="outline"
                    className="min-h-11"
                    disabled={busy}
                    onClick={() => setRemoveOpen(true)}
                  >
                    {t("remove")}
                  </Button>
                  {children.length > 0 && (
                    <Button
                      variant="outline"
                      className="min-h-11"
                      disabled={busy}
                      onClick={() => {
                        stopDrag()
                        setEditing(!edit)
                      }}
                    >
                      {edit ? t("done") : t("edit")}
                    </Button>
                  )}
                </>
              )}
            </div>
          )}
          {!node.floor_plan_image_id ? (
            <div className="space-y-2 rounded-sm border p-4">
              <p>{t("noPlan")}</p>
              {!readOnly && <p className="text-muted-foreground text-sm">{t("uploadHint")}</p>}
            </div>
          ) : (
            <>
              {!readOnly && <p className="text-muted-foreground text-sm">{t("replaceHint")}</p>}
              {edit && (
                <p id="plan-instructions" className="text-muted-foreground text-sm">
                  {t("instructions")}
                </p>
              )}
              {edit && (
                <div role="group" aria-label={t("children")} className="flex flex-wrap gap-2">
                  {children.map((child) => (
                    <Button
                      key={child.id}
                      variant={selected === child.id ? "secondary" : "outline"}
                      className={cn(
                        "min-h-11",
                        selected === child.id && "ring-ring ring-2 ring-offset-2",
                      )}
                      aria-pressed={selected === child.id}
                      aria-label={`${t("select")} ${child.name}`}
                      disabled={busy}
                      onClick={() => {
                        stopDrag()
                        setSelected(child.id)
                      }}
                    >
                      {child.name}
                      {!child.plan_region && (
                        <span className="text-muted-foreground ml-1 text-xs">
                          {t("unplaced")}
                        </span>
                      )}
                    </Button>
                  ))}
                </div>
              )}
              <div
                className="relative w-full"
                data-testid="floor-plan-canvas"
                style={{ touchAction: edit ? "none" : "auto" }}
                onPointerDown={(event) => {
                  if (!edit || busy || !ready || selected === null || event.button !== 0) return
                  const targetRegion = (event.target as HTMLElement).closest<HTMLButtonElement>(
                    "button[data-region-id]",
                  )
                  if (targetRegion && Number(targetRegion.dataset.regionId) !== selected) return
                  event.preventDefault()
                  drag.current = { start: point(event), pointerId: event.pointerId }
                  event.currentTarget.setPointerCapture(event.pointerId)
                  setPreview(dragRegion(drag.current.start, drag.current.start))
                }}
                onPointerMove={(event) => {
                  if (drag.current?.pointerId === event.pointerId)
                    setPreview(dragRegion(drag.current.start, point(event)))
                }}
                onPointerCancel={stopDrag}
                onLostPointerCapture={stopDrag}
                onPointerUp={(event) => {
                  if (drag.current?.pointerId !== event.pointerId || selected === null) return
                  const end = point(event)
                  if (end.x === drag.current.start.x && end.y === drag.current.start.y) {
                    stopDrag()
                    return
                  }
                  const region = dragRegion(drag.current.start, end)
                  stopDrag()
                  void save(selected, { plan_region: region })
                }}
              >
                <AuthImage
                  key={imageKey}
                  imageId={node.floor_plan_image_id}
                  alt={t("imageAlt", { name: node.name })}
                  className="block h-auto w-full select-none"
                  draggable={false}
                  placeholder={skeleton}
                  fallback={imageError}
                  onLoad={() => setLoadedImage(imageKey)}
                  onError={() => setLoadedImage(null)}
                />
                {ready &&
                  children.map((child) => {
                    const region =
                      edit && selected === child.id && preview ? preview : child.plan_region
                    if (!region) return null
                    const label = t("regionLabel", { name: child.name, count: totalItems(child) })
                    const className = cn(
                      "absolute flex items-start justify-start overflow-hidden border-[1.5px] border-primary bg-primary/10 p-0.5 text-left text-xs font-semibold focus-visible:outline-hidden focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2",
                      edit
                        ? selected === child.id
                          ? "border-2"
                          : "border-muted-foreground"
                        : "hover:bg-primary/20 focus-visible:bg-primary/20",
                    )
                    const content = (
                      <span className="bg-background/90 text-foreground max-w-full truncate rounded-sm px-1 py-0.5 tabular-nums">
                        {label}
                      </span>
                    )
                    return edit ? (
                      <button
                        key={child.id}
                        data-region-id={child.id}
                        type="button"
                        aria-label={label}
                        aria-pressed={selected === child.id}
                        aria-describedby="plan-instructions"
                        className={className}
                        style={regionStyle(region)}
                        onClick={() => setSelected(child.id)}
                        onKeyDown={(event) => {
                          if (
                            busy ||
                            selected !== child.id ||
                            ![
                              "ArrowLeft",
                              "ArrowRight",
                              "ArrowUp",
                              "ArrowDown",
                              "Delete",
                              "Backspace",
                            ].includes(event.key)
                          )
                            return
                          event.preventDefault()
                          event.stopPropagation()
                          void save(child.id, {
                            plan_region: adjustRegion(region, event.key, event.shiftKey),
                          })
                        }}
                      >
                        {content}
                      </button>
                    ) : (
                      <Link
                        key={child.id}
                        href={`/items?location=${child.id}`}
                        aria-label={label}
                        className={className}
                        style={regionStyle(region)}
                      >
                        {content}
                      </Link>
                    )
                  })}
              </div>
              {children.length === 0 ? (
                <p>{t("noChildren")}</p>
              ) : !children.some((child) => child.plan_region) && !edit ? (
                <div className="space-y-2">
                  <p>{t("noRegions")}</p>
                  {!readOnly && (
                    <Button className="min-h-11" onClick={() => setEditing(true)}>
                      {t("start")}
                    </Button>
                  )}
                </div>
              ) : null}
            </>
          )}
          <div className="space-y-2">
            <h2 className="text-sm font-semibold">{t("children")}</h2>
            <ul className="divide-y">
              {children.map((child) => (
                <li key={child.id} className="flex min-w-0 flex-wrap items-center gap-2 py-2">
                  <Link
                    href={`/items?location=${child.id}`}
                    aria-label={t("regionLabel", { name: child.name, count: totalItems(child) })}
                    className="text-primary inline-flex min-h-11 min-w-11 flex-1 items-center break-words text-sm underline"
                  >
                    <span className="min-w-0 break-words tabular-nums">
                      {t("regionLabel", { name: child.name, count: totalItems(child) })}
                    </span>
                  </Link>
                  {!child.plan_region && (
                    <span className="text-muted-foreground text-xs">{t("unplaced")}</span>
                  )}
                  {edit && node.floor_plan_image_id && (
                    <>
                      {child.plan_region && (
                        <Button
                          variant="outline"
                          className="min-h-11"
                          disabled={busy}
                          aria-label={`${t("clear")} ${child.name}`}
                          onClick={() => void save(child.id, { plan_region: null })}
                        >
                          {t("clear")}
                          <span className="sr-only"> {child.name}</span>
                        </Button>
                      )}
                    </>
                  )}
                </li>
              ))}
            </ul>
          </div>
          {!readOnly && (
            <AlertDialog open={removeOpen} onOpenChange={setRemoveOpen}>
              <AlertDialogContent>
                <AlertDialogHeader>
                  <AlertDialogTitle>{t("removeTitle")}</AlertDialogTitle>
                  <AlertDialogDescription>{t("removeDescription")}</AlertDialogDescription>
                </AlertDialogHeader>
                <AlertDialogFooter>
                  <AlertDialogCancel className="min-h-11">{t("cancel")}</AlertDialogCancel>
                  <AlertDialogAction
                    className="min-h-11"
                    disabled={busy}
                    onClick={() => {
                      stopDrag()
                      setEditing(false)
                      void save(locationId, { floor_plan_image_id: null })
                    }}
                  >
                    {t("remove")}
                  </AlertDialogAction>
                </AlertDialogFooter>
              </AlertDialogContent>
            </AlertDialog>
          )}
        </>
      )}
    </section>
  )
}
