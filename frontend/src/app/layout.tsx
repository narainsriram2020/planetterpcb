import type { Metadata } from 'next'
import { Inter } from 'next/font/google'
import './globals.css'

const inter = Inter({ subsets: ['latin'], display: 'swap' })

export const metadata: Metadata = {
  title: 'Terp Assistant - UMD Course & Professor Guide',
  description: 'Get intelligent recommendations for University of Maryland courses and professors. Powered by PlanetTerp data and Google Gemini AI.',
  keywords: ['UMD', 'University of Maryland', 'courses', 'professors', 'chatbot', 'PlanetTerp', 'Terrapins'],
  authors: [{ name: 'Terp Assistant' }],
  viewport: 'width=device-width, initial-scale=1',
  themeColor: '#E21833',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <head>
        <link rel="icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><text y='.9em' font-size='90'>M</text></svg>" />
      </head>
      <body className={inter.className} suppressHydrationWarning>{children}</body>
    </html>
  )
}
