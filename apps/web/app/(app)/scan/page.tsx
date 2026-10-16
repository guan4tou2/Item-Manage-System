"use client"

import dynamic from "next/dynamic"
import { useTranslations } from "next-intl"

import {
  Breadcrumb,
  BreadcrumbItem,
  BreadcrumbList,
  BreadcrumbPage,
} from "@/components/ui/breadcrumb"

// 掃描引擎（原生 BarcodeDetector／@zxing/browser）僅存在於瀏覽器環境，
// 保持 client-only 動態載入以免進 server bundle。
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
    <section className="space-y-6 p-6">
      <Breadcrumb>
        <BreadcrumbList>
          <BreadcrumbItem>
            <BreadcrumbPage>{t("nav.scan")}</BreadcrumbPage>
          </BreadcrumbItem>
        </BreadcrumbList>
      </Breadcrumb>

      <h1 className="text-2xl font-semibold">{t("nav.scan")}</h1>
      <p className="text-sm text-muted-foreground">
        {t("scan.instruction")}
      </p>

      <QrScannerView />
    </section>
  )
}
