import { useQuery } from '@tanstack/react-query'
import { AnimatePresence, motion } from 'framer-motion'
import { useState } from 'react'
import { listActivity } from '../api/client'
import type { ActivityEvent } from '../api/types'
import { STATUS_LABELS } from '../statusStyle'
import { timeAgo } from '../timeAgo'

const COLLAPSED_STORAGE_KEY = 'glonk:activity-collapsed'

function readStoredCollapsed(): boolean {
  try {
    return localStorage.getItem(COLLAPSED_STORAGE_KEY) === 'true'
  } catch {
    return false
  }
}

function writeStoredCollapsed(value: boolean): void {
  try {
    localStorage.setItem(COLLAPSED_STORAGE_KEY, String(value))
  } catch {
    // Private browsing or blocked storage. Collapsed state just won't persist.
  }
}

function ChevronIcon({ collapsed }: { collapsed: boolean }) {
  return (
    <motion.svg
      width="14"
      height="14"
      viewBox="0 0 16 16"
      fill="none"
      animate={{ rotate: collapsed ? -90 : 0 }}
      transition={{ duration: 0.15 }}
    >
      <path
        d="M4 6l4 4 4-4"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </motion.svg>
  )
}

function describe(event: ActivityEvent): string {
  switch (event.event_type) {
    case 'added':
      return `added to ${STATUS_LABELS[event.to_status!]}`
    case 'status_changed':
      return `moved to ${STATUS_LABELS[event.to_status!]}`
    case 'removed':
      return 'removed from backlog'
  }
}

function EventRow({ event }: { event: ActivityEvent }) {
  return (
    <motion.div
      layout
      initial={{ opacity: 0, x: 12 }}
      animate={{ opacity: 1, x: 0 }}
      exit={{ opacity: 0 }}
      style={{ display: 'flex', gap: '0.55rem', padding: '0.55rem 0' }}
    >
      {event.user.avatar_url ? (
        <img
          src={event.user.avatar_url}
          alt={event.user.username}
          style={{ width: 26, height: 26, borderRadius: '50%', flexShrink: 0 }}
        />
      ) : (
        <div
          style={{
            width: 26,
            height: 26,
            borderRadius: '50%',
            background: 'var(--accent-bg)',
            flexShrink: 0,
          }}
        />
      )}
      <div style={{ minWidth: 0, flex: 1 }}>
        <p style={{ margin: 0, fontSize: '0.8rem', lineHeight: 1.35 }}>
          <strong>{event.user.username}</strong>{' '}
          <span style={{ color: 'var(--text-muted)' }}>{describe(event)}</span>
        </p>
        <p
          style={{
            margin: 0,
            fontSize: '0.78rem',
            fontWeight: 600,
            overflow: 'hidden',
            textOverflow: 'ellipsis',
            whiteSpace: 'nowrap',
          }}
        >
          {event.game.title}
        </p>
        <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>
          {timeAgo(event.created_at)}
        </span>
      </div>
    </motion.div>
  )
}

export function ActivityFeed({ workspaceId }: { workspaceId: number }) {
  const [collapsed, setCollapsed] = useState(readStoredCollapsed)
  const { data: events, isPending } = useQuery({
    queryKey: ['activity', workspaceId],
    queryFn: () => listActivity(workspaceId),
    refetchInterval: 15000,
  })

  function toggleCollapsed() {
    setCollapsed((prev) => {
      const next = !prev
      writeStoredCollapsed(next)
      return next
    })
  }

  return (
    <aside
      style={{
        width: collapsed ? 'auto' : 260,
        flexShrink: 0,
        borderRadius: 'var(--radius-lg)',
        background: 'var(--bg-elevated)',
        boxShadow: 'var(--shadow-sm)',
        padding: '1rem 1.1rem',
        height: 'fit-content',
        maxHeight: 'calc(100vh - 8rem)',
        overflowY: collapsed ? 'visible' : 'auto',
      }}
    >
      <button
        type="button"
        onClick={toggleCollapsed}
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: '0.4rem',
          width: '100%',
          border: 'none',
          background: 'transparent',
          color: 'var(--text-muted)',
          padding: 0,
          marginBottom: collapsed ? 0 : '0.25rem',
        }}
      >
        <h2
          style={{
            flex: 1,
            textAlign: 'left',
            fontSize: '0.8rem',
            textTransform: 'uppercase',
            letterSpacing: '0.03em',
            margin: 0,
          }}
        >
          Activity
        </h2>
        {events && events.length > 0 && (
          <span
            style={{
              background: 'var(--bg)',
              borderRadius: 999,
              padding: '0.1rem 0.5rem',
              fontSize: '0.72rem',
              fontWeight: 600,
            }}
          >
            {events.length}
          </span>
        )}
        <ChevronIcon collapsed={collapsed} />
      </button>

      {!collapsed && (
        <>
          {isPending && <p style={{ color: 'var(--text-muted)', fontSize: '0.8rem' }}>Loading</p>}
          {!isPending && (!events || events.length === 0) && (
            <p style={{ color: 'var(--text-muted)', fontSize: '0.8rem' }}>No activity yet.</p>
          )}

          <div style={{ display: 'flex', flexDirection: 'column' }}>
            <AnimatePresence initial={false}>
              {events?.map((event, i) => (
                <div key={event.id}>
                  {i > 0 && <div style={{ borderTop: '1px solid var(--border)' }} />}
                  <EventRow event={event} />
                </div>
              ))}
            </AnimatePresence>
          </div>
        </>
      )}
    </aside>
  )
}
