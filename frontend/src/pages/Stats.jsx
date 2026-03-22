import { useQuery } from '@tanstack/react-query'
import { BarChart2, Play, Users, RefreshCw, FileText, Bookmark, Tag } from 'lucide-react'
import { fetchStats } from '../api.js'

const METRIC_CARDS = [
  { key: 'total_videos',    label: 'Total watches',   Icon: Play,      cls: 'bg-accent-sky-dim    text-accent-sky'    },
  { key: 'unique_videos',   label: 'Unique videos',   Icon: Play,      cls: 'bg-accent-violet-dim text-accent-violet' },
  { key: 'total_channels',  label: 'Channels',        Icon: Users,     cls: 'bg-accent-mint-dim   text-accent-mint'   },
  { key: 'rewatched_count', label: 'Re-watched',      Icon: RefreshCw, cls: 'bg-accent-amber-dim  text-accent-amber'  },
  { key: 'transcript_count',label: 'Transcripts',     Icon: FileText,  cls: 'bg-accent-mint-dim   text-accent-mint'   },
  { key: 'watchlist_count', label: 'In watchlist',    Icon: Bookmark,  cls: 'bg-accent-amber-dim  text-accent-amber'  },
  { key: 'total_tags',      label: 'Tags',            Icon: Tag,       cls: 'bg-accent-violet-dim text-accent-violet' },
]

const STATUS_COLOR = {
  'to-rewatch':  '#f59e0b',
  'reference':   '#0284c7',
  'to-download': '#10b981',
  'in-progress': '#7c3aed',
  'done':        '#8a8aa0',
}

export default function Stats() {
  const { data, isLoading } = useQuery({ queryKey: ['stats'], queryFn: fetchStats })

  // Build hour chart — 24 bars, normalised to max
  const hourData = data?.watches_by_hour ?? {}
  const hours = Array.from({ length: 24 }, (_, i) => ({
    hour: i,
    count: hourData[String(i).padStart(2, '0')] ?? 0,
  }))
  const maxHour = Math.max(...hours.map(h => h.count), 1)

  return (
    <div className="min-h-screen bg-surface-0 overflow-x-hidden pb-20">
      {/* Header */}
      <header className="sticky top-0 z-30 bg-surface-0/80 backdrop-blur-xl border-b border-border-dim">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center h-14 gap-3">
            <div className="w-8 h-8 rounded-lg bg-accent-violet-dim flex items-center justify-center">
              <BarChart2 className="w-4 h-4 text-accent-violet" />
            </div>
            <h1 className="text-base font-semibold text-text-primary">Stats</h1>
          </div>
        </div>
      </header>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 space-y-6">

        {/* Metric cards */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          {METRIC_CARDS.slice(0, 4).map(({ key, label, Icon, cls }, i) => (
            <MetricCard
              key={key}
              label={label}
              value={data?.[key]}
              Icon={Icon}
              cls={cls}
              delay={i * 60}
              isLoading={isLoading}
            />
          ))}
        </div>
        <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
          {METRIC_CARDS.slice(4).map(({ key, label, Icon, cls }, i) => (
            <MetricCard
              key={key}
              label={label}
              value={data?.[key]}
              Icon={Icon}
              cls={cls}
              delay={(i + 4) * 60}
              isLoading={isLoading}
            />
          ))}
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-[1fr_300px] gap-4">
          {/* Watches by hour */}
          <div className="bg-surface-1 border border-border-dim rounded-xl p-4 animate-fade-in-up"
               style={{ animationDelay: '420ms' }}>
            <div className="flex items-center gap-2 mb-4">
              <h2 className="text-xs font-medium text-text-muted uppercase tracking-wider">
                Watches by hour of day
              </h2>
            </div>
            <div className="flex items-end gap-0.5 h-24">
              {hours.map(({ hour, count }) => (
                <div
                  key={hour}
                  className="flex-1 flex flex-col items-center gap-1 group/bar"
                  title={`${hour}:00 — ${count.toLocaleString()} watches`}
                >
                  <div
                    className="w-full rounded-sm transition-all duration-500 bg-accent-sky/50 hover:bg-accent-sky/80"
                    style={{ height: `${Math.max(2, (count / maxHour) * 80)}px` }}
                  />
                </div>
              ))}
            </div>
            <div className="flex justify-between mt-2 text-[10px] font-mono text-text-muted tabular-nums">
              <span>12am</span>
              <span>6am</span>
              <span>12pm</span>
              <span>6pm</span>
              <span>11pm</span>
            </div>
          </div>

          {/* Watchlist by status */}
          {data?.watchlist_by_status && Object.keys(data.watchlist_by_status).length > 0 && (
            <div className="bg-surface-1 border border-border-dim rounded-xl p-4 animate-fade-in-up"
                 style={{ animationDelay: '480ms' }}>
              <h2 className="text-xs font-medium text-text-muted uppercase tracking-wider mb-4">
                Watchlist by status
              </h2>
              <div className="space-y-2.5">
                {Object.entries(data.watchlist_by_status).map(([status, count]) => {
                  const total = Object.values(data.watchlist_by_status).reduce((a, b) => a + b, 0)
                  const pct = Math.round((count / total) * 100)
                  const color = STATUS_COLOR[status] ?? '#8a8aa0'
                  return (
                    <div key={status}>
                      <div className="flex items-center justify-between mb-1">
                        <div className="flex items-center gap-2">
                          <div className="w-2 h-2 rounded-full" style={{ backgroundColor: color, opacity: 0.7 }} />
                          <span className="text-xs text-text-secondary">{status}</span>
                        </div>
                        <span className="text-xs font-mono tabular-nums text-text-muted">{count}</span>
                      </div>
                      <div className="h-1.5 bg-surface-2 rounded-full overflow-hidden">
                        <div
                          className="h-full rounded-full transition-all duration-500"
                          style={{ width: `${pct}%`, backgroundColor: color, opacity: 0.5 }}
                        />
                      </div>
                    </div>
                  )
                })}
              </div>
            </div>
          )}
        </div>

        {/* Top channels */}
        {data?.top_channels?.length > 0 && (
          <div className="bg-surface-1 border border-border-dim rounded-xl animate-fade-in-up"
               style={{ animationDelay: '540ms' }}>
            <div className="flex items-center justify-between px-4 py-3 border-b border-border-dim">
              <h2 className="text-xs font-medium text-text-muted uppercase tracking-wider">
                Top channels
              </h2>
              <span className="text-xs text-text-muted">by watch count</span>
            </div>
            <div className="divide-y divide-border-dim">
              {data.top_channels.map((ch, i) => {
                const max = data.top_channels[0].watch_count
                const pct = Math.round((ch.watch_count / max) * 100)
                return (
                  <div key={ch.channel_name}
                    className="flex items-center gap-4 px-4 py-3 hover:bg-surface-2/50 transition-colors">
                    <span className="text-xs font-mono tabular-nums text-text-muted w-4 shrink-0">
                      {i + 1}
                    </span>
                    <div className="flex-1 min-w-0">
                      <p className="text-sm text-text-primary truncate">{ch.channel_name}</p>
                      <div className="h-1 bg-surface-2 rounded-full overflow-hidden mt-1.5">
                        <div
                          className="h-full bg-accent-sky/40 rounded-full transition-all duration-500"
                          style={{ width: `${pct}%` }}
                        />
                      </div>
                    </div>
                    <span className="text-sm font-mono font-semibold tabular-nums text-accent-sky shrink-0">
                      {ch.watch_count.toLocaleString()}
                    </span>
                  </div>
                )
              })}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

function MetricCard({ label, value, Icon, cls, delay, isLoading }) {
  return (
    <div
      className="bg-surface-1 border border-border-dim rounded-xl p-4 animate-fade-in-up"
      style={{ animationDelay: `${delay}ms` }}
    >
      <div className="flex items-start justify-between mb-3">
        <span className="text-xs font-medium text-text-muted uppercase tracking-wider">{label}</span>
        <div className={`w-7 h-7 rounded-lg flex items-center justify-center ${cls}`}>
          <Icon className="w-3.5 h-3.5" />
        </div>
      </div>
      {isLoading ? (
        <div className="h-7 w-20 bg-surface-2 rounded animate-pulse" />
      ) : (
        <div className={`text-lg sm:text-2xl font-mono font-semibold tabular-nums ${cls.split(' ')[1]}`}>
          {(value ?? 0).toLocaleString()}
        </div>
      )}
    </div>
  )
}
