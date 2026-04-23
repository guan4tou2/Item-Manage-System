"use client"
import { useParams, useRouter } from "next/navigation"
import { useTranslations } from "next-intl"
import { AddMemberDialog } from "@/components/collaboration/add-member-dialog"
import { AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle, AlertDialogTrigger } from "@/components/ui/alert-dialog"
import { Breadcrumb, BreadcrumbItem, BreadcrumbLink, BreadcrumbList, BreadcrumbPage, BreadcrumbSeparator } from "@/components/ui/breadcrumb"
import { Button } from "@/components/ui/button"
import { Skeleton } from "@/components/ui/skeleton"
import { useDeleteGroup, useGroup, useRemoveGroupMember } from "@/lib/hooks/use-groups"
import { useAuthStore } from "@/lib/auth/auth-store"

export default function GroupDetailPage() {
  const t = useTranslations()
  const params = useParams()
  const router = useRouter()
  const id = String(params.id)
  const query = useGroup(id)
  const remove = useRemoveGroupMember(id)
  const del = useDeleteGroup()
  const currentUserId = useAuthStore((s) => s.user?.id ?? "")

  if (query.isLoading) return <section className="p-6"><Skeleton className="h-8 w-60" /></section>
  if (!query.data) return <section className="p-6">Not found.</section>
  const g = query.data

  return (
    <section className="space-y-6 p-6">
      <Breadcrumb>
        <BreadcrumbList>
          <BreadcrumbItem><BreadcrumbLink href="/collaboration">{t("collab.title")}</BreadcrumbLink></BreadcrumbItem>
          <BreadcrumbSeparator />
          <BreadcrumbItem><BreadcrumbPage>{g.name}</BreadcrumbPage></BreadcrumbItem>
        </BreadcrumbList>
      </Breadcrumb>
      <div className="flex items-start justify-between">
        <h1 className="text-2xl font-semibold">{g.name}</h1>
        {g.is_owner ? (
          <AlertDialog>
            <AlertDialogTrigger asChild><Button variant="outline" size="sm">{t("collab.groups.detail.delete")}</Button></AlertDialogTrigger>
            <AlertDialogContent>
              <AlertDialogHeader>
                <AlertDialogTitle>{t("collab.groups.detail.delete")}</AlertDialogTitle>
                <AlertDialogDescription>{t("collab.groups.detail.confirmDelete")}</AlertDialogDescription>
              </AlertDialogHeader>
              <AlertDialogFooter>
                <AlertDialogCancel>{t("lists.new.cancel")}</AlertDialogCancel>
                <AlertDialogAction onClick={async () => { await del.mutateAsync(id); router.push("/collaboration") }}>{t("collab.groups.detail.delete")}</AlertDialogAction>
              </AlertDialogFooter>
            </AlertDialogContent>
          </AlertDialog>
        ) : (
          <Button variant="outline" size="sm" onClick={async () => { await remove.mutateAsync(currentUserId); router.push("/collaboration") }}>
            {t("collab.groups.detail.leave")}
          </Button>
        )}
      </div>

      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-semibold">{t("collab.groups.memberCount", { count: g.member_count })}</h2>
          {g.is_owner ? <AddMemberDialog groupId={id} /> : null}
        </div>
        <ul className="divide-y rounded border">
          {g.members.map((m) => (
            <li key={m.user_id} className="flex items-center justify-between p-3">
              <div>
                <span className="font-medium">{m.username}</span>
                {m.user_id === g.owner_id ? <span className="ml-2 text-xs text-muted-foreground">({t("collab.groups.youAreOwner")})</span> : null}
              </div>
              {g.is_owner && m.user_id !== g.owner_id ? (
                <Button variant="ghost" size="sm" onClick={() => remove.mutate(m.user_id)}>{t("collab.groups.detail.removeMember")}</Button>
              ) : null}
            </li>
          ))}
        </ul>
      </div>
    </section>
  )
}
