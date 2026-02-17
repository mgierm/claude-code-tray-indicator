#!/usr/bin/env python3
"""Claude Code system tray indicator for Ubuntu (AppIndicator3).

Reads per-session status from ~/.claude-tray/sessions.json
and shows an aggregate icon + per-session details in the menu.

The icon updates every second via polling. The menu content is only
refreshed when the user opens it (on-demand), avoiding flicker.

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


def read_sessions():
    try:
        with open(STATUS_FILE) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


class ClaudeTray:
    def __init__(self):
        self.indicator = AppIndicator3.Indicator.new(
            "claude-code-indicator",
            "user-offline",
            AppIndicator3.IndicatorCategory.APPLICATION_STATUS,
        )
        self.indicator.set_status(AppIndicator3.IndicatorStatus.ACTIVE)
        self.indicator.set_title("Claude Code")

        self._last_agg = None
        self.menu = Gtk.Menu()

        # Populate menu once at start, then refresh on open
        self._build_menu(read_sessions())
        self.menu.connect("show", self._on_menu_show)

        self.indicator.set_menu(self.menu)
        GLib.timeout_add_seconds(1, self._update_icon)

    def _on_menu_show(self, _widget):
        """Refresh menu content each time the user opens it."""
        self._build_menu(read_sessions())

    def _build_menu(self, sessions):
        """Rebuild menu from scratch (only called on open, not on timer)."""
        for child in self.menu.get_children():
            self.menu.remove(child)

        if not sessions:
            item = Gtk.MenuItem(label="No active sessions")
            item.set_sensitive(False)
            self.menu.append(item)
        else:
            header = Gtk.MenuItem(label=f"{len(sessions)} session(s)")
            header.set_sensitive(False)
            self.menu.append(header)
            self.menu.append(Gtk.SeparatorMenuItem())

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

                item = Gtk.MenuItem(label=label)
                item.set_sensitive(False)
                self.menu.append(item)

        self.menu.append(Gtk.SeparatorMenuItem())
        quit_item = Gtk.MenuItem(label="Quit")
        quit_item.connect("activate", Gtk.main_quit)
        self.menu.append(quit_item)
        self.menu.show_all()

    def _update_icon(self):
        """Timer callback: only update the tray icon, never touch the menu."""
        sessions = read_sessions()
        agg = aggregate_status(sessions)

        if agg != self._last_agg:
            self.indicator.set_icon_full(ICONS.get(agg, "user-offline"), agg)
            self.indicator.set_title(f"Claude Code: {agg}")
            self._last_agg = agg

        return True


ClaudeTray()
Gtk.main()
