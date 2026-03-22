// Renders a small colored tag pill using the tag's stored hex color.
export default function TagBadge({ tag, onRemove }) {
  return (
    <span
      className="inline-flex items-center gap-1 text-[11px] px-2 py-0.5 rounded-md font-medium
        border transition-all duration-150"
      style={{
        color: tag.color,
        backgroundColor: tag.color + '18',  // ~10% opacity
        borderColor: tag.color + '30',
      }}
    >
      {tag.name}
      {onRemove && (
        <button
          onClick={(e) => { e.stopPropagation(); onRemove(tag) }}
          className="ml-0.5 opacity-60 hover:opacity-100 cursor-pointer leading-none"
        >
          ×
        </button>
      )}
    </span>
  )
}
