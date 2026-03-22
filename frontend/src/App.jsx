import { useState } from 'react'
import Sidebar from './components/Sidebar.jsx'
import Library from './pages/Library.jsx'
import Watchlist from './pages/Watchlist.jsx'
import Stats from './pages/Stats.jsx'

export default function App() {
  const [page, setPage] = useState('library')

  return (
    <div className="flex min-h-screen bg-surface-0 overflow-x-hidden">
      <Sidebar page={page} onNavigate={setPage} />
      <main className="flex-1 ml-14 min-w-0">
        {page === 'library'   && <Library />}
        {page === 'watchlist' && <Watchlist />}
        {page === 'stats'     && <Stats />}
      </main>
    </div>
  )
}
