import { useMutation, useQueryClient } from '@tanstack/react-query'
import { AnimatePresence, motion } from 'framer-motion'
import { useState } from 'react'
import { commitSteamImport, previewSteamImport } from '../api/client'
import type { SteamPreviewGame } from '../api/types'

function GameRow({
  item,
  checked,
  onToggle,
}: {
  item: SteamPreviewGame
  checked: boolean
  onToggle: () => void
}) {
  const disabled = item.already_in_backlog
  return (
    <label
      style={{
        display: 'flex',
        alignItems: 'center',
        gap: '0.6rem',
        padding: '0.4rem 0.6rem',
        borderRadius: 8,
        opacity: disabled ? 0.5 : 1,
        cursor: disabled ? 'default' : 'pointer',
      }}
    >
      <input type="checkbox" checked={checked} onChange={onToggle} disabled={disabled} />
      {item.game?.cover_url ? (
        <img
          src={item.game.cover_url}
          alt=""
          style={{ width: 28, height: 28, objectFit: 'cover', borderRadius: 5, flexShrink: 0 }}
        />
      ) : (
        <div
          style={{ width: 28, height: 28, borderRadius: 5, background: 'var(--accent-bg)', flexShrink: 0 }}
        />
      )}
      <span
        style={{
          flex: 1,
          minWidth: 0,
          fontSize: '0.85rem',
          whiteSpace: 'nowrap',
          overflow: 'hidden',
          textOverflow: 'ellipsis',
        }}
      >
        {item.game?.title ?? item.steam_name}
        {!item.game && (
          <span style={{ color: 'var(--text-muted)', fontSize: '0.72rem' }}> (no game data)</span>
        )}
      </span>
      {item.hours_played > 0 && (
        <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)', flexShrink: 0 }}>
          {item.hours_played}h
        </span>
      )}
      {disabled && (
        <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)', flexShrink: 0 }}>
          Already added
        </span>
      )}
    </label>
  )
}

export function SteamImportPanel({ workspaceId }: { workspaceId: number }) {
  const [profile, setProfile] = useState('')
  const [checkedAppIds, setCheckedAppIds] = useState<Set<number>>(new Set())
  const queryClient = useQueryClient()

  const previewMutation = useMutation({
    mutationFn: () => previewSteamImport(workspaceId, profile),
    onSuccess: (data) => {
      // Unplayed games are what a backlog tool is actually for, so they start checked.
      // Already-played and already-added games start unchecked, still visible to review.
      const initial = new Set(
        data.games.filter((g) => g.hours_played === 0 && !g.already_in_backlog).map((g) => g.steam_appid),
      )
      setCheckedAppIds(initial)
    },
  })

  const commitMutation = useMutation({
    mutationFn: () => {
      const selected = (previewMutation.data?.games ?? []).filter((g) =>
        checkedAppIds.has(g.steam_appid),
      )
      return commitSteamImport(
        workspaceId,
        selected.map((g) => ({
          game_id: g.game?.id,
          title: g.game ? undefined : g.steam_name,
          hours_played: g.hours_played,
        })),
      )
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['backlog', workspaceId] })
      previewMutation.reset()
      setProfile('')
      setCheckedAppIds(new Set())
    },
  })

  function toggle(appid: number) {
    setCheckedAppIds((prev) => {
      const next = new Set(prev)
      if (next.has(appid)) next.delete(appid)
      else next.add(appid)
      return next
    })
  }

  function selectAll() {
    const selectable = (previewMutation.data?.games ?? []).filter((g) => !g.already_in_backlog)
    setCheckedAppIds(new Set(selectable.map((g) => g.steam_appid)))
  }

  function selectNone() {
    setCheckedAppIds(new Set())
  }

  return (
    <div>
      <div
        style={{
          padding: '0.9rem',
          borderRadius: 'var(--radius-md)',
          background: 'var(--bg-elevated)',
          boxShadow: 'var(--shadow-sm)',
          marginBottom: '1.25rem',
        }}
      >
        <p style={{ margin: '0 0 0.6rem', fontSize: '0.85rem', color: 'var(--text-muted)' }}>
          Paste your Steam profile URL, vanity name, or SteamID64. Your Steam library
          privacy must be set to Public under Steam's Privacy Settings.
        </p>
        <form
          onSubmit={(e) => {
            e.preventDefault()
            if (profile.trim()) previewMutation.mutate()
          }}
          style={{ display: 'flex', gap: '0.5rem' }}
        >
          <input
            value={profile}
            onChange={(e) => setProfile(e.target.value)}
            placeholder="https://steamcommunity.com/id/yourname"
            style={{
              flex: 1,
              padding: '0.5rem 0.65rem',
              borderRadius: 8,
              border: '1px solid var(--border)',
              background: 'var(--bg)',
              color: 'var(--text)',
              fontSize: '0.9rem',
            }}
          />
          <button
            type="submit"
            disabled={!profile.trim() || previewMutation.isPending}
            style={{
              padding: '0.5rem 1rem',
              borderRadius: 999,
              border: 'none',
              background: 'var(--accent)',
              color: '#fff',
              fontWeight: 600,
              fontSize: '0.85rem',
              flexShrink: 0,
            }}
          >
            {previewMutation.isPending ? 'Loading' : 'Find my library'}
          </button>
        </form>
        {previewMutation.isError && (
          <p style={{ color: 'var(--danger)', fontSize: '0.82rem', marginTop: '0.5rem' }}>
            {(previewMutation.error as Error).message}
          </p>
        )}
      </div>

      <AnimatePresence>
        {previewMutation.data && (
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                marginBottom: '0.6rem',
              }}
            >
              <p style={{ margin: 0, fontSize: '0.85rem', color: 'var(--text-muted)' }}>
                {previewMutation.data.steam_display_name
                  ? `Library for ${previewMutation.data.steam_display_name}: `
                  : ''}
                {previewMutation.data.games.length} games found, {checkedAppIds.size} selected
              </p>
              <div style={{ display: 'flex', gap: '0.4rem' }}>
                <button type="button" onClick={selectAll} style={{ fontSize: '0.75rem' }}>
                  Select all
                </button>
                <button type="button" onClick={selectNone} style={{ fontSize: '0.75rem' }}>
                  Select none
                </button>
              </div>
            </div>

            <div
              style={{
                maxHeight: '50vh',
                overflowY: 'auto',
                borderRadius: 'var(--radius-md)',
                background: 'var(--bg-elevated)',
                boxShadow: 'var(--shadow-sm)',
                padding: '0.5rem',
                marginBottom: '0.75rem',
              }}
            >
              {previewMutation.data.games.map((item) => (
                <GameRow
                  key={item.steam_appid}
                  item={item}
                  checked={checkedAppIds.has(item.steam_appid)}
                  onToggle={() => toggle(item.steam_appid)}
                />
              ))}
            </div>

            {commitMutation.isError && (
              <p style={{ color: 'var(--danger)', fontSize: '0.82rem' }}>
                {(commitMutation.error as Error).message}
              </p>
            )}
            {commitMutation.data && (
              <p style={{ color: 'var(--text-muted)', fontSize: '0.82rem' }}>
                Added {commitMutation.data.imported} games
                {commitMutation.data.skipped > 0 && ` (${commitMutation.data.skipped} already in your backlog)`}.
              </p>
            )}

            <button
              type="button"
              onClick={() => commitMutation.mutate()}
              disabled={checkedAppIds.size === 0 || commitMutation.isPending}
              style={{
                padding: '0.5rem 1.1rem',
                borderRadius: 999,
                border: 'none',
                background: 'var(--accent)',
                color: '#fff',
                fontWeight: 600,
                fontSize: '0.85rem',
              }}
            >
              Add {checkedAppIds.size} selected to my backlog
            </button>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}
