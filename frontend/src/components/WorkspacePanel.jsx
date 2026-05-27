import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from 'react-query'
import { FileText, Upload, Trash2, Download, Plus, BookOpen, Code, Layers, FileCheck } from 'lucide-react'
import { listSources, pasteSource, deleteSource, uploadSource, generateReport, listReports, updateProject } from '../services/api'
import ThemeBuilder from './ThemeBuilder'
import ReportViewer from './ReportViewer'

function WorkspacePanel({ project, phaseState, onSendMessage }) {
  const queryClient = useQueryClient()
  const phase = project.current_phase

  const { data: sources } = useQuery(
    ['sources', project.id],
    () => listSources(project.id),
    { enabled: !!project.id }
  )

  const { data: reports } = useQuery(
    ['reports', project.id],
    () => listReports(project.id),
    { enabled: phase === 7 }
  )

  const pasteMutation = useMutation(
    (data) => pasteSource(project.id, data),
    {
      onSuccess: () => queryClient.invalidateQueries(['sources', project.id]),
    }
  )

  const deleteMutation = useMutation(deleteSource, {
    onSuccess: () => queryClient.invalidateQueries(['sources', project.id]),
  })

  const reportMutation = useMutation(
    ({ projectId, format }) => generateReport(projectId, format),
    {
      onSuccess: () => queryClient.invalidateQueries(['reports', project.id]),
    }
  )

  const updateMutation = useMutation(
    ({ id, data }) => updateProject(id, data),
    {
      onSuccess: () => queryClient.invalidateQueries(['project', project.id]),
    }
  )

  const handleFileUpload = async (e) => {
    const file = e.target.files[0]
    if (!file) return
    const formData = new FormData()
    formData.append('project_id', project.id)
    formData.append('name', file.name)
    formData.append('source_type', 'interview')
    formData.append('file', file)
    await uploadSource(project.id, formData)
    queryClient.invalidateQueries(['sources', project.id])
  }

  const handlePasteSubmit = (e) => {
    e.preventDefault()
    const form = e.target
    const name = form.name.value
    const content = form.content.value
    if (!name || !content) return
    pasteMutation.mutate({ name, source_type: 'interview', content })
    form.reset()
  }

  // Phase 0 / 1: Sources & Decisions
  if (phase <= 1) {
    return (
      <div className="flex h-full flex-col overflow-hidden">
        <div className="border-b border-white/5 bg-slate-900/40 px-6 py-4">
          <h3 className="text-xs font-bold text-indigo-400 uppercase tracking-widest flex items-center gap-2">
            <BookOpen size={16} /> Data Corpus
          </h3>
        </div>
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          {/* Research Question */}
          <div className="rounded-2xl border border-white/5 bg-slate-900/40 p-5 glass-panel">
            <label className="text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-2 block">Research Question</label>
            <textarea
              defaultValue={project.research_question || ''}
              onBlur={e => updateMutation.mutate({ id: project.id, data: { research_question: e.target.value } })}
              rows={2}
              className="w-full rounded-xl bg-slate-950/50 border border-white/10 px-4 py-3 text-sm text-slate-200 focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 transition duration-200"
              placeholder="Enter your research question..."
            />
          </div>

          {/* Sources list */}
          <div className="space-y-3">
            <div className="flex items-center justify-between px-1">
              <span className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">Sources ({sources?.length || 0})</span>
              <label className="flex cursor-pointer items-center gap-1.5 rounded-lg bg-indigo-500/10 border border-indigo-500/20 px-3 py-1.5 text-xs font-semibold text-indigo-400 transition hover:bg-indigo-500/20">
                <Upload size={14} /> Upload File
                <input type="file" className="hidden" onChange={handleFileUpload} accept=".txt,.docx,.pdf,.csv,.xlsx" />
              </label>
            </div>
            <div className="space-y-2">
              {sources?.map(source => (
                <div key={source.id} className="group flex items-center justify-between rounded-xl border border-white/5 bg-slate-900/30 p-3 text-sm transition hover:bg-slate-900/50 hover:border-indigo-500/20">
                  <div className="flex items-center gap-3 min-w-0">
                    <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-indigo-500/10 text-indigo-400">
                      <FileText size={16} />
                    </div>
                    <span className="truncate font-medium text-slate-200">{source.name}</span>
                    <span className="text-[10px] uppercase tracking-wider text-slate-500 shrink-0 font-medium bg-slate-950/50 px-2 py-0.5 rounded-md border border-white/5">{source.source_type}</span>
                  </div>
                  {source.source_type !== 'phase_output' ? (
                    <button onClick={() => deleteMutation.mutate(source.id)} className="text-slate-500 hover:text-rose-400 transition shrink-0 opacity-0 group-hover:opacity-100 p-2 rounded-lg hover:bg-rose-500/10">
                      <Trash2 size={16} />
                    </button>
                  ) : (
                    <span className="text-[10px] uppercase tracking-wider text-indigo-400/70 bg-indigo-950/40 px-2 py-0.5 rounded border border-indigo-500/20 shrink-0 font-medium">Memory File</span>
                  )}
                </div>
              ))}
            </div>
          </div>

          {/* Paste text */}
          <form onSubmit={handlePasteSubmit} className="space-y-3 rounded-2xl border border-white/5 bg-slate-900/40 p-5 glass-panel">
            <h4 className="text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-1">Paste Raw Text</h4>
            <input name="name" type="text" placeholder="Source name..." className="w-full rounded-xl bg-slate-950/50 border border-white/10 px-4 py-2 text-sm text-slate-200 focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 transition duration-200" />
            <textarea name="content" rows={4} placeholder="Paste transcript text here..." className="w-full rounded-xl bg-slate-950/50 border border-white/10 px-4 py-3 text-sm text-slate-200 resize-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 transition duration-200" />
            <button type="submit" className="w-full flex items-center justify-center gap-2 rounded-xl bg-indigo-500/10 border border-indigo-500/20 px-4 py-2.5 text-xs font-semibold text-indigo-400 transition hover:bg-indigo-500/20">
              <Plus size={14} /> Add Source
            </button>
          </form>

          {/* Analytic Decisions */}
          {phase === 1 && (
            <div className="rounded-2xl border border-white/5 bg-slate-900/40 p-5 glass-panel space-y-4">
              <h4 className="text-[10px] font-bold text-indigo-400 uppercase tracking-widest">Four Upfront Decisions</h4>
              {['scope', 'coding_approach', 'theme_level', 'epistemology'].map((key) => (
                <div key={key} className="space-y-1.5">
                  <label className="text-[10px] font-semibold text-slate-400 uppercase tracking-wider block">{key.replace('_', ' ')}</label>
                  <select
                    defaultValue={project.analytic_decisions?.[key] || ''}
                    onChange={e => {
                      const current = project.analytic_decisions || {}
                      updateMutation.mutate({
                        id: project.id,
                        data: { analytic_decisions: { ...current, [key]: e.target.value } }
                      })
                    }}
                    className="w-full rounded-xl bg-slate-950/50 border border-white/10 px-4 py-2.5 text-sm text-slate-200 focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 transition duration-200"
                  >
                    <option value="">Select...</option>
                    {key === 'scope' && <><option value="rich_description">Rich description of whole data set</option><option value="detailed_aspect">Detailed account of one aspect</option></>}
                    {key === 'coding_approach' && <><option value="inductive">Inductive (bottom-up)</option><option value="theoretical">Theoretical / deductive (top-down)</option></>}
                    {key === 'theme_level' && <><option value="semantic">Semantic (surface meaning)</option><option value="latent">Latent (underlying ideas)</option></>}
                    {key === 'epistemology' && <><option value="realist">Essentialist / realist</option><option value="contextualist">Contextualist</option><option value="constructionist">Constructionist</option></>}
                  </select>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    )
  }

  // Phase 2: Familiarisation
  if (phase === 2) {
    const notes = phaseState?.structured_data?.source_notes || []
    return (
      <div className="flex h-full flex-col overflow-hidden">
        <div className="border-b border-white/5 bg-slate-900/40 px-6 py-4">
          <h3 className="text-xs font-bold text-indigo-400 uppercase tracking-widest flex items-center gap-2">
            <BookOpen size={16} /> Familiarisation Notes
          </h3>
        </div>
        <div className="flex-1 overflow-y-auto p-6 space-y-4">
          {notes.length === 0 && (
            <div className="flex h-32 items-center justify-center rounded-2xl border border-dashed border-white/10 text-sm text-slate-500">
              No familiarisation notes yet. Chat with the AI to generate them.
            </div>
          )}
          {notes.map((note, i) => (
            <div key={i} className="rounded-2xl border border-white/5 bg-slate-900/40 p-5 glass-panel">
              <div className="text-[11px] font-bold text-indigo-400 uppercase tracking-wider mb-2">{note.name}</div>
              <div className="text-sm text-slate-300 leading-relaxed whitespace-pre-wrap">{note.summary}</div>
            </div>
          ))}
          {phaseState?.structured_data?.initial_ideas && (
            <div className="rounded-2xl border border-white/5 bg-slate-900/40 p-5 glass-panel mt-6">
              <div className="text-[11px] font-bold text-violet-400 uppercase tracking-wider mb-3">Initial Ideas / Hunches</div>
              <ul className="list-disc list-inside text-sm text-slate-300 space-y-2">
                {phaseState.structured_data.initial_ideas.map((idea, i) => (
                  <li key={i} className="pl-1">{idea}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
      </div>
    )
  }

  // Phase 3: Coding
  if (phase === 3) {
    const codes = phaseState?.structured_data?.codes || []
    return (
      <div className="flex h-full flex-col overflow-hidden">
        <div className="border-b border-white/5 bg-slate-900/40 px-6 py-4">
          <h3 className="text-xs font-bold text-indigo-400 uppercase tracking-widest flex items-center gap-2">
            <Code size={16} /> Initial Codes
          </h3>
        </div>
        <div className="flex-1 overflow-y-auto p-6">
          {codes.length === 0 ? (
            <div className="flex h-32 items-center justify-center rounded-2xl border border-dashed border-white/10 text-sm text-slate-500">
              No codes generated yet. Chat with the AI to start coding.
            </div>
          ) : (
            <div className="space-y-4">
              <div className="text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-3">{codes.length} codes generated</div>
              {codes.map((code, i) => (
                <div key={i} className="rounded-2xl border border-white/5 bg-slate-900/40 p-5 glass-panel">
                  <div className="flex items-center gap-3 mb-2">
                    <span className="rounded-lg bg-indigo-500/20 px-2.5 py-1 text-xs font-bold text-indigo-300 border border-indigo-500/20">{code.name}</span>
                    <span className="text-[10px] font-semibold text-slate-500 uppercase tracking-wider">{code.extracts?.length || 0} extracts</span>
                  </div>
                  {code.definition && (
                    <div className="text-xs text-slate-400 mb-3 leading-relaxed">{code.definition}</div>
                  )}
                  <div className="space-y-2 mt-4">
                    {(code.extracts || []).slice(0, 3).map((ex, j) => (
                      <div key={j} className="rounded-xl bg-slate-950/50 px-4 py-3 text-xs text-slate-300 border-l-2 border-indigo-500/50 leading-relaxed shadow-inner shadow-black/10">
                        {ex.text?.substring(0, 150)}...
                      </div>
                    ))}
                    {(code.extracts || []).length > 3 && (
                      <div className="text-[10px] font-bold text-slate-500 uppercase tracking-widest pl-2">
                        + {code.extracts.length - 3} more extracts
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    )
  }

  // Phases 4-6: Theme builder
  if (phase >= 4 && phase <= 6) {
    return (
      <div className="flex h-full flex-col overflow-hidden">
        <div className="border-b border-white/5 bg-slate-900/40 px-6 py-4">
          <h3 className="text-xs font-bold text-indigo-400 uppercase tracking-widest flex items-center gap-2">
            <Layers size={16} /> Theme Builder
          </h3>
        </div>
        <div className="flex-1 overflow-hidden">
          <ThemeBuilder
            projectId={project.id}
            phaseState={phaseState}
            phase={phase}
          />
        </div>
      </div>
    )
  }

  // Phase 7: Report
  if (phase === 7) {
    return (
      <div className="flex h-full flex-col overflow-hidden">
        <div className="border-b border-white/5 bg-slate-900/40 px-6 py-4 flex items-center justify-between">
          <h3 className="text-xs font-bold text-indigo-400 uppercase tracking-widest flex items-center gap-2">
            <FileCheck size={16} /> Report
          </h3>
          <div className="flex gap-2">
            <button
              onClick={() => reportMutation.mutate({ projectId: project.id, format: 'pdf' })}
              disabled={reportMutation.isLoading}
              className="flex items-center gap-1.5 rounded-lg bg-indigo-500/10 border border-indigo-500/20 px-3 py-1.5 text-xs font-semibold text-indigo-400 transition hover:bg-indigo-500/20 disabled:opacity-50"
            >
              <Download size={14} /> PDF
            </button>
            <button
              onClick={() => reportMutation.mutate({ projectId: project.id, format: 'docx' })}
              disabled={reportMutation.isLoading}
              className="flex items-center gap-1.5 rounded-lg bg-indigo-500/10 border border-indigo-500/20 px-3 py-1.5 text-xs font-semibold text-indigo-400 transition hover:bg-indigo-500/20 disabled:opacity-50"
            >
              <Download size={14} /> Word
            </button>
          </div>
        </div>
        <div className="flex-1 overflow-hidden bg-slate-900/20">
          <ReportViewer
            project={project}
            reports={reports || []}
            phaseState={phaseState}
          />
        </div>
      </div>
    )
  }

  return <div className="p-4 text-slate-500 text-sm">Unknown phase</div>
}

export default WorkspacePanel
