import Link from "next/link"

export default function OfflinePage() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center gap-4 p-6 text-center">
      <h1 className="text-2xl font-semibold">離線中</h1>
      <p className="text-muted-foreground">
        目前無法連線到伺服器。請檢查網路後再試。
      </p>
      <Link href="/" className="underline">
        回首頁
      </Link>
    </main>
  )
}
