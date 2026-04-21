import Link from 'next/link'

import { Button } from '@/components/ui/button'

export default function HomePage() {
  return (
    <main className="container flex min-h-screen flex-col items-center justify-center gap-6 py-24">
      <h1 className="text-4xl font-bold tracking-tight">物品管理系統 v2</h1>
      <p className="text-muted-foreground">骨架已就緒。下一步：#1 設計系統。</p>
      <div className="flex gap-3">
        <Button asChild>
          <Link href="/login">登入</Link>
        </Button>
        <Button variant="outline" asChild>
          <a href="/api/docs" target="_blank" rel="noreferrer">API 文件</a>
        </Button>
      </div>
    </main>
  )
}
