"use client"

import { useState } from "react"
import { useRouter } from "next/navigation"
import { useTranslations } from "next-intl"

import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { useLogin } from "@/lib/auth/use-auth"

export function LoginForm() {
  const t = useTranslations()
  const router = useRouter()
  const login = useLogin()
  const [username, setUsername] = useState("")
  const [password, setPassword] = useState("")
  const [error, setError] = useState<string | null>(null)

  async function onSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setError(null)
    try {
      await login.mutateAsync({ username, password })
      router.push("/dashboard")
    } catch {
      // Coarse-grained for now — refine once we have distinct error copy
      setError(t("login.error"))
    }
  }

  return (
    <form onSubmit={onSubmit} className="mx-auto flex w-full max-w-sm flex-col gap-4">
      <h1 className="text-2xl font-bold">{t("login.title")}</h1>
      <div className="flex flex-col gap-1.5">
        <Label htmlFor="username">{t("login.username")}</Label>
        <Input
          id="username"
          name="username"
          autoComplete="username"
          required
          value={username}
          onChange={(e) => setUsername(e.target.value)}
        />
      </div>
      <div className="flex flex-col gap-1.5">
        <Label htmlFor="password">{t("login.password")}</Label>
        <Input
          id="password"
          name="password"
          type="password"
          autoComplete="current-password"
          required
          value={password}
          onChange={(e) => setPassword(e.target.value)}
        />
      </div>
      {error && (
        <p role="alert" className="text-sm text-destructive">
          {error}
        </p>
      )}
      <Button type="submit" disabled={login.isPending}>
        {login.isPending ? t("login.submitting") : t("login.submit")}
      </Button>
    </form>
  )
}
