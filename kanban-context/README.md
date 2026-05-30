# kanban-context plugin 🗂️

Injects recent Kanban board activity (task creation, moves, completions, blocks, worker heartbeats) into agent context via the `pre_llm_call` hook. Gives every agent in a session awareness of what work items are flowing through the board — without requiring them to call board tools explicitly.

## The Problem

The Hermes Kanban system (`hermes kanban`) powers multi-agent work queues with dependency chains, worker claims, and automatic promotion. But by default, the board lives in a SQLite database that agents never read during conversation. Workers using `kanban_*` tools see their assigned task, but orchestrators and conversation agents have **zero visibility** into:

- Tasks being created and moving through the pipeline
- Blocked items that may affect downstream work
- Completed tasks whose output (summaries) could be useful
- Worker progress notes (heartbeats)

This forces agents to operate blindly — they don't know what the team is working on unless someone mentions it in chat.

## The Solution

This plugin hooks into `pre_llm_call` and reads the last N events from the shared Kanban SQLite database. It injects a structured context block like:

```
[Recent Kanban Activity]

- [2h ago] [kanban] **Design auth schema** (created → ready)
- [30m ago] [kanban] **Implement auth API** (completed)
- [5m ago] [linkedin-content] **Weekly trends post** (in progress: scraper running)

[End Kanban Activity]
```

Agents see this before every LLM call — they know what's happening on the board without asking. No board queries, no extra tools, no context-switching.

## Multi-board support

Scans both the default board (`{$HERMES_HOME}/kanban.db`) and all named boards (`{$HERMES_HOME}/kanban/boards/*/kanban.db`). Events from all boards are merged and sorted chronologically, with a board label so agents can distinguish them.

## Relationship to multi-agent-context

The `multi-agent-context` plugin (also in this repo) shares conversation history across Telegram/Discord bots. `kanban-context` complements it by sharing **board** history — together they give agents both conversational and operational context.

## Requirements

- Hermes Agent v0.13.0+ with plugin system
- Python 3.11+
- No extra dependencies — uses Python stdlib (`sqlite3`, `json`, `os`)

## Install

```bash
cp -r kanban-context ~/.hermes/plugins/kanban-context
```

Add to your profile's `config.yaml`:
```yaml
plugins:
  enabled:
    - kanban-context
```

Restart the gateway.

For multi-profile setups, symlink or copy into each profile's plugins dir:
```bash
for agent in profile-a profile-b profile-c; do
  mkdir -p ~/.hermes/profiles/${agent}/plugins/
  ln -sf ~/.hermes/plugins/kanban-context \
          ~/.hermes/profiles/${agent}/plugins/kanban-context
done
```

## Configuration (Environment Variables)

| Variable | Default | Description |
|----------|---------|-------------|
| `KANBAN_CONTEXT_EVENT_LIMIT` | `10` | Max events to inject per pre-LLM context block |
| `KANBAN_CONTEXT_LOOKBACK_H` | `12` | Lookback window in hours |

## Events Tracked

| kind | Description |
|------|-------------|
| `created` | Task entered the board (includes target column) |
| `assigned` | Assignee changed |
| `claimed` | Worker picked it up |
| `completed` | Worker finished |
| `blocked` | Waiting on external input (includes reason) |
| `unblocked` | No longer blocked |
| `heartbeat` | Periodic progress note from worker |
| `spawned` | Worker process started |
| `archived` | Removed from active view |
| `commented` | Discussion added |
| `linked` | Dependency link set |
| `edited` | Metadata changed |
| `promoted` | Dependency engine moved it (e.g., todo → ready) |
