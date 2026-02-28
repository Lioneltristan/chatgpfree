"""
ChatGPT History for Claude — Installer
A one-click GUI to set up the MCP server in Claude Desktop.
"""
import json
import shutil
import subprocess
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox


REPO = "git+https://github.com/Lioneltristan/chatgpfree"
PACKAGE = "chatgpt-history-mcp"
SERVER_NAME = "ChatGPT history"
CLAUDE_DIR = Path.home() / "Library" / "Application Support" / "Claude"
CONFIG_PATH = CLAUDE_DIR / "claude_desktop_config.json"
HISTORY_DIR = CLAUDE_DIR / "chatgpt-history"


# ---------------------------------------------------------------------------
# Backend logic
# ---------------------------------------------------------------------------

def find_uvx() -> str | None:
    candidates = [
        Path.home() / ".local" / "bin" / "uvx",
        Path.home() / ".cargo" / "bin" / "uvx",
        Path("/usr/local/bin/uvx"),
        Path("/opt/homebrew/bin/uvx"),
    ]
    for p in candidates:
        if p.exists():
            return str(p)
    try:
        r = subprocess.run(["which", "uvx"], capture_output=True, text=True)
        if r.returncode == 0 and r.stdout.strip():
            return r.stdout.strip()
    except Exception:
        pass
    return None


def install_uv(log):
    log("Downloading uv…")
    r = subprocess.run(
        ["curl", "-LsSf", "https://astral.sh/uv/install.sh"],
        capture_output=True, text=True,
    )
    if r.returncode != 0:
        raise RuntimeError(f"Could not download uv installer:\n{r.stderr}")
    r2 = subprocess.run(["sh"], input=r.stdout, capture_output=True, text=True)
    if r2.returncode != 0:
        raise RuntimeError(f"uv installation failed:\n{r2.stderr}")
    log("uv installed.")


def copy_export(export_path: str, log) -> str:
    HISTORY_DIR.mkdir(parents=True, exist_ok=True)
    dest = HISTORY_DIR / "conversations.json"
    shutil.copy2(export_path, dest)
    log("Export file saved.")
    return str(dest)


def write_config(stored_path: str, uvx_path: str, log):
    config: dict = {}
    if CONFIG_PATH.exists():
        try:
            config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            pass
    config.setdefault("mcpServers", {})[SERVER_NAME] = {
        "command": uvx_path,
        "args": ["--from", REPO, PACKAGE, "--export-path", stored_path],
    }
    CONFIG_PATH.write_text(json.dumps(config, indent=2), encoding="utf-8")
    log("Claude Desktop config updated.")


# ---------------------------------------------------------------------------
# Design tokens
# ---------------------------------------------------------------------------

W           = 460
BG          = "#ffffff"
BG2         = "#f5f5f7"
HEADER_BG   = "#1d1d1f"
TEXT1       = "#1d1d1f"
TEXT2       = "#6e6e73"
INPUT_BG    = "#f5f5f7"
INPUT_BD    = "#d2d2d7"
BTN_BG      = "#0071e3"
BTN_FG      = "#ffffff"
BTN_ACT     = "#0077ed"
BTN2_BG     = "#e8e8ed"
BTN2_FG     = "#1d1d1f"
BTN2_ACT    = "#d8d8dd"
SUCCESS_BG  = "#28a745"
ERROR_BG    = "#dc3545"
DIVIDER     = "#e5e5ea"
F_BODY      = ("Helvetica Neue", 13)
F_SMALL     = ("Helvetica Neue", 11)
F_LABEL     = ("Helvetica Neue", 11)
F_TITLE     = ("Helvetica Neue", 18, "bold")
F_SUB       = ("Helvetica Neue", 13)
F_BTN       = ("Helvetica Neue", 13, "bold")
F_MONO      = ("Menlo", 11)


# ---------------------------------------------------------------------------
# GUI
# ---------------------------------------------------------------------------

class InstallerApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("ChatGPT History for Claude")
        self.resizable(False, False)
        self.configure(bg=BG)
        self.selected_path: str | None = None
        self._build_ui()
        self.update_idletasks()
        w = self.winfo_width()
        h = self.winfo_height()
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        self.geometry(f"+{(sw - w) // 2}+{(sh - h) // 2}")

    def _build_ui(self):

        # ── Header ───────────────────────────────────────────────────────────
        hdr = tk.Frame(self, bg=HEADER_BG)
        hdr.pack(fill="x")

        tk.Label(
            hdr, text="💬",
            font=("Helvetica Neue", 36), bg=HEADER_BG,
        ).pack(pady=(28, 6))

        tk.Label(
            hdr, text="ChatGPT History for Claude",
            font=F_TITLE, fg="#f5f5f7", bg=HEADER_BG,
        ).pack()

        tk.Label(
            hdr,
            text="Search your past ChatGPT conversations\ndirectly from Claude Desktop.",
            font=F_SUB, fg="#98989d", bg=HEADER_BG, justify="center",
        ).pack(pady=(6, 28))

        # ── Body ─────────────────────────────────────────────────────────────
        body = tk.Frame(self, bg=BG, padx=28, pady=24)
        body.pack(fill="both")

        # Section label
        tk.Label(
            body, text="YOUR CHATGPT EXPORT FILE",
            font=("Helvetica Neue", 10, "bold"), fg=TEXT2, bg=BG, anchor="w",
        ).pack(fill="x")

        tk.Label(
            body,
            text="In ChatGPT: Settings → Data Controls → Export Data.\nYou'll get an email with a .zip file to download.",
            font=F_SMALL, fg=TEXT2, bg=BG, anchor="w", justify="left",
        ).pack(fill="x", pady=(3, 12))

        # ── File input row ────────────────────────────────────────────────────
        file_frame = tk.Frame(body, bg=INPUT_BD, padx=1, pady=1)
        file_frame.pack(fill="x")

        inner = tk.Frame(file_frame, bg=INPUT_BG)
        inner.pack(fill="x")

        self._file_lbl = tk.Label(
            inner, text="No file selected",
            font=F_LABEL, fg=INPUT_BD, bg=INPUT_BG,
            anchor="w", padx=12, pady=10,
        )
        self._file_lbl.pack(side="left", fill="x", expand=True)

        tk.Frame(inner, bg=INPUT_BD, width=1).pack(side="left", fill="y")

        tk.Button(
            inner, text="Browse…",
            command=self._pick_file,
            font=F_LABEL, fg=TEXT1, bg=INPUT_BG,
            relief="flat", padx=14, pady=10,
            cursor="hand2",
            activebackground=BG2, activeforeground=TEXT1,
            bd=0,
        ).pack(side="right")

        # ── Divider ───────────────────────────────────────────────────────────
        tk.Frame(body, bg=DIVIDER, height=1).pack(fill="x", pady=20)

        # ── Install button ────────────────────────────────────────────────────
        self.install_btn = tk.Button(
            body, text="Set up with Claude Desktop",
            command=self._start_install,
            font=F_BTN, fg=BTN_FG, bg=BTN_BG,
            relief="flat", pady=13,
            cursor="hand2",
            activebackground=BTN_ACT, activeforeground=BTN_FG,
            bd=0,
        )
        self.install_btn.pack(fill="x")

        # ── Status ────────────────────────────────────────────────────────────
        self.status_var = tk.StringVar(value="")
        self._status_lbl = tk.Label(
            body, textvariable=self.status_var,
            font=F_MONO, fg=TEXT2, bg=BG,
            anchor="w", justify="left", wraplength=W - 56,
        )
        self._status_lbl.pack(fill="x", pady=(14, 0))

        self.geometry(f"{W}x580")

    # ── Interactions ──────────────────────────────────────────────────────────

    def _pick_file(self):
        path = filedialog.askopenfilename(
            title="Select your ChatGPT export",
            filetypes=[("ChatGPT export", "*.zip *.json"), ("All files", "*.*")],
        )
        if path:
            self.selected_path = path
            name = Path(path).name
            self._file_lbl.config(text=f"  {name}", fg=TEXT1)

    def _start_install(self):
        if not self.selected_path:
            messagebox.showwarning(
                "No file selected",
                "Please select your ChatGPT export file first.",
            )
            return
        self.install_btn.config(state="disabled", text="Setting up…", bg=BTN2_BG, fg=BTN2_FG)
        threading.Thread(target=self._install, daemon=True).start()

    def _log(self, msg: str):
        self.after(0, lambda m=msg: self.status_var.set(m))

    def _install(self):
        try:
            self._log("Looking for uv…")
            uvx = find_uvx()
            if not uvx:
                install_uv(self._log)
                uvx = find_uvx()
                if not uvx:
                    raise RuntimeError(
                        "uv was installed but uvx wasn't found. "
                        "Please restart your Mac and run the installer again."
                    )

            self._log("Saving your export file…")
            stored = copy_export(self.selected_path, self._log)

            self._log("Updating Claude Desktop…")
            write_config(stored, uvx, self._log)

            self._log("All done — restart Claude Desktop to activate.")
            self.after(0, lambda: self.install_btn.config(
                text="✓  Setup complete", bg=SUCCESS_BG, fg=BTN_FG, state="disabled",
            ))
        except Exception as exc:
            self._log(f"Error: {exc}")
            self.after(0, lambda: self.install_btn.config(
                text="Try again", bg=ERROR_BG, fg=BTN_FG, state="normal",
            ))


def main():
    app = InstallerApp()
    app.mainloop()


if __name__ == "__main__":
    main()
