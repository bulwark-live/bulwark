import { useState } from 'react'
import { Shield, Key } from 'lucide-react'
import { setApiKey } from '../api/client'

export function ApiKeyPrompt() {
  const [key, setKey] = useState('')

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (key.trim()) {
      setApiKey(key.trim())
    }
  }

  return (
    <div className="min-h-screen bg-gray-950 flex items-center justify-center">
      <div className="w-96">
        <div className="flex items-center justify-center gap-3 mb-8">
          <Shield className="w-10 h-10 text-red-500" />
          <div>
            <h1 className="text-2xl font-bold text-white">BULWARK</h1>
            <p className="text-sm text-gray-500">AI Safety Monitor</p>
          </div>
        </div>

        <form onSubmit={handleSubmit} className="bg-gray-900 border border-gray-800 rounded-xl p-6">
          <div className="flex items-center gap-2 mb-4">
            <Key className="w-4 h-4 text-gray-400" />
            <label className="text-sm font-medium text-gray-300">API Key</label>
          </div>
          <input
            type="password"
            value={key}
            onChange={e => setKey(e.target.value)}
            placeholder="bwk_..."
            className="w-full px-4 py-2.5 bg-gray-800 border border-gray-700 rounded-lg text-sm text-gray-200 placeholder-gray-600 focus:outline-none focus:border-gray-600 font-mono mb-4"
          />
          <button
            type="submit"
            disabled={!key.trim()}
            className="w-full py-2.5 bg-red-600 hover:bg-red-500 disabled:bg-gray-700 disabled:text-gray-500 text-white font-medium rounded-lg transition-colors text-sm"
          >
            Connect
          </button>
          <p className="text-xs text-gray-600 mt-3 text-center">
            Generate a key with: cd api && python seed.py
          </p>
        </form>
      </div>
    </div>
  )
}
