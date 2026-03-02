import { useStats } from '../api/client'
import { Activity, Cpu, Zap, DollarSign } from 'lucide-react'

export function StatsStrip() {
  const { data } = useStats()

  const stats = [
    {
      label: 'Active Sessions',
      value: data?.active_sessions ?? '-',
      icon: Activity,
      color: 'text-green-400',
    },
    {
      label: 'Agents',
      value: data?.total_agents ?? '-',
      icon: Cpu,
      color: 'text-blue-400',
    },
    {
      label: 'Events / min',
      value: data?.events_per_minute ?? '-',
      icon: Zap,
      color: 'text-yellow-400',
    },
    {
      label: 'Cost (24h)',
      value: data?.cost_24h != null ? `$${data.cost_24h.toFixed(2)}` : '-',
      icon: DollarSign,
      color: 'text-emerald-400',
    },
  ]

  return (
    <div className="grid grid-cols-4 gap-4 mb-6">
      {stats.map(s => {
        const Icon = s.icon
        return (
          <div
            key={s.label}
            className="bg-gray-900 border border-gray-800 rounded-lg px-4 py-3 flex items-center gap-3"
          >
            <Icon className={`w-5 h-5 ${s.color}`} />
            <div>
              <div className="text-lg font-semibold">{s.value}</div>
              <div className="text-xs text-gray-500">{s.label}</div>
            </div>
          </div>
        )
      })}
    </div>
  )
}
