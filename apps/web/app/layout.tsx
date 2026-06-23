import type { Viewport } from 'next'
import { Inter } from 'next/font/google'
import { NextIntlClientProvider } from 'next-intl'
import { getLocale, getMessages, getTranslations } from 'next-intl/server'

import './globals.css'
import { ServiceWorkerProvider } from '@/components/pwa/service-worker-provider'
import { Providers } from './providers'

const inter = Inter({
  subsets: ['latin'],
  variable: '--font-sans',
  display: 'swap',
})

export async function generateMetadata() {
  const t = await getTranslations()
  return {
    title: t('appName'),
    description: t('landing.tagline'),
    manifest: '/manifest.webmanifest',
    applicationName: 'IMS',
    appleWebApp: {
      capable: true,
      title: 'IMS',
      statusBarStyle: 'default' as const,
    },
    icons: {
      apple: [
        { url: '/icons/icon-192.png', sizes: '192x192', type: 'image/png' },
        { url: '/icons/icon-512.png', sizes: '512x512', type: 'image/png' },
      ],
    },
    formatDetection: {
      telephone: false,
    },
  }
}

export const viewport: Viewport = {
  themeColor: '#2563eb',
  width: 'device-width',
  initialScale: 1,
  viewportFit: 'cover',
}

export default async function RootLayout({ children }: { children: React.ReactNode }) {
  const locale = await getLocale()
  const messages = await getMessages()

  return (
    <html lang={locale === 'zh-TW' ? 'zh-Hant' : 'en'} suppressHydrationWarning>
      <body className={`${inter.variable} bg-background min-h-screen font-sans antialiased`}>
        <NextIntlClientProvider locale={locale} messages={messages}>
          <Providers>
            {children}
            <ServiceWorkerProvider />
          </Providers>
        </NextIntlClientProvider>
      </body>
    </html>
  )
}
