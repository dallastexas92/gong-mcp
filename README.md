# Gong MCP Server

MCP server for integrating Gong with Claude Desktop.

## Prerequisites

- Python 3.11+
- UV package manager: https://docs.astral.sh/uv/
- Gong API access

## Setup

### 1. Clone and Install

```bash
git clone https://github.com/YOUR_USERNAME/gong-mcp-server.git
cd gong-mcp-server
uv sync
```

### 2. Get Gong API Credentials

1. Go to https://app.gong.io/settings/api
2. Click "Create API Key"
3. Copy the Access Key and Secret

### 3. Configure Environment

Copy `.env.example` to `.env` and add your credentials:

```bash
cp .env.example .env
```

### 4. Configure Claude Desktop

First, find your Claude Desktop configuration file:

- **Mac**: `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`
- **Linux**: `~/.config/Claude/claude_desktop_config.json`

Open this file and add the following configuration:

```json
{
  "mcpServers": {
    "gong": {
      "command": "/bin/bash",
      "args": ["-c", "cd /path/to/gong-mcp-server && uv run python gong_mcp_server.py"],
      "cwd": "/path/to/gong-mcp-server"
    }
  }
}
```

**Important**: Replace `/path/to/gong-mcp-server` with the actual full path to where you cloned this repository.

### 5. Restart Claude Desktop

1. Completely quit Claude Desktop (Cmd+Q on Mac, not just close the window)
2. Start Claude Desktop again
3. Look for the 🔌 icon in the text input area
4. Click it to verify "gong" is listed with 4 available tools

## Usage

Once configured, you can ask Claude:

- "Search for my Gong calls from the last 3 days"
- "Get the transcript for call ID [xyz]"
- "Show me stats for my recent calls"
- "List Gong scorecards from the last week"

## Available Tools

| Tool | Description |
|------|-------------|
| `search_calls` | Search Gong calls with date filters |
| `get_call_transcript` | Get transcript for a specific call |
| `get_call_stats` | Get statistics for a call (talk ratio, questions asked, etc.) |
| `list_scorecards` | List Gong scorecards |

## Troubleshooting

### MCP server not showing up in Claude Desktop?

1. **Check the logs**:
   ```bash
   # Mac
   tail -f ~/Library/Logs/Claude/mcp-server-gong.log
   
   # Windows
   Get-Content "$env:APPDATA\Claude\logs\mcp-server-gong.log" -Wait
   ```

2. **Verify UV is working**:
   ```bash
   uv --version
   ```

3. **Test the server directly**:
   ```bash
   cd /path/to/gong-mcp-server
   uv run python gong_mcp_server.py
   ```
   If this works without errors, the issue is likely with the Claude Desktop configuration.

4. **Common issues**:
   - Wrong path in configuration file
   - Missing or invalid Gong API credentials in `.env`
   - Claude Desktop needs complete restart (not just window close)
   - JSON syntax error in config file (no trailing commas!)

### API errors?

- **405 Method Not Allowed**: The server is using an outdated API endpoint. Make sure you have the latest version.
- **401 Unauthorized**: Check your Gong API credentials in the `.env` file.
- **Cannot resolve host**: Check your network connection or VPN settings.

## Contributing

Pull requests are welcome! Please make sure to update tests as appropriate.

## License

MIT