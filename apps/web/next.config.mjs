import createNextIntlPlugin from "next-intl/plugin"

const withNextIntl = createNextIntlPlugin("./lib/i18n/request.ts")

/** @type {import('next').NextConfig} */
const nextConfig = {
  output: "standalone",
  reactStrictMode: true,
  typedRoutes: true,
  // `app/__dev` 會因 Next 的私有資料夾規則（`_` 前綴）永遠不路由，
  // 因此實體目錄改放 `app/dev`，再由 rewrite 保留對外的 /__dev/* 路徑。
  // 該頁面本身仍由 NEXT_PUBLIC_ENABLE_DEV_ROUTES 控制，生產環境預設 404。
  async rewrites() {
    return [{ source: "/__dev/:path*", destination: "/dev/:path*" }]
  },
}

export default withNextIntl(nextConfig)
