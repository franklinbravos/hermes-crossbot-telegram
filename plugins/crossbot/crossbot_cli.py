#!/usr/bin/env python3
"""CLI for Kanban workers when crossbot_* tools are not in the worker toolset.

Hermes kanban workers use _HERMES_CORE_TOOLS only — plugin tools are not
inherited. Workers should call this script via the terminal tool:

  python3 ~/.hermes/plugins/crossbot/crossbot_cli.py respond 55 "Your reply"
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


def _load_plugin():
    init_path = Path(__file__).resolve().parent / "__init__.py"
    spec = importlib.util.spec_from_file_location("crossbot_plugin", init_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load plugin from {init_path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main() -> None:
    if len(sys.argv) < 2:
        print(
            "Usage:\n"
            "  crossbot_cli.py respond <outbox_id> <response_text>\n"
            "  crossbot_cli.py send <to_bot> <subject> <body>",
            file=sys.stderr,
        )
        sys.exit(2)

    mod = _load_plugin()
    cmd = sys.argv[1]

    if cmd == "respond":
        if len(sys.argv) < 4:
            print("Usage: crossbot_cli.py respond <outbox_id> <response_text>", file=sys.stderr)
            sys.exit(2)
        outbox_id = int(sys.argv[2])
        response = sys.argv[3]
        ok = mod.crossbot_respond(outbox_id, response)
        print(f"crossbot_respond({outbox_id}): {'OK' if ok else 'FAILED'}")
        sys.exit(0 if ok else 1)

    if cmd == "send":
        if len(sys.argv) < 5:
            print("Usage: crossbot_cli.py send <to_bot> <subject> <body>", file=sys.stderr)
            sys.exit(2)
        outbox_id = mod.crossbot_send(sys.argv[2], sys.argv[3], sys.argv[4])
        print(f"crossbot_send: outbox_id={outbox_id}")
        sys.exit(0)

    print(f"Unknown command: {cmd}", file=sys.stderr)
    sys.exit(2)


if __name__ == "__main__":
    main()
