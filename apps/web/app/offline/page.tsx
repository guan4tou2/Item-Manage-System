import Link from "next/link"
import { useTranslations } from "next-intl"

export default function OfflinePage() {
  const t = useTranslations()
  return (
    <main className="flex min-h-screen flex-col items-center justify-center gap-4 p-6 text-center">
      <h1 className="text-2xl font-semibold">{t("pwa.offline.title")}</h1>
      <p className="text-muted-foreground">
        {t("pwa.offline.body")}
      </p>
      <Link href="/" className="underline">
        {t("pwa.offline.home")}
      </Link>
    </main>
  )
}
