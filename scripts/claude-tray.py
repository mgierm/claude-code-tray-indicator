#!/usr/bin/env python3
"""Claude Code system tray indicator for Ubuntu (AppIndicator3).

Reads per-session status from ~/.claude-tray/sessions.json
and shows an aggregate icon + per-session details in the menu.

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

ICONS = {
    "working": "media-record",
    "waiting": "dialog-question",
    "active":  "user-available",
    "idle":    "user-offline",
}

STATUS_PRIORITY = {"working": 0, "waiting": 1, "active": 2, "idle": 3}


def aggregate_status(sessions):
    """Return the highest-priority status across all sessions."""
    if not sessions:
        return "idle"
    return min(
        (s.get("status", "idle") for s in sessions.values()),
        key=lambda s: STATUS_PRIORITY.get(s, 99),
    )


def short_id(session_id):
    return session_id[:8] if len(session_id) > 8 else session_id


def build_labels(sessions):
    """Build a list of label strings representing current state."""
    labels = []
    if not sessions:
        labels.append("No active sessions")
    else:
        labels.append(f"{len(sessions)} session(s)")
        for sid, info in sessions.items():
            status = info.get("status", "?")
            tool = info.get("tool_name")
            cwd = info.get("cwd", "")
            dirname = os.path.basename(cwd) if cwd else ""

            label = f"[{short_id(sid)}] {status}"
            if tool:
                label += f" ({tool})"
            if dirname:
                label += f"  \u2014 {dirname}"
            labels.append(label)
    return labels


class ClaudeTray:
    def __init__(self):
        self.indicator = AppIndicator3.Indicator.new(
            "claude-code-indicator",
            "user-offline",
            AppIndicator3.IndicatorCategory.APPLICATION_STATUS,
        )
        self.indicator.set_status(AppIndicator3.IndicatorStatus.ACTIVE)
        self.indicator.set_title("Claude Code")
        self.menu = Gtk.Menu()
        self._last_labels = None
        self._last_agg = None
        self._session_items = []
        self._build_menu([])
        self.indicator.set_menu(self.menu)
        GLib.timeout_add_seconds(1, self.update_status)

    def _build_menu(self, labels):
        """Full menu rebuild — only called when labels actually change."""
        for child in self.menu.get_children():
            self.menu.remove(child)

        self._session_items = []
        for text in labels:
            item = Gtk.MenuItem(label=text)
            item.set_sensitive(False)
            self.menu.append(item)
            self._session_items.append(item)

        self.menu.append(Gtk.SeparatorMenuItem())
        quit_item = Gtk.MenuItem(label="Quit")
        quit_item.connect("activate", Gtk.main_quit)
        self.menu.append(quit_item)
        self.menu.show_all()
        self._last_labels = labels

    def update_status(self):
        try:
            with open(STATUS_FILE) as f:
                sessions = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            sessions = {}

        agg = aggregate_status(sessions)

        if agg != self._last_agg:
            self.indicator.set_icon_full(ICONS.get(agg, "user-offline"), agg)
            self.indicator.set_title(f"Claude Code: {agg}")
            self._last_agg = agg

        labels = build_labels(sessions)
        if labels != self._last_labels:
            self._build_menu(labels)

        return True


ClaudeTray()
Gtk.main()
