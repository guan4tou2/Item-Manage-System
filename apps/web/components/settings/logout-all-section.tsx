"use client"
import { useRouter } from "next/navigation"
import { useTranslations } from "next-intl"
import { toast } from "sonner"

import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog"
import { Button } from "@/components/ui/button"
import { useLogoutAll } from "@/lib/auth/use-auth"

export function LogoutAllSection() {
  const t = useTranslations("settings.password.logoutAll")
  const router = useRouter()
  const logoutAll = useLogoutAll()

  const confirm = async () => {
    try {
      await logoutAll.mutateAsync()
      // 成功後 store 已清空；對齊 user-menu 的登出做法導回登入頁
      router.push("/login")
    } catch {
      toast.error(t("failed"))
    }
  }

  return (
    <section className="max-w-md space-y-3 border-t pt-6">
      <h2 className="text-base font-semibold">{t("title")}</h2>
      <p className="text-sm text-muted-foreground">{t("description")}</p>
      <AlertDialog>
        <AlertDialogTrigger asChild>
          <Button type="button" variant="destructive" disabled={logoutAll.isPending}>
            {t("button")}
          </Button>
        </AlertDialogTrigger>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>{t("confirmTitle")}</AlertDialogTitle>
            <AlertDialogDescription>{t("confirmBody")}</AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>{t("cancel")}</AlertDialogCancel>
            <AlertDialogAction onClick={confirm}>{t("confirm")}</AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </section>
  )
}
