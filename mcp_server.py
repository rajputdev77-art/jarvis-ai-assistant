"""
JARVIS MCP Server — exposes JARVIS's tools as a FastMCP server.

Run:
    python C:\\Users\\Dev\\JARVIS\\mcp_server.py
or with the SSE transport for use over the network:
    python C:\\Users\\Dev\\JARVIS\\mcp_server.py --sse

Add this to Cursor / Claude Desktop's MCP config:
    {
      "mcpServers": {
        "jarvis": {
          "command": "C:\\\\Users\\\\Dev\\\\JARVIS\\\\venv\\\\Scripts\\\\python.exe",
          "args": ["C:\\\\Users\\\\Dev\\\\JARVIS\\\\mcp_server.py"]
        }
      }
    }

Then Cursor / Claude Desktop can call JARVIS tools directly — shell, files,
windows, vision, project knowledge, the whole Avengers crew — natively
from inside the editor.
"""

import os
import sys
import json
import importlib.util

# Import jarvis.py without launching the voice loop
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
spec = importlib.util.spec_from_file_location(
    "jarvis_core", os.path.join(os.path.dirname(os.path.abspath(__file__)), "jarvis.py"))
jarvis = importlib.util.module_from_spec(spec)
sys.modules["jarvis_core"] = jarvis

# Suppress voice loop / tray / HUD if mcp_server is run standalone
os.environ["JARVIS_MCP_ONLY"] = "1"
spec.loader.exec_module(jarvis)

from fastmcp import FastMCP

mcp = FastMCP(
    name="JARVIS",
    instructions=(
        "You are connected to Mr. Stark's J.A.R.V.I.S. — a personal AI with "
        "shell execution, filesystem control, window/keyboard control, vision, "
        "Gmail, Telegram, project knowledge, and a five-agent Avengers crew. "
        "Use the tools to act on Mr. Stark's Windows machine. Be honest about "
        "what tools actually returned — never invent."
    ),
)


# ─── EXPOSE JARVIS TOOLS AS MCP TOOLS ────────────────────────────
# We wrap each native JARVIS function with a typed MCP-decorated function.
# Only the most useful tools for an IDE / chat context are exposed.

@mcp.tool()
def run_shell(command: str, shell: str = "powershell") -> str:
    """Execute a PowerShell or cmd command on Mr. Stark's Windows machine and return its output. Dangerous patterns (rm, del, format, shutdown) are blocked until confirm_with_user is called first."""
    return jarvis.dispatch_tool("run_shell", {"command": command, "shell": shell})


@mcp.tool()
def read_file(path: str) -> str:
    """Read a text file from Mr. Stark's machine. Truncates at 4000 chars."""
    return jarvis.dispatch_tool("read_file", {"path": path})


@mcp.tool()
def write_file(path: str, content: str, append: bool = False) -> str:
    """Write text to a file. Append mode optional. Refuses overwriting files outside JARVIS_HOME without confirmation."""
    return jarvis.dispatch_tool("write_file", {"path": path, "content": content, "append": append})


@mcp.tool()
def list_dir(path: str = ".") -> str:
    """List the contents of a directory."""
    return jarvis.dispatch_tool("list_dir", {"path": path})


@mcp.tool()
def find_files(pattern: str, root: str = "C:/Users/Dev") -> str:
    """Recursively find files matching a glob pattern under a root directory."""
    return jarvis.dispatch_tool("find_files", {"pattern": pattern, "root": root})


@mcp.tool()
def open_app(name_or_path: str, args: str = "") -> str:
    """Open an app on Mr. Stark's machine — known apps, Microsoft Store apps, .exe paths, folders, files, or URIs."""
    return jarvis.dispatch_tool("open_app", {"name_or_path": name_or_path, "args": args})


@mcp.tool()
def open_settings(panel: str) -> str:
    """Open a Windows Settings panel (bluetooth, wifi, display, sound, notifications, etc.)."""
    return jarvis.dispatch_tool("open_settings", {"panel": panel})


@mcp.tool()
def list_windows() -> str:
    """List visible top-level windows on the desktop."""
    return jarvis.dispatch_tool("list_windows", {})


@mcp.tool()
def focus_window(title: str) -> str:
    """Bring a window to the foreground by partial title match."""
    return jarvis.dispatch_tool("focus_window", {"title": title})


@mcp.tool()
def send_keys(keys: str) -> str:
    """Send keystrokes to the active window. PowerShell SendKeys syntax (^c=Ctrl+C, {ENTER}, %{F4}=Alt+F4)."""
    return jarvis.dispatch_tool("send_keys", {"keys": keys})


@mcp.tool()
def clipboard_read() -> str:
    """Return the current Windows clipboard text."""
    return jarvis.dispatch_tool("clipboard_read", {})


@mcp.tool()
def clipboard_write(text: str) -> str:
    """Set the Windows clipboard to the given text."""
    return jarvis.dispatch_tool("clipboard_write", {"text": text})


@mcp.tool()
def take_screenshot() -> str:
    """Capture Mr. Stark's screen and save it to his Pictures folder. Returns the saved path."""
    return jarvis.dispatch_tool("take_screenshot", {})


@mcp.tool()
def analyze_screen(question: str) -> str:
    """Look at Mr. Stark's screen and answer a question about it. Uses a vision model."""
    return jarvis.dispatch_tool("analyze_screen", {"question": question})


@mcp.tool()
def list_processes(filter: str = "") -> str:
    """List running processes, optionally filtered by name substring."""
    return jarvis.dispatch_tool("list_processes", {"filter": filter})


@mcp.tool()
def http_get(url: str) -> str:
    """Fetch a URL and return the response body (truncated)."""
    return jarvis.dispatch_tool("http_get", {"url": url})


@mcp.tool()
def system_status() -> str:
    """Return battery, CPU, RAM, and disk summary."""
    return jarvis.dispatch_tool("system_status", {})


@mcp.tool()
def get_weather(city: str = "Greater Noida") -> str:
    """Get weather for a city."""
    return jarvis.dispatch_tool("get_weather", {"city": city})


@mcp.tool()
def get_news(topic: str = "general") -> str:
    """Top news headlines on a topic, or general headlines."""
    return jarvis.dispatch_tool("get_news", {"topic": topic})


@mcp.tool()
def list_my_projects() -> str:
    """Return Mr. Stark's indexed project list (name, stack, last modified, path)."""
    return jarvis.dispatch_tool("list_my_projects", {})


@mcp.tool()
def gmail_read(count: int = 5, query: str = "is:unread") -> str:
    """Read messages from Mr. Stark's Gmail via the Gmail API."""
    return jarvis.dispatch_tool("gmail_read", {"count": count, "query": query})


@mcp.tool()
def gmail_send(to: str, subject: str, body: str) -> str:
    """Compose and send an email via Gmail API."""
    return jarvis.dispatch_tool("gmail_send", {"to": to, "subject": subject, "body": body})


@mcp.tool()
def telegram_send(message: str, chat_id: str = "") -> str:
    """Send a message via Telegram bot."""
    return jarvis.dispatch_tool("telegram_send", {"message": message, "chat_id": chat_id})


@mcp.tool()
def dispatch_crew(task: str) -> str:
    """Dispatch the Avengers (THOR, CAPTAIN, HULK, HAWKEYE, WIDOW) in parallel for a complex multi-domain task. Returns combined report."""
    return jarvis.dispatch_tool("dispatch_crew", {"task": task})


@mcp.tool()
def verify_app_running(name_substring: str) -> str:
    """Check if a process with that name is actually running. Returns YES/NO + PIDs."""
    return jarvis.dispatch_tool("verify_app_running", {"name_substring": name_substring})


@mcp.tool()
def verify_file_exists(path: str) -> str:
    """Check whether a file exists at a path."""
    return jarvis.dispatch_tool("verify_file_exists", {"path": path})


# ─── RESOURCES ────────────────────────────────────────────────────
@mcp.resource("jarvis://projects")
def projects_resource() -> str:
    """Mr. Stark's indexed project list as text."""
    return jarvis.load_project_index()


@mcp.resource("jarvis://status")
def status_resource() -> str:
    """Current system status."""
    return jarvis.system_status_summary()


# ─── PROMPTS ──────────────────────────────────────────────────────
@mcp.prompt()
def jarvis_personality() -> str:
    """The JARVIS personality prompt — use this in any LLM call to get
    the British butler tone and the Five Laws of operation."""
    return jarvis.SYSTEM_PROMPT


def main():
    transport = "sse" if "--sse" in sys.argv else "stdio"
    if transport == "sse":
        print("Starting JARVIS MCP server on SSE :8765 ...", flush=True)
        mcp.run(transport="sse", host="127.0.0.1", port=8765)
    else:
        mcp.run()  # stdio (for Cursor/Claude Desktop)


if __name__ == "__main__":
    main()
