"use client"
import { useParams, useRouter } from "next/navigation"
import { useTranslations } from "next-intl"
import { toast } from "sonner"
import { AddMemberDialog } from "@/components/collaboration/add-member-dialog"
import { AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle, AlertDialogTrigger } from "@/components/ui/alert-dialog"
import { Badge } from "@/components/ui/badge"
import { Breadcrumb, BreadcrumbItem, BreadcrumbLink, BreadcrumbList, BreadcrumbPage, BreadcrumbSeparator } from "@/components/ui/breadcrumb"
import { Button } from "@/components/ui/button"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Skeleton } from "@/components/ui/skeleton"
import type { GroupAssignableRole, GroupMember } from "@/lib/api/groups"
import { useDeleteGroup, useGroup, useRemoveGroupMember, useUpdateMemberRole } from "@/lib/hooks/use-groups"
import { useAuthStore } from "@/lib/auth/auth-store"

const ASSIGNABLE_ROLES: GroupAssignableRole[] = ["admin", "editor", "viewer"]

export default function GroupDetailPage() {
  const t = useTranslations()
  const params = useParams()
  const router = useRouter()
  const id = String(params.id)
  const query = useGroup(id)
  const remove = useRemoveGroupMember(id)
  const del = useDeleteGroup()
  const updateRole = useUpdateMemberRole(id)
  const currentUserId = useAuthStore((s) => s.user?.id ?? "")

  if (query.isLoading) return <section className="p-6"><Skeleton className="h-8 w-60" /></section>
  if (!query.data) return <section className="p-6">Not found.</section>
  const g = query.data
  // Phase 30：owner／admin 可管理成員；editor／viewer 僅能檢視角色
  const canManage = g.my_role === "owner" || g.my_role === "admin"

  const changeRole = (member: GroupMember, role: string) => {
    if (role === member.role) return
    updateRole.mutate(
      { userId: member.user_id, role: role as GroupAssignableRole },
      {
        onSuccess: () =>
          toast.success(t("collab.groups.detail.roleChanged", { username: member.username })),
        onError: () => toast.error(t("collab.groups.detail.changeRoleFailed")),
      },
    )
  }

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
        <div className="flex items-center justify-between gap-3">
          <div>
            <h2 className="text-lg font-semibold">{t("collab.groups.memberCount", { count: g.member_count })}</h2>
            {canManage ? (
              <p className="text-xs text-muted-foreground">{t("collab.roles.hint")}</p>
            ) : null}
          </div>
          {canManage ? <AddMemberDialog groupId={id} /> : null}
        </div>
        <ul className="divide-y rounded-sm border">
          {g.members.map((m) => (
            <li key={m.user_id} className="flex items-center justify-between gap-3 p-3">
              <span className="min-w-0 truncate font-medium">{m.username}</span>
              <div className="flex shrink-0 items-center gap-2">
                {m.role === "owner" ? (
                  <Badge variant="secondary">{t("collab.roles.owner")}</Badge>
                ) : canManage ? (
                  <Select
                    value={m.role}
                    onValueChange={(role) => changeRole(m, role)}
                    disabled={updateRole.isPending}
                  >
                    <SelectTrigger
                      className="h-9 w-32"
                      aria-label={t("collab.groups.detail.roleFor", { username: m.username })}
                    >
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {ASSIGNABLE_ROLES.map((role) => (
                        <SelectItem key={role} value={role}>{t(`collab.roles.${role}`)}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                ) : (
                  <Badge variant="outline">{t(`collab.roles.${m.role}`)}</Badge>
                )}
                {canManage && m.role !== "owner" ? (
                  <Button variant="ghost" size="sm" onClick={() => remove.mutate(m.user_id)}>{t("collab.groups.detail.removeMember")}</Button>
                ) : null}
              </div>
            </li>
          ))}
        </ul>
      </div>
    </section>
  )
}
