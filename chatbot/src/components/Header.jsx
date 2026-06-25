/**
 * Header Component
 * 
 * Application header with title, agent selector, and refresh button.
 */

export default function Header({ title, agents, selectedAgent, onAgentChange, onRefresh }) {
  return (
    <header className="header">
      <div className="header-left">
        <svg className="header-logo" viewBox="0 0 100 100" fill="none" xmlns="http://www.w3.org/2000/svg">
          <defs>
            <linearGradient id="headerGrad" x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" stopColor="#4F46E5" />
              <stop offset="100%" stopColor="#7C3AED" />
            </linearGradient>
          </defs>
          <circle cx="50" cy="50" r="45" fill="url(#headerGrad)" />
          <path d="M30 35 h40 M30 50 h30 M30 65 h35" stroke="white" strokeWidth="6" strokeLinecap="round" />
          <circle cx="75" cy="65" r="8" fill="white" />
        </svg>
        <h1 className="header-title">{title}</h1>
      </div>
      
      <div className="header-right">
        <div className="agent-selector">
          <label htmlFor="agent-select">Agent:</label>
          <select 
            id="agent-select"
            value={selectedAgent || ''} 
            onChange={(e) => onAgentChange(e.target.value)}
            disabled={agents.length === 0}
          >
            {agents.length === 0 ? (
              <option value="">No agents available</option>
            ) : (
              agents.map(agent => (
                <option key={agent.id} value={agent.id}>
                  {agent.name || agent.id}
                </option>
              ))
            )}
          </select>
        </div>
        
        <button 
          className="refresh-button" 
          onClick={onRefresh}
          title="Refresh agents list"
          aria-label="Refresh agents list"
        >
          <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <polyline points="23 4 23 10 17 10"></polyline>
            <polyline points="1 20 1 14 7 14"></polyline>
            <path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"></path>
          </svg>
        </button>
      </div>
    </header>
  )
}
