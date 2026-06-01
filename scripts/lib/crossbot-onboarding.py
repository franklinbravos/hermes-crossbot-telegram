#!/usr/bin/env python3
"""CLI entry for crossbot guided onboarding."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
PLUGIN_DIR = REPO_ROOT / "plugins" / "crossbot"
if str(PLUGIN_DIR) not in sys.path:
    sys.path.insert(0, str(PLUGIN_DIR))

import onboarding as ob  # noqa: E402


def _print_json(data: object) -> None:
    print(json.dumps(data, indent=2, ensure_ascii=False))


def cmd_start(_args: argparse.Namespace) -> int:
    _print_json(ob.cmd_start())
    print("\nPróximo: crossbot-onboarding.sh current")
    return 0


def cmd_reset(args: argparse.Namespace) -> int:
    _print_json(ob.cmd_reset(step=args.step))
    return 0


def cmd_status(_args: argparse.Namespace) -> int:
    _print_json(ob.cmd_status())
    return 0


def cmd_current(_args: argparse.Namespace) -> int:
    data = ob.cmd_current()
    if data.get("error"):
        print("Onboarding não iniciado. Rode: crossbot-onboarding.sh start", file=sys.stderr)
        return 1
    _print_json(data)
    return 0


def cmd_verify(args: argparse.Namespace) -> int:
    data = ob.cmd_verify(watch=args.watch, step=args.step)
    if data.get("error"):
        print(data["error"], file=sys.stderr)
        return 1
    _print_json(data)
    return 0 if data.get("passed") else 2


def cmd_advance(_args: argparse.Namespace) -> int:
    data = ob.cmd_advance()
    if data.get("error"):
        _print_json(data)
        return 1
    _print_json(data)
    return 0


def cmd_run_action(args: argparse.Namespace) -> int:
    st = ob.load_state()
    if not st:
        print("Onboarding não iniciado", file=sys.stderr)
        return 1
    step = args.step or st.get("current_step")
    data = ob.run_action(step, st)
    _print_json(data)
    return 0 if data.get("ok") else 1


def main() -> int:
    parser = argparse.ArgumentParser(description="Crossbot guided onboarding")
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("start", help="Iniciar onboarding (step 1)")
    p_reset = sub.add_parser("reset", help="Resetar state")
    p_reset.add_argument("--step", help="Reiniciar em step específico (ex: 6)")

    sub.add_parser("status", help="Status geral")
    sub.add_parser("current", help="Etapa atual + instruções")

    p_verify = sub.add_parser("verify", help="Verificar gate da etapa")
    p_verify.add_argument("--watch", type=int, default=0, help="Poll a cada 5s até SEC")
    p_verify.add_argument("--step", help="Verificar step específico")

    sub.add_parser("advance", help="Avançar após verify OK")

    p_action = sub.add_parser("run-action", help="Executar ação automatizável da etapa")
    p_action.add_argument("--step", help="Step (default: current)")

    args = parser.parse_args()
    handlers = {
        "start": cmd_start,
        "reset": cmd_reset,
        "status": cmd_status,
        "current": cmd_current,
        "verify": cmd_verify,
        "advance": cmd_advance,
        "run-action": cmd_run_action,
    }
    return handlers[args.cmd](args)


if __name__ == "__main__":
    sys.exit(main())
