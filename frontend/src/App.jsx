import { Routes, Route, Link } from 'react-router-dom'
import HomePage from './pages/HomePage'
import ProjectPage from './pages/ProjectPage'

function App() {
  return (
    <div className="min-h-screen text-slate-100 selection:bg-indigo-500/30 selection:text-indigo-200">
      <nav className="sticky top-0 z-50 border-b border-white/5 bg-slate-950/65 backdrop-blur-xl px-8 py-4">
        <div className="mx-auto flex max-w-7xl items-center justify-between">
          <Link to="/" className="flex items-center gap-3 group">
            <div className="relative flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-tr from-indigo-500 to-violet-600 shadow-lg shadow-indigo-500/20 group-hover:scale-105 transition-transform duration-300">
              <span className="text-white font-extrabold text-lg">T</span>
              <div className="absolute inset-0 rounded-xl bg-white/10 opacity-0 group-hover:opacity-100 transition-opacity duration-300"></div>
            </div>
            <div>
              <span className="text-xl font-bold tracking-tight bg-gradient-to-r from-white via-slate-100 to-slate-400 bg-clip-text text-transparent group-hover:text-indigo-400 transition-colors">
                Thematic Analysis AI
              </span>
              <p className="text-[10px] text-slate-400 font-medium tracking-wide">QUALITATIVE WORKSPACE</p>
            </div>
          </Link>
          <div className="flex items-center gap-3">
            <span className="rounded-full bg-indigo-500/10 border border-indigo-500/20 px-3.5 py-1 text-xs font-semibold tracking-wider text-indigo-400 uppercase">
              Braun & Clarke Framework
            </span>
          </div>
        </div>
      </nav>
      <main className="mx-auto max-w-7xl px-8 py-10">
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/project/:projectId" element={<ProjectPage />} />
        </Routes>
      </main>
    </div>
  )
}

export default App
