import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { X, ExternalLink, FileText, Bookmark, BookmarkCheck, Download, Copy, Check } from 'lucide-react'
import { format, parseISO } from 'date-fns'
import {
  fetchVideo, fetchTranscript, triggerTranscriptFetch,
  fetchNotes, upsertNotes, setVideoTags,
  addToWatchlist, updateWatchlistItem, removeFromWatchlist,
} from '../api.js'
import TagBadge from './TagBadge.jsx'
import TagPicker from './TagPicker.jsx'

const STATUS_OPTS = ['to-rewatch', 'reference', 'to-download', 'in-progress', 'done']
const STATUS_STYLE = {
  'to-rewatch':  'bg-accent-amber-dim text-accent-amber border-accent-amber/20',
  'reference':   'bg-accent-sky-dim text-accent-sky border-accent-sky/20',
  'to-download': 'bg-accent-mint-dim text-accent-mint border-accent-mint/20',
  'in-progress': 'bg-accent-violet-dim text-accent-violet border-accent-violet/20',
  'done':        'bg-surface-2 text-text-muted border-border-dim',
}

function fmt(ts) {
  try { return format(parseISO(ts), 'MMM d, yyyy') } catch { return ts }
}

function HeroThumb({ videoId }) {
  const [errored, setErrored] = useState(false)
  if (errored) return null
  return (
    <img
      src={`https://img.youtube.com/vi/${videoId}/hqdefault.jpg`}
      alt=""
      onError={() => setErrored(true)}
      className="w-full aspect-video rounded-lg object-cover bg-surface-2"
    />
  )
}

export default function VideoDetail({ videoId, onClose }) {
  const qc = useQueryClient()
  const [notesVal, setNotesVal] = useState(null)  // null = not editing
  const [savedNote, setSavedNote] = useState(false)
  const [fetchingTranscript, setFetchingTranscript] = useState(false)
  const [copiedObsidian, setCopiedObsidian] = useState(false)

  const { data: video, isLoading } = useQuery({
    queryKey: ['video', videoId],
    queryFn: () => fetchVideo(videoId),
    enabled: !!videoId,
  })

  const { data: transcript, refetch: refetchTranscript } = useQuery({
    queryKey: ['transcript', videoId],
    queryFn: () => fetchTranscript(videoId),
    enabled: !!videoId,
    retry: false,
  })

  const { data: notes } = useQuery({
    queryKey: ['notes', videoId],
    queryFn: () => fetchNotes(videoId),
    enabled: !!videoId,
    retry: false,
  })

  const saveNotes = useMutation({
    mutationFn: (content) => upsertNotes(videoId, content),
    onSuccess: () => {
      qc.invalidateQueries(['notes', videoId])
      setSavedNote(true)
      setTimeout(() => setSavedNote(false), 1500)
    },
  })

  const saveTags = useMutation({
    mutationFn: (ids) => setVideoTags(videoId, ids),
    onSuccess: () => {
      qc.invalidateQueries(['video', videoId])
      qc.invalidateQueries(['videos'])
    },
  })

  const wlAdd = useMutation({
    mutationFn: (status) => addToWatchlist({ video_id: videoId, status }),
    onSuccess: () => { qc.invalidateQueries(['video', videoId]); qc.invalidateQueries(['watchlist']) },
  })

  const wlUpdate = useMutation({
    mutationFn: (status) => updateWatchlistItem(videoId, { status }),
    onSuccess: () => { qc.invalidateQueries(['video', videoId]); qc.invalidateQueries(['watchlist']) },
  })

  const wlRemove = useMutation({
    mutationFn: () => removeFromWatchlist(videoId),
    onSuccess: () => { qc.invalidateQueries(['video', videoId]); qc.invalidateQueries(['watchlist']) },
  })

  async function handleFetchTranscript() {
    setFetchingTranscript(true)
    await triggerTranscriptFetch(videoId)
    // Poll until ready (max 30s)
    for (let i = 0; i < 15; i++) {
      await new Promise(r => setTimeout(r, 2000))
      const result = await refetchTranscript()
      if (result.data?.transcript) break
    }
    setFetchingTranscript(false)
  }

  async function handleCopyObsidian() {
    const res = await fetch(`/api/transcripts/${videoId}/obsidian`)
    const text = await res.text()
    await navigator.clipboard.writeText(text)
    setCopiedObsidian(true)
    setTimeout(() => setCopiedObsidian(false), 2000)
  }

  const currentTagIds = video?.tags?.map(t => t.id) ?? []
  const watchlistStatus = video?.watchlist?.status

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 z-40 bg-black/20 backdrop-blur-sm"
        onClick={onClose}
      />

      {/* Panel */}
      <div className="fixed inset-y-0 right-0 z-50 w-full max-w-lg
        bg-surface-1 border-l border-border-default shadow-2xl shadow-black/10
        overflow-y-auto animate-slide-in-right">

        {/* Header */}
        <div className="sticky top-0 z-10 bg-surface-1/95 backdrop-blur-xl
          border-b border-border-dim px-5 py-4 flex items-start justify-between gap-3">
          <div className="min-w-0 flex-1">
            {isLoading ? (
              <div className="h-5 w-48 bg-surface-2 rounded animate-pulse" />
            ) : (
              <h2 className="text-base font-semibold text-text-primary leading-snug line-clamp-2">
                {video?.video_title}
              </h2>
            )}
            {video?.channel_name && (
              <p className="text-xs text-text-muted mt-0.5">{video.channel_name}</p>
            )}
          </div>
          <div className="flex items-center gap-2 shrink-0">
            {video?.video_url && (
              <a
                href={video.video_url}
                target="_blank"
                rel="noreferrer"
                className="w-8 h-8 rounded-lg flex items-center justify-center
                  hover:bg-surface-2 text-text-muted hover:text-accent-sky
                  transition-colors"
                title="Open on YouTube"
              >
                <ExternalLink className="w-4 h-4" />
              </a>
            )}
            <button
              onClick={onClose}
              className="w-8 h-8 rounded-lg flex items-center justify-center
                hover:bg-surface-3 text-text-muted hover:text-text-secondary
                transition-colors cursor-pointer"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        </div>

        <div className="p-5 space-y-6">
          {isLoading ? (
            <div className="space-y-3">
              {[...Array(4)].map((_, i) => (
                <div key={i} className="h-4 bg-surface-2 rounded animate-pulse" style={{ width: `${70 + i * 5}%` }} />
              ))}
            </div>
          ) : (
            <>
              {/* Hero thumbnail */}
              {video?.video_id?.trim() && <HeroThumb videoId={video.video_id} />}

              {/* Watch history */}
              <section>
                <SectionHeader label={`Watch history (${video?.watch_count ?? 1})`} />
                <div className="space-y-1 mt-2">
                  {video?.watch_history?.slice(0, 5).map((w, i) => (
                    <div key={i} className="text-xs font-mono text-text-secondary">
                      {fmt(w.watched_at)}
                    </div>
                  ))}
                  {(video?.watch_history?.length ?? 0) > 5 && (
                    <div className="text-xs text-text-muted">
                      +{video.watch_history.length - 5} more
                    </div>
                  )}
                </div>
              </section>

              {/* Tags */}
              <section>
                <SectionHeader label="Tags" />
                <div className="mt-2">
                  <TagPicker
                    selectedIds={currentTagIds}
                    onChange={(ids) => saveTags.mutate(ids)}
                  />
                </div>
                {video?.tags?.length > 0 && (
                  <div className="flex flex-wrap gap-1.5 mt-2">
                    {video.tags.map(t => <TagBadge key={t.id} tag={t} />)}
                  </div>
                )}
              </section>

              {/* Watchlist */}
              <section>
                <SectionHeader label="Watchlist" />
                <div className="mt-2 flex flex-wrap gap-1.5">
                  {STATUS_OPTS.map(s => (
                    <button
                      key={s}
                      onClick={() => {
                        if (watchlistStatus === s) wlRemove.mutate()
                        else if (watchlistStatus) wlUpdate.mutate(s)
                        else wlAdd.mutate(s)
                      }}
                      className={`px-3 py-1.5 rounded-md text-xs font-medium border transition-all duration-150 cursor-pointer
                        ${watchlistStatus === s
                          ? STATUS_STYLE[s]
                          : 'text-text-muted border-border-dim hover:bg-surface-2'}`}
                    >
                      {s}
                    </button>
                  ))}
                </div>
                {watchlistStatus && video?.watchlist?.notes && (
                  <p className="mt-2 text-xs text-text-secondary italic">{video.watchlist.notes}</p>
                )}
              </section>

              {/* Notes */}
              <section>
                <div className="flex items-center justify-between mb-2">
                  <SectionHeader label="Notes" inline />
                  {notes?.content && notesVal === null && (
                    <button
                      onClick={() => setNotesVal(notes.content)}
                      className="text-xs text-accent-sky hover:underline cursor-pointer"
                    >
                      Edit
                    </button>
                  )}
                </div>
                {notesVal !== null ? (
                  <div className="space-y-2">
                    <textarea
                      className="w-full px-3 py-2.5 rounded-lg bg-surface-2 border border-border-dim
                        text-sm text-text-primary placeholder:text-text-muted
                        focus:outline-none focus:border-accent-sky/50 focus:ring-1 focus:ring-accent-sky/20
                        transition-colors resize-none"
                      rows={4}
                      value={notesVal}
                      onChange={e => setNotesVal(e.target.value)}
                      placeholder="Add your notes..."
                    />
                    <div className="flex gap-2">
                      <button
                        onClick={() => { saveNotes.mutate(notesVal); setNotesVal(null) }}
                        className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold cursor-pointer
                          bg-accent-sky/10 hover:bg-accent-sky/20 text-accent-sky border border-accent-sky/15
                          transition-all duration-150"
                      >
                        {savedNote ? <><Check className="w-3 h-3" /> Saved</> : 'Save'}
                      </button>
                      <button
                        onClick={() => setNotesVal(null)}
                        className="px-3 py-1.5 rounded-lg text-xs text-text-muted hover:bg-surface-2
                          border border-border-dim transition-all duration-150 cursor-pointer"
                      >
                        Cancel
                      </button>
                    </div>
                  </div>
                ) : notes?.content ? (
                  <p className="text-sm text-text-secondary whitespace-pre-wrap">{notes.content}</p>
                ) : (
                  <button
                    onClick={() => setNotesVal('')}
                    className="text-xs text-text-muted hover:text-accent-sky cursor-pointer transition-colors"
                  >
                    + Add notes
                  </button>
                )}
              </section>

              {/* Transcript */}
              <section>
                <div className="flex items-center justify-between mb-2">
                  <SectionHeader label="Transcript" inline />
                  <div className="flex items-center gap-2">
                    {transcript?.transcript && (
                      <button
                        onClick={handleCopyObsidian}
                        title="Copy as Obsidian markdown"
                        className="flex items-center gap-1 text-xs text-text-muted hover:text-accent-violet
                          cursor-pointer transition-colors"
                      >
                        {copiedObsidian ? <Check className="w-3 h-3" /> : <Copy className="w-3 h-3" />}
                        {copiedObsidian ? 'Copied' : 'Obsidian'}
                      </button>
                    )}
                    {!transcript?.transcript && (
                      <button
                        onClick={handleFetchTranscript}
                        disabled={fetchingTranscript}
                        className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold
                          bg-accent-mint/10 hover:bg-accent-mint/20 text-accent-mint border border-accent-mint/15
                          transition-all duration-150 cursor-pointer disabled:opacity-50"
                      >
                        <FileText className="w-3.5 h-3.5" />
                        {fetchingTranscript ? 'Fetching…' : 'Fetch transcript'}
                      </button>
                    )}
                  </div>
                </div>
                {transcript?.transcript ? (
                  <div className="text-xs text-text-secondary leading-relaxed max-h-48 overflow-y-auto
                    bg-surface-2 rounded-lg p-3 border border-border-dim">
                    {transcript.transcript}
                  </div>
                ) : (
                  <p className="text-xs text-text-muted">No transcript stored.</p>
                )}
              </section>
            </>
          )}
        </div>
      </div>
    </>
  )
}

function SectionHeader({ label, inline }) {
  const cls = "text-xs font-medium text-text-muted uppercase tracking-wider"
  return inline ? <span className={cls}>{label}</span> : <h3 className={cls}>{label}</h3>
}
