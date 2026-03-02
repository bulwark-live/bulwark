import { useAlertRules, useToggleRule } from '../api/client'
import { ShieldAlert, ToggleLeft, ToggleRight, Skull, Bell, Webhook } from 'lucide-react'

export function RulesPanel() {
  const { data } = useAlertRules()
  const toggle = useToggleRule()
  const rules = data?.rules ?? []

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-sm font-medium text-gray-400 uppercase tracking-wider flex items-center gap-2">
          <ShieldAlert className="w-4 h-4" />
          Alert Rules
        </h2>
        <span className="text-xs text-gray-600">{rules.length} rules</span>
      </div>

      {rules.length === 0 ? (
        <div className="bg-gray-900 border border-gray-800 rounded-lg p-8 text-center">
          <ShieldAlert className="w-8 h-8 text-gray-700 mx-auto mb-3" />
          <p className="text-sm text-gray-500">No alert rules configured.</p>
          <p className="text-xs text-gray-600 mt-1">Create rules via API: POST /v1/rules</p>
        </div>
      ) : (
        <div className="space-y-3">
          {rules.map(rule => (
            <div
              key={rule.id}
              className={`bg-gray-900 border rounded-lg p-4 transition-colors ${
                rule.enabled ? 'border-gray-700' : 'border-gray-800 opacity-60'
              }`}
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <h3 className="text-sm font-medium text-gray-200">{rule.name}</h3>
                  {rule.actions.some(a => a.type === 'auto_kill') && (
                    <span className="flex items-center gap-1 text-xs px-1.5 py-0.5 rounded bg-red-950 text-red-400">
                      <Skull className="w-3 h-3" />
                      Auto-kill
                    </span>
                  )}
                </div>
                <button
                  onClick={() => toggle.mutate(rule.id)}
                  className="text-gray-400 hover:text-gray-200"
                >
                  {rule.enabled ? (
                    <ToggleRight className="w-6 h-6 text-green-500" />
                  ) : (
                    <ToggleLeft className="w-6 h-6 text-gray-600" />
                  )}
                </button>
              </div>

              {rule.description && (
                <p className="text-xs text-gray-500 mt-1">{rule.description}</p>
              )}

              <div className="flex items-center gap-4 mt-3">
                <div className="text-xs text-gray-600">
                  <span className="text-gray-400">{rule.condition.metric}</span>
                  {' '}{rule.condition.operator}{' '}
                  <span className="text-gray-400">{rule.condition.threshold}</span>
                  {' '}/ {rule.condition.window_seconds}s
                </div>
                <div className="flex items-center gap-1.5">
                  {rule.actions.map((a, i) => (
                    <span key={i} className="text-xs text-gray-600">
                      {a.type === 'auto_kill' && <Skull className="w-3 h-3 inline text-red-500" />}
                      {a.type === 'dashboard_notification' && <Bell className="w-3 h-3 inline text-yellow-500" />}
                      {a.type === 'webhook' && <Webhook className="w-3 h-3 inline text-blue-500" />}
                    </span>
                  ))}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
