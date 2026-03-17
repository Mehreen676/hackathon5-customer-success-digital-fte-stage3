import type { Metadata } from 'next'
import { Inter } from 'next/font/google'
import './globals.css'

const inter = Inter({ subsets: ['latin'], variable: '--font-inter' })

export const metadata: Metadata = {
  title: 'Nexora Support Dashboard | Customer Success FTE',
  description:
    'Stage 3 AI-powered Customer Success dashboard for Nexora. ' +
    'Monitor conversations, tickets, analytics, and test the AI agent in real-time.',
  keywords: ['customer success', 'AI agent', 'support dashboard', 'Nexora'],
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en" className={inter.variable}>
      <body className="antialiased" style={{ background: '#0B0F19', color: '#F1F5F9', margin: 0, padding: 0 }}>{children}</body>
    </html>
  )
}
