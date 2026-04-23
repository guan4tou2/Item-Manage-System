"use client"
import { useState } from "react"
import { useTranslations } from "next-intl"
import { toast } from "sonner"

import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { useChangePassword } from "@/lib/hooks/use-profile"

export function PasswordForm() {
  const t = useTranslations()
  const change = useChangePassword()
  const [current, setCurrent] = useState("")
  const [next, setNext] = useState("")
  const [confirm, setConfirm] = useState("")
  const mismatch = next !== "" && confirm !== "" && next !== confirm

  const submit = async () => {
    if (mismatch || next.length < 8) return
    try {
      await change.mutateAsync({ current_password: current, new_password: next })
      toast.success(t("settings.password.saved"))
      setCurrent(""); setNext(""); setConfirm("")
    } catch {
      toast.error(t("settings.password.wrongCurrent"))
    }
  }

  return (
    <form
      onSubmit={(e) => { e.preventDefault(); submit() }}
      className="max-w-md space-y-4"
    >
      <div className="space-y-1">
        <Label htmlFor="current">{t("settings.password.current")}</Label>
        <Input id="current" type="password" value={current} onChange={(e) => setCurrent(e.target.value)} />
      </div>
      <div className="space-y-1">
        <Label htmlFor="next">{t("settings.password.new")}</Label>
        <Input id="next" type="password" value={next} onChange={(e) => setNext(e.target.value)} />
      </div>
      <div className="space-y-1">
        <Label htmlFor="confirm">{t("settings.password.confirm")}</Label>
        <Input id="confirm" type="password" value={confirm} onChange={(e) => setConfirm(e.target.value)} />
        {mismatch ? <p className="text-sm text-destructive">{t("settings.password.mismatch")}</p> : null}
      </div>
      <Button type="submit" disabled={change.isPending || mismatch || !current || next.length < 8}>
        {t("settings.password.save")}
      </Button>
    </form>
  )
}
