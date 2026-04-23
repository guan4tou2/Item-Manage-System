"use client"
import { useSearchParams } from "next/navigation"
import { useState, useEffect } from "react"
import { useTranslations } from "next-intl"
import { GroupCard } from "@/components/collaboration/group-card"
import { NewGroupDialog } from "@/components/collaboration/new-group-dialog"
import { TransferCard } from "@/components/collaboration/transfer-card"
import { Breadcrumb, BreadcrumbItem, BreadcrumbList, BreadcrumbPage } from "@/components/ui/breadcrumb"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { useGroups } from "@/lib/hooks/use-groups"
import { useTransfers } from "@/lib/hooks/use-transfers"
import { useAuthStore } from "@/lib/auth/auth-store"

export default function CollaborationPage() {
  const t = useTranslations()
  const sp = useSearchParams()
  const [tab, setTab] = useState<"groups" | "transfers">(() => (sp.get("tab") === "transfers" ? "transfers" : "groups"))
  useEffect(() => {
    const q = sp.get("tab")
    if (q === "transfers" || q === "groups") setTab(q)
  }, [sp])
  const groups = useGroups()
  const transfers = useTransfers()
  const userId = useAuthStore((s) => s.user?.id ?? "")

  return (
    <section className="space-y-6 p-6">
      <Breadcrumb><BreadcrumbList><BreadcrumbItem><BreadcrumbPage>{t("collab.title")}</BreadcrumbPage></BreadcrumbItem></BreadcrumbList></Breadcrumb>
      <h1 className="text-2xl font-semibold">{t("collab.title")}</h1>
      <Tabs value={tab} onValueChange={(v) => setTab(v as "groups" | "transfers")}>
        <TabsList>
          <TabsTrigger value="groups">{t("collab.tabs.groups")}</TabsTrigger>
          <TabsTrigger value="transfers">{t("collab.tabs.transfers")}</TabsTrigger>
        </TabsList>
        <TabsContent value="groups" className="space-y-4">
          <div className="flex justify-end"><NewGroupDialog /></div>
          {(groups.data?.length ?? 0) === 0 ? (
            <p className="text-sm text-muted-foreground">{t("collab.groups.empty")}</p>
          ) : (
            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
              {groups.data?.map((g) => <GroupCard key={g.id} row={g} />)}
            </div>
          )}
        </TabsContent>
        <TabsContent value="transfers" className="space-y-4">
          {(transfers.data?.length ?? 0) === 0 ? (
            <p className="text-sm text-muted-foreground">{t("collab.transfers.empty")}</p>
          ) : (
            <div className="grid gap-4 md:grid-cols-2">
              {transfers.data?.map((r) => <TransferCard key={r.id} row={r} currentUserId={userId} />)}
            </div>
          )}
        </TabsContent>
      </Tabs>
    </section>
  )
}
