import { Shield } from 'lucide-react'
import type { ReactNode } from 'react'

interface LayoutProps {
  sidebar: ReactNode
  topRight: ReactNode
  children: ReactNode
}

export function Layout({ sidebar, topRight, children }: LayoutProps) {
  return (
    <div className="flex h-screen bg-gray-950 text-gray-100">
      {/* Sidebar */}
      <aside className="w-64 border-r border-gray-800 flex flex-col">
        <div className="p-4 border-b border-gray-800">
          <div className="flex items-center gap-2">
            <Shield className="w-6 h-6 text-red-500" />
            <span className="text-lg font-bold tracking-tight">BULWARK</span>
          </div>
          <p className="text-xs text-gray-500 mt-1">AI Safety Monitor</p>
        </div>
        <div className="flex-1 overflow-y-auto">
          {sidebar}
        </div>
      </aside>

      {/* Main Content */}
      <main className="flex-1 flex flex-col overflow-hidden">
        {/* Top Bar */}
        <header className="h-14 border-b border-gray-800 flex items-center justify-between px-6">
          <div className="text-sm text-gray-400">
            Real-time Agent Monitoring
          </div>
          {topRight}
        </header>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-6">
          {children}
        </div>
      </main>
    </div>
  )
}
