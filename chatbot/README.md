# Data Agent Chatbot Interface

**A web-based chat interface for querying databases through the MCP Server.**

A React-based chatbot UI that connects to the MCP Server, enabling natural language queries against Oracle, SQL Server, and PostgreSQL databases.

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
                                  │ HTTPS
                                  ▼
┌─────────────────────────────────────────────────────────────────┐
│              Azure Static Web Apps (API Functions)               │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │                   API Proxy Functions                    │    │
│  │  /api/query  │  /api/agents  │  /api/health             │    │
│  └─────────────────────────────────────────────────────────┘    │
└─────────────────────────────────┬───────────────────────────────┘
                                  │ HTTPS
                                  ▼
┌─────────────────────────────────────────────────────────────────┐
│                          MCP Server                              │
│          (Azure Container Apps / Azure Functions)                │
└─────────────────────────────────────────────────────────────────┘
```

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

Create a `.env` file:

```env
VITE_MCP_SERVER_URL=http://localhost:8080
VITE_APP_TITLE=Data Agent Chat
```

---

## Deployment

### Deploy to Azure Static Web Apps

```bash
# Login to Azure
az login

# Deploy infrastructure
az deployment group create \
  -g your-resource-group \
  -f infra/main.bicep \
  --parameters @infra/main.parameters.json

# Or use the deployment script
./deploy.sh --resource-group your-rg --location eastus
```

### Environment Variables (Production)

Set these in Azure Static Web Apps configuration:

| Variable | Description |
|----------|-------------|
| `MCP_SERVER_URL` | URL of the MCP Server |
| `MCP_AUTH_TOKEN` | Optional authentication token |

---

## API Endpoints

The Azure Functions API provides these endpoints:

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/query` | POST | Send a query to an agent |
| `/api/agents` | GET | List available agents |
| `/api/health` | GET | Health check |

### Query Request

```json
POST /api/query
{
  "agentId": "hr_employees",
  "question": "Show me the top 5 employees by salary"
}
```

### Query Response

```json
{
  "success": true,
  "data": {
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
