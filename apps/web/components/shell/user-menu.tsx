"use client"

import Link from "next/link"
import { useState } from "react"
import { useRouter } from "next/navigation"
import { useTranslations } from "next-intl"
import { Languages, LogOut, Palette, Settings, User as UserIcon } from "lucide-react"

import { offlineQueue } from "@/lib/offline/runtime"
import {
  AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent,
  AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle,
} from "@/components/ui/alert-dialog"
import { Avatar, AvatarFallback } from "@/components/ui/avatar"
import { Button } from "@/components/ui/button"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuRadioGroup,
  DropdownMenuRadioItem,
  DropdownMenuSeparator,
  DropdownMenuSub,
  DropdownMenuSubContent,
  DropdownMenuSubTrigger,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import { useCurrentUser, useLogout } from "@/lib/auth/use-auth"
import { locales } from "@/lib/i18n/config"
import { useLocale } from "@/lib/locale/use-locale"

import { ThemeMenuItems } from "./theme-menu-items"

function initials(email: string | undefined): string {
  if (!email) return "?"
  const name = email.split("@")[0] ?? ""
  return name.slice(0, 2).toUpperCase() || "?"
}

export function UserMenu() {
  const t = useTranslations()
  const router = useRouter()
  const user = useCurrentUser()
  const logout = useLogout()
  const [confirmLogout, setConfirmLogout] = useState(false)
  const { locale, setLocale, isSyncing } = useLocale()

  async function handleLogout() {
    if (user) {
      try {
        const rows = await offlineQueue.storage.list(user.id)
        if (rows.length) {
          setConfirmLogout(true)
          return
        }
      } catch {
        // 無法讀取儲存層時仍允許登出；已保存的資料不會被刪除。
      }
    }
    await performLogout()
  }

  async function performLogout() {
    try {
      await logout.mutateAsync()
    } finally {
      // Forced local logout: always redirect even if API call fails.
      // Server-side revocation best-effort; cookie/store clear is handled
      // by useLogout's onSuccess and apiFetch's 401 handler.
      router.push("/login")
    }
  }

  return (
    <>
      <AlertDialog open={confirmLogout} onOpenChange={setConfirmLogout}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>{t("menu.logout")}</AlertDialogTitle>
            <AlertDialogDescription>{t("offline.logoutWarning")}</AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>{t("offline.cancel")}</AlertDialogCancel>
            <AlertDialogAction onClick={() => { void performLogout() }}>{t("menu.logout")}</AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <Button
            variant="ghost"
            size="icon"
            className="relative"
            aria-label={t("a11y.userMenu")}
          >
            <Avatar className="h-8 w-8">
              <AvatarFallback>{initials(user?.email)}</AvatarFallback>
            </Avatar>
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="end" className="w-56">
          <DropdownMenuLabel className="truncate text-xs text-muted-foreground">
            {user?.email ?? ""}
          </DropdownMenuLabel>
          <DropdownMenuSeparator />

          <DropdownMenuItem asChild>
            <Link href="/settings" className="flex items-center gap-2">
              <Settings className="h-4 w-4" />
              {t("menu.profile")}
            </Link>
          </DropdownMenuItem>

          <DropdownMenuSub>
            <DropdownMenuSubTrigger className="flex items-center gap-2">
              <Languages className="h-4 w-4" />
              {t("menu.language")}
            </DropdownMenuSubTrigger>
            <DropdownMenuSubContent>
              <DropdownMenuRadioGroup
                value={locale}
                onValueChange={(v) => setLocale(v as (typeof locales)[number])}
              >
                {locales.map((l) => (
                  <DropdownMenuRadioItem key={l} value={l} disabled={isSyncing}>
                    {t(`locale.${l}` as "locale.zh-TW" | "locale.en")}
                  </DropdownMenuRadioItem>
                ))}
              </DropdownMenuRadioGroup>
            </DropdownMenuSubContent>
          </DropdownMenuSub>

          <DropdownMenuSub>
            <DropdownMenuSubTrigger className="flex items-center gap-2">
              <Palette className="h-4 w-4" />
              {t("menu.theme")}
            </DropdownMenuSubTrigger>
            <DropdownMenuSubContent>
              <ThemeMenuItems />
            </DropdownMenuSubContent>
          </DropdownMenuSub>

          <DropdownMenuSeparator />

          <DropdownMenuItem
            onSelect={() => { void handleLogout() }}
            className="text-destructive focus:text-destructive"
          >
            <LogOut className="mr-2 h-4 w-4" />
            {t("menu.logout")}
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>
    </>
  )
}
