import { useRef, useEffect } from 'react'
import { useChat } from '../hooks/useChat'
import ChatMessage from './ChatMessage'
import ChatInput from './ChatInput'

/**
 * Chat Component
 * 
 * Main chat container that displays messages and handles user input.
 */
export default function Chat({ agentId, agentName }) {
  const { messages, isLoading, sendMessage, clearMessages } = useChat(agentId)
  const messagesEndRef = useRef(null)

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const handleSendMessage = (message) => {
    sendMessage(message)
  }

  const handleSuggestionClick = (suggestion) => {
    sendMessage(suggestion)
  }

  const suggestions = [
    'Show me all tables',
    'What columns are in this table?',
    'Show me the first 10 rows',
    'What are the relationships between tables?',
  ]

  return (
    <div className="chat-container">
      <div className="messages-container">
        {messages.length === 0 ? (
          <div className="empty-state">
            <svg className="empty-state-icon" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
              <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path>
              <path d="M8 10h.01M12 10h.01M16 10h.01"></path>
            </svg>
            <h2>Start a Conversation</h2>
            <p>
              Ask questions about your data in natural language. 
              {agentName && ` Currently connected to ${agentName}.`}
            </p>
            <div className="suggestions">
              {suggestions.map((suggestion, index) => (
                <button
                  key={index}
                  className="suggestion-chip"
                  onClick={() => handleSuggestionClick(suggestion)}
                >
                  {suggestion}
                </button>
              ))}
            </div>
          </div>
        ) : (
          <div className="messages-list">
            {messages.map((message) => (
              <ChatMessage key={message.id} message={message} />
            ))}
            {isLoading && (
              <div className="message assistant">
                <div className="message-avatar">AI</div>
                <div className="message-content">
                  <div className="typing-indicator">
                    <span></span>
                    <span></span>
                    <span></span>
                  </div>
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>
        )}
      </div>
      
      <ChatInput 
        onSend={handleSendMessage} 
        disabled={isLoading || !agentId}
        placeholder={agentId ? "Ask a question about your data..." : "Select an agent to start"}
      />
    </div>
  )
}
