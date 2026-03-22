import { useState, useRef, useEffect } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { fetchTags, createTag } from '../api.js'
import TagBadge from './TagBadge.jsx'

export default function TagPicker({ selectedIds = [], onChange }) {
  const qc = useQueryClient()
  const { data: tags = [] } = useQuery({ queryKey: ['tags'], queryFn: fetchTags })
  const [newTagName, setNewTagName] = useState('')
  const [tagError, setTagError] = useState('')
  const errorTimerRef = useRef(null)
  useEffect(() => () => clearTimeout(errorTimerRef.current), [])

  const createMutation = useMutation({
    mutationFn: (name) => createTag({ name }),
    onSuccess: (newTag) => {
      qc.invalidateQueries({ queryKey: ['tags'] })
      onChange([...selectedIds, newTag.id])
      setNewTagName('')
      setTagError('')
    },
    onError: (e) => {
      const isDuplicate = e.message.toLowerCase().includes('already')
      setTagError(isDuplicate ? 'already exists' : 'error saving')
      clearTimeout(errorTimerRef.current)
      errorTimerRef.current = setTimeout(() => setTagError(''), 2000)
    },
  })

  function toggle(tag) {
    if (selectedIds.includes(tag.id)) {
      onChange(selectedIds.filter(id => id !== tag.id))
    } else {
      onChange([...selectedIds, tag.id])
    }
  }

  function handleKeyDown(e) {
    if (e.key !== 'Enter') return
    e.preventDefault()
    const trimmed = newTagName.trim()
    if (!trimmed) return
    createMutation.mutate(trimmed)
  }

  return (
    <div className="flex flex-wrap gap-1.5">
      {tags.map(tag => (
        <button
          key={tag.id}
          onClick={() => toggle(tag)}
          className={`transition-all duration-150 cursor-pointer rounded-md
            ${selectedIds.includes(tag.id) ? 'ring-2 ring-offset-1' : 'opacity-50 hover:opacity-80'}`}
          style={selectedIds.includes(tag.id) ? { outlineColor: tag.color } : {}}
        >
          <TagBadge tag={tag} />
        </button>
      ))}
      <div className="relative">
        <input
          type="text"
          value={newTagName}
          onChange={e => setNewTagName(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="New tag…"
          className="text-xs px-2 py-1 rounded-md bg-surface-2 border border-border-dim
            text-text-secondary placeholder:text-text-muted focus:outline-none
            focus:border-border-default w-24"
          disabled={createMutation.isPending}
        />
        {tagError && (
          <span className="absolute left-0 -bottom-5 text-[10px] text-accent-rose whitespace-nowrap">
            {tagError}
          </span>
        )}
      </div>
    </div>
  )
}
