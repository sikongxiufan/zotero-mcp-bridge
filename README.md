# Zotero MCP Bridge

Bridge Zotero MCP server over LAN for remote AI assistants.

## Overview

This project enables AI assistants (e.g., Claude Code) running on **Machine A** to access a Zotero library running on **Machine B** over the local network.

```
┌─────────────┐    HTTP/JSON-RPC     ┌──────────────────────────┐
│  Mac/Linux  │ ←──────────────────→ │  Windows (Machine B)     │
│  Claude     │   ZOTERO_MCP_URL     │  Zotero + MCP Plugin     │
│  Code       │   (LAN address)      │  Listening on port 23120│
└─────────────┘                      └──────────────────────────┘
```

## Prerequisites

### Machine B (Zotero Server)

- [Zotero](https://www.zotero.org/) installed
- [Zotero MCP plugin](https://github.com/nicholashh/zotero-mcp-server) installed and running
- Zotero MCP server must be accessible over LAN (default: `http://localhost:23120/mcp`)
- Both machines must be on the **same local network**

### Machine A (Claude Code Client)

- Python 3.10+

## Installation

### 1. Clone or copy this project

```bash
git clone https://github.com/YOUR_USERNAME/zotero-mcp-bridge.git
cd zotero-mcp-bridge
```

### 2. Create virtual environment

```bash
python -m venv venv
source venv/bin/activate      # macOS/Linux
# venv\Scripts\activate       # Windows
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

## Configuration

### Step 1: Find Machine B's LAN IP

On **Machine B** (Windows), open a terminal and run:

```bash
ipconfig
```

Look for the IPv4 address under your active network adapter (e.g., `192.168.1.100`).

> **Note:** If Zotero MCP is running on the **same machine** as Claude Code, use `127.0.0.1` instead.

### Step 2: Configure the Zotero MCP URL

Copy the example config:

```bash
# macOS
cp claude_desktop_config.example.json ~/.claude.json

# Linux
cp claude_desktop_config.example.json ~/.config/claude-desktop/config.json
```

Then edit `~/.claude.json` and replace the IP address:

```json
{
  "mcpServers": {
    "zotero": {
      "command": "python",
      "args": ["/absolute/path/to/zotero_claude_bridge.py"],
      "env": {
        "ZOTERO_MCP_URL": "http://192.168.1.100:23120/mcp"
      }
    }
  }
}
```

### Step 3: Restart Claude Code

Restart Claude Code (or reconnect to the project) to load the new MCP configuration.

## How It Works

- The bridge acts as a **FastMCP stdio server** on Machine A
- It proxies all tool calls to the remote Zotero MCP server on Machine B via HTTP/JSON-RPC
- Claude Code communicates with the bridge over stdio (no network exposure)
- The `ZOTERO_MCP_URL` environment variable tells the bridge where to find the remote Zotero MCP server

## Troubleshooting

### "Connection refused" error

1. Make sure Machine B's firewall allows incoming connections on port **23120**
2. Verify the IP address in `ZOTERO_MCP_URL` is correct
3. On Machine B, test in browser: `http://<machine-b-ip>:23120/mcp` — you should see JSON response

### "No tools found" error

1. Verify the Zotero MCP plugin is installed and running on Machine B
2. Check that Zotero is running on Machine B
3. Try accessing `http://<machine-b-ip>:23120/mcp` directly in a browser on Machine A

## Project Structure

```
zotero-mcp-bridge/
├── zotero_claude_bridge.py     # Main bridge script
├── requirements.txt            # Python dependencies
├── claude_desktop_config.example.json  # Config template
├── LICENSE                     # MIT License
└── README.md
```

## Dependencies

- [mcp](https://github.com/modelcontextprotocol/python-sdk) >= 1.4.1
- [requests](https://github.com/psf/requests) >= 2.25.0

## License

MIT
