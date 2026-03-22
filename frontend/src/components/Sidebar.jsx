import { BookOpen, Bookmark, BarChart2 } from 'lucide-react'

// Full class strings required so Tailwind v4 scanner can detect them
const NAV = [
  {
    id: 'library',
    Icon: BookOpen,
    label: 'Library',
    activeClass: 'bg-accent-sky-dim text-accent-sky',
  },
  {
    id: 'watchlist',
    Icon: Bookmark,
    label: 'Watchlist',
    activeClass: 'bg-accent-amber-dim text-accent-amber',
  },
  {
    id: 'stats',
    Icon: BarChart2,
    label: 'Stats',
    activeClass: 'bg-accent-violet-dim text-accent-violet',
  },
]

export default function Sidebar({ page, onNavigate }) {
  return (
    <nav className="fixed left-0 top-0 bottom-0 w-14 bg-surface-1 border-r border-border-dim
      flex flex-col items-center py-4 gap-2 z-40">

      {/* Logo */}
      <div className="w-8 h-8 rounded-lg bg-accent-sky-dim flex items-center justify-center mb-4">
        <span className="text-sm font-bold text-accent-sky font-mono">Y</span>
      </div>

      {NAV.map(({ id, Icon, label, activeClass }) => {
        const active = page === id
        return (
          <button
            key={id}
            title={label}
            onClick={() => onNavigate(id)}
            className={`w-10 h-10 rounded-lg flex items-center justify-center
              transition-all duration-150 cursor-pointer
              ${active ? activeClass : 'text-text-muted hover:text-text-secondary hover:bg-surface-2'}`}
          >
            <Icon className="w-[18px] h-[18px]" />
          </button>
        )
      })}
    </nav>
  )
}
