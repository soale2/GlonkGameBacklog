import {
  DndContext,
  DragOverlay,
  PointerSensor,
  useSensor,
  useSensors,
  type DragEndEvent,
  type DragStartEvent,
} from '@dnd-kit/core'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { LayoutGroup } from 'framer-motion'
import { useState } from 'react'
import { deleteBacklogEntry, fetchMe, listBacklog, updateBacklogEntry } from '../api/client'
import { BACKLOG_STATUSES, type BacklogEntry, type BacklogStatus } from '../api/types'
import { GameCardPreview, type EntryGroup } from './GameCard'
import { KanbanColumn } from './KanbanColumn'

function groupByGame(entries: BacklogEntry[], status: BacklogStatus): EntryGroup[] {
  const groups = new Map<number, EntryGroup>()
  for (const entry of entries) {
    if (entry.status !== status) continue
    const existing = groups.get(entry.game.id)
    if (existing) {
      existing.entries.push(entry)
    } else {
      groups.set(entry.game.id, { status, game: entry.game, entries: [entry] })
    }
  }
  return Array.from(groups.values())
}

export function KanbanBoard({ workspaceId }: { workspaceId: number }) {
  const queryClient = useQueryClient()
  const [activeEntry, setActiveEntry] = useState<BacklogEntry | null>(null)

  const { data: me } = useQuery({ queryKey: ['me'], queryFn: fetchMe })
  const { data: entries } = useQuery({
    queryKey: ['backlog', workspaceId],
    queryFn: () => listBacklog(workspaceId),
  })

  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 4 } }),
  )

  const moveMutation = useMutation({
    mutationFn: ({ entryId, status }: { entryId: number; status: BacklogStatus }) =>
      updateBacklogEntry(workspaceId, entryId, { status }),
    onError: () => queryClient.invalidateQueries({ queryKey: ['backlog', workspaceId] }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['activity', workspaceId] }),
  })

  const removeMutation = useMutation({
    mutationFn: (entryId: number) => deleteBacklogEntry(workspaceId, entryId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['backlog', workspaceId] })
      queryClient.invalidateQueries({ queryKey: ['activity', workspaceId] })
    },
  })

  function handleDragStart(event: DragStartEvent) {
    setActiveEntry(entries?.find((e) => e.id === event.active.id) ?? null)
  }

  function handleDragEnd(event: DragEndEvent) {
    setActiveEntry(null)
    const { active, over } = event
    if (!over) return

    const targetStatus = over.id as BacklogStatus
    const entry = entries?.find((e) => e.id === active.id)
    if (!entry || entry.status === targetStatus) return

    // Optimistic update so the card settles into its new column immediately, the
    // network round-trip resolves quietly behind that.
    queryClient.setQueryData<BacklogEntry[]>(['backlog', workspaceId], (old) =>
      old?.map((e) => (e.id === entry.id ? { ...e, status: targetStatus } : e)),
    )
    moveMutation.mutate({ entryId: entry.id, status: targetStatus })
  }

  return (
    <DndContext sensors={sensors} onDragStart={handleDragStart} onDragEnd={handleDragEnd}>
      <LayoutGroup>
        <div style={{ display: 'flex', gap: '0.75rem', overflowX: 'auto', paddingBottom: '1rem' }}>
          {BACKLOG_STATUSES.map((status) => (
            <KanbanColumn
              key={status}
              status={status}
              groups={groupByGame(entries ?? [], status)}
              currentUserId={me?.id}
              workspaceId={workspaceId}
              onRemove={(entryId) => removeMutation.mutate(entryId)}
            />
          ))}
        </div>
      </LayoutGroup>

      <DragOverlay>{activeEntry && <GameCardPreview entry={activeEntry} />}</DragOverlay>
    </DndContext>
  )
}
