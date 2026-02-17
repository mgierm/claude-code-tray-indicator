#!/usr/bin/env python3
"""Claude Code tray indicator hook.

Tracks per-session status in a shared JSON file (~/.claude-tray/sessions.json).
On SessionStart, auto-launches the tray app if not already running.
On first UserPromptSubmit, captures the prompt as session title.
Finds terminal PID via parent process chain for window focusing.
"""
import json, sys, os, fcntl, subprocess, shutil
from datetime import datetime

STATUS_DIR = os.path.expanduser("~/.claude-tray")
STATUS_FILE = os.path.join(STATUS_DIR, "sessions.json")

STATE_MAP = {
    "UserPromptSubmit": "working",
    "PreToolUse": "working",
    "Stop": "waiting",
    "SessionStart": "active",
    "SessionEnd": "idle",
}

TITLE_MAX_LEN = 20

# Terminal emulator process names
TERMINAL_NAMES = {
    "gnome-terminal-", "gnome-terminal-server",
    "konsole", "xfce4-terminal", "mate-terminal",
    "tilix", "terminator", "alacritty", "kitty", "wezterm",
    "xterm", "urxvt", "st", "foot",
}


def is_tray_running():
    try:
        result = subprocess.run(
            ["pgrep", "-f", "claude-tray.py"],
            capture_output=True,
        )
        return result.returncode == 0
    except OSError:
        return False


def launch_tray():
    plugin_root = os.environ.get("CLAUDE_PLUGIN_ROOT", "")
    tray_script = os.path.join(plugin_root, "scripts", "claude-tray.py")

    if not os.path.isfile(tray_script):
        return

    python = shutil.which("python3") or "python3"
    subprocess.Popen(
        [python, tray_script],
        start_new_session=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def find_terminal_pid():
    """Walk up the process tree to find the terminal emulator PID."""
    try:
        pid = os.getppid()  # claude process
        for _ in range(10):  # max depth
            stat_path = f"/proc/{pid}/stat"
            comm_path = f"/proc/{pid}/comm"
            if not os.path.exists(stat_path):
                break
            with open(comm_path) as f:
                name = f.read().strip()
            if any(name.startswith(t) for t in TERMINAL_NAMES):
                return pid
            with open(stat_path) as f:
                fields = f.read().split()
                ppid = int(fields[3])
            if ppid <= 1:
                break
            pid = ppid
    except (OSError, IndexError, ValueError):
        pass
    return None


def update_status(data, event, session_id):
    status = STATE_MAP.get(event, "unknown")
    os.makedirs(STATUS_DIR, exist_ok=True)

    try:
        fd = os.open(STATUS_FILE, os.O_RDWR | os.O_CREAT)
        fcntl.flock(fd, fcntl.LOCK_EX)
        with os.fdopen(fd, "r+") as f:
            try:
                sessions = json.load(f)
            except (json.JSONDecodeError, ValueError):
                sessions = {}

            if event == "SessionEnd":
                sessions.pop(session_id, None)
            else:
                existing = sessions.get(session_id, {})

                # Capture first user prompt as session title
                title = existing.get("title", "")
                if not title and event == "UserPromptSubmit":
                    prompt = data.get("prompt", "")
                    title = prompt[:TITLE_MAX_LEN]
                    if len(prompt) > TITLE_MAX_LEN:
                        title += "..."

                # Find terminal PID on first event
                terminal_pid = existing.get("terminal_pid")
                if terminal_pid is None and event == "SessionStart":
                    terminal_pid = find_terminal_pid()

                sessions[session_id] = {
                    "status": status,
                    "event": event,
                    "title": title,
                    "tool_name": data.get("tool_name"),
                    "cwd": data.get("cwd"),
                    "terminal_pid": terminal_pid,
                    "timestamp": datetime.now().isoformat(),
                }

            f.seek(0)
            f.truncate()
            json.dump(sessions, f)
    except OSError:
        pass


def main():
    data = json.load(sys.stdin)
    event = data.get("hook_event_name", "")
    session_id = data.get("session_id", "unknown")

    if event == "SessionStart" and not is_tray_running():
        launch_tray()

    update_status(data, event, session_id)


main()
