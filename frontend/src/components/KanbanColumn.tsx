import { useDroppable } from '@dnd-kit/core'
import { AnimatePresence, motion } from 'framer-motion'
import type { BacklogStatus } from '../api/types'
import { STATUS_COLOR_VAR, STATUS_LABELS } from '../statusStyle'
import { GameCard, type EntryGroup } from './GameCard'

export function KanbanColumn({
  status,
  groups,
  currentUserId,
  workspaceId,
  onRemove,
}: {
  status: BacklogStatus
  groups: EntryGroup[]
  currentUserId: number | undefined
  workspaceId: number
  onRemove: (entryId: number) => void
}) {
  const { setNodeRef, isOver } = useDroppable({ id: status })

  return (
    <div
      ref={setNodeRef}
      style={{
        flex: '1 1 0',
        minWidth: 220,
        borderRadius: 'var(--radius-lg)',
        padding: '0.85rem',
        background: isOver ? 'var(--accent-bg)' : 'transparent',
        transition: 'background 0.15s ease',
      }}
    >
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: '0.4rem',
          marginBottom: '0.75rem',
          fontSize: '0.8rem',
          fontWeight: 600,
          letterSpacing: '0.02em',
          textTransform: 'uppercase',
          color: 'var(--text-muted)',
        }}
      >
        <span
          style={{
            width: 8,
            height: 8,
            borderRadius: '50%',
            background: STATUS_COLOR_VAR[status],
            flexShrink: 0,
          }}
        />
        <span style={{ flex: 1 }}>{STATUS_LABELS[status]}</span>
        <motion.span
          key={groups.length}
          initial={{ y: -6, opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          style={{
            background: 'var(--bg-elevated)',
            borderRadius: 999,
            padding: '0.1rem 0.5rem',
            fontWeight: 600,
          }}
        >
          {groups.length}
        </motion.span>
      </div>

      <AnimatePresence>
        {groups.map((group) => (
          <GameCard
            key={group.game.id}
            group={group}
            currentUserId={currentUserId}
            workspaceId={workspaceId}
            onRemove={onRemove}
          />
        ))}
      </AnimatePresence>
    </div>
  )
}
