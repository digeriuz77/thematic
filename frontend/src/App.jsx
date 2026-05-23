import { Routes, Route, Link } from 'react-router-dom'
import HomePage from './pages/HomePage'
import ProjectPage from './pages/ProjectPage'

function App() {
  return (
    <div className="min-h-screen bg-bg text-text">
      <nav className="sticky top-0 z-50 border-b border-accent/15 bg-bg/95 backdrop-blur-md px-6 py-3">
        <div className="mx-auto flex max-w-7xl items-center gap-4">
          <Link to="/" className="text-lg font-bold text-accent tracking-tight">
            Thematic Analysis Toolkit
          </Link>
          <span className="text-xs text-muted uppercase tracking-wider ml-auto">Braun & Clarke (2006)</span>
        </div>
      </nav>
      <main className="mx-auto max-w-7xl p-6">
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/project/:projectId" element={<ProjectPage />} />
        </Routes>
      </main>
    </div>
  )
}

export default App
