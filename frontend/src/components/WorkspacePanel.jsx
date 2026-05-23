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
        <div className="border-b border-accent/10 px-4 py-3">
          <h3 className="text-sm font-bold text-accent uppercase tracking-wider flex items-center gap-2">
            <BookOpen size={14} /> Data Corpus
          </h3>
        </div>
        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          {/* Research Question */}
          <div className="rounded-lg border border-accent/10 bg-bg p-3">
            <label className="text-xs font-semibold text-muted uppercase mb-1 block">Research Question</label>
            <textarea
              defaultValue={project.research_question || ''}
              onBlur={e => updateMutation.mutate({ id: project.id, data: { research_question: e.target.value } })}
              rows={2}
              className="w-full rounded-lg px-3 py-2 text-sm"
              placeholder="Enter your research question..."
            />
          </div>

          {/* Sources list */}
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold text-muted uppercase">Sources ({sources?.length || 0})</span>
              <label className="flex cursor-pointer items-center gap-1 rounded-lg bg-accent/10 px-2 py-1 text-xs font-medium text-accent transition hover:bg-accent/20">
                <Upload size={12} /> Upload File
                <input type="file" className="hidden" onChange={handleFileUpload} accept=".txt,.docx,.pdf,.csv,.xlsx" />
              </label>
            </div>
            {sources?.map(source => (
              <div key={source.id} className="flex items-center justify-between rounded-lg border border-accent/10 bg-bg p-2 text-sm">
                <div className="flex items-center gap-2 min-w-0">
                  <FileText size={14} className="text-accent shrink-0" />
                  <span className="truncate">{source.name}</span>
                  <span className="text-xs text-muted shrink-0">({source.source_type})</span>
                </div>
                <button onClick={() => deleteMutation.mutate(source.id)} className="text-muted hover:text-red transition shrink-0">
                  <Trash2 size={14} />
                </button>
              </div>
            ))}
          </div>

          {/* Paste text */}
          <form onSubmit={handlePasteSubmit} className="space-y-2">
            <input name="name" type="text" placeholder="Source name..." className="w-full rounded-lg px-3 py-2 text-sm" />
            <textarea name="content" rows={4} placeholder="Paste transcript text here..." className="w-full rounded-lg px-3 py-2 text-sm resize-none" />
            <button type="submit" className="flex items-center gap-1 rounded-lg bg-accent/10 px-3 py-1.5 text-xs font-medium text-accent transition hover:bg-accent/20">
              <Plus size={12} /> Add Source
            </button>
          </form>

          {/* Analytic Decisions */}
          {phase === 1 && (
            <div className="rounded-lg border border-accent/10 bg-bg p-3 space-y-3">
              <h4 className="text-xs font-bold text-accent uppercase tracking-wider">Four Upfront Decisions</h4>
              {['scope', 'coding_approach', 'theme_level', 'epistemology'].map((key) => (
                <div key={key}>
                  <label className="text-xs text-muted uppercase mb-1 block">{key.replace('_', ' ')}</label>
                  <select
                    defaultValue={project.analytic_decisions?.[key] || ''}
                    onChange={e => {
                      const current = project.analytic_decisions || {}
                      updateMutation.mutate({
                        id: project.id,
                        data: { analytic_decisions: { ...current, [key]: e.target.value } }
                      })
                    }}
                    className="w-full rounded-lg px-3 py-2 text-sm"
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
        <div className="border-b border-accent/10 px-4 py-3">
          <h3 className="text-sm font-bold text-accent uppercase tracking-wider flex items-center gap-2">
            <BookOpen size={14} /> Familiarisation Notes
          </h3>
        </div>
        <div className="flex-1 overflow-y-auto p-4 space-y-3">
          {notes.length === 0 && (
            <div className="text-sm text-muted">No familiarisation notes yet. Chat with the AI to generate them.</div>
          )}
          {notes.map((note, i) => (
            <div key={i} className="rounded-lg border border-accent/10 bg-bg p-3">
              <div className="text-xs font-semibold text-accent mb-1">{note.name}</div>
              <div className="text-sm text-text/90 whitespace-pre-wrap">{note.summary}</div>
            </div>
          ))}
          {phaseState?.structured_data?.initial_ideas && (
            <div className="rounded-lg border border-accent/10 bg-bg p-3">
              <div className="text-xs font-semibold text-accent mb-2">Initial Ideas / Hunches</div>
              <ul className="list-disc list-inside text-sm text-text/90 space-y-1">
                {phaseState.structured_data.initial_ideas.map((idea, i) => (
                  <li key={i}>{idea}</li>
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
        <div className="border-b border-accent/10 px-4 py-3">
          <h3 className="text-sm font-bold text-accent uppercase tracking-wider flex items-center gap-2">
            <Code size={14} /> Initial Codes
          </h3>
        </div>
        <div className="flex-1 overflow-y-auto p-4">
          {codes.length === 0 ? (
            <div className="text-sm text-muted">No codes generated yet. Chat with the AI to start coding.</div>
          ) : (
            <div className="space-y-3">
              <div className="text-xs text-muted mb-2">{codes.length} codes generated</div>
              {codes.map((code, i) => (
                <div key={i} className="rounded-lg border border-accent/10 bg-bg p-3">
                  <div className="flex items-center gap-2 mb-1">
                    <span className="rounded bg-accent/20 px-2 py-0.5 text-xs font-semibold text-accent">{code.name}</span>
                    <span className="text-xs text-muted">{code.extracts?.length || 0} extracts</span>
                  </div>
                  {code.definition && (
                    <div className="text-xs text-muted mb-2">{code.definition}</div>
                  )}
                  <div className="space-y-1">
                    {(code.extracts || []).slice(0, 3).map((ex, j) => (
                      <div key={j} className="rounded bg-bg2 px-2 py-1 text-xs text-text/80 border-l-2 border-accent/30">
                        {ex.text?.substring(0, 120)}...
                      </div>
                    ))}
                    {(code.extracts || []).length > 3 && (
                      <div className="text-xs text-muted">+ {code.extracts.length - 3} more extracts</div>
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
        <div className="border-b border-accent/10 px-4 py-3">
          <h3 className="text-sm font-bold text-accent uppercase tracking-wider flex items-center gap-2">
            <Layers size={14} /> Theme Builder
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
        <div className="border-b border-accent/10 px-4 py-3 flex items-center justify-between">
          <h3 className="text-sm font-bold text-accent uppercase tracking-wider flex items-center gap-2">
            <FileCheck size={14} /> Report
          </h3>
          <div className="flex gap-2">
            <button
              onClick={() => reportMutation.mutate({ projectId: project.id, format: 'pdf' })}
              disabled={reportMutation.isLoading}
              className="flex items-center gap-1 rounded-lg bg-accent/10 px-3 py-1.5 text-xs font-medium text-accent transition hover:bg-accent/20 disabled:opacity-50"
            >
              <Download size={12} /> PDF
            </button>
            <button
              onClick={() => reportMutation.mutate({ projectId: project.id, format: 'docx' })}
              disabled={reportMutation.isLoading}
              className="flex items-center gap-1 rounded-lg bg-accent/10 px-3 py-1.5 text-xs font-medium text-accent transition hover:bg-accent/20 disabled:opacity-50"
            >
              <Download size={12} /> Word
            </button>
          </div>
        </div>
        <div className="flex-1 overflow-hidden">
          <ReportViewer
            project={project}
            reports={reports || []}
            phaseState={phaseState}
          />
        </div>
      </div>
    )
  }

  return <div className="p-4 text-muted text-sm">Unknown phase</div>
}

export default WorkspacePanel
