import { useQuery } from '@tanstack/react-query'
import { motion } from 'framer-motion'
import { useState } from 'react'
import './App.css'
import { fetchMe } from './api/client'
import type { Workspace } from './api/types'
import { BacklogPage } from './pages/BacklogPage'

function initials(name: string): string {
  return name
    .split(/\s+/)
    .map((w) => w[0])
    .join('')
    .slice(0, 2)
    .toUpperCase()
}

function Sidebar({
  workspaces,
  activeId,
  onSelect,
}: {
  workspaces: Workspace[]
  activeId: number | null
  onSelect: (id: number) => void
}) {
  return (
    <nav className="sidebar">
      {workspaces.map((w) => (
        <motion.button
          key={w.id}
          type="button"
          className={`server-icon${w.id === activeId ? ' active' : ''}`}
          title={w.name}
          onClick={() => onSelect(w.id)}
          whileHover={{ scale: 1.05 }}
          whileTap={{ scale: 0.95 }}
        >
          {initials(w.name)}
        </motion.button>
      ))}
    </nav>
  )
}

function App() {
  const { data: me, isPending } = useQuery({
    queryKey: ['me'],
    queryFn: fetchMe,
  })
  const [selectedWorkspaceId, setSelectedWorkspaceId] = useState<number | null>(null)

  const activeWorkspaceId =
    selectedWorkspaceId ?? (me?.workspaces.length ? me.workspaces[0].id : null)
  const activeWorkspace = me?.workspaces.find((w) => w.id === activeWorkspaceId)

  if (isPending) {
    return (
      <div className="loading-screen">
        <p>Loading</p>
      </div>
    )
  }

  if (!me) {
    return (
      <div className="login-screen">
        <h1>Glonk Backlog Manager</h1>
        <p>Track your games. See what your friends recommend.</p>
        <a href="/api/auth/login" style={{ textDecoration: 'none' }}>
          <motion.button
            type="button"
            className="discord-button"
            whileHover={{ scale: 1.03 }}
            whileTap={{ scale: 0.97 }}
          >
            <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor">
              <path d="M20.317 4.37a19.79 19.79 0 0 0-4.885-1.515.074.074 0 0 0-.079.037c-.21.375-.444.864-.608 1.25a18.27 18.27 0 0 0-5.487 0 12.64 12.64 0 0 0-.617-1.25.077.077 0 0 0-.079-.037A19.736 19.736 0 0 0 3.677 4.37a.07.07 0 0 0-.032.027C.533 9.046-.32 13.58.099 18.057a.082.082 0 0 0 .031.057 19.9 19.9 0 0 0 5.993 3.03.078.078 0 0 0 .084-.028c.462-.63.874-1.295 1.226-1.994a.076.076 0 0 0-.041-.106 13.107 13.107 0 0 1-1.872-.892.077.077 0 0 1-.008-.128c.126-.094.252-.192.372-.291a.074.074 0 0 1 .077-.01c3.928 1.793 8.18 1.793 12.062 0a.074.074 0 0 1 .078.009c.12.099.246.198.373.292a.077.077 0 0 1-.006.127 12.3 12.3 0 0 1-1.873.892.076.076 0 0 0-.04.107c.36.698.772 1.362 1.225 1.993a.076.076 0 0 0 .084.028 19.84 19.84 0 0 0 6.002-3.03.077.077 0 0 0 .032-.054c.5-5.177-.838-9.674-3.549-13.66a.06.06 0 0 0-.031-.03Z" />
            </svg>
            Log in with Discord
          </motion.button>
        </a>
      </div>
    )
  }

  return (
    <div className="app-shell">
      {me.workspaces.length > 0 && (
        <Sidebar
          workspaces={me.workspaces}
          activeId={activeWorkspaceId}
          onSelect={setSelectedWorkspaceId}
        />
      )}

      <motion.main
        key={activeWorkspaceId ?? 'none'}
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.3, ease: 'easeOut' }}
        className="main-area"
      >
        <div className="top-bar">
          <h1>{activeWorkspace ? activeWorkspace.name : 'Glonk Backlog Manager'}</h1>
          <div className="user-chip">
            {me.avatar_url && <img src={me.avatar_url} alt={me.username} />}
            <span>{me.username}</span>
          </div>
        </div>

        {me.workspaces.length === 0 && (
          <p style={{ color: 'var(--text-muted)' }}>
            You are not in a shared server yet. Ask a friend to add the bot to your Discord
            server. Then log in again.
          </p>
        )}

        {activeWorkspaceId && <BacklogPage workspaceId={activeWorkspaceId} />}
      </motion.main>
    </div>
  )
}

export default App
