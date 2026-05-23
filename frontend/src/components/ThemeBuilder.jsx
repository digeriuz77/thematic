import { useState, useEffect } from 'react'
import { useQuery, useMutation, useQueryClient } from 'react-query'
import { getProject, updateProject } from '../services/api'
import { TreePine, Circle, GitBranch, Plus, X } from 'lucide-react'

function ThemeBuilder({ projectId, phaseState, phase }) {
  const queryClient = useQueryClient()
  const [themes, setThemes] = useState([])

  const { data: project } = useQuery(['project', projectId], () => getProject(projectId))

  useEffect(() => {
    if (phaseState?.structured_data) {
      const data = phaseState.structured_data
      let parsedThemes = []
      if (phase === 4 && data.candidate_themes) {
        parsedThemes = data.candidate_themes
      } else if (phase === 5 && data.refined_themes) {
        parsedThemes = data.refined_themes
      } else if (phase === 6 && data.final_themes) {
        parsedThemes = data.final_themes
      }
      setThemes(parsedThemes)
    }
  }, [phaseState, phase])

  const handleAddTheme = () => {
    setThemes(prev => [...prev, { name: 'New Theme', definition: '', type: 'overarching', code_names: [] }])
  }

  const handleRemoveTheme = (index) => {
    setThemes(prev => prev.filter((_, i) => i !== index))
  }

  const handleUpdateTheme = (index, field, value) => {
    setThemes(prev => {
      const updated = [...prev]
      updated[index] = { ...updated[index], [field]: value }
      return updated
    })
  }

  const saveToProject = () => {
    // This is a simplified manual edit - in production, you'd persist to backend
    const key = phase === 4 ? 'candidate_themes' : phase === 5 ? 'refined_themes' : 'final_themes'
    // For now we just keep local state; real persistence would update phase_state.structured_data
  }

  return (
    <div className="flex h-full flex-col overflow-hidden">
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {themes.length === 0 && (
          <div className="text-sm text-muted text-center py-8">
            <TreePine size={32} className="mx-auto mb-2 text-accent/30" />
            <p>No themes yet. Chat with the AI to generate candidate themes.</p>
          </div>
        )}

        {/* Overarching themes */}
        {themes.filter(t => t.type === 'overarching' || !t.type).map((theme, i) => (
          <div key={i} className="rounded-xl border border-accent/15 bg-bg p-4 space-y-3">
            <div className="flex items-center gap-2">
              <Circle size={14} className="text-accent" />
              <input
                value={theme.name}
                onChange={e => handleUpdateTheme(themes.indexOf(theme), 'name', e.target.value)}
                className="flex-1 rounded bg-transparent px-2 py-1 text-sm font-semibold text-text border-none focus:ring-1 focus:ring-accent/30"
              />
              <button onClick={() => handleRemoveTheme(themes.indexOf(theme))} className="text-muted hover:text-red transition">
                <X size={14} />
              </button>
            </div>
            <textarea
              value={theme.definition || ''}
              onChange={e => handleUpdateTheme(themes.indexOf(theme), 'definition', e.target.value)}
              placeholder="Theme definition..."
              rows={2}
              className="w-full rounded bg-bg2 px-3 py-2 text-xs text-muted resize-none"
            />
            <div className="flex flex-wrap gap-1">
              {(theme.code_names || []).map((code, j) => (
                <span key={j} className="rounded bg-accent/10 px-2 py-0.5 text-xs text-accent">{code}</span>
              ))}
            </div>

            {/* Sub-themes */}
            <div className="ml-4 space-y-2 border-l-2 border-accent/10 pl-3">
              {themes.filter(t => t.parent_name === theme.name || t.parent === theme.name).map((sub, j) => (
                <div key={j} className="rounded-lg border border-accent/10 bg-bg2 p-2">
                  <div className="flex items-center gap-2">
                    <GitBranch size={12} className="text-accent2" />
                    <input
                      value={sub.name}
                      onChange={e => {
                        const subIdx = themes.indexOf(sub)
                        handleUpdateTheme(subIdx, 'name', e.target.value)
                      }}
                      className="flex-1 rounded bg-transparent px-1 py-0.5 text-xs font-medium text-text border-none"
                    />
                    <button onClick={() => handleRemoveTheme(themes.indexOf(sub))} className="text-muted hover:text-red transition">
                      <X size={12} />
                    </button>
                  </div>
                  <textarea
                    value={sub.definition || ''}
                    onChange={e => {
                      const subIdx = themes.indexOf(sub)
                      handleUpdateTheme(subIdx, 'definition', e.target.value)
                    }}
                    placeholder="Sub-theme definition..."
                    rows={1}
                    className="w-full rounded bg-bg px-2 py-1 text-xs text-muted resize-none mt-1"
                  />
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>

      <div className="border-t border-accent/10 p-3 flex items-center justify-between">
        <button
          onClick={handleAddTheme}
          className="flex items-center gap-1 rounded-lg bg-accent/10 px-3 py-1.5 text-xs font-medium text-accent transition hover:bg-accent/20"
        >
          <Plus size={12} /> Add Theme
        </button>
        <span className="text-xs text-muted">{themes.length} themes</span>
      </div>
    </div>
  )
}

export default ThemeBuilder
