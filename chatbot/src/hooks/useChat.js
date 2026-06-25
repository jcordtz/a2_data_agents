import { useState, useCallback, useRef, useEffect } from 'react'
import { queryAgent } from '../services/mcpService'

/**
 * Custom hook for managing chat state and interactions
 * @param {string} agentId - The ID of the current agent
 * @returns {Object} Chat state and actions
 */
export function useChat(agentId) {
  const [messages, setMessages] = useState([])
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState(null)
  const abortControllerRef = useRef(null)

  // Clear messages when agent changes
  useEffect(() => {
    setMessages([])
    setError(null)
  }, [agentId])

  /**
   * Send a message to the agent
   * @param {string} question - The user's question
   */
  const sendMessage = useCallback(async (question) => {
    if (!question.trim() || !agentId || isLoading) return

    // Cancel any pending request
    if (abortControllerRef.current) {
      abortControllerRef.current.abort()
    }
    abortControllerRef.current = new AbortController()

    const userMessage = {
      id: Date.now(),
      role: 'user',
      content: question,
      timestamp: new Date().toISOString(),
    }

    setMessages(prev => [...prev, userMessage])
    setIsLoading(true)
    setError(null)

    try {
      const response = await queryAgent(agentId, question)
      
      const assistantMessage = {
        id: Date.now() + 1,
        role: 'assistant',
        content: response.data?.answer || response.answer || 'No response received.',
        sql: response.data?.sql || response.sql,
        results: response.data?.results || response.results,
        timestamp: new Date().toISOString(),
      }

      setMessages(prev => [...prev, assistantMessage])
    } catch (err) {
      if (err.name === 'AbortError') return
      
      setError(err.message || 'Failed to get a response. Please try again.')
      
      // Add error message to chat
      const errorMessage = {
        id: Date.now() + 1,
        role: 'assistant',
        content: `Sorry, I encountered an error: ${err.message || 'Unknown error'}. Please try again.`,
        isError: true,
        timestamp: new Date().toISOString(),
      }
      
      setMessages(prev => [...prev, errorMessage])
    } finally {
      setIsLoading(false)
    }
  }, [agentId, isLoading])

  /**
   * Clear all messages
   */
  const clearMessages = useCallback(() => {
    setMessages([])
    setError(null)
  }, [])

  /**
   * Cancel pending request
   */
  const cancelRequest = useCallback(() => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort()
      setIsLoading(false)
    }
  }, [])

  return {
    messages,
    isLoading,
    error,
    sendMessage,
    clearMessages,
    cancelRequest,
  }
}
