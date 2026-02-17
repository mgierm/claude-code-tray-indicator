# tray-indicator

System tray indicator for Ubuntu showing Claude Code session status with multi-session support.

## Features

- Shows aggregate status icon in the system tray
- Tracks multiple concurrent Claude Code sessions
- Per-session details in the dropdown menu (session ID, status, current tool, working directory)

## Status icons

| Icon | Meaning |
|------|---------|
| media-record (red dot) | Claude is working (running tools) |
| dialog-question | Claude is waiting for your input |
| user-available | Session active (just started) |
| user-offline | No active sessions |

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

## Usage

Everything is automatic:
- The plugin hooks report session status to `~/.claude-tray/sessions.json`
- On `SessionStart`, the tray app auto-launches if not already running
- The tray icon shows aggregate status across all sessions
- The dropdown menu lists each active session with its status, tool, and working directory
