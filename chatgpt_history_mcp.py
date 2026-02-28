"""
ChatGPT History MCP Server
===========================
Makes your ChatGPT conversation history searchable from Claude.

Export your ChatGPT data, point this server at the ZIP file,
and Claude can search through all your past ChatGPT conversations.

Usage:
    uvx chatgpt-history-mcp --export-path /path/to/chatgpt-export.zip
    # or
    python chatgpt_history_mcp.py --export-path /path/to/chatgpt-export.zip
"""

import json
import math
import os
import re
import sys
import zipfile
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from mcp.server.fastmcp import FastMCP
from mcp.types import Icon
from pydantic import BaseModel, Field, ConfigDict


# ===========================================================================
# Data models
# ===========================================================================

@dataclass
class Message:
    """A single message in a conversation."""
    role: str          # "user", "assistant", "system", "tool"
    text: str
    timestamp: Optional[float] = None

    @property
    def date_str(self) -> str:
        if self.timestamp:
            return datetime.fromtimestamp(self.timestamp, tz=timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        return ""


@dataclass
class Conversation:
    """A parsed ChatGPT conversation."""
    id: str
    title: str
    create_time: Optional[float] = None
    update_time: Optional[float] = None
    messages: list[Message] = field(default_factory=list)
    model_slug: str = ""

    @property
    def date_str(self) -> str:
        ts = self.create_time or self.update_time
        if ts:
            return datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d")
        return "unknown date"

    @property
    def message_count(self) -> int:
        return len(self.messages)

    @property
    def full_text(self) -> str:
        """All message text concatenated (for search indexing)."""
        parts = [self.title]
        for m in self.messages:
            parts.append(m.text)
        return " ".join(parts)

    def preview(self, max_chars: int = 300) -> str:
        """Short preview of the conversation content."""
        user_msgs = [m.text for m in self.messages if m.role == "user"]
        preview_text = " | ".join(user_msgs)
        if len(preview_text) > max_chars:
            preview_text = preview_text[:max_chars] + "…"
        return preview_text


# ===========================================================================
# ChatGPT export parser
# ===========================================================================

def parse_chatgpt_export(export_path: str) -> list[Conversation]:
    """
    Parse a ChatGPT data export ZIP or conversations.json file.

    ChatGPT exports contain a conversations.json with a tree structure
    (mapping of node IDs). We flatten each tree into a linear conversation.
    """
    path = Path(export_path)
    raw_json = None

    if path.suffix == ".zip":
        with zipfile.ZipFile(path, "r") as zf:
            for name in zf.namelist():
                if name.endswith("conversations.json"):
                    raw_json = json.loads(zf.read(name))
                    break
        if raw_json is None:
            raise FileNotFoundError("No conversations.json found in the ZIP file.")
    elif path.suffix == ".json":
        raw_json = json.loads(path.read_text(encoding="utf-8"))
    else:
        raise ValueError(f"Unsupported file format: {path.suffix}. Use .zip or .json")

    conversations: list[Conversation] = []

    for entry in raw_json:
        conv = Conversation(
            id=entry.get("id", entry.get("conversation_id", "")),
            title=entry.get("title", "Untitled"),
            create_time=entry.get("create_time"),
            update_time=entry.get("update_time"),
            model_slug=entry.get("default_model_slug", ""),
        )

        # Flatten the message tree
        mapping = entry.get("mapping", {})
        if mapping:
            messages = _flatten_message_tree(mapping)
            conv.messages = messages
        else:
            # Some exports have a flat "messages" array
            for msg in entry.get("messages", []):
                if msg and msg.get("content"):
                    text = _extract_text(msg["content"])
                    if text.strip():
                        conv.messages.append(Message(
                            role=msg.get("role", msg.get("author", {}).get("role", "unknown")),
                            text=text,
                            timestamp=msg.get("create_time"),
                        ))

        if conv.messages:
            conversations.append(conv)

    # Sort newest first
    conversations.sort(key=lambda c: c.create_time or 0, reverse=True)
    return conversations


def _flatten_message_tree(mapping: dict) -> list[Message]:
    """
    Convert ChatGPT's tree-structured mapping into a flat list of messages.
    Follows the main branch (first child at each node).
    """
    # Find the root node (no parent or parent not in mapping)
    root_id = None
    for node_id, node in mapping.items():
        parent = node.get("parent")
        if parent is None or parent not in mapping:
            root_id = node_id
            break

    if root_id is None:
        return []

    # Walk the tree depth-first following first child
    messages: list[Message] = []
    current_id = root_id

    while current_id:
        node = mapping.get(current_id, {})
        msg_data = node.get("message")

        if msg_data and msg_data.get("content"):
            author = msg_data.get("author", {}).get("role", "unknown")
            text = _extract_text(msg_data["content"])

            if text.strip() and author in ("user", "assistant", "system", "tool"):
                messages.append(Message(
                    role=author,
                    text=text,
                    timestamp=msg_data.get("create_time"),
                ))

        # Follow first child
        children = node.get("children", [])
        current_id = children[0] if children else None

    return messages


def _extract_text(content: dict) -> str:
    """Extract readable text from a ChatGPT message content object."""
    if isinstance(content, str):
        return content

    parts = content.get("parts", [])
    texts = []
    for part in parts:
        if isinstance(part, str):
            texts.append(part)
        elif isinstance(part, dict):
            # Could be an image, code, etc.
            if "text" in part:
                texts.append(part["text"])
    return "\n".join(texts)


# ===========================================================================
# Search engine (TF-IDF + keyword)
# ===========================================================================

class SearchEngine:
    """
    Lightweight search engine using TF-IDF scoring.
    No external dependencies needed — works on pure Python.
    """

    def __init__(self, conversations: list[Conversation]):
        self.conversations = conversations
        self._index: dict[str, list[tuple[int, float]]] = {}  # term -> [(conv_idx, tf)]
        self._idf: dict[str, float] = {}
        self._build_index()

    def _tokenize(self, text: str) -> list[str]:
        """Simple tokenizer: lowercase, split on non-alphanumeric."""
        return re.findall(r"[a-z0-9]+", text.lower())

    def _build_index(self):
        """Build inverted index with TF-IDF scores."""
        doc_freq: Counter = Counter()
        n_docs = len(self.conversations)

        # Compute term frequencies per document
        tf_per_doc: list[Counter] = []
        for conv in self.conversations:
            tokens = self._tokenize(conv.full_text)
            tf = Counter(tokens)
            tf_per_doc.append(tf)
            for term in set(tokens):
                doc_freq[term] += 1

        # Compute IDF
        for term, df in doc_freq.items():
            self._idf[term] = math.log((n_docs + 1) / (df + 1)) + 1

        # Build inverted index with TF-IDF
        for idx, tf in enumerate(tf_per_doc):
            total_tokens = sum(tf.values()) or 1
            for term, count in tf.items():
                normalized_tf = count / total_tokens
                if term not in self._index:
                    self._index[term] = []
                self._index[term].append((idx, normalized_tf))

    def search(
        self,
        query: str,
        limit: int = 10,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
    ) -> list[tuple[Conversation, float]]:
        """
        Search conversations by query string.
        Returns list of (conversation, score) tuples, sorted by relevance.
        """
        query_tokens = self._tokenize(query)
        if not query_tokens:
            return []

        # Score each document
        scores: dict[int, float] = {}
        for token in query_tokens:
            idf = self._idf.get(token, 0)
            for idx, tf in self._index.get(token, []):
                scores[idx] = scores.get(idx, 0) + tf * idf

        # Boost exact title matches
        query_lower = query.lower()
        for idx, conv in enumerate(self.conversations):
            if query_lower in conv.title.lower():
                scores[idx] = scores.get(idx, 0) * 2.0

        # Apply date filters
        results = []
        ts_from = _parse_date(date_from) if date_from else None
        ts_to = _parse_date(date_to) if date_to else None

        for idx, score in sorted(scores.items(), key=lambda x: x[1], reverse=True):
            conv = self.conversations[idx]
            ts = conv.create_time or 0

            if ts_from and ts < ts_from:
                continue
            if ts_to and ts > ts_to:
                continue

            results.append((conv, score))
            if len(results) >= limit:
                break

        return results


def _parse_date(date_str: str) -> Optional[float]:
    """Parse a date string like '2024-01-15' into a Unix timestamp."""
    try:
        dt = datetime.strptime(date_str.strip(), "%Y-%m-%d").replace(tzinfo=timezone.utc)
        return dt.timestamp()
    except ValueError:
        return None


# ===========================================================================
# MCP Server
# ===========================================================================

# Global state — initialized on startup
_conversations: list[Conversation] = []
_engine: Optional[SearchEngine] = None


def _init_from_path(export_path: str):
    """Parse the export and build the search index."""
    global _conversations, _engine
    print(f"📂 Loading ChatGPT export from: {export_path}", file=sys.stderr)
    _conversations = parse_chatgpt_export(export_path)
    _engine = SearchEngine(_conversations)
    print(f"✅ Indexed {len(_conversations)} conversations", file=sys.stderr)


# Initialize the FastMCP server
mcp = FastMCP(
    "ChatGPT History",
    instructions=(
        "This server provides access to the user's ChatGPT conversation history. "
        "Use it to search past conversations, retrieve full conversation content, "
        "and get statistics about the user's ChatGPT usage."
    ),
    icons=[Icon(src="https://chatgpt.com/apple-touch-icon.png", mimeType="image/png")],
)


# --- Tool input models ---

class SearchInput(BaseModel):
    """Input for searching ChatGPT conversations."""
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    query: str = Field(
        ...,
        description="Search query — use keywords, topics, or phrases to find relevant conversations. "
                    "Example: 'python debugging', 'marketing strategy', 'recipe for pasta'",
        min_length=1,
        max_length=500,
    )
    limit: int = Field(
        default=10,
        description="Maximum number of results to return",
        ge=1,
        le=50,
    )
    date_from: Optional[str] = Field(
        default=None,
        description="Filter: only conversations from this date onwards (format: YYYY-MM-DD)",
    )
    date_to: Optional[str] = Field(
        default=None,
        description="Filter: only conversations up to this date (format: YYYY-MM-DD)",
    )


class GetConversationInput(BaseModel):
    """Input for retrieving a full conversation."""
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    conversation_id: str = Field(
        ...,
        description="The ID of the conversation to retrieve (from search results)",
        min_length=1,
    )
    max_messages: Optional[int] = Field(
        default=None,
        description="Limit the number of messages returned. None = all messages.",
        ge=1,
        le=500,
    )


class ListInput(BaseModel):
    """Input for listing recent conversations."""
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    limit: int = Field(
        default=20,
        description="Number of conversations to list",
        ge=1,
        le=100,
    )
    offset: int = Field(
        default=0,
        description="Offset for pagination",
        ge=0,
    )


# --- Tools ---

@mcp.tool(
    name="chatgpt_search",
    annotations={
        "title": "Search ChatGPT History",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    },
)
async def chatgpt_search(params: SearchInput) -> str:
    """Search through your ChatGPT conversation history by topic, keyword, or phrase.

    Returns a ranked list of matching conversations with titles, dates, and previews.
    Use conversation IDs from the results to retrieve full conversation content.

    Args:
        params (SearchInput): Search parameters including query, limit, and date filters.

    Returns:
        str: Markdown-formatted search results with conversation IDs, titles, dates, and previews.
    """
    if _engine is None:
        return "Error: ChatGPT history not loaded. Please check the server configuration."

    results = _engine.search(
        query=params.query,
        limit=params.limit,
        date_from=params.date_from,
        date_to=params.date_to,
    )

    if not results:
        return f"No conversations found matching '{params.query}'."

    lines = [f"## Found {len(results)} conversation(s) matching '{params.query}'\n"]

    for i, (conv, score) in enumerate(results, 1):
        lines.append(f"### {i}. {conv.title}")
        lines.append(f"- **ID**: `{conv.id}`")
        lines.append(f"- **Date**: {conv.date_str}")
        lines.append(f"- **Messages**: {conv.message_count}")
        if conv.model_slug:
            lines.append(f"- **Model**: {conv.model_slug}")
        lines.append(f"- **Preview**: {conv.preview(200)}")
        lines.append("")

    return "\n".join(lines)


@mcp.tool(
    name="chatgpt_get_conversation",
    annotations={
        "title": "Get Full ChatGPT Conversation",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    },
)
async def chatgpt_get_conversation(params: GetConversationInput) -> str:
    """Retrieve the full content of a specific ChatGPT conversation.

    Use the conversation ID from search results to get the complete message history.

    Args:
        params (GetConversationInput): Conversation ID and optional message limit.

    Returns:
        str: Markdown-formatted full conversation with all messages.
    """
    conv = _find_conversation(params.conversation_id)
    if conv is None:
        return f"Error: Conversation with ID '{params.conversation_id}' not found."

    messages = conv.messages
    if params.max_messages:
        messages = messages[:params.max_messages]

    lines = [
        f"## {conv.title}",
        f"**Date**: {conv.date_str} | **Messages**: {conv.message_count}",
        "",
        "---",
        "",
    ]

    for msg in messages:
        role_label = {"user": "🧑 You", "assistant": "🤖 ChatGPT", "system": "⚙️ System", "tool": "🔧 Tool"}.get(msg.role, msg.role)
        date_label = f" ({msg.date_str})" if msg.date_str else ""
        lines.append(f"**{role_label}**{date_label}:")
        lines.append(msg.text)
        lines.append("")

    truncated = len(conv.messages) - len(messages)
    if truncated > 0:
        lines.append(f"*… {truncated} more messages not shown. Increase max_messages to see more.*")

    return "\n".join(lines)


@mcp.tool(
    name="chatgpt_list_conversations",
    annotations={
        "title": "List ChatGPT Conversations",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    },
)
async def chatgpt_list_conversations(params: ListInput) -> str:
    """List your ChatGPT conversations, sorted by date (newest first).

    Useful for browsing your history or finding conversations by date.

    Args:
        params (ListInput): Pagination parameters (limit and offset).

    Returns:
        str: Markdown-formatted list of conversations with pagination info.
    """
    if not _conversations:
        return "No conversations loaded."

    total = len(_conversations)
    start = min(params.offset, total)
    end = min(start + params.limit, total)
    page = _conversations[start:end]

    lines = [
        f"## ChatGPT Conversations ({start + 1}–{end} of {total})\n",
    ]

    for conv in page:
        lines.append(f"- **{conv.title}** ({conv.date_str}) — {conv.message_count} messages — ID: `{conv.id}`")

    lines.append("")
    has_more = end < total
    if has_more:
        lines.append(f"*Showing {len(page)} of {total}. Use offset={end} to see more.*")

    return "\n".join(lines)


@mcp.tool(
    name="chatgpt_stats",
    annotations={
        "title": "ChatGPT Usage Statistics",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    },
)
async def chatgpt_stats() -> str:
    """Get an overview of your ChatGPT usage: total conversations, messages, date range, and common topics.

    Returns:
        str: Markdown-formatted usage statistics.
    """
    if not _conversations:
        return "No conversations loaded."

    total_convs = len(_conversations)
    total_msgs = sum(c.message_count for c in _conversations)

    dates = [c.create_time for c in _conversations if c.create_time]
    earliest = datetime.fromtimestamp(min(dates), tz=timezone.utc).strftime("%Y-%m-%d") if dates else "unknown"
    latest = datetime.fromtimestamp(max(dates), tz=timezone.utc).strftime("%Y-%m-%d") if dates else "unknown"

    # Model distribution
    model_counts: Counter = Counter()
    for c in _conversations:
        model_counts[c.model_slug or "unknown"] += 1

    # Monthly distribution
    monthly: Counter = Counter()
    for c in _conversations:
        if c.create_time:
            month = datetime.fromtimestamp(c.create_time, tz=timezone.utc).strftime("%Y-%m")
            monthly[month] += 1

    lines = [
        "## ChatGPT Usage Statistics\n",
        f"- **Total conversations**: {total_convs:,}",
        f"- **Total messages**: {total_msgs:,}",
        f"- **Date range**: {earliest} → {latest}",
        "",
        "### Model Usage",
    ]
    for model, count in model_counts.most_common(10):
        lines.append(f"- {model}: {count:,} conversations")

    lines.append("")
    lines.append("### Monthly Activity (last 12 months)")
    for month, count in sorted(monthly.items(), reverse=True)[:12]:
        bar = "█" * min(count, 50)
        lines.append(f"- {month}: {bar} ({count})")

    return "\n".join(lines)


# --- Helper ---

def _find_conversation(conv_id: str) -> Optional[Conversation]:
    """Find a conversation by ID."""
    for conv in _conversations:
        if conv.id == conv_id:
            return conv
    return None


# ===========================================================================
# Entrypoint
# ===========================================================================

def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="ChatGPT History MCP Server — makes your ChatGPT conversations searchable from Claude",
    )
    parser.add_argument(
        "--export-path",
        type=str,
        default=os.environ.get("CHATGPT_EXPORT_PATH", ""),
        help="Path to your ChatGPT export ZIP or conversations.json file. "
             "Can also be set via CHATGPT_EXPORT_PATH environment variable.",
    )
    args = parser.parse_args()

    export_path = args.export_path
    if not export_path:
        print("Error: No export path provided.", file=sys.stderr)
        print("Use --export-path or set CHATGPT_EXPORT_PATH environment variable.", file=sys.stderr)
        print("\nTo export your data from ChatGPT:", file=sys.stderr)
        print("  1. Go to https://chatgpt.com", file=sys.stderr)
        print("  2. Settings → Data Controls → Export Data", file=sys.stderr)
        print("  3. Wait for the email, download the ZIP", file=sys.stderr)
        print(f"  4. Run: python {sys.argv[0]} --export-path /path/to/export.zip", file=sys.stderr)
        sys.exit(1)

    if not Path(export_path).exists():
        print(f"Error: File not found: {export_path}", file=sys.stderr)
        sys.exit(1)

    _init_from_path(export_path)
    mcp.run()


if __name__ == "__main__":
    main()
