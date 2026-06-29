# Data Agent Chatbot Interface

**A web-based chat interface for querying databases through the MCP Server.**

A React-based chatbot UI that connects to the MCP Server, enabling natural language queries against Oracle, SQL Server, PostgreSQL, and IBM DB2 databases.

> **⚠️ Disclaimer**: This code was generated with AI assistance (AI-generated code). It is provided "AS-IS" under the MIT License without warranty of any kind. Users should review and test thoroughly before production use.

---

## Features

- **Natural Language Interface**: Ask questions in plain English
- **Multi-Database Support**: Query Oracle, SQL Server, and PostgreSQL through MCP
- **Real-time Responses**: Streaming-like response display
- **Conversation History**: Maintains context across queries
- **Agent Selection**: Choose which data agent to query
- **Responsive Design**: Works on desktop and mobile
- **Azure Deployment**: Deploys to Azure Static Web Apps

---

## Architecture

The chatbot is a static React application that calls the MCP server directly (no backend API layer needed).

```
┌─────────────────────────────────────────────────────────────────┐
│                         User Browser                             │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │              React Chat Interface                        │    │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐   │    │
│  │  │  Chat Input  │  │   Messages   │  │ Agent Select │   │    │
│  │  └──────────────┘  └──────────────┘  └──────────────┘   │    │
│  └─────────────────────────────────────────────────────────┘    │
└─────────────────────────────────┬───────────────────────────────┘
                                  │ HTTPS (direct call)
                                  ▼
┌─────────────────────────────────────────────────────────────────┐
│                          MCP Server                              │
│             (Azure Container Apps with CORS enabled)             │
└─────────────────────────────────────────────────────────────────┘
```

**Note:** The MCP server URL and auth token are baked into the frontend at build time via environment variables (`VITE_MCP_SERVER_URL` and `VITE_MCP_AUTH_TOKEN`).

---

## Project Structure

```
chatbot/
├── src/                      # React source code
│   ├── components/           # UI components
│   │   ├── Chat.jsx          # Main chat container
│   │   ├── ChatInput.jsx     # Message input component
│   │   ├── ChatMessage.jsx   # Individual message display
│   │   ├── AgentSelector.jsx # Agent selection dropdown
│   │   └── Header.jsx        # App header
│   ├── hooks/                # Custom React hooks
│   │   └── useChat.js        # Chat state management
│   ├── services/             # API services
│   │   └── mcpService.js     # MCP Server communication
│   ├── styles/               # CSS styles
│   │   └── main.css          # Main stylesheet
│   ├── App.jsx               # Main App component
│   └── main.jsx              # Entry point
├── api/                      # Azure Functions API (serverless backend)
│   ├── query/                # Query endpoint
│   │   └── index.js
│   ├── agents/               # List agents endpoint
│   │   └── index.js
│   └── health/               # Health check endpoint
│       └── index.js
├── public/                   # Static assets
│   └── favicon.ico
├── infra/                    # Bicep infrastructure
│   ├── main.bicep
│   └── main.parameters.json
├── package.json              # Node.js dependencies
├── vite.config.js            # Vite configuration
├── staticwebapp.config.json  # Azure Static Web Apps config
├── deploy.sh                 # Deployment script
└── README.md                 # This file
```

---

## Quick Start

### Prerequisites

- Node.js 18+
- npm or yarn
- Azure CLI
- Azure subscription

### Local Development

```bash
# Install dependencies
cd chatbot
npm install

# Set environment variables
cp .env.example .env
# Edit .env with your MCP server URL

# Start development server
npm run dev
```

The app will be available at `http://localhost:5173`

### Configuration

Create a `.env` file for local development:

```env
VITE_MCP_SERVER_URL=http://localhost:8080
VITE_MCP_AUTH_TOKEN=your-auth-token
VITE_APP_TITLE=Data Agent Chat
```

---

## Deployment

### Deploy to Azure Static Web Apps

The chatbot deploys as a pure static site. The MCP server URL and auth token are baked in at build time.

```bash
# Login to Azure
az login

# Use the deployment script (recommended)
./deploy.sh \
  --resource-group your-rg \
  --mcp-url https://your-mcp-server.azurecontainerapps.io \
  --mcp-token YOUR_MCP_AUTH_TOKEN \
  --location eastus

# Or deploy via the master script
cd ..
./run.sh --chatbot \
  --resource-group your-rg \
  --mcp-url https://your-mcp-server.azurecontainerapps.io \
  --mcp-token YOUR_MCP_AUTH_TOKEN
```

**Note:** The MCP server URL and token are embedded in the JavaScript bundle at build time. There's no backend API layer - the React app calls the MCP server directly via HTTPS.

---

## MCP Server Endpoints

The chatbot calls the MCP server directly. These are the MCP endpoints used:

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/mcp/v1/tools/call` | POST | Execute MCP tool (query_table, list_agents) |
| `/health` | GET | Health check |

### Query Request (via MCP)

```json
POST /mcp/v1/tools/call
{
  "name": "query_table",
  "arguments": {
    "agent_id": "hr_employees",
    "question": "Show me the top 5 employees by salary"
  }
}
```

### List Agents Request

```json
POST /mcp/v1/tools/call
{
  "name": "list_agents",
  "arguments": {}
}
```

### Query Response

```json
{
  "content": {
    "answer": "Here are the top 5 employees...",
    "sql": "SELECT * FROM employees ORDER BY salary DESC LIMIT 5",
    "results": [...]
  }
}
```

---

## Development

### Available Scripts

```bash
npm run dev      # Start development server
npm run build    # Build for production
npm run preview  # Preview production build
npm run lint     # Run ESLint
```

### Adding New Features

1. Create components in `src/components/`
2. Add API endpoints in `api/`
3. Update styles in `src/styles/`

---

## License

MIT License - Copyright (c) 2026
