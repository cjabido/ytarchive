import { useState, useCallback } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Search, BookOpen, ChevronLeft, ChevronRight, Eye, RefreshCw, FileText } from 'lucide-react'
import { format, parseISO } from 'date-fns'
import { fetchVideos, fetchTags } from '../api.js'
import TagBadge from '../components/TagBadge.jsx'
import VideoDetail from '../components/VideoDetail.jsx'

const STATUS_OPTS = ['to-rewatch', 'reference', 'to-download', 'in-progress', 'done']
const STATUS_STYLE = {
  'to-rewatch':  'bg-accent-amber-dim text-accent-amber',
  'reference':   'bg-accent-sky-dim text-accent-sky',
  'to-download': 'bg-accent-mint-dim text-accent-mint',
  'in-progress': 'bg-accent-violet-dim text-accent-violet',
  'done':        'bg-surface-2 text-text-muted',
}

function fmt(ts) {
  try { return format(parseISO(ts), 'MMM d, yyyy') } catch { return '' }
}

function useDebounce(value, delay = 300) {
  const [debouncedValue, setDebouncedValue] = useState(value)
  const [timer, setTimer] = useState(null)
  const update = useCallback((val) => {
    if (timer) clearTimeout(timer)
    setTimer(setTimeout(() => setDebouncedValue(val), delay))
  }, [delay])
  return [debouncedValue, update]
}

export default function Library() {
  const [search, setSearch] = useState('')
  const [debouncedQ, setDebouncedQ] = useDebounce('')
  const [filterTag, setFilterTag] = useState('')
  const [filterStatus, setFilterStatus] = useState('')
  const [sort, setSort] = useState('last_watched')
  const [page, setPage] = useState(1)
  const [selectedVideoId, setSelectedVideoId] = useState(null)

  const { data: tags = [] } = useQuery({ queryKey: ['tags'], queryFn: fetchTags })

  const { data, isLoading, isFetching } = useQuery({
    queryKey: ['videos', debouncedQ, filterTag, filterStatus, sort, page],
    queryFn: () => fetchVideos({ q: debouncedQ, tag: filterTag, watchlist_status: filterStatus, sort, page, per_page: 50 }),
    keepPreviousData: true,
  })

  function handleSearch(e) {
    setSearch(e.target.value)
    setDebouncedQ(e.target.value)
    setPage(1)
  }

  function setFilter(setter) {
    return (val) => { setter(val); setPage(1) }
  }

  const totalPages = data ? Math.ceil(data.total / 50) : 1

  return (
    <div className="min-h-screen bg-surface-0 overflow-x-hidden">
      {/* Sticky header */}
      <header className="sticky top-0 z-30 bg-surface-0/80 backdrop-blur-xl border-b border-border-dim">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-14 gap-3">
            {/* Title */}
            <div className="flex items-center gap-3 shrink-0">
              <div className="w-8 h-8 rounded-lg bg-accent-sky-dim flex items-center justify-center">
                <BookOpen className="w-4 h-4 text-accent-sky" />
              </div>
              <h1 className="text-base font-semibold text-text-primary">Library</h1>
              {data && (
                <span className="text-xs text-text-muted font-mono tabular-nums hidden sm:inline">
                  {data.total.toLocaleString()} videos
                </span>
              )}
            </div>

            {/* Search */}
            <div className="relative flex-1 max-w-xs animate-fade-in-up">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-text-muted" />
              <input
                value={search}
                onChange={handleSearch}
                placeholder="Search videos…"
                className="w-full pl-9 pr-3 py-2 rounded-lg bg-surface-1 border border-border-dim
                  text-sm text-text-primary placeholder:text-text-muted
                  focus:outline-none focus:border-accent-sky/40 transition-colors"
              />
            </div>
          </div>
        </div>
      </header>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 space-y-4">
        {/* Filters row */}
        <div className="flex flex-wrap items-center gap-3">
          {/* Status filter */}
          <div className="flex items-center gap-1 p-1 bg-surface-1 border border-border-dim rounded-lg">
            <button
              onClick={() => setFilter(setFilterStatus)('')}
              className={`px-3 py-1.5 rounded-md text-xs font-medium transition-all duration-150 cursor-pointer
                ${!filterStatus ? 'bg-surface-3 text-text-primary shadow-sm' : 'text-text-muted hover:text-text-secondary'}`}
            >
              All
            </button>
            {STATUS_OPTS.map(s => (
              <button
                key={s}
                onClick={() => setFilter(setFilterStatus)(filterStatus === s ? '' : s)}
                className={`px-3 py-1.5 rounded-md text-xs font-medium transition-all duration-150 cursor-pointer
                  ${filterStatus === s ? 'bg-surface-3 text-text-primary shadow-sm' : 'text-text-muted hover:text-text-secondary'}`}
              >
                {s}
              </button>
            ))}
          </div>

          {/* Tag filter */}
          {tags.length > 0 && (
            <select
              value={filterTag}
              onChange={e => setFilter(setFilterTag)(e.target.value)}
              className="px-3 py-2 rounded-lg appearance-none bg-surface-1 border border-border-dim
                text-xs text-text-primary focus:outline-none focus:border-accent-sky/50
                focus:ring-1 focus:ring-accent-sky/20 transition-colors cursor-pointer"
            >
              <option value="">All tags</option>
              {tags.map(t => <option key={t.id} value={t.name}>{t.name}</option>)}
            </select>
          )}

          {/* Sort */}
          <select
            value={sort}
            onChange={e => setSort(e.target.value)}
            className="px-3 py-2 rounded-lg appearance-none bg-surface-1 border border-border-dim
              text-xs text-text-primary focus:outline-none focus:border-accent-sky/50
              focus:ring-1 focus:ring-accent-sky/20 transition-colors cursor-pointer ml-auto"
          >
            <option value="last_watched">Last watched</option>
            <option value="watch_count">Most watched</option>
            <option value="title">Title A–Z</option>
          </select>
        </div>

        {/* Video list */}
        {isLoading ? (
          <div className="space-y-2">
            {[...Array(8)].map((_, i) => (
              <div key={i} className="bg-surface-1 border border-border-dim rounded-lg px-4 py-3.5 animate-pulse">
                <div className="h-4 bg-surface-2 rounded w-2/3 mb-2" />
                <div className="h-3 bg-surface-2 rounded w-1/3" />
              </div>
            ))}
          </div>
        ) : data?.videos?.length === 0 ? (
          <div className="py-16 text-center">
            <div className="w-12 h-12 rounded-xl bg-surface-2 flex items-center justify-center mx-auto mb-3">
              <Search className="w-5 h-5 text-text-muted" />
            </div>
            <p className="text-sm text-text-muted">No videos match your filter</p>
          </div>
        ) : (
          <div className={`space-y-2 transition-opacity duration-150 ${isFetching ? 'opacity-60' : 'opacity-100'}`}>
            {data?.videos?.map((v, i) => (
              <VideoRow
                key={v.video_id}
                video={v}
                index={i}
                onClick={() => setSelectedVideoId(v.video_id)}
              />
            ))}
          </div>
        )}

        {/* Pagination */}
        {totalPages > 1 && (
          <div className="flex items-center justify-between pt-2">
            <button
              onClick={() => setPage(p => Math.max(1, p - 1))}
              disabled={page === 1}
              className="flex items-center gap-1 px-3 py-1.5 rounded-lg text-xs font-medium
                bg-surface-1 border border-border-dim text-text-secondary
                hover:bg-surface-2 disabled:opacity-40 disabled:cursor-not-allowed
                transition-all duration-150 cursor-pointer"
            >
              <ChevronLeft className="w-3.5 h-3.5" /> Prev
            </button>
            <span className="text-xs text-text-muted font-mono tabular-nums">
              {page} / {totalPages.toLocaleString()}
            </span>
            <button
              onClick={() => setPage(p => Math.min(totalPages, p + 1))}
              disabled={page === totalPages}
              className="flex items-center gap-1 px-3 py-1.5 rounded-lg text-xs font-medium
                bg-surface-1 border border-border-dim text-text-secondary
                hover:bg-surface-2 disabled:opacity-40 disabled:cursor-not-allowed
                transition-all duration-150 cursor-pointer"
            >
              Next <ChevronRight className="w-3.5 h-3.5" />
            </button>
          </div>
        )}
      </div>

      {/* Detail panel */}
      {selectedVideoId && (
        <VideoDetail
          videoId={selectedVideoId}
          onClose={() => setSelectedVideoId(null)}
        />
      )}
    </div>
  )
}

function VideoThumb({ videoId, channelName }) {
  const [errored, setErrored] = useState(false)
  if (errored || !videoId?.trim()) {
    return (
      <div className="w-16 h-9 rounded-md bg-accent-sky-dim flex items-center justify-center shrink-0">
        <span className="text-sm font-semibold text-accent-sky font-mono">
          {(channelName || '?')[0].toUpperCase()}
        </span>
      </div>
    )
  }
  return (
    <img
      src={`https://img.youtube.com/vi/${videoId}/hqdefault.jpg`}
      alt=""
      onError={() => setErrored(true)}
      className="w-16 h-9 rounded-md object-cover shrink-0 bg-surface-2"
    />
  )
}

function VideoRow({ video, index, onClick }) {
  return (
    <div
      onClick={onClick}
      className="group/row flex items-center gap-4 px-4 py-3.5
        bg-surface-1 border border-border-dim rounded-lg
        hover:bg-surface-2/60 hover:border-border-default
        transition-all duration-200 cursor-pointer animate-fade-in-up"
      style={{ animationDelay: `${Math.min(index, 20) * 30}ms` }}
    >
      {/* Thumbnail */}
      <VideoThumb videoId={video.video_id} channelName={video.channel_name} />

      {/* Info */}
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium text-text-primary truncate leading-snug">
          {video.video_title}
        </p>
        <div className="flex items-center gap-2 mt-0.5 flex-wrap">
          <span className="text-xs text-text-muted truncate">{video.channel_name}</span>
          {video.last_watched && (
            <span className="text-xs font-mono text-text-muted tabular-nums shrink-0">
              {fmt(video.last_watched)}
            </span>
          )}
        </div>
      </div>

      {/* Badges */}
      <div className="flex items-center gap-2 shrink-0">
        {video.watch_count > 1 && (
          <div className="flex items-center gap-1">
            <RefreshCw className="w-3 h-3 text-accent-violet" />
            <span className="text-xs font-mono tabular-nums text-accent-violet">{video.watch_count}</span>
          </div>
        )}
        {video.has_transcript && (
          <FileText className="w-3.5 h-3.5 text-accent-mint" title="Has transcript" />
        )}
        {video.watchlist_status && (
          <span className={`text-[10px] px-1.5 py-0.5 rounded font-medium ${STATUS_STYLE[video.watchlist_status]}`}>
            {video.watchlist_status}
          </span>
        )}
        {video.tags?.slice(0, 2).map(name => {
          // Render a minimal pill using just the name (no color obj here)
          return (
            <span key={name} className="text-[10px] px-1.5 py-0.5 rounded bg-surface-3 text-text-muted font-medium hidden sm:inline">
              {name}
            </span>
          )
        })}
      </div>
    </div>
  )
}
