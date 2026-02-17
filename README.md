# tray-indicator

System tray indicator for Ubuntu showing Claude Code session status — one icon per active session.

## Features

- One tray icon per active Claude Code session
- Icon label shows working directory, session title, status, and current tool
- Session title captured from the first user prompt (truncated to 20 chars)
- Auto-launches on first `SessionStart`, stays running for subsequent sessions
- File-based IPC with file locking for safe concurrent access

## Status icons

| Icon | Meaning |
|------|---------|
| ![red circle](icons/claude-working.svg) `working` | Claude is running tools |
| ![blinking cursor](icons/claude-waiting.svg) `waiting` | Claude is waiting for your input |
| ![green circle](icons/claude-active.svg) `active` | Session just started |
| ![gray circle](icons/claude-idle.svg) `idle` | No active sessions |

## How it works

```
Claude Code hook event
        │
        ▼
tray-status-hook.py  (receives JSON on stdin, writes to sessions.json)
        │
        ▼
~/.claude-tray/sessions.json  (file-locked, one entry per session)
        │
        ▼  (polled every 1s)
claude-tray.py  (GTK3/AppIndicator3 tray icons)
```

## Requirements

```bash
sudo apt install gir1.2-appindicator3-0.1
```

## Installation

Add the marketplace and install the plugin from within Claude Code:

```
/plugin marketplace add mgierm/claude-code-tray-indicator
/plugin install tray-indicator@mgierm-tray
```

That's it. The tray app launches automatically when you start a Claude Code session.
