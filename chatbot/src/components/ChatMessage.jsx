/**
 * ChatMessage Component
 * 
 * Displays a single chat message with formatting support.
 */
export default function ChatMessage({ message }) {
  const { role, content, sql, isError } = message

  // Simple markdown-like rendering for code blocks
  const renderContent = (text) => {
    if (!text) return null
    
    // Split by code blocks
    const parts = text.split(/(```[\s\S]*?```)/g)
    
    return parts.map((part, index) => {
      if (part.startsWith('```') && part.endsWith('```')) {
        // Code block
        const codeContent = part.slice(3, -3)
        const [lang, ...codeLines] = codeContent.split('\n')
        const code = lang.match(/^[a-z]+$/i) ? codeLines.join('\n') : codeContent
        
        return (
          <pre key={index}>
            <code>{code.trim()}</code>
          </pre>
        )
      }
      
      // Regular text - handle inline code and basic formatting
      return (
        <div key={index}>
          {part.split('\n').map((line, lineIndex) => {
            // Handle inline code
            const renderedLine = line.split(/(`[^`]+`)/g).map((segment, segIndex) => {
              if (segment.startsWith('`') && segment.endsWith('`')) {
                return <code key={segIndex}>{segment.slice(1, -1)}</code>
              }
              return segment
            })
            
            return (
              <p key={lineIndex}>
                {renderedLine}
              </p>
            )
          }).filter(p => p.props.children[0] !== '')}
        </div>
      )
    })
  }

  return (
    <div className={`message ${role} ${isError ? 'error' : ''}`}>
      <div className="message-avatar">
        {role === 'user' ? 'U' : 'AI'}
      </div>
      <div className="message-content">
        {renderContent(content)}
        
        {sql && (
          <div className="sql-block">
            <div className="sql-label">Generated SQL</div>
            <code>{sql}</code>
          </div>
        )}
      </div>
    </div>
  )
}
