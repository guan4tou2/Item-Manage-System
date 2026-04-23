"use client"
import { useEffect, useState } from "react"
import { useTranslations } from "next-intl"
import { toast } from "sonner"

import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { useMe, useUpdateProfile } from "@/lib/hooks/use-profile"

export function ProfileForm() {
  const t = useTranslations()
  const me = useMe()
  const update = useUpdateProfile()
  const [email, setEmail] = useState("")
  const [username, setUsername] = useState("")

  useEffect(() => {
    if (me.data) {
      setEmail(me.data.email)
      setUsername(me.data.username)
    }
  }, [me.data])

  const submit = async () => {
    try {
      await update.mutateAsync({ email, username })
      toast.success(t("settings.profile.saved"))
    } catch {
      toast.error(t("settings.profile.conflict"))
    }
  }

  return (
    <form
      onSubmit={(e) => { e.preventDefault(); submit() }}
      className="max-w-md space-y-4"
    >
      <div className="space-y-1">
        <Label htmlFor="email">{t("settings.profile.email")}</Label>
        <Input id="email" type="email" value={email} onChange={(e) => setEmail(e.target.value)} />
      </div>
      <div className="space-y-1">
        <Label htmlFor="username">{t("settings.profile.username")}</Label>
        <Input id="username" value={username} onChange={(e) => setUsername(e.target.value)} />
      </div>
      <Button type="submit" disabled={update.isPending || me.isLoading}>
        {t("settings.profile.save")}
      </Button>
    </form>
  )
}
