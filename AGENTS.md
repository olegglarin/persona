# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

`persona` is an AI agent CLI built with Pydantic-AI. It runs an interactive REPL and dispatches tool calls (bash commands, file writes, skill loading) into a Docker sandbox container.

## Commands

```bash
uv sync                         # install dependencies
source .venv/bin/activate       # activate venv
docker build -t ubuntu.sandbox . # build sandbox image

persona                         # interactive REPL
persona "prompt"                # single prompt (non-interactive)
persona -p "prompt" --stream    # single prompt with streaming output
persona --skills-dir ./skills   # custom skills directory
persona --no-mnt                # disable host directory mounting
persona --mnt-dir /path/to/dir  # custom mount directory

# Testing
pytest tests/ -v
pytest tests/test_cli_eval.py -v                   # E2E CLI tests
pytest tests/test_conversation_history.py -v       # conversation history tests
python3 -m unittest discover -s skills -p "*_test.py" -v  # skill unit tests
python3 -m py_compile src/persona/some_file.py     # syntax check

# Linting / type checking (install first)
ruff check .
pyright .
```

## Environment & Configuration

- Copy `.env.example` → `.env` and configure API keys
- `DEBUG=true persona ...` — enables logfire instrumentation of Pydantic-AI and all HTTPX requests
- `LOGFIRE=true` — sends telemetry to configured logfire backend
- `OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4318` — optional local observability
- Sandbox env vars go in `.env.sandbox` (see `.env.sandbox.example`)

### MCP Servers

Set `MCP_ENABLED=true` in `.env`, then create `mcp_config.json` (see `mcp_config.json.sample`). Status is displayed in the REPL status bar.

## Architecture

### Request Flow

```
CLI args (cli.py)
  → create_agent() + ContainerManager (agent/builder.py, sandbox/manager.py)
  → PersonaREPL.run() (repl.py)
      → CommandRegistry.handle() — /commands intercepted before agent sees them
      → agent.iter() — autonomous loop:
          ModelRequestNode → streams text via PartStartEvent / PartDeltaEvent
          CallToolsNode    → executes tools, loops back automatically
          End              → task complete
```

### Key Components

**`repl.py` — `PersonaREPL`**: The interactive loop. Uses `prompt_toolkit` for input with history, `rich.Live + Markdown` for streaming output, and `rich.Status` spinner while waiting for the first token. Handles `Ctrl+C` via `SIGINT` signal handler + `InterruptedException` for clean mid-stream interruption.

**`agent/tools.py` — agent tools**: All tools use `@agent.tool_plain` (not `@agent.tool`). Three tools:
- `run_cmd(cmd)` — `docker exec` into the sandbox container
- `save_text_file(path, content)` — writes to sandbox, creates parent dirs
- `load_skill(skill_name)` — reads `skills/{name}/SKILL.md` from the container

**`session.py` — `SessionManager`**: Persists conversation history as JSON using `ModelMessagesTypeAdapter`. Auto-saves to 'latest' after every response; `/save`, `/load`, `/list`, `/new` commands manage named sessions.

**`sandbox/manager.py` — `ContainerManager`**: Starts/stops the Docker container. Mounts: `/mnt` (user files, default is current directory), `/skills` (skill definitions), `/tmp`. Registers `atexit` cleanup. Syncs host timezone to container.

**`skills/parser.py`**: Parses YAML frontmatter from `skills/{name}/SKILL.md`. Skills may also have `examples.md`, `reference.md`, and `scripts/`.

### Non-Obvious Patterns

- Agent tools are registered at startup inside `create_tools()` via closure over `container_name` — the container must exist before tool registration.
- `/commands` are processed by `CommandRegistry` before the agent loop; the agent never receives them.
- Single-prompt mode (non-interactive) still uses the same `agent.iter()` loop, just exits after one turn.
- `instructions.md` is the system prompt loaded at agent creation time.
