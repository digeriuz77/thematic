import { useState, useRef, useEffect } from 'react'
import { Send, Loader2, Bot, User } from 'lucide-react'

function ChatPanel({ messages, onSend, isLoading }) {
  const [input, setInput] = useState('')
  const scrollRef = useRef(null)

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight
    }
  }, [messages, isLoading])

  const handleSubmit = (e) => {
    e.preventDefault()
    if (!input.trim() || isLoading) return
    onSend(input.trim())
    setInput('')
  }

  return (
    <div className="flex flex-1 flex-col overflow-hidden">
      <div ref={scrollRef} className="flex-1 overflow-y-auto p-6 space-y-6">
        {messages.length === 0 && (
          <div className="flex h-full flex-col items-center justify-center text-center px-4">
            <div className="relative mb-6">
              <div className="absolute inset-0 animate-ping rounded-full bg-indigo-500/20"></div>
              <div className="relative flex h-16 w-16 items-center justify-center rounded-full bg-gradient-to-br from-indigo-500/20 to-violet-600/20 border border-indigo-500/30 text-indigo-400">
                <Bot size={32} />
              </div>
            </div>
            <p className="text-lg font-medium text-slate-200 mb-2">Ready to Analyze</p>
            <p className="text-sm text-slate-400 max-w-[250px]">The AI will guide you through the methodology. Say hello to begin.</p>
          </div>
        )}
        {messages.map((msg, i) => (
          <div key={i} className={`flex gap-3 ${msg.role === 'user' ? 'flex-row-reverse' : ''}`}>
            <div className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-full text-xs shadow-lg ${
              msg.role === 'user' 
                ? 'bg-gradient-to-br from-indigo-500 to-violet-600 text-white shadow-indigo-500/20' 
                : 'bg-slate-800 border border-white/10 text-indigo-400 shadow-black/20'
            }`}>
              {msg.role === 'user' ? <User size={14} /> : <Bot size={14} />}
            </div>
            <div className={`max-w-[85%] px-4 py-3 text-[13px] leading-relaxed whitespace-pre-wrap rounded-2xl ${
              msg.role === 'user' 
                ? 'bg-indigo-500/10 border border-indigo-500/20 text-indigo-50 rounded-tr-sm' 
                : 'bg-slate-900/60 border border-white/5 text-slate-300 rounded-tl-sm glass-panel'
            }`}>
              {msg.content}
            </div>
          </div>
        ))}
        {isLoading && (
          <div className="flex gap-3">
            <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-slate-800 border border-white/10 text-indigo-400 shadow-lg shadow-black/20">
              <Bot size={14} />
            </div>
            <div className="glass-panel px-4 py-3 rounded-2xl rounded-tl-sm bg-slate-900/60 border border-white/5 text-slate-400">
              <Loader2 size={16} className="animate-spin" />
            </div>
          </div>
        )}
      </div>

      <form onSubmit={handleSubmit} className="p-4 bg-slate-950/50 backdrop-blur-md border-t border-white/5">
        <div className="flex gap-3 items-center relative">
          <input
            type="text"
            value={input}
            onChange={e => setInput(e.target.value)}
            placeholder="Type your message..."
            className="flex-1 rounded-full bg-slate-900 border border-white/10 px-5 py-3.5 text-sm text-slate-200 placeholder-slate-500 focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 transition duration-200"
          />
          <button
            type="submit"
            disabled={isLoading || !input.trim()}
            className="absolute right-2 flex h-10 w-10 items-center justify-center rounded-full bg-indigo-500 text-white transition hover:bg-indigo-400 disabled:opacity-50 disabled:hover:bg-indigo-500 shadow-lg shadow-indigo-500/20"
          >
            <Send size={16} className="ml-1" />
          </button>
        </div>
      </form>
    </div>
  )
}

export default ChatPanel
