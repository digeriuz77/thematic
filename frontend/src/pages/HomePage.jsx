import { useState, useRef } from 'react'
import { useQuery, useMutation, useQueryClient } from 'react-query'
import { Link, useNavigate } from 'react-router-dom'
import { 
  Plus, FileText, Trash2, ChevronRight, BookOpen, 
  AlertCircle, RefreshCw, FolderOpen, Layers, Compass, UploadCloud
} from 'lucide-react'
import { listProjects, createProject, deleteProject, uploadSource } from '../services/api'

function HomePage() {
  const [newTitle, setNewTitle] = useState('')
  const [newRQ, setNewRQ] = useState('')
  const queryClient = useQueryClient()
  const navigate = useNavigate()
  const fileInputRef = useRef(null)

  const { data: projects, isLoading, isError, error, refetch } = useQuery('projects', listProjects, {
    retry: 1,
    refetchOnWindowFocus: false
  })

  const createMutation = useMutation(async ({ title, validFiles }) => {
    const project = await createProject({ title, research_question: '' })
    
    // Upload files
    for (const file of validFiles) {
      const formData = new FormData()
      formData.append('project_id', project.id)
      formData.append('name', file.name)
      formData.append('source_type', 'document')
      formData.append('file', file)
      await uploadSource(project.id, formData)
    }
    return project
  }, {
    onSuccess: (data) => {
      queryClient.invalidateQueries('projects')
      navigate(`/project/${data.id}`)
    },
  })

  const deleteMutation = useMutation(deleteProject, {
    onSuccess: () => queryClient.invalidateQueries('projects'),
  })

  const handleFolderSelect = (e) => {
    const files = e.target.files
    if (!files || files.length === 0) return

    const validFiles = Array.from(files).filter(f => {
      const ext = f.name.split('.').pop().toLowerCase()
      return ['txt', 'csv', 'md', 'docx', 'pdf'].includes(ext)
    })

    if (validFiles.length === 0) {
      alert("No valid text/data files found in this folder (.txt, .csv, .md, .docx, .pdf).")
      return
    }

    const folderName = validFiles[0].webkitRelativePath.split('/')[0] || 'New Workspace'
    createMutation.mutate({ title: folderName, validFiles })
  }

  return (
    <div className="space-y-12">
      {/* Premium Hero and Conceptual Explanation */}
      <div className="relative overflow-hidden rounded-3xl border border-white/5 bg-slate-950/40 p-8 md:p-12 lg:flex lg:items-center lg:justify-between lg:gap-8 glass-panel glass-panel-glow">
        <div className="absolute -left-12 -top-12 h-64 w-64 rounded-full bg-indigo-500/10 blur-3xl"></div>
        <div className="absolute -right-12 -bottom-12 h-64 w-64 rounded-full bg-violet-600/10 blur-3xl"></div>
        
        <div className="relative max-w-2xl space-y-4">
          <div className="inline-flex items-center gap-2 rounded-full bg-indigo-500/10 border border-indigo-500/20 px-3 py-1 text-xs font-semibold text-indigo-400">
            <Compass size={14} className="animate-spin-slow" />
            Qualitative Analysis Engine
          </div>
          <h1 className="text-4xl font-extrabold tracking-tight md:text-5xl bg-gradient-to-r from-white via-slate-100 to-indigo-300 bg-clip-text text-transparent">
            Make Sense of Qualitative Data
          </h1>
          <p className="text-slate-400 text-lg leading-relaxed font-light">
            Conduct rigorous, academic-grade **thematic analysis** following Braun & Clarke's six-phase framework. Get clear guided AI support to unpack patterns, organize ideas, and export beautiful reports.
          </p>
        </div>

        <div className="relative mt-8 lg:mt-0 max-w-md w-full rounded-2xl border border-white/5 bg-slate-900/60 p-6 backdrop-blur-md">
          <h3 className="text-sm font-semibold tracking-wider text-slate-300 uppercase mb-3 flex items-center gap-2">
            <FolderOpen size={16} className="text-indigo-400" />
            What is a Project?
          </h3>
          <p className="text-xs text-slate-400 leading-relaxed mb-4">
            A **Project** is your workspace for analyzing a collection of text/data files. Think of it as a dedicated folder containing:
          </p>
          <ul className="space-y-3.5 text-xs text-slate-300">
            <li className="flex items-start gap-2.5">
              <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-md bg-indigo-500/15 text-indigo-400 font-bold text-[10px]">1</span>
              <span>**Data Files**: Your qualitative sources (e.g., CSV, TXT, markdown files of interviews or focus groups).</span>
            </li>
            <li className="flex items-start gap-2.5">
              <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-md bg-indigo-500/15 text-indigo-400 font-bold text-[10px]">2</span>
              <span>**Research Question**: The guiding inquiry that structures your analysis.</span>
            </li>
            <li className="flex items-start gap-2.5">
              <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-md bg-indigo-500/15 text-indigo-400 font-bold text-[10px]">3</span>
              <span>**Coding Table & Themes**: Your workspace to extract patterns and build models.</span>
            </li>
          </ul>
        </div>
      </div>

      <div className="grid gap-8 lg:grid-cols-12">
        {/* Left Side: Create Project & Information */}
        <div className="lg:col-span-5 space-y-6">
          <div className="rounded-2xl border border-white/5 bg-slate-950/30 p-6 glass-panel">
            <h2 className="text-lg font-bold tracking-tight text-white mb-1">Create New Workspace</h2>
            <p className="text-xs text-slate-400 mb-5">Set up a folder/project to start analyzing your files.</p>
            
            <div className="space-y-4">
              <input
                type="file"
                ref={fileInputRef}
                onChange={handleFolderSelect}
                webkitdirectory="true"
                directory="true"
                multiple
                className="hidden"
              />
              <button
                onClick={() => fileInputRef.current?.click()}
                disabled={createMutation.isLoading}
                className="w-full flex flex-col items-center justify-center gap-3 rounded-2xl border-2 border-dashed border-indigo-500/30 bg-indigo-500/5 hover:bg-indigo-500/10 hover:border-indigo-500/50 p-8 transition duration-200 glow-btn group cursor-pointer disabled:opacity-50"
              >
                <div className="rounded-full bg-indigo-500/20 p-3 text-indigo-400 group-hover:scale-110 transition-transform">
                  <UploadCloud size={24} />
                </div>
                <div className="text-center">
                  <span className="block text-sm font-semibold text-white mb-1">
                    {createMutation.isLoading ? 'Uploading & Creating...' : 'Select Folder to Analyze'}
                  </span>
                  <span className="block text-xs text-slate-400">
                    Supports .txt, .csv, .md, .docx, .pdf
                  </span>
                </div>
              </button>
            </div>
          </div>

          {/* Braun & Clarke Phase Quick Guide */}
          <div className="rounded-2xl border border-white/5 bg-slate-950/20 p-6">
            <h3 className="text-xs font-bold tracking-wider text-slate-400 uppercase mb-4 flex items-center gap-2">
              <Layers size={14} className="text-violet-400" />
              6-Phase Roadmap
            </h3>
            <div className="relative pl-6 space-y-4 step-line">
              <div className="relative">
                <div className="absolute -left-[27px] top-1.5 flex h-4 w-4 items-center justify-center rounded-full bg-indigo-500/20 border border-indigo-400/40 text-[9px] text-indigo-300 font-bold">1</div>
                <h4 className="text-xs font-semibold text-slate-200">Familiarisation with Data</h4>
                <p className="text-[10px] text-slate-400">Read transcripts thoroughly, note down initial ideas and insights.</p>
              </div>
              <div className="relative">
                <div className="absolute -left-[27px] top-1.5 flex h-4 w-4 items-center justify-center rounded-full bg-indigo-500/20 border border-indigo-400/40 text-[9px] text-indigo-300 font-bold">2</div>
                <h4 className="text-xs font-semibold text-slate-200">Generating Codes</h4>
                <p className="text-[10px] text-slate-400">Assign systematic codes to specific quotes and interesting features.</p>
              </div>
              <div className="relative">
                <div className="absolute -left-[27px] top-1.5 flex h-4 w-4 items-center justify-center rounded-full bg-indigo-500/20 border border-indigo-400/40 text-[9px] text-indigo-300 font-bold">3</div>
                <h4 className="text-xs font-semibold text-slate-200">Searching & Reviewing Themes</h4>
                <p className="text-[10px] text-slate-400">Group codes into candidate themes, test against the full dataset.</p>
              </div>
            </div>
          </div>
        </div>

        {/* Right Side: Active Projects / Workspaces */}
        <div className="lg:col-span-7 space-y-6">
          <div className="flex items-center justify-between border-b border-white/5 pb-3">
            <h2 className="text-xl font-bold tracking-tight text-white flex items-center gap-2">
              Your Analysis Workspaces
              {projects && (
                <span className="rounded-full bg-indigo-500/10 px-2 py-0.5 text-xs text-indigo-400">
                  {projects.length}
                </span>
              )}
            </h2>
          </div>

          {/* Error State */}
          {isError ? (
            <div className="rounded-2xl border border-rose-500/10 bg-rose-500/5 p-6 text-center">
              <AlertCircle size={32} className="mx-auto mb-3 text-rose-500/80 animate-pulse" />
              <h3 className="text-sm font-bold text-rose-200 mb-1">API Connection Error</h3>
              <p className="text-xs text-rose-300/70 max-w-sm mx-auto mb-4 leading-relaxed">
                Could not connect to the toolkit backend API. Please make sure the backend is running (`uvicorn backend.app.main:app`).
              </p>
              <button 
                onClick={() => refetch()}
                className="inline-flex items-center gap-1.5 rounded-lg bg-rose-500/15 border border-rose-500/30 px-3.5 py-1.5 text-xs font-semibold text-rose-300 hover:bg-rose-500/25 transition"
              >
                <RefreshCw size={12} /> Retry Connection
              </button>
            </div>
          ) : isLoading ? (
            <div className="space-y-3">
              {[1, 2].map((i) => (
                <div key={i} className="animate-pulse rounded-2xl border border-white/5 bg-slate-950/20 p-5 space-y-3">
                  <div className="flex justify-between items-center">
                    <div className="h-4 bg-slate-800 rounded w-1/3"></div>
                    <div className="h-6 bg-slate-800 rounded-lg w-16"></div>
                  </div>
                  <div className="h-3 bg-slate-800 rounded w-2/3"></div>
                </div>
              ))}
            </div>
          ) : !projects || projects.length === 0 ? (
            <div className="rounded-2xl border border-dashed border-white/10 bg-slate-950/10 p-12 text-center">
              <BookOpen size={40} className="mx-auto mb-4 text-slate-500/60" />
              <h3 className="text-sm font-bold text-slate-200 mb-1">No workspaces yet</h3>
              <p className="text-xs text-slate-400 max-w-sm mx-auto leading-relaxed">
                Create a workspace folder on the left to start uploading transcripts and analyzing qualitative data.
              </p>
            </div>
          ) : (
            <div className="grid gap-4">
              {projects.map((project) => (
                <div
                  key={project.id}
                  className="group relative flex items-center justify-between rounded-2xl border border-white/5 bg-slate-950/30 p-5 transition hover:border-indigo-500/30 hover:bg-slate-900/30 glass-panel"
                >
                  <div className="flex-1 min-w-0 pr-4">
                    <div className="flex items-center gap-2.5 mb-1.5">
                      <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-indigo-500/10 border border-indigo-500/20 text-indigo-400">
                        <FileText size={16} />
                      </div>
                      <h3 className="font-semibold text-slate-200 group-hover:text-indigo-400 transition truncate">{project.title}</h3>
                    </div>
                    {project.research_question ? (
                      <p className="text-xs text-slate-400 line-clamp-1 mb-2 font-light">
                        Q: {project.research_question}
                      </p>
                    ) : (
                      <p className="text-xs text-slate-500 italic mb-2">No research question defined</p>
                    )}
                    <div className="flex items-center gap-3">
                      <span className="rounded-full bg-slate-800 border border-white/5 px-2.5 py-0.5 text-[10px] font-semibold text-slate-300">
                        Phase {project.current_phase}
                      </span>
                      <span className="text-[10px] text-slate-500">
                        {project.phase_status === 'not_started' ? 'Not started' : 'In progress'}
                      </span>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => deleteMutation.mutate(project.id)}
                      className="rounded-lg p-2 text-slate-400 transition hover:bg-rose-500/10 hover:text-rose-400"
                      title="Delete workspace"
                    >
                      <Trash2 size={16} />
                    </button>
                    <Link
                      to={`/project/${project.id}`}
                      className="flex items-center gap-1 rounded-lg bg-indigo-500/15 border border-indigo-500/20 px-3.5 py-1.5 text-xs font-semibold text-indigo-400 transition hover:bg-indigo-500/25"
                    >
                      Open Folder <ChevronRight size={14} />
                    </Link>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

export default HomePage
