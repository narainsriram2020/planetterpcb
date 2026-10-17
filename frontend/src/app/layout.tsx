import type { Metadata, Viewport } from 'next'
import { Inter } from 'next/font/google'
import './globals.css'

const inter = Inter({ subsets: ['latin'], display: 'swap' })

export const metadata: Metadata = {
  title: 'TerpAdvisor - AI Course Advisor for UMD',
  description: 'Ask about University of Maryland courses, professors, and grade distributions. Answers are grounded in PlanetTerp data.',
  keywords: ['UMD', 'University of Maryland', 'courses', 'professors', 'chatbot', 'PlanetTerp', 'Terrapins'],
  authors: [{ name: 'TerpAdvisor' }],
}

export const viewport: Viewport = {
  width: 'device-width',
  initialScale: 1,
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
        <link rel="icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><text y='.9em' font-size='90'>🐢</text></svg>" />
      </head>
      <body className={inter.className} suppressHydrationWarning>{children}</body>
    </html>
  )
}
