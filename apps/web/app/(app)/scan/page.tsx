"use client"

import dynamic from "next/dynamic"
import { useTranslations } from "next-intl"

import {
  Breadcrumb,
  BreadcrumbItem,
  BreadcrumbList,
  BreadcrumbPage,
} from "@/components/ui/breadcrumb"

// qr-scanner touches navigator.mediaDevices at module scope, so keep it
// out of the server bundle.
const QrScannerView = dynamic(
  () =>
    import("@/components/scan/qr-scanner-view").then((m) => ({
      default: m.QrScannerView,
    })),
  { ssr: false },
)

export default function ScanPage() {
  const t = useTranslations()
  return (
    <section className="space-y-4 p-6">
      <Breadcrumb>
        <BreadcrumbList>
          <BreadcrumbItem>
            <BreadcrumbPage>{t("nav.scan")}</BreadcrumbPage>
          </BreadcrumbItem>
        </BreadcrumbList>
      </Breadcrumb>

      <h1 className="text-2xl font-semibold">{t("nav.scan")}</h1>
      <p className="text-sm text-muted-foreground">
        將物品標籤對準相機。掃到由本系統產生的 QR 會自動跳轉到該物品頁面。
      </p>

      <QrScannerView />
    </section>
  )
}
