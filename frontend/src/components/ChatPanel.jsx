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
      <div ref={scrollRef} className="flex-1 overflow-y-auto p-4 space-y-3">
        {messages.length === 0 && (
          <div className="text-center text-muted text-sm py-8">
            <Bot size={32} className="mx-auto mb-2 text-accent/30" />
            <p>Start the conversation to begin this phase.</p>
            <p className="text-xs mt-1">The AI will guide you through the methodology.</p>
          </div>
        )}
        {messages.map((msg, i) => (
          <div key={i} className={`flex gap-2 ${msg.role === 'user' ? 'flex-row-reverse' : ''}`}>
            <div className={`flex h-6 w-6 shrink-0 items-center justify-center rounded-full text-xs ${
              msg.role === 'user' ? 'bg-accent/20 text-accent' : 'bg-muted/20 text-muted'
            }`}>
              {msg.role === 'user' ? <User size={12} /> : <Bot size={12} />}
            </div>
            <div className={`max-w-[85%] px-3 py-2 text-sm leading-relaxed whitespace-pre-wrap ${
              msg.role === 'user' ? 'message-user text-text' : 'message-assistant text-text/90'
            }`}>
              {msg.content}
            </div>
          </div>
        ))}
        {isLoading && (
          <div className="flex gap-2">
            <div className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-muted/20 text-muted">
              <Bot size={12} />
            </div>
            <div className="message-assistant px-3 py-2 text-sm text-muted">
              <Loader2 size={14} className="animate-spin" />
            </div>
          </div>
        )}
      </div>

      <form onSubmit={handleSubmit} className="border-t border-accent/10 p-3">
        <div className="flex gap-2">
          <input
            type="text"
            value={input}
            onChange={e => setInput(e.target.value)}
            placeholder="Type your message..."
            className="flex-1 rounded-lg px-3 py-2 text-sm"
          />
          <button
            type="submit"
            disabled={isLoading || !input.trim()}
            className="flex items-center justify-center rounded-lg bg-accent px-3 py-2 text-white transition hover:bg-accent/90 disabled:opacity-50"
          >
            <Send size={16} />
          </button>
        </div>
      </form>
    </div>
  )
}

export default ChatPanel
