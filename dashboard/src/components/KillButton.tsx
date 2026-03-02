import { useState } from 'react'
import { useKillSession, useSessions } from '../api/client'
import { Skull, X } from 'lucide-react'

interface KillButtonProps {
  selectedSession: string | null
}

export function KillButton({ selectedSession }: KillButtonProps) {
  const [showConfirm, setShowConfirm] = useState(false)
  const [targetSession, setTargetSession] = useState<string | null>(null)
  const kill = useKillSession()
  const { data } = useSessions()

  const activeSessions = (data?.sessions ?? []).filter(s => !s.ended_at && !s.killed_at)

  function handleClick() {
    if (selectedSession) {
      setTargetSession(selectedSession)
      setShowConfirm(true)
    } else if (activeSessions.length === 1) {
      setTargetSession(activeSessions[0].id)
      setShowConfirm(true)
    } else if (activeSessions.length > 1) {
      // Show dropdown to pick session
      setShowConfirm(true)
      setTargetSession(null)
    }
  }

  function confirmKill() {
    if (targetSession) {
      kill.mutate(targetSession)
      setShowConfirm(false)
      setTargetSession(null)
    }
  }

  return (
    <>
      <button
        onClick={handleClick}
        disabled={activeSessions.length === 0}
        className="flex items-center gap-2 px-4 py-2 bg-red-600 hover:bg-red-500 disabled:bg-gray-700 disabled:text-gray-500 text-white font-medium rounded-lg transition-colors text-sm"
      >
        <Skull className="w-4 h-4" />
        KILL
      </button>

      {/* Confirmation Modal */}
      {showConfirm && (
        <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50">
          <div className="bg-gray-900 border border-gray-700 rounded-xl p-6 w-96 shadow-2xl">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold text-red-400 flex items-center gap-2">
                <Skull className="w-5 h-5" />
                Kill Agent Session
              </h3>
              <button
                onClick={() => { setShowConfirm(false); setTargetSession(null) }}
                className="p-1 hover:bg-gray-800 rounded"
              >
                <X className="w-4 h-4 text-gray-500" />
              </button>
            </div>

            {targetSession ? (
              <div>
                <p className="text-sm text-gray-300 mb-4">
                  This will immediately terminate the agent session. The agent will detect the kill signal and shut down.
                </p>
                <div className="bg-gray-800 rounded-lg p-3 mb-4 font-mono text-sm text-gray-300">
                  {targetSession}
                </div>
                <div className="flex gap-3">
                  <button
                    onClick={() => { setShowConfirm(false); setTargetSession(null) }}
                    className="flex-1 py-2 px-4 border border-gray-700 rounded-lg text-sm text-gray-300 hover:bg-gray-800 transition-colors"
                  >
                    Cancel
                  </button>
                  <button
                    onClick={confirmKill}
                    className="flex-1 py-2 px-4 bg-red-600 hover:bg-red-500 rounded-lg text-sm text-white font-medium transition-colors"
                  >
                    Kill Session
                  </button>
                </div>
              </div>
            ) : (
              <div>
                <p className="text-sm text-gray-300 mb-3">Select a session to kill:</p>
                <div className="space-y-2 mb-4 max-h-48 overflow-y-auto">
                  {activeSessions.map(s => (
                    <button
                      key={s.id}
                      onClick={() => setTargetSession(s.id)}
                      className={`w-full text-left p-3 rounded-lg border transition-colors ${
                        targetSession === s.id
                          ? 'border-red-600 bg-red-950/30'
                          : 'border-gray-700 hover:border-gray-600'
                      }`}
                    >
                      <div className="font-mono text-sm text-gray-200">{s.id}</div>
                      <div className="text-xs text-gray-500 mt-1">{s.agent_name} | {s.event_count} events</div>
                    </button>
                  ))}
                </div>
                <div className="flex gap-3">
                  <button
                    onClick={() => { setShowConfirm(false); setTargetSession(null) }}
                    className="flex-1 py-2 px-4 border border-gray-700 rounded-lg text-sm text-gray-300 hover:bg-gray-800 transition-colors"
                  >
                    Cancel
                  </button>
                  <button
                    onClick={confirmKill}
                    disabled={!targetSession}
                    className="flex-1 py-2 px-4 bg-red-600 hover:bg-red-500 disabled:bg-gray-700 disabled:text-gray-500 rounded-lg text-sm text-white font-medium transition-colors"
                  >
                    Kill Session
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </>
  )
}
