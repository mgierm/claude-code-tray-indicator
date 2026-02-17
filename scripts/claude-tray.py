#!/usr/bin/env python3
"""Claude Code system tray indicator for Ubuntu (AppIndicator3).

Reads per-session status from ~/.claude-tray/sessions.json
and shows an aggregate icon + per-session details in the menu.

- Icon updates every second via polling.
- Menu content updates only when the user opens it (show signal).
- Sessions with no hook activity for 60s are considered dead.

Requirements:
    sudo apt install gir1.2-appindicator3-0.1

Usage:
    python3 claude-tray.py &
"""
import gi, json, os
from datetime import datetime, timedelta
gi.require_version('Gtk', '3.0')
gi.require_version('AppIndicator3', '0.1')
from gi.repository import Gtk, AppIndicator3, GLib

STATUS_FILE = os.path.expanduser("~/.claude-tray/sessions.json")
MAX_SLOTS = 10
STALE_SECONDS = 60

ICONS = {
    "working": "media-record",
    "waiting": "dialog-question",
    "active":  "user-available",
    "idle":    "user-offline",
}

STATUS_PRIORITY = {"working": 0, "waiting": 1, "active": 2, "idle": 3}


def aggregate_status(sessions):
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
            sessions = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

    cutoff = (datetime.now() - timedelta(seconds=STALE_SECONDS)).isoformat()
    return {
        sid: info for sid, info in sessions.items()
        if info.get("timestamp", "") > cutoff
    }


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

        # Pre-allocate all widgets once — never add/remove later
        self._header = Gtk.MenuItem(label="No active sessions")
        self._header.set_sensitive(False)
        self.menu.append(self._header)

        self._slot_sep = Gtk.SeparatorMenuItem()
        self._slot_sep.set_no_show_all(True)
        self.menu.append(self._slot_sep)

        self._slots = []
        for _ in range(MAX_SLOTS):
            item = Gtk.MenuItem(label="")
            item.set_sensitive(False)
            item.set_no_show_all(True)
            self.menu.append(item)
            self._slots.append(item)

        self.menu.append(Gtk.SeparatorMenuItem())
        quit_item = Gtk.MenuItem(label="Quit")
        quit_item.connect("activate", Gtk.main_quit)
        self.menu.append(quit_item)
        self.menu.show_all()

        # Refresh menu content only when user clicks the tray icon
        self.menu.connect("show", self._on_menu_show)

        self.indicator.set_menu(self.menu)
        GLib.timeout_add_seconds(1, self._update_icon)

    def _on_menu_show(self, _widget):
        """Populate pre-allocated slots with current data when menu opens."""
        sessions = read_sessions()
        items = list(sessions.items())[:MAX_SLOTS]

        if not items:
            self._header.set_label("No active sessions")
            self._slot_sep.hide()
        else:
            self._header.set_label(f"{len(items)} session(s)")
            self._slot_sep.show()

        for i, slot in enumerate(self._slots):
            if i < len(items):
                sid, info = items[i]
                status = info.get("status", "?")
                tool = info.get("tool_name")
                cwd = info.get("cwd", "")
                dirname = os.path.basename(cwd) if cwd else ""

                label = f"[{short_id(sid)}] {status}"
                if tool:
                    label += f" ({tool})"
                if dirname:
                    label += f"  \u2014 {dirname}"

                slot.set_label(label)
                slot.show()
            else:
                slot.hide()

    def _update_icon(self):
        """Timer: only update tray icon, never touch menu widgets."""
        sessions = read_sessions()
        agg = aggregate_status(sessions)

        if agg != self._last_agg:
            self.indicator.set_icon_full(ICONS.get(agg, "user-offline"), agg)
            self.indicator.set_title(f"Claude Code: {agg}")
            self._last_agg = agg

        return True


ClaudeTray()
Gtk.main()
