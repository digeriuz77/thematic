import { useState, useEffect } from 'react'
import { useParams } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from 'react-query'
import { getProject, advancePhase, previousPhase, resetProject, getPhaseState, sendPhaseChat, validatePhase } from '../services/api'
import ChatPanel from '../components/ChatPanel'
import WorkspacePanel from '../components/WorkspacePanel'
import { Loader2, ArrowLeft, RotateCcw, Home, Play, Square } from 'lucide-react'

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
  const [isAutoPilot, setIsAutoPilot] = useState(false)
  const [retryCount, setRetryCount] = useState(0)
  const [autoPilotStatus, setAutoPilotStatus] = useState('idle') // idle, running, validating, correcting, error
  const [autoPilotError, setAutoPilotError] = useState(null)

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

  const previousMutation = useMutation(previousPhase, {
    onSuccess: () => {
      queryClient.invalidateQueries(['project', projectId])
    },
  })

  const resetMutation = useMutation(resetProject, {
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

  // Auto-Pilot Effect Loop
  useEffect(() => {
    if (!isAutoPilot || !project || chatMutation.isLoading || advanceMutation.isLoading || autoPilotStatus === 'validating') return;

    if (project.current_phase >= 7) {
      setIsAutoPilot(false);
      setAutoPilotStatus('idle');
      return;
    }

    const lastMessage = chatMessages[chatMessages.length - 1];

    if (!lastMessage || lastMessage.role === 'user') {
      // AI hasn't spoken yet for this phase
      setAutoPilotStatus('running');
      const autoMessage = project.current_phase === 0
        ? "Please acknowledge the files and let's begin Phase 1."
        : "Please automatically conduct this phase of the thematic analysis following best practices, using the data provided.";
      
      handleSendMessage(autoMessage);
    } else if (lastMessage.role === 'assistant') {
      // AI just finished its turn, let's validate the data before advancing!
      setAutoPilotStatus('validating');
      setAutoPilotError(null);

      validatePhase(projectId, project.current_phase)
        .then(result => {
          if (result.valid) {
            // Data is securely saved! Reset retry counter and advance phase
            setRetryCount(0);
            setAutoPilotStatus('running');
            handleAdvancePhase();
          } else {
            // Validation failed!
            if (retryCount < 3) {
              setRetryCount(prev => prev + 1);
              setAutoPilotStatus('correcting');
              
              const errorDetails = result.errors.map(err => `- ${err}`).join('\n');
              const correctionMessage = `It looks like the structured data generated for this phase is missing or invalid:\n${errorDetails}\n\nPlease analyze the data carefully and output the complete and valid JSON block matching the required keys. Do not omit any required fields!`;
              
              handleSendMessage(correctionMessage);
            } else {
              // Exceeded max retries
              setIsAutoPilot(false);
              setAutoPilotStatus('error');
              setAutoPilotError(`Failed to save valid phase data after 3 retries:\n${result.errors.join('\n')}`);
              alert(`Auto-Pilot stopped: The AI repeatedly failed to generate valid structured data for ${PHASE_LABELS[project.current_phase]}.\n\nErrors:\n${result.errors.join('\n')}`);
            }
          }
        })
        .catch(err => {
          setIsAutoPilot(false);
          setAutoPilotStatus('error');
          setAutoPilotError(`Validation check failed: ${err.message}`);
          alert(`Auto-Pilot validation error: ${err.message}`);
        });
    }
  }, [isAutoPilot, project?.current_phase, chatMessages, chatMutation.isLoading, advanceMutation.isLoading, autoPilotStatus, retryCount]);

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
    <div className="flex h-[calc(100vh-80px)] flex-col gap-6 lg:flex-row p-2">
      {/* Chat Panel */}
      <div className="flex flex-1 flex-col rounded-3xl border border-white/10 bg-slate-950/40 min-h-[300px] glass-panel overflow-hidden shadow-xl shadow-indigo-500/5 relative">
        
        {/* Action Header */}
        <div className="absolute top-0 left-0 right-0 p-4 flex justify-between items-start pointer-events-none z-10">
          <div className="pointer-events-auto">
            <button
              onClick={() => window.location.href = '/'}
              className="flex items-center justify-center h-8 w-8 rounded-full bg-slate-900/80 border border-white/10 text-slate-400 hover:text-white hover:bg-indigo-500/50 transition backdrop-blur-md"
              title="Back to Home"
            >
              <Home size={14} />
            </button>
          </div>
          
          <div className="flex gap-2 pointer-events-auto">
            {project.current_phase > 0 && (
              <>
                <button
                  onClick={() => previousMutation.mutate(projectId)}
                  disabled={previousMutation.isLoading || isAutoPilot}
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-slate-900/80 border border-white/10 text-xs font-semibold text-slate-300 hover:text-white hover:bg-indigo-500/50 transition backdrop-blur-md disabled:opacity-50"
                >
                  <ArrowLeft size={12} /> Previous
                </button>
                <button
                  onClick={() => {
                    if (window.confirm("Are you sure you want to completely restart the analysis? All progress will be lost.")) {
                      setIsAutoPilot(false);
                      resetMutation.mutate(projectId);
                    }
                  }}
                  disabled={resetMutation.isLoading || isAutoPilot}
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-slate-900/80 border border-rose-500/30 text-xs font-semibold text-rose-400 hover:text-white hover:bg-rose-500/80 transition backdrop-blur-md disabled:opacity-50"
                >
                  <RotateCcw size={12} /> Restart
                </button>
              </>
            )}
          </div>
        </div>

        <div className="border-b border-white/5 bg-slate-900/40 px-6 py-4 flex items-center justify-between pt-14">
          <div className="text-xs font-bold text-indigo-400 uppercase tracking-widest">{currentPhaseLabel}</div>
          <div className="flex items-center gap-3">
            <button
              onClick={() => {
                if (!isAutoPilot) {
                  setRetryCount(0);
                  setAutoPilotStatus('running');
                  setAutoPilotError(null);
                }
                setIsAutoPilot(!isAutoPilot);
              }}
              className={`flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold uppercase tracking-wider transition-all ${
                isAutoPilot 
                  ? 'bg-rose-500/20 text-rose-400 border border-rose-500/50 hover:bg-rose-500/30 shadow-[0_0_15px_rgba(244,63,94,0.3)] animate-pulse' 
                  : 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/30 hover:bg-emerald-500/20 hover:shadow-[0_0_15px_rgba(16,185,129,0.2)]'
              }`}
            >
              {isAutoPilot ? <Square size={12} fill="currentColor" /> : <Play size={12} fill="currentColor" />}
              {isAutoPilot ? 'Stop Auto-Pilot' : 'Auto-Pilot Mode'}
            </button>
            {isAutoPilot && (
              <div className={`text-[10px] font-bold uppercase tracking-wider px-2.5 py-1 rounded-full border transition-all duration-300 animate-pulse ${
                autoPilotStatus === 'validating' 
                  ? 'bg-amber-500/10 text-amber-400 border-amber-500/30 shadow-[0_0_10px_rgba(245,158,11,0.1)]'
                  : autoPilotStatus === 'correcting'
                  ? 'bg-amber-600/20 text-amber-300 border-amber-500/50 shadow-[0_0_12px_rgba(245,158,11,0.2)]'
                  : 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30 shadow-[0_0_10px_rgba(16,185,129,0.1)]'
              }`}>
                {autoPilotStatus === 'validating' && 'Validating Data...'}
                {autoPilotStatus === 'correcting' && `Self-Correcting (Retry ${retryCount}/3)...`}
                {autoPilotStatus === 'running' && 'AI Thinking...'}
              </div>
            )}
            <div className="text-[10px] font-medium text-slate-400 uppercase tracking-wider bg-slate-800/50 px-2 py-1 rounded-full border border-white/5">
              {project.phase_status.replace('_', ' ')}
            </div>
          </div>
        </div>
        <ChatPanel
          messages={chatMessages}
          onSend={handleSendMessage}
          isLoading={chatMutation.isLoading}
        />
        {project.current_phase < 7 && (
          <div className="border-t border-white/5 bg-slate-900/40 p-4">
            <button
              onClick={handleAdvancePhase}
              disabled={advanceMutation.isLoading}
              className="w-full flex items-center justify-center gap-2 rounded-xl bg-gradient-to-r from-indigo-500 to-violet-600 px-4 py-3 text-sm font-semibold text-white transition hover:brightness-110 disabled:opacity-50 shadow-md shadow-indigo-500/10 glow-btn"
            >
              {advanceMutation.isLoading ? 'Advancing...' : `Advance to ${PHASE_LABELS[project.current_phase + 1]}`}
            </button>
          </div>
        )}
      </div>

      {/* Workspace Panel */}
      <div className="flex-[1.5] rounded-3xl border border-white/10 bg-slate-950/40 overflow-hidden glass-panel shadow-xl shadow-violet-500/5">
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
