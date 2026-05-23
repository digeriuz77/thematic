import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from 'react-query'
import { Link } from 'react-router-dom'
import { Plus, FileText, Trash2, ChevronRight, BookOpen } from 'lucide-react'
import { listProjects, createProject, deleteProject } from '../services/api'

function HomePage() {
  const [newTitle, setNewTitle] = useState('')
  const [newRQ, setNewRQ] = useState('')
  const queryClient = useQueryClient()

  const { data: projects, isLoading } = useQuery('projects', listProjects)

  const createMutation = useMutation(createProject, {
    onSuccess: () => {
      queryClient.invalidateQueries('projects')
      setNewTitle('')
      setNewRQ('')
    },
  })

  const deleteMutation = useMutation(deleteProject, {
    onSuccess: () => queryClient.invalidateQueries('projects'),
  })

  const handleCreate = (e) => {
    e.preventDefault()
    if (!newTitle.trim()) return
    createMutation.mutate({ title: newTitle, research_question: newRQ || null })
  }

  return (
    <div>
      <div className="mb-8">
        <h1 className="text-3xl font-extrabold bg-gradient-to-r from-white to-accent2 bg-clip-text text-transparent mb-2">
          Qualitative Analysis Toolkit
        </h1>
        <p className="text-muted max-w-xl">
          Conduct rigorous thematic analysis following Braun & Clarke's six-phase framework.
          Upload transcripts, collaborate with AI guidance, and generate publication-ready reports.
        </p>
      </div>

      {/* Create project */}
      <div className="mb-8 rounded-xl border border-accent/15 bg-bg2 p-5">
        <h2 className="text-sm font-bold text-accent uppercase tracking-wider mb-4">New Project</h2>
        <form onSubmit={handleCreate} className="flex flex-col gap-3">
          <input
            type="text"
            placeholder="Project title..."
            value={newTitle}
            onChange={e => setNewTitle(e.target.value)}
            className="rounded-lg px-4 py-2 text-sm"
          />
          <textarea
            placeholder="Research question (optional - can refine later)..."
            value={newRQ}
            onChange={e => setNewRQ(e.target.value)}
            rows={2}
            className="rounded-lg px-4 py-2 text-sm resize-none"
          />
          <button
            type="submit"
            disabled={createMutation.isLoading || !newTitle.trim()}
            className="flex items-center justify-center gap-2 rounded-lg bg-accent px-4 py-2 text-sm font-semibold text-white transition hover:bg-accent/90 disabled:opacity-50"
          >
            <Plus size={16} /> Create Project
          </button>
        </form>
      </div>

      {/* Projects list */}
      <h2 className="text-sm font-bold text-accent uppercase tracking-wider mb-4">Your Projects</h2>
      {isLoading ? (
        <div className="text-muted text-sm">Loading...</div>
      ) : projects?.length === 0 ? (
        <div className="rounded-xl border border-accent/10 bg-bg2 p-8 text-center text-muted">
          <BookOpen size={32} className="mx-auto mb-3 text-accent/40" />
          <p>No projects yet. Create one above to get started.</p>
        </div>
      ) : (
        <div className="grid gap-3">
          {projects.map(project => (
            <div
              key={project.id}
              className="group flex items-center justify-between rounded-xl border border-accent/10 bg-bg2 p-4 transition hover:border-accent/30"
            >
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-1">
                  <FileText size={16} className="text-accent" />
                  <h3 className="font-semibold text-text truncate">{project.title}</h3>
                </div>
                <p className="text-xs text-muted truncate">
                  Phase {project.current_phase} • {project.research_question || 'No research question set'}
                </p>
              </div>
              <div className="flex items-center gap-2 ml-4">
                <button
                  onClick={() => deleteMutation.mutate(project.id)}
                  className="rounded-lg p-2 text-muted transition hover:bg-red/10 hover:text-red"
                >
                  <Trash2 size={16} />
                </button>
                <Link
                  to={`/project/${project.id}`}
                  className="flex items-center gap-1 rounded-lg bg-accent/10 px-3 py-1.5 text-sm font-medium text-accent transition hover:bg-accent/20"
                >
                  Open <ChevronRight size={14} />
                </Link>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

export default HomePage
