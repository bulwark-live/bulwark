import { useState } from 'react'
import { Bell, Check, Skull, AlertTriangle, X } from 'lucide-react'
import { useAlerts, useUnreadAlerts, useAcknowledgeAlert } from '../api/client'
import type { AlertRecord } from '../api/client'

interface AlertBellProps {
  onSelectSession: (id: string) => void
}

function formatTime(ts: string): string {
  const d = new Date(ts)
  return d.toLocaleTimeString('en-US', { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' })
}

export function AlertBell({ onSelectSession }: AlertBellProps) {
  const [open, setOpen] = useState(false)
  const { data: unreadData } = useUnreadAlerts()
  const { data: alertsData } = useAlerts()
  const ack = useAcknowledgeAlert()

  const unread = unreadData?.unread ?? 0
  const alerts = alertsData?.alerts ?? []

  return (
    <div className="relative">
      <button
        onClick={() => setOpen(!open)}
        className="relative p-2 rounded-lg hover:bg-gray-800 transition-colors"
      >
        <Bell className={`w-5 h-5 ${unread > 0 ? 'text-red-400' : 'text-gray-400'}`} />
        {unread > 0 && (
          <span className="absolute -top-0.5 -right-0.5 bg-red-600 text-white text-xs rounded-full w-4.5 h-4.5 flex items-center justify-center font-bold">
            {unread}
          </span>
        )}
      </button>

      {open && (
        <>
          <div className="fixed inset-0 z-40" onClick={() => setOpen(false)} />
          <div className="absolute right-0 top-10 w-96 bg-gray-900 border border-gray-700 rounded-xl shadow-2xl z-50 max-h-96 overflow-hidden flex flex-col">
            <div className="flex items-center justify-between px-4 py-3 border-b border-gray-800">
              <h3 className="text-sm font-medium text-gray-200">Alerts</h3>
              <button onClick={() => setOpen(false)} className="p-1 hover:bg-gray-800 rounded">
                <X className="w-3.5 h-3.5 text-gray-500" />
              </button>
            </div>

            <div className="overflow-y-auto flex-1">
              {alerts.length === 0 ? (
                <div className="p-6 text-center text-gray-600 text-sm">
                  No alerts yet. Create rules to start monitoring.
                </div>
              ) : (
                alerts.map(a => (
                  <AlertItem
                    key={a.id}
                    alert={a}
                    onAck={() => ack.mutate(a.id)}
                    onViewSession={() => {
                      onSelectSession(a.session_id)
                      setOpen(false)
                    }}
                  />
                ))
              )}
            </div>
          </div>
        </>
      )}
    </div>
  )
}

function AlertItem({
  alert,
  onAck,
  onViewSession,
}: {
  alert: AlertRecord
  onAck: () => void
  onViewSession: () => void
}) {
  const hasAutoKill = alert.actions_taken.includes('auto_kill')

  return (
    <div
      className={`px-4 py-3 border-b border-gray-800/50 ${
        alert.acknowledged ? 'opacity-50' : ''
      }`}
    >
      <div className="flex items-start gap-2">
        {hasAutoKill ? (
          <Skull className="w-4 h-4 text-red-500 mt-0.5 flex-shrink-0" />
        ) : (
          <AlertTriangle className="w-4 h-4 text-yellow-500 mt-0.5 flex-shrink-0" />
        )}
        <div className="flex-1 min-w-0">
          <div className="text-sm font-medium text-gray-200">{alert.rule_name}</div>
          <div className="text-xs text-gray-500 mt-0.5">
            Value: {alert.metric_value} (threshold: {alert.threshold})
          </div>
          {hasAutoKill && (
            <div className="text-xs text-red-400 mt-0.5 font-medium">
              Agent auto-killed
            </div>
          )}
          <div className="flex items-center gap-2 mt-1.5">
            <span className="text-xs text-gray-600">{formatTime(alert.created_at)}</span>
            <button
              onClick={onViewSession}
              className="text-xs text-blue-400 hover:text-blue-300"
            >
              View session
            </button>
            {!alert.acknowledged && (
              <button
                onClick={onAck}
                className="text-xs text-gray-500 hover:text-gray-300 flex items-center gap-1"
              >
                <Check className="w-3 h-3" />
                Ack
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
