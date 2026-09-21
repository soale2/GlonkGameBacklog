import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { AnimatePresence, motion } from 'framer-motion'
import { useEffect, useState, type ReactNode } from 'react'
import { addBacklogEntry, searchGames } from '../api/client'
import type { Game } from '../api/types'
import { ActivityFeed } from '../components/ActivityFeed'
import { KanbanBoard } from '../components/KanbanBoard'
import { RecommendationsPanel } from '../components/RecommendationsPanel'

function useDebouncedValue<T>(value: T, delayMs: number): T {
  const [debounced, setDebounced] = useState(value)
  useEffect(() => {
    const timer = setTimeout(() => setDebounced(value), delayMs)
    return () => clearTimeout(timer)
  }, [value, delayMs])
  return debounced
}

function SearchIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 16 16" fill="none" style={{ flexShrink: 0 }}>
      <circle cx="7" cy="7" r="5.25" stroke="currentColor" strokeWidth="1.4" />
      <path d="M11 11L14.5 14.5" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" />
    </svg>
  )
}

function GameTile({ game, onAdd, pending }: { game: Game; onAdd: () => void; pending: boolean }) {
  return (
    <motion.button
      type="button"
      whileHover={{ y: -3 }}
      whileTap={{ scale: 0.97 }}
      onClick={onAdd}
      disabled={pending}
      style={{
        position: 'relative',
        textAlign: 'left',
        padding: 0,
        border: 'none',
        borderRadius: 'var(--radius-md)',
        overflow: 'hidden',
        cursor: 'pointer',
        background: 'var(--bg-elevated)',
        boxShadow: 'var(--shadow-sm)',
        aspectRatio: '3 / 4',
      }}
    >
      {game.cover_url ? (
        <img
          src={game.cover_url}
          alt={game.title}
          style={{ width: '100%', height: '100%', objectFit: 'cover', display: 'block' }}
        />
      ) : (
        <div style={{ width: '100%', height: '100%', background: 'var(--accent-bg)' }} />
      )}
      <div
        style={{
          position: 'absolute',
          inset: 0,
          background: 'linear-gradient(to top, rgba(0,0,0,0.85) 0%, rgba(0,0,0,0.1) 55%, transparent 75%)',
        }}
      />
      <strong
        style={{
          position: 'absolute',
          left: 8,
          right: 8,
          bottom: 8,
          fontSize: '0.8rem',
          color: '#fff',
          lineHeight: 1.25,
          display: '-webkit-box',
          WebkitLineClamp: 3,
          WebkitBoxOrient: 'vertical',
          overflow: 'hidden',
        }}
      >
        {game.title}
      </strong>
    </motion.button>
  )
}

function GameSearch({ workspaceId }: { workspaceId: number }) {
  const [query, setQuery] = useState('')
  const debouncedQuery = useDebouncedValue(query, 350)
  const queryClient = useQueryClient()

  const { data, isFetching } = useQuery({
    queryKey: ['games-search', debouncedQuery],
    queryFn: () => searchGames(debouncedQuery),
    enabled: debouncedQuery.trim().length > 1,
  })

  const addMutation = useMutation({
    mutationFn: (payload: { game_id?: number; title?: string }) =>
      addBacklogEntry(workspaceId, { ...payload, status: 'backlog' }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['backlog', workspaceId] })
      queryClient.invalidateQueries({ queryKey: ['activity', workspaceId] })
      setQuery('')
    },
  })

  return (
    <div style={{ marginBottom: '1.75rem' }}>
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: '0.5rem',
          padding: '0.55rem 0.9rem',
          borderRadius: 'var(--radius-md)',
          background: 'var(--bg-elevated)',
          boxShadow: 'var(--shadow-sm)',
          color: 'var(--text-muted)',
        }}
      >
        <SearchIcon />
        <input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Search for a game"
          style={{
            flex: 1,
            border: 'none',
            outline: 'none',
            background: 'transparent',
            fontSize: '0.95rem',
            color: 'var(--text)',
          }}
        />
      </div>

      {addMutation.isError && (
        <p style={{ color: 'var(--danger)', fontSize: '0.85rem', marginTop: '0.4rem' }}>
          {(addMutation.error as Error).message}
        </p>
      )}

      <AnimatePresence>
        {debouncedQuery.trim().length > 1 && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            style={{ overflow: 'hidden' }}
          >
            {isFetching && (
              <p style={{ color: 'var(--text-muted)', fontSize: '0.85rem', padding: '0.75rem 0' }}>
                Searching
              </p>
            )}

            {data && !data.enriched && (
              <div style={{ padding: '0.75rem 0' }}>
                <p style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>
                  Game details are not available right now.
                </p>
                <button
                  type="button"
                  onClick={() => addMutation.mutate({ title: query })}
                  disabled={addMutation.isPending}
                  style={{
                    marginTop: '0.4rem',
                    padding: '0.45rem 0.9rem',
                    borderRadius: 999,
                    border: 'none',
                    background: 'var(--accent)',
                    color: '#fff',
                    fontWeight: 600,
                    fontSize: '0.85rem',
                  }}
                >
                  Add "{query}" without details
                </button>
              </div>
            )}

            {data && data.enriched && (
              <div
                style={{
                  display: 'grid',
                  gridTemplateColumns: 'repeat(auto-fill, minmax(130px, 1fr))',
                  gap: '0.75rem',
                  padding: '0.85rem 0',
                }}
              >
                {data.results.map((game: Game) => (
                  <GameTile
                    key={game.id}
                    game={game}
                    pending={addMutation.isPending}
                    onAdd={() => addMutation.mutate({ game_id: game.id })}
                  />
                ))}
              </div>
            )}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}

function TabButton({
  active,
  onClick,
  children,
}: {
  active: boolean
  onClick: () => void
  children: ReactNode
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      style={{
        padding: '0.45rem 1rem',
        borderRadius: 999,
        border: 'none',
        background: active ? 'var(--accent)' : 'var(--bg-elevated)',
        color: active ? '#fff' : 'var(--text-muted)',
        fontWeight: 600,
        fontSize: '0.85rem',
      }}
    >
      {children}
    </button>
  )
}

export function BacklogPage({ workspaceId }: { workspaceId: number }) {
  const [tab, setTab] = useState<'board' | 'recommendations'>('board')

  return (
    <div style={{ display: 'flex', gap: '1.5rem', alignItems: 'flex-start' }}>
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '1.25rem' }}>
          <TabButton active={tab === 'board'} onClick={() => setTab('board')}>
            Board
          </TabButton>
          <TabButton active={tab === 'recommendations'} onClick={() => setTab('recommendations')}>
            Recommendations
          </TabButton>
        </div>

        {tab === 'board' && (
          <>
            <GameSearch workspaceId={workspaceId} />
            <KanbanBoard workspaceId={workspaceId} />
          </>
        )}
        {tab === 'recommendations' && <RecommendationsPanel workspaceId={workspaceId} />}
      </div>
      <ActivityFeed workspaceId={workspaceId} />
    </div>
  )
}
