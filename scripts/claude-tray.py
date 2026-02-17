#!/usr/bin/env python3
"""Claude Code system tray indicator for Ubuntu (AppIndicator3).

Reads per-session status from ~/.claude-tray/sessions.json
and shows an aggregate icon + per-session details in the menu.

The icon updates every second via polling. The menu uses pre-allocated
slots that are shown/hidden as needed — no widgets are ever added or
removed after init, so the menu never flickers.

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
STALE_MINUTES = 10

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

    # Prune stale sessions (no update for STALE_MINUTES)
    cutoff = (datetime.now() - timedelta(minutes=STALE_MINUTES)).isoformat()
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

        # Pre-allocate header + session slots (hidden by default)
        self._header = Gtk.MenuItem(label="No active sessions")
        self._header.set_sensitive(False)
        self.menu.append(self._header)

        self._slot_sep = Gtk.SeparatorMenuItem()
        self.menu.append(self._slot_sep)
        self._slot_sep.hide()

        self._slots = []
        for _ in range(MAX_SLOTS):
            item = Gtk.MenuItem(label="")
            item.set_sensitive(False)
            item.set_no_show_all(True)
            item.hide()
            self.menu.append(item)
            self._slots.append(item)

        self.menu.append(Gtk.SeparatorMenuItem())
        quit_item = Gtk.MenuItem(label="Quit")
        quit_item.connect("activate", Gtk.main_quit)
        self.menu.append(quit_item)
        self.menu.show_all()

        # show_all would show hidden slots, so re-hide them
        self._slot_sep.hide()
        for slot in self._slots:
            slot.hide()

        self.indicator.set_menu(self.menu)
        GLib.timeout_add_seconds(1, self._update)

    def _update(self):
        sessions = read_sessions()
        agg = aggregate_status(sessions)

        if agg != self._last_agg:
            self.indicator.set_icon_full(ICONS.get(agg, "user-offline"), agg)
            self.indicator.set_title(f"Claude Code: {agg}")
            self._last_agg = agg

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

        return True


ClaudeTray()
Gtk.main()
