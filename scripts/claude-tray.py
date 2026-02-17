#!/usr/bin/env python3
"""Claude Code system tray indicator for Ubuntu (AppIndicator3).

One tray icon per Claude Code session. Each icon shows the session's
current status. Icons appear when sessions start, disappear on SessionEnd.

Requirements:
    sudo apt install gir1.2-appindicator3-0.1

Usage:
    python3 claude-tray.py &
"""
import gi, json, os
gi.require_version('Gtk', '3.0')
gi.require_version('AppIndicator3', '0.1')
from gi.repository import Gtk, AppIndicator3, GLib

STATUS_FILE = os.path.expanduser("~/.claude-tray/sessions.json")
ICONS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "icons")

ICONS = {
    "working": "claude-working",
    "waiting": "claude-waiting",
    "active":  "claude-active",
    "idle":    "claude-idle",
}


def short_id(session_id):
    return session_id[:8] if len(session_id) > 8 else session_id


def read_sessions():
    try:
        with open(STATUS_FILE) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


class SessionIndicator:
    """A single tray icon for one Claude Code session."""

    def __init__(self, session_id, info):
        self.session_id = session_id
        self.indicator = AppIndicator3.Indicator.new(
            f"claude-session-{session_id}",
            "claude-idle",
            AppIndicator3.IndicatorCategory.APPLICATION_STATUS,
        )
        self.indicator.set_icon_theme_path(os.path.abspath(ICONS_DIR))
        self.indicator.set_status(AppIndicator3.IndicatorStatus.ACTIVE)

        # Minimal menu (AppIndicator3 requires one)
        menu = Gtk.Menu()
        self._label_item = Gtk.MenuItem(label="")
        self._label_item.set_sensitive(False)
        menu.append(self._label_item)
        menu.show_all()
        self.indicator.set_menu(menu)

        self._last_status = None
        self.update(info)

    def update(self, info):
        status = info.get("status", "idle")
        tool = info.get("tool_name")
        title = info.get("title", "")
        cwd = info.get("cwd", "")
        dirname = os.path.basename(cwd) if cwd else ""

        parts = []
        if dirname:
            parts.append(dirname)
        if title:
            parts.append(f"| {title}")
        parts.append(f"— {status}")
        if tool:
            parts.append(f"({tool})")

        label = " ".join(parts)
        self.indicator.set_title(label)
        self._label_item.set_label(label)

        if status != self._last_status:
            self.indicator.set_icon_full(
                ICONS.get(status, "claude-idle"), status
            )
            self._last_status = status

    def remove(self):
        self.indicator.set_status(AppIndicator3.IndicatorStatus.PASSIVE)


class ClaudeTrayManager:
    """Manages one SessionIndicator per active session."""

    def __init__(self):
        self._indicators = {}
        GLib.timeout_add_seconds(1, self._poll)

    def _poll(self):
        sessions = read_sessions()

        for sid, info in sessions.items():
            if sid in self._indicators:
                self._indicators[sid].update(info)
            else:
                self._indicators[sid] = SessionIndicator(sid, info)

        dead = [sid for sid in self._indicators if sid not in sessions]
        for sid in dead:
            self._indicators[sid].remove()
            del self._indicators[sid]

        return True


ClaudeTrayManager()
Gtk.main()
