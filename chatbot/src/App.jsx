import { useState, useEffect } from 'react'
import Header from './components/Header'
import Chat from './components/Chat'
import { fetchAgents } from './services/mcpService'

function App() {
  const [agents, setAgents] = useState([])
  const [selectedAgent, setSelectedAgent] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    loadAgents()
  }, [])

  const loadAgents = async () => {
    try {
      setLoading(true)
      setError(null)
      const agentList = await fetchAgents()
      setAgents(agentList)
      
      // Set default agent
      const defaultAgent = import.meta.env.VITE_DEFAULT_AGENT
      if (defaultAgent && agentList.find(a => a.id === defaultAgent)) {
        setSelectedAgent(defaultAgent)
      } else if (agentList.length > 0) {
        setSelectedAgent(agentList[0].id)
      }
    } catch (err) {
      console.error('Failed to load agents:', err)
      setError('Failed to connect to the server. Please check your connection.')
    } finally {
      setLoading(false)
    }
  }

  const appTitle = import.meta.env.VITE_APP_TITLE || 'Data Agent Chat'

  return (
    <div className="app">
      <Header 
        title={appTitle}
        agents={agents}
        selectedAgent={selectedAgent}
        onAgentChange={setSelectedAgent}
        onRefresh={loadAgents}
      />
      <main className="main-content">
        {loading ? (
          <div className="loading-container">
            <div className="loading-spinner"></div>
            <p>Connecting to server...</p>
          </div>
        ) : error ? (
          <div className="error-container">
            <p className="error-message">{error}</p>
            <button onClick={loadAgents} className="retry-button">
              Retry Connection
            </button>
          </div>
        ) : (
          <Chat 
            agentId={selectedAgent} 
            agentName={agents.find(a => a.id === selectedAgent)?.name || selectedAgent}
          />
        )}
      </main>
    </div>
  )
}

export default App
