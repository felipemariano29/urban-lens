import type { Metadata } from 'next'
import { Analytics } from '@vercel/analytics/next'
import { IBM_Plex_Mono, Space_Grotesk } from 'next/font/google'
import type { ReactNode } from 'react'

import { ApiKeyProvider } from '@/contexts/api-key-context'
import './globals.css'

const sansFont = Space_Grotesk({
  subsets: ['latin'],
  variable: '--font-ui-sans',
})

const monoFont = IBM_Plex_Mono({
  subsets: ['latin'],
  variable: '--font-ui-mono',
  weight: ['400', '500'],
})

export const metadata: Metadata = {
  title: 'Urban Lens Analytics',
  description: 'Workspace governado para analytics, consulta RAG e evidencias de seguranca urbana.',
  icons: {
    icon: [
      {
        url: '/icon.svg',
        type: 'image/svg+xml',
      },
    ],
    apple: '/apple-icon.png',
  },
}

export default function RootLayout({
  children,
}: Readonly<{
  children: ReactNode
}>) {
  return (
    <html lang="pt-BR" className="dark bg-background">
      <body className={`${sansFont.variable} ${monoFont.variable} font-sans antialiased`}>
        <ApiKeyProvider>{children}</ApiKeyProvider>
        {process.env.NODE_ENV === 'production' && <Analytics />}
      </body>
    </html>
  )
}
