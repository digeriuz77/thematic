import { useState, useEffect } from 'react'
import { useParams } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from 'react-query'
import { getProject, advancePhase, getPhaseState, sendPhaseChat } from '../services/api'
import ChatPanel from '../components/ChatPanel'
import WorkspacePanel from '../components/WorkspacePanel'
import { Loader2 } from 'lucide-react'

const PHASE_LABELS = [
  'Step 0: Research Question',
  'Phase 1: Interview & Planning',
  'Phase 2: Familiarisation',
  'Phase 3: Generating Codes',
  'Phase 4: Searching for Themes',
  'Phase 5: Reviewing Themes',
  'Phase 6: Defining & Naming Themes',
  'Phase 7: Producing the Report',
]

function ProjectPage() {
  const { projectId } = useParams()
  const queryClient = useQueryClient()
  const [chatMessages, setChatMessages] = useState([])

  const { data: project, isLoading } = useQuery(
    ['project', projectId],
    () => getProject(projectId),
    { refetchInterval: 5000 }
  )

  const { data: phaseState } = useQuery(
    ['phaseState', projectId, project?.current_phase],
    () => getPhaseState(projectId, project?.current_phase || 0),
    { enabled: !!project }
  )

  // Load prior chat from phase state
  useEffect(() => {
    if (phaseState?.ai_transcript) {
      try {
        const parsed = JSON.parse(phaseState.ai_transcript)
        setChatMessages(parsed)
      } catch {
        setChatMessages([])
      }
    } else {
      setChatMessages([])
    }
  }, [phaseState])

  const chatMutation = useMutation(sendPhaseChat, {
    onSuccess: (data) => {
      setChatMessages(prev => [...prev, { role: 'assistant', content: data.response }])
      queryClient.invalidateQueries(['phaseState', projectId, project?.current_phase])
    },
  })

  const advanceMutation = useMutation(advancePhase, {
    onSuccess: () => {
      queryClient.invalidateQueries(['project', projectId])
      setChatMessages([])
    },
  })

  const handleSendMessage = (content) => {
    const newMessages = [...chatMessages, { role: 'user', content }]
    setChatMessages(newMessages)
    chatMutation.mutate({
      project_id: projectId,
      phase_number: project?.current_phase || 0,
      messages: newMessages,
    })
  }

  const handleAdvancePhase = () => {
    advanceMutation.mutate(projectId)
  }

  if (isLoading || !project) {
    return (
      <div className="flex h-96 items-center justify-center text-muted">
        <Loader2 className="mr-2 animate-spin" size={20} />
        Loading project...
      </div>
    )
  }

  const currentPhaseLabel = PHASE_LABELS[project.current_phase] || 'Unknown Phase'

  return (
    <div className="flex h-[calc(100vh-80px)] flex-col gap-4 lg:flex-row">
      {/* Chat Panel */}
      <div className="flex flex-1 flex-col rounded-xl border border-accent/15 bg-bg2 min-h-[300px]">
        <div className="border-b border-accent/10 px-4 py-3">
          <div className="text-xs font-bold text-accent uppercase tracking-wider">{currentPhaseLabel}</div>
          <div className="mt-1 text-xs text-muted">Status: {project.phase_status}</div>
        </div>
        <ChatPanel
          messages={chatMessages}
          onSend={handleSendMessage}
          isLoading={chatMutation.isLoading}
        />
        {project.current_phase < 7 && (
          <div className="border-t border-accent/10 p-3">
            <button
              onClick={handleAdvancePhase}
              disabled={advanceMutation.isLoading}
              className="w-full rounded-lg bg-accent px-4 py-2 text-sm font-semibold text-white transition hover:bg-accent/90 disabled:opacity-50"
            >
              {advanceMutation.isLoading ? 'Advancing...' : `Advance to ${PHASE_LABELS[project.current_phase + 1]}`}
            </button>
          </div>
        )}
      </div>

      {/* Workspace Panel */}
      <div className="flex-[1.5] rounded-xl border border-accent/15 bg-bg2 overflow-hidden">
        <WorkspacePanel
          project={project}
          phaseState={phaseState}
          onSendMessage={handleSendMessage}
        />
      </div>
    </div>
  )
}

export default ProjectPage
