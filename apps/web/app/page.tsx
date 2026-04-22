import Link from "next/link"
import { useTranslations } from "next-intl"

import { Button } from "@/components/ui/button"

// middleware 已處理：已登入訪問 `/` → redirect `/dashboard`
export default function HomePage() {
  const t = useTranslations()
  return (
    <main className="container flex min-h-screen flex-col items-center justify-center gap-6 py-24">
      <h1 className="text-4xl font-bold tracking-tight">{t("appName")}</h1>
      <p className="text-muted-foreground">{t("landing.tagline")}</p>
      <div className="flex gap-3">
        <Button asChild>
          <Link href="/login">{t("landing.ctaLogin")}</Link>
        </Button>
        <Button variant="outline" asChild>
          <a href="/api/docs" target="_blank" rel="noreferrer">
            {t("landing.ctaDocs")}
          </a>
        </Button>
      </div>
    </main>
  )
}
