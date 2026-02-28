# ChatGPT history for Claude

**Search your past ChatGPT conversations directly from Claude Desktop.**

Switched from ChatGPT to Claude? Now you can ask Claude things like *"What did I discuss about marketing strategy in ChatGPT?"* and get real answers — without going back to ChatGPT.

![MCP](https://img.shields.io/badge/MCP-Compatible-blue)
![Python](https://img.shields.io/badge/Python-3.10+-green)
![License](https://img.shields.io/badge/License-MIT-yellow)

---

## Install (macOS)

**Step 1 — Export your ChatGPT data**

In ChatGPT: Settings → Data Controls → Export Data. You'll get an email with a `.zip` file.

**Step 2 — Run the installer**

Open Terminal (⌘ Space → type "Terminal") and paste:

```bash
curl -fsSL https://raw.githubusercontent.com/Lioneltristan/chatgpfree/main/install.command | bash
```

Select your export file when prompted. Claude Desktop restarts automatically.

**Step 3 — Search**

Ask Claude anything:
- *"Search my ChatGPT history for Python debugging"*
- *"What did I discuss about marketing in ChatGPT?"*
- *"Show me my ChatGPT conversations from January 2024"*

---

## What it does

| Tool | Description |
|------|-------------|
| `chatgpt_search` | Full-text search across all conversations with optional date filters |
| `chatgpt_get_conversation` | Retrieve the full content of any conversation by ID |
| `chatgpt_list_conversations` | Browse conversations by date with pagination |
| `chatgpt_stats` | Usage overview: total conversations, messages, monthly activity |

---

## Privacy

Everything runs locally on your machine. Your conversations are never uploaded anywhere.

- No API keys required
- No external network calls
- Open source — read every line of code

---

## How it works

Your ChatGPT export is parsed and indexed in memory using TF-IDF when Claude Desktop starts. When you ask Claude to search your history, it calls the local MCP server which responds instantly from the in-memory index.

---

## Requirements

- macOS
- Python 3.10+
- [Claude Desktop](https://claude.ai/download)

---

## Manual setup (advanced)

If you prefer to configure manually, add this to `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "ChatGPT history": {
      "command": "uvx",
      "args": [
        "--from", "git+https://github.com/Lioneltristan/chatgpfree",
        "chatgpt-history-mcp",
        "--export-path", "/path/to/conversations.json"
      ]
    }
  }
}
```

---

## Troubleshooting

**No conversations showing up**
Make sure your export file path is correct. The installer copies it to `~/Library/Application Support/Claude/chatgpt-history/conversations.json`.

**Claude Desktop not picking up the server**
Restart Claude Desktop after running the installer. Check that the config file is valid JSON.

---

## Roadmap

- [ ] Publish to PyPI for `uvx chatgpt-history-mcp` (no `--from` needed)
- [ ] Semantic search with local embeddings
- [ ] Support for other AI chat exports (Gemini, Copilot)

---

MIT — [lionelmorlot.com/chatgpfree](https://lionelmorlot.com/chatgpfree)
