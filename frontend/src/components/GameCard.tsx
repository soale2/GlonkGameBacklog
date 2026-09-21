import { useDraggable } from '@dnd-kit/core'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { AnimatePresence, motion } from 'framer-motion'
import { useState } from 'react'
import { updateBacklogEntry } from '../api/client'
import type { BacklogEntry, BacklogStatus, EntryUser, Game } from '../api/types'
import { STATUS_COLOR_VAR } from '../statusStyle'

export interface EntryGroup {
  status: BacklogStatus
  game: Game
  entries: BacklogEntry[]
}

const MAX_VISIBLE_AVATARS = 4

function AvatarStack({ users }: { users: EntryUser[] }) {
  const visible = users.slice(0, MAX_VISIBLE_AVATARS)
  const overflow = users.length - visible.length

  return (
    <div style={{ display: 'flex', alignItems: 'center', flexShrink: 0 }}>
      {visible.map((u, i) => (
        <div
          key={u.id}
          title={u.username}
          style={{
            width: 20,
            height: 20,
            borderRadius: '50%',
            marginLeft: i === 0 ? 0 : -6,
            border: '1.5px solid var(--card-bg)',
            background: 'var(--accent-bg)',
            overflow: 'hidden',
            flexShrink: 0,
            zIndex: visible.length - i,
          }}
        >
          {u.avatar_url && (
            <img
              src={u.avatar_url}
              alt={u.username}
              style={{ width: '100%', height: '100%', objectFit: 'cover' }}
            />
          )}
        </div>
      ))}
      {overflow > 0 && (
        <div
          style={{
            width: 20,
            height: 20,
            borderRadius: '50%',
            marginLeft: -6,
            border: '1.5px solid var(--card-bg)',
            background: 'var(--text-muted)',
            color: 'var(--card-bg)',
            fontSize: '0.55rem',
            fontWeight: 700,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
          }}
        >
          +{overflow}
        </div>
      )}
    </div>
  )
}

function NoteIcon({ filled }: { filled: boolean }) {
  return (
    <svg width="12" height="12" viewBox="0 0 16 16" fill="none" style={{ flexShrink: 0 }}>
      <path
        d="M3 2.5h10a1 1 0 0 1 1 1v6.6a1 1 0 0 1-1 1H8.8L5.5 14v-2.9H3a1 1 0 0 1-1-1v-6.6a1 1 0 0 1 1-1Z"
        stroke="currentColor"
        strokeWidth="1.2"
        fill={filled ? 'currentColor' : 'none'}
        opacity={filled ? 0.9 : 0.6}
      />
    </svg>
  )
}

function RemoveButton({ onRemove }: { onRemove: () => void }) {
  return (
    <motion.button
      type="button"
      aria-label="Remove this game from your backlog"
      className="remove-btn"
      onPointerDown={(e) => e.stopPropagation()}
      onClick={onRemove}
      whileHover={{ background: 'var(--danger-bg)', color: 'var(--danger)' }}
      whileTap={{ scale: 0.9 }}
      style={{
        width: 18,
        height: 18,
        borderRadius: '50%',
        border: 'none',
        background: 'transparent',
        color: 'var(--text-muted)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        flexShrink: 0,
        padding: 0,
      }}
    >
      <svg width="10" height="10" viewBox="0 0 12 12" fill="none">
        <path
          d="M1 1L11 11M11 1L1 11"
          stroke="currentColor"
          strokeWidth="1.6"
          strokeLinecap="round"
        />
      </svg>
    </motion.button>
  )
}

function NotesPanel({
  group,
  myEntry,
  workspaceId,
}: {
  group: EntryGroup
  myEntry?: BacklogEntry
  workspaceId: number
}) {
  const queryClient = useQueryClient()
  const [draft, setDraft] = useState(myEntry?.notes ?? '')

  const notesMutation = useMutation({
    mutationFn: (notes: string) => updateBacklogEntry(workspaceId, myEntry!.id, { notes }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['backlog', workspaceId] }),
  })

  const othersWithNotes = group.entries.filter((e) => e.id !== myEntry?.id && e.notes)

  return (
    <motion.div
      initial={{ opacity: 0, height: 0 }}
      animate={{ opacity: 1, height: 'auto' }}
      exit={{ opacity: 0, height: 0 }}
      style={{ overflow: 'hidden' }}
      onPointerDown={(e) => e.stopPropagation()}
    >
      <div style={{ padding: '0.4rem 0.65rem 0.6rem 1.15rem', fontSize: '0.75rem' }}>
        {myEntry && (
          <textarea
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            onBlur={() => {
              if (draft !== (myEntry.notes ?? '')) notesMutation.mutate(draft)
            }}
            placeholder="Add a note"
            rows={2}
            style={{
              width: '100%',
              resize: 'vertical',
              border: '1px solid var(--border)',
              borderRadius: 6,
              padding: '0.35rem 0.5rem',
              background: 'var(--bg)',
              color: 'var(--text)',
              fontSize: '0.75rem',
              fontFamily: 'inherit',
            }}
          />
        )}

        {othersWithNotes.map((entry) => (
          <div key={entry.id} style={{ marginTop: '0.4rem', display: 'flex', gap: '0.4rem' }}>
            {entry.user.avatar_url && (
              <img
                src={entry.user.avatar_url}
                alt={entry.user.username}
                style={{ width: 16, height: 16, borderRadius: '50%', flexShrink: 0, marginTop: 1 }}
              />
            )}
            <p style={{ margin: 0, color: 'var(--text-muted)' }}>
              <strong style={{ color: 'var(--text)' }}>{entry.user.username}:</strong> {entry.notes}
            </p>
          </div>
        ))}
      </div>
    </motion.div>
  )
}

function GameCardVisual({
  group,
  myEntry,
  workspaceId,
  onRemove,
  dragging,
}: {
  group: EntryGroup
  myEntry?: BacklogEntry
  workspaceId: number
  onRemove?: () => void
  dragging?: boolean
}) {
  const [expanded, setExpanded] = useState(false)
  const hasAnyNotes = group.entries.some((e) => e.notes)

  return (
    <div
      className="game-card"
      style={{
        opacity: dragging ? 0.35 : 1,
        borderRadius: 'var(--radius-sm)',
        marginBottom: '0.3rem',
        background: 'var(--card-bg)',
        boxShadow: 'var(--shadow-sm)',
        color: 'var(--text)',
      }}
    >
      <div
        onClick={() => setExpanded((v) => !v)}
        style={{
          display: 'flex',
          gap: '0.5rem',
          alignItems: 'center',
          position: 'relative',
          padding: '0.32rem 0.5rem 0.32rem 0.65rem',
          cursor: myEntry ? 'grab' : 'pointer',
          touchAction: 'none',
        }}
      >
        <span
          style={{
            position: 'absolute',
            left: 0,
            top: '20%',
            bottom: '20%',
            width: 2,
            borderRadius: 2,
            background: STATUS_COLOR_VAR[group.status],
          }}
        />
        {group.game.cover_url ? (
          <img
            src={group.game.cover_url}
            alt={group.game.title}
            style={{
              width: 26,
              height: 26,
              objectFit: 'cover',
              borderRadius: 5,
              pointerEvents: 'none',
              flexShrink: 0,
            }}
          />
        ) : (
          <div
            style={{ width: 26, height: 26, borderRadius: 5, background: 'var(--accent-bg)', flexShrink: 0 }}
          />
        )}
        <span
          style={{
            flex: 1,
            minWidth: 0,
            fontSize: '0.8rem',
            fontWeight: 500,
            whiteSpace: 'nowrap',
            overflow: 'hidden',
            textOverflow: 'ellipsis',
          }}
          title={group.game.title}
        >
          {group.game.title}
        </span>
        {myEntry?.rating != null && (
          <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)', flexShrink: 0 }}>
            ★{myEntry.rating}
          </span>
        )}
        {hasAnyNotes && (
          <span style={{ color: 'var(--text-muted)' }}>
            <NoteIcon filled />
          </span>
        )}
        <AvatarStack users={group.entries.map((e) => e.user)} />
        {onRemove && <RemoveButton onRemove={onRemove} />}
      </div>

      <AnimatePresence>
        {expanded && <NotesPanel group={group} myEntry={myEntry} workspaceId={workspaceId} />}
      </AnimatePresence>
    </div>
  )
}

/** The real draggable card, rendered inside a column. Only draggable when the viewer
 * has their own entry within the group, dragging always moves just that one entry. */
export function GameCard({
  group,
  currentUserId,
  workspaceId,
  onRemove,
}: {
  group: EntryGroup
  currentUserId: number | undefined
  workspaceId: number
  onRemove: (entryId: number) => void
}) {
  const myEntry = group.entries.find((e) => e.user.id === currentUserId)
  const { attributes, listeners, setNodeRef, isDragging } = useDraggable({
    id: myEntry ? myEntry.id : `readonly-${group.game.id}-${group.status}`,
    disabled: !myEntry,
  })

  // Position/movement is handled by dnd-kit's DragOverlay (the floating preview that
  // follows the pointer) plus Framer Motion's layout animation (the settle-into-place
  // animation once dropped). This element never gets a drag transform of its own, since
  // that would fight with Framer Motion's layout transform.
  return (
    <motion.div
      ref={setNodeRef}
      layoutId={`card-${group.status}-${group.game.id}`}
      layout
      initial={{ opacity: 0, scale: 0.9 }}
      animate={{ opacity: 1, scale: 1 }}
      exit={{ opacity: 0, scale: 0.9 }}
      whileHover={myEntry ? { x: 1, boxShadow: 'var(--shadow-md)' } : undefined}
      transition={{ type: 'spring', stiffness: 400, damping: 32 }}
      {...listeners}
      {...attributes}
    >
      <GameCardVisual
        group={group}
        myEntry={myEntry}
        workspaceId={workspaceId}
        onRemove={myEntry ? () => onRemove(myEntry.id) : undefined}
        dragging={isDragging}
      />
    </motion.div>
  )
}

/** A static, non-draggable copy for dnd-kit's DragOverlay (the element that actually
 * follows the pointer). Must not call useDraggable itself, only one hook instance per
 * drag id is allowed per DndContext. */
export function GameCardPreview({ entry }: { entry: BacklogEntry }) {
  const group: EntryGroup = { status: entry.status, game: entry.game, entries: [entry] }
  return (
    <div style={{ boxShadow: 'var(--shadow-md)', borderRadius: 'var(--radius-sm)', width: 220 }}>
      <GameCardVisual group={group} myEntry={entry} workspaceId={0} />
    </div>
  )
}
