# 🔄 ChatGPT History MCP Server

**Make your ChatGPT conversations searchable from Claude.**

Switching from ChatGPT to Claude? Don't leave your conversation history behind. This MCP server lets Claude search through all your past ChatGPT conversations — so you can ask things like *"What did I discuss about marketing strategy in ChatGPT?"* and get real answers.

![MCP](https://img.shields.io/badge/MCP-Compatible-blue)
![Python](https://img.shields.io/badge/Python-3.10+-green)
![License](https://img.shields.io/badge/License-MIT-yellow)

---

## ⚡ Quick Start (5 minutes)

### Step 1: Export your ChatGPT data

1. Go to [chatgpt.com](https://chatgpt.com)
2. Click your profile → **Settings** → **Data Controls** → **Export Data**
3. Click **Confirm Export**
4. Wait for the email (usually 5–30 minutes)
5. Download the ZIP file and save it somewhere, e.g. `~/Downloads/chatgpt-export.zip`

### Step 2: Add to Claude Desktop

Open your Claude Desktop config file:

| OS | Config file location |
|----|---------------------|
| **Mac** | `~/Library/Application Support/Claude/claude_desktop_config.json` |
| **Windows** | `%APPDATA%\Claude\claude_desktop_config.json` |
| **Linux** | `~/.config/Claude/claude_desktop_config.json` |

Add the following to your config (create the file if it doesn't exist):

```json
{
  "mcpServers": {
    "chatgpt-history": {
      "command": "uvx",
      "args": [
        "chatgpt-history-mcp",
        "--export-path",
        "/FULL/PATH/TO/YOUR/chatgpt-export.zip"
      ]
    }
  }
}
```

> ⚠️ Replace `/FULL/PATH/TO/YOUR/chatgpt-export.zip` with the actual path to your downloaded file.

### Step 3: Restart Claude Desktop

Close and reopen Claude Desktop. You should see a 🔧 icon in the bottom-left of the chat indicating MCP tools are available.

### Step 4: Start asking!

Try these in Claude:

- *"Search my ChatGPT history for discussions about Python"*
- *"What did I talk about with ChatGPT regarding marketing?"*
- *"Show me my ChatGPT usage statistics"*
- *"Find ChatGPT conversations from January 2024"*

---

## 🛠 What You Can Do

| Command | What it does |
|---------|-------------|
| **Search** | Find conversations by topic, keyword, or phrase |
| **Read** | Retrieve the full content of any conversation |
| **Browse** | List conversations by date |
| **Stats** | See your ChatGPT usage overview: total conversations, messages, models used, monthly activity |

Claude has access to four tools:

- `chatgpt_search` — Keyword search with TF-IDF ranking and date filters
- `chatgpt_get_conversation` — Retrieve full conversation content by ID
- `chatgpt_list_conversations` — Browse conversations with pagination
- `chatgpt_stats` — Usage statistics and activity overview

---

## 🔒 Privacy & Security

Your data stays **100% local**:

- ✅ The export file is read locally — nothing is uploaded anywhere
- ✅ No API keys needed — the search runs entirely on your machine
- ✅ No external calls — the server never contacts any remote service
- ✅ Open source — you can read every line of code

The server only reads your export file when it starts up and builds an in-memory search index. When Claude asks to search your history, it calls the local MCP server which runs on your machine.

---

## 📋 Requirements

- **Python 3.10+** (check with `python3 --version`)
- **Claude Desktop** (with MCP support)
- **A ChatGPT data export** (ZIP file from OpenAI)

If you don't have Python installed, the easiest way:
- **Mac**: `brew install python`
- **Windows**: Download from [python.org](https://www.python.org/downloads/)
- **Linux**: `sudo apt install python3 python3-pip`

If you don't have `uvx`:
```bash
pip install uv
```

---

## 🔧 Alternative: Install from Source

If you prefer not to use `uvx`:

```bash
# Clone the repo
git clone https://github.com/YOUR_USERNAME/chatgpt-history-mcp.git
cd chatgpt-history-mcp

# Install
pip install .

# Run directly
chatgpt-history-mcp --export-path ~/Downloads/chatgpt-export.zip
```

Or use the Claude Desktop config with `python` directly:

```json
{
  "mcpServers": {
    "chatgpt-history": {
      "command": "python",
      "args": [
        "/FULL/PATH/TO/chatgpt_history_mcp.py",
        "--export-path",
        "/FULL/PATH/TO/YOUR/chatgpt-export.zip"
      ]
    }
  }
}
```

---

## 🤔 How It Works

```
┌──────────────┐     ┌─────────────────┐     ┌──────────────────┐
│  ChatGPT     │     │  MCP Server     │     │  Claude Desktop  │
│  Export ZIP   │────▶│  (local Python) │◀───▶│                  │
│              │     │                 │     │  "What did I     │
│ conversations│     │ • Parse JSON    │     │   discuss about  │
│    .json     │     │ • Build index   │     │   marketing?"    │
└──────────────┘     │ • Search (TF-IDF│     └──────────────────┘
                     │ • Serve results │
                     └─────────────────┘
                        Runs on YOUR machine
                        No data leaves your computer
```

1. **On startup**: The server reads your ChatGPT export, parses the conversation tree structure, and builds a TF-IDF search index in memory.
2. **When Claude asks**: Claude calls the MCP tools (search, get, list, stats), the server responds with relevant conversations.
3. **Everything is local**: The server runs as a subprocess of Claude Desktop. No network calls, no cloud, no API keys.

---

## 🐛 Troubleshooting

**"No conversations loaded"**
- Check that the file path in your config is correct and absolute
- Make sure the ZIP file contains `conversations.json`

**Claude doesn't show the 🔧 icon**
- Make sure you restarted Claude Desktop after editing the config
- Check the config JSON is valid (no trailing commas!)
- Check Claude Desktop logs for errors

**"uvx not found"**
- Install uv first: `pip install uv`
- Or use the direct Python method in the Alternative section

**Slow startup with huge exports**
- If you have 10,000+ conversations, the initial indexing may take a few seconds
- After that, searches are instant

---

## 💡 Tips

- **Be specific in your searches**: "Python async debugging" works better than just "Python"
- **Use date filters**: Narrow down results with `date_from` and `date_to`
- **Ask Claude to summarize**: After finding a conversation, ask Claude to summarize the key takeaways
- **Compare approaches**: Ask Claude "How did I solve X in ChatGPT? How would you approach it differently?"

---

## 🗺 Roadmap

- [ ] Publish to PyPI for one-command install via `uvx`
- [ ] Support for ChatGPT shared links import
- [ ] Optional semantic search (with local embeddings)
- [ ] Web UI for browsing history without Claude
- [ ] Support for other AI chat exports (Gemini, Copilot, etc.)

---

## 📄 License

MIT — do whatever you want with it.

---

## 🤝 Contributing

PRs welcome! Some ideas:
- Better search ranking algorithms
- Support for more export formats
- Performance optimizations for very large exports
- Tests!

---

**Made with ☕ by Lionel Morlot** — *Because your AI conversations shouldn't be locked in silos.*
