import type { Metadata } from "next"

import { PublicListClient } from "./public-list-client"

export const metadata: Metadata = {
  robots: { index: false, follow: false },
  referrer: "no-referrer",
}

export default function SharePage() {
  return <PublicListClient />
}
