import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { AnimatePresence, motion } from 'framer-motion'
import { useState } from 'react'
import {
  acceptRecommendation,
  addRecommendation,
  fetchMe,
  listBacklog,
  listRecommendations,
} from '../api/client'
import type { Recommendation } from '../api/types'
import { timeAgo } from '../timeAgo'

function RecommendForm({ workspaceId }: { workspaceId: number }) {
  const [title, setTitle] = useState('')
  const [note, setNote] = useState('')
  const queryClient = useQueryClient()

  const mutation = useMutation({
    mutationFn: () => addRecommendation(workspaceId, { title, note: note || undefined }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['recommendations', workspaceId] })
      setTitle('')
      setNote('')
    },
  })

  return (
    <form
      onSubmit={(e) => {
        e.preventDefault()
        if (title.trim()) mutation.mutate()
      }}
      style={{
        display: 'flex',
        flexDirection: 'column',
        gap: '0.5rem',
        padding: '0.9rem',
        borderRadius: 'var(--radius-md)',
        background: 'var(--bg-elevated)',
        boxShadow: 'var(--shadow-sm)',
        marginBottom: '1.25rem',
      }}
    >
      <input
        value={title}
        onChange={(e) => setTitle(e.target.value)}
        placeholder="Game title"
        style={{
          padding: '0.5rem 0.65rem',
          borderRadius: 8,
          border: '1px solid var(--border)',
          background: 'var(--bg)',
          color: 'var(--text)',
          fontSize: '0.9rem',
        }}
      />
      <input
        value={note}
        onChange={(e) => setNote(e.target.value)}
        placeholder="Why do you recommend it? (optional)"
        style={{
          padding: '0.5rem 0.65rem',
          borderRadius: 8,
          border: '1px solid var(--border)',
          background: 'var(--bg)',
          color: 'var(--text)',
          fontSize: '0.9rem',
        }}
      />
      {mutation.isError && (
        <p style={{ color: 'var(--danger)', fontSize: '0.8rem', margin: 0 }}>
          {(mutation.error as Error).message}
        </p>
      )}
      <button
        type="submit"
        disabled={!title.trim() || mutation.isPending}
        style={{
          alignSelf: 'flex-start',
          padding: '0.45rem 1rem',
          borderRadius: 999,
          border: 'none',
          background: 'var(--accent)',
          color: '#fff',
          fontWeight: 600,
          fontSize: '0.85rem',
        }}
      >
        Recommend to this server
      </button>
    </form>
  )
}

function RecommendationCard({
  rec,
  workspaceId,
  alreadyInBacklog,
}: {
  rec: Recommendation
  workspaceId: number
  alreadyInBacklog: boolean
}) {
  const queryClient = useQueryClient()

  const acceptMutation = useMutation({
    mutationFn: () => acceptRecommendation(workspaceId, rec.id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['backlog', workspaceId] })
      queryClient.invalidateQueries({ queryKey: ['activity', workspaceId] })
    },
  })

  return (
    <motion.div
      layout
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0 }}
      style={{
        display: 'flex',
        gap: '0.75rem',
        padding: '0.75rem',
        borderRadius: 'var(--radius-md)',
        background: 'var(--bg-elevated)',
        boxShadow: 'var(--shadow-sm)',
        marginBottom: '0.6rem',
      }}
    >
      {rec.game.cover_url ? (
        <img
          src={rec.game.cover_url}
          alt={rec.game.title}
          style={{ width: 48, height: 64, objectFit: 'cover', borderRadius: 6, flexShrink: 0 }}
        />
      ) : (
        <div
          style={{
            width: 48,
            height: 64,
            borderRadius: 6,
            background: 'var(--accent-bg)',
            flexShrink: 0,
          }}
        />
      )}
      <div style={{ flex: 1, minWidth: 0 }}>
        <strong style={{ fontSize: '0.9rem' }}>{rec.game.title}</strong>
        {rec.note && (
          <p style={{ margin: '0.2rem 0 0', fontSize: '0.82rem', color: 'var(--text-muted)' }}>
            {rec.note}
          </p>
        )}
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '0.4rem',
            marginTop: '0.4rem',
            fontSize: '0.72rem',
            color: 'var(--text-muted)',
          }}
        >
          {rec.recommended_by.avatar_url && (
            <img
              src={rec.recommended_by.avatar_url}
              alt={rec.recommended_by.username}
              style={{ width: 16, height: 16, borderRadius: '50%' }}
            />
          )}
          <span>
            {rec.recommended_by.username} &middot; {timeAgo(rec.created_at)}
            {rec.source === 'bot' && ' · via /recommend'}
          </span>
        </div>
      </div>
      <button
        type="button"
        onClick={() => acceptMutation.mutate()}
        disabled={alreadyInBacklog || acceptMutation.isPending || acceptMutation.isSuccess}
        style={{
          alignSelf: 'center',
          padding: '0.4rem 0.8rem',
          borderRadius: 999,
          border: 'none',
          background: alreadyInBacklog || acceptMutation.isSuccess ? 'var(--bg)' : 'var(--accent)',
          color: alreadyInBacklog || acceptMutation.isSuccess ? 'var(--text-muted)' : '#fff',
          fontWeight: 600,
          fontSize: '0.78rem',
          flexShrink: 0,
        }}
      >
        {alreadyInBacklog || acceptMutation.isSuccess ? 'In your backlog' : 'Add to my backlog'}
      </button>
    </motion.div>
  )
}

export function RecommendationsPanel({ workspaceId }: { workspaceId: number }) {
  const { data: recommendations, isPending } = useQuery({
    queryKey: ['recommendations', workspaceId],
    queryFn: () => listRecommendations(workspaceId),
  })
  const { data: backlog } = useQuery({
    queryKey: ['backlog', workspaceId],
    queryFn: () => listBacklog(workspaceId),
  })
  const { data: me } = useQuery({ queryKey: ['me'], queryFn: fetchMe })

  const myGameIds = new Set(
    (backlog ?? []).filter((e) => e.user.id === me?.id).map((e) => e.game.id),
  )

  return (
    <div>
      <RecommendForm workspaceId={workspaceId} />

      {isPending && <p style={{ color: 'var(--text-muted)' }}>Loading</p>}
      {!isPending && recommendations?.length === 0 && (
        <p style={{ color: 'var(--text-muted)' }}>
          No recommendations yet. Use the form above, or run /recommend in Discord.
        </p>
      )}

      <AnimatePresence>
        {recommendations?.map((rec) => (
          <RecommendationCard
            key={rec.id}
            rec={rec}
            workspaceId={workspaceId}
            alreadyInBacklog={myGameIds.has(rec.game.id)}
          />
        ))}
      </AnimatePresence>
    </div>
  )
}
