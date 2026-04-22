import { getRequestConfig } from "next-intl/server"
import { cookies, headers } from "next/headers"

import { defaultLocale, normalizeLocale } from "./config"

export default getRequestConfig(async () => {
  const cookieStore = await cookies()
  const headerStore = await headers()

  const cookieLocale = cookieStore.get("ims_locale")?.value
  const acceptLang = headerStore.get("accept-language") ?? ""
  const locale = normalizeLocale(cookieLocale ?? acceptLang) || defaultLocale

  const messages = (await import(`../../messages/${locale}.json`)).default

  return { locale, messages }
})
