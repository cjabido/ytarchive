import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Bookmark, ExternalLink, Trash2 } from 'lucide-react'
import { format, parseISO } from 'date-fns'
import { fetchWatchlist, updateWatchlistItem, removeFromWatchlist } from '../api.js'
import VideoDetail from '../components/VideoDetail.jsx'

const STATUSES = ['to-rewatch', 'reference', 'to-download', 'in-progress', 'done']

const STATUS_CONFIG = {
  'to-rewatch':  { label: 'To Rewatch',  cls: 'text-accent-amber  border-accent-amber/20  bg-accent-amber-dim',  dot: 'bg-accent-amber'  },
  'reference':   { label: 'Reference',   cls: 'text-accent-sky    border-accent-sky/20    bg-accent-sky-dim',    dot: 'bg-accent-sky'    },
  'to-download': { label: 'To Download', cls: 'text-accent-mint   border-accent-mint/20   bg-accent-mint-dim',   dot: 'bg-accent-mint'   },
  'in-progress': { label: 'In Progress', cls: 'text-accent-violet border-accent-violet/20 bg-accent-violet-dim', dot: 'bg-accent-violet' },
  'done':        { label: 'Done',        cls: 'text-text-muted    border-border-dim       bg-surface-2',         dot: 'bg-surface-4'     },
}

function fmt(ts) {
  try { return format(parseISO(ts), 'MMM d, yyyy') } catch { return '' }
}

export default function Watchlist() {
  const qc = useQueryClient()
  const [filterStatus, setFilterStatus] = useState('')
  const [selectedVideoId, setSelectedVideoId] = useState(null)

  const { data: items = [], isLoading } = useQuery({
    queryKey: ['watchlist', filterStatus],
    queryFn: () => fetchWatchlist({ status: filterStatus || undefined }),
  })

  const update = useMutation({
    mutationFn: ({ videoId, status }) => updateWatchlistItem(videoId, { status }),
    onSuccess: () => qc.invalidateQueries(['watchlist']),
  })

  const remove = useMutation({
    mutationFn: (videoId) => removeFromWatchlist(videoId),
    onSuccess: () => qc.invalidateQueries(['watchlist']),
  })

  // Group by status if showing all
  const grouped = filterStatus
    ? { [filterStatus]: items }
    : STATUSES.reduce((acc, s) => {
        const grp = items.filter(i => i.status === s)
        if (grp.length > 0) acc[s] = grp
        return acc
      }, {})

  return (
    <div className="min-h-screen bg-surface-0 overflow-x-hidden pb-20">
      {/* Header */}
      <header className="sticky top-0 z-30 bg-surface-0/80 backdrop-blur-xl border-b border-border-dim">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-14 gap-3">
            <div className="flex items-center gap-3">
              <div className="w-8 h-8 rounded-lg bg-accent-amber-dim flex items-center justify-center">
                <Bookmark className="w-4 h-4 text-accent-amber" />
              </div>
              <h1 className="text-base font-semibold text-text-primary">Watchlist</h1>
              {items.length > 0 && (
                <span className="text-xs text-text-muted font-mono tabular-nums hidden sm:inline">
                  {items.length} item{items.length !== 1 ? 's' : ''}
                </span>
              )}
            </div>

            {/* Status filter pills */}
            <div className="flex items-center gap-1 p-1 bg-surface-1 border border-border-dim rounded-lg overflow-x-auto">
              <button
                onClick={() => setFilterStatus('')}
                className={`px-3 py-1.5 rounded-md text-xs font-medium whitespace-nowrap transition-all duration-150 cursor-pointer
                  ${!filterStatus ? 'bg-surface-3 text-text-primary shadow-sm' : 'text-text-muted hover:text-text-secondary'}`}
              >
                All
              </button>
              {STATUSES.map(s => (
                <button
                  key={s}
                  onClick={() => setFilterStatus(filterStatus === s ? '' : s)}
                  className={`px-3 py-1.5 rounded-md text-xs font-medium whitespace-nowrap transition-all duration-150 cursor-pointer
                    ${filterStatus === s ? 'bg-surface-3 text-text-primary shadow-sm' : 'text-text-muted hover:text-text-secondary'}`}
                >
                  {STATUS_CONFIG[s].label}
                </button>
              ))}
            </div>
          </div>
        </div>
      </header>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 space-y-6">
        {isLoading ? (
          <div className="space-y-2">
            {[...Array(5)].map((_, i) => (
              <div key={i} className="bg-surface-1 border border-border-dim rounded-lg px-4 py-3.5 animate-pulse">
                <div className="h-4 bg-surface-2 rounded w-2/3 mb-2" />
                <div className="h-3 bg-surface-2 rounded w-1/3" />
              </div>
            ))}
          </div>
        ) : items.length === 0 ? (
          <div className="py-16 text-center">
            <div className="w-12 h-12 rounded-xl bg-surface-2 flex items-center justify-center mx-auto mb-3">
              <Bookmark className="w-5 h-5 text-text-muted" />
            </div>
            <p className="text-sm text-text-muted">
              {filterStatus ? `No items with status "${filterStatus}"` : 'Your watchlist is empty'}
            </p>
            <p className="text-xs text-text-muted mt-1">Open a video in the Library to add it.</p>
          </div>
        ) : (
          Object.entries(grouped).map(([status, grpItems]) => {
            const cfg = STATUS_CONFIG[status]
            return (
              <section key={status} className="animate-fade-in-up">
                {/* Group header */}
                <div className="flex items-center gap-2 mb-2">
                  <div className={`w-2 h-2 rounded-full ${cfg.dot}`} />
                  <h2 className="text-xs font-medium text-text-muted uppercase tracking-wider">
                    {cfg.label} <span className="normal-case">({grpItems.length})</span>
                  </h2>
                </div>

                {/* Items */}
                <div className="space-y-2">
                  {grpItems.map((item, i) => (
                    <WatchlistRow
                      key={item.video_id}
                      item={item}
                      index={i}
                      statusCfg={cfg}
                      onOpen={() => setSelectedVideoId(item.video_id)}
                      onStatusChange={(s) => update.mutate({ videoId: item.video_id, status: s })}
                      onRemove={() => remove.mutate(item.video_id)}
                    />
                  ))}
                </div>
              </section>
            )
          })
        )}
      </div>

      {selectedVideoId && (
        <VideoDetail
          videoId={selectedVideoId}
          onClose={() => setSelectedVideoId(null)}
        />
      )}
    </div>
  )
}

function WatchlistRow({ item, index, statusCfg, onOpen, onStatusChange, onRemove }) {
  return (
    <div
      className="group/row flex items-center gap-4 px-4 py-3.5
        bg-surface-1 border border-border-dim rounded-lg
        hover:bg-surface-2/60 hover:border-border-default
        transition-all duration-200 animate-fade-in-up"
      style={{ animationDelay: `${Math.min(index, 15) * 40}ms` }}
    >
      {/* Status dot */}
      <div className={`w-9 h-9 rounded-lg flex items-center justify-center shrink-0 ${statusCfg.cls}`}>
        <Bookmark className="w-4 h-4" />
      </div>

      {/* Info */}
      <div className="flex-1 min-w-0 cursor-pointer" onClick={onOpen}>
        <p className="text-sm font-medium text-text-primary truncate">{item.video_title}</p>
        <div className="flex items-center gap-2 mt-0.5">
          <span className="text-xs text-text-muted truncate">{item.channel_name}</span>
          {item.added_at && (
            <span className="text-xs font-mono text-text-muted tabular-nums shrink-0">
              Added {fmt(item.added_at)}
            </span>
          )}
        </div>
        {item.notes && (
          <p className="text-xs text-text-secondary mt-1 truncate italic">{item.notes}</p>
        )}
      </div>

      {/* Actions */}
      <div className="flex items-center gap-2 shrink-0 opacity-0 group-hover/row:opacity-100 transition-opacity">
        <select
          value={item.status}
          onChange={e => onStatusChange(e.target.value)}
          onClick={e => e.stopPropagation()}
          className="text-xs rounded-md border border-border-dim bg-surface-1 text-text-secondary
            px-2 py-1 focus:outline-none focus:border-accent-sky/50 cursor-pointer"
        >
          {STATUSES.map(s => (
            <option key={s} value={s}>{STATUS_CONFIG[s].label}</option>
          ))}
        </select>
        <a
          href={item.video_url}
          target="_blank"
          rel="noreferrer"
          onClick={e => e.stopPropagation()}
          className="w-7 h-7 rounded-lg flex items-center justify-center
            hover:bg-surface-2 text-text-muted hover:text-accent-sky transition-colors"
        >
          <ExternalLink className="w-3.5 h-3.5" />
        </a>
        <button
          onClick={(e) => { e.stopPropagation(); onRemove() }}
          className="w-7 h-7 rounded-lg flex items-center justify-center
            hover:bg-accent-rose-dim text-text-muted hover:text-accent-rose
            transition-colors cursor-pointer"
        >
          <Trash2 className="w-3.5 h-3.5" />
        </button>
      </div>
    </div>
  )
}
