from __future__ import annotations

import argparse
import asyncio
import json
import sys
from typing import Any, Dict

from .config import AIConfig
from .kernel import invoke
from .orchestrator import run_batch


def _parse_json_arg(arg: str | None) -> Any:
    if not arg:
        return None
    try:
        return json.loads(arg)
    except json.JSONDecodeError as e:
        raise SystemExit(f"Invalid JSON for argument: {e}")


def main(argv: list[str] | None = None) -> int:
    argv = argv or sys.argv[1:]
    parser = argparse.ArgumentParser(prog="ai_kernel_core")
    sub = parser.add_subparsers(dest="cmd", required=True)

    run_p = sub.add_parser("run", help="Run a single task")
    run_p.add_argument("task", help="Task name, e.g., nl2cypher|summarize|classify|extract")
    run_p.add_argument("--input", help="JSON input for the task")

    batch_p = sub.add_parser("batch", help="Run a task over JSONL inputs")
    batch_p.add_argument("task", help="Task name")
    batch_p.add_argument("--input-file", required=True, help="Path to JSONL file")
    batch_p.add_argument("--output-file", help="Path to JSONL output (default stdout)")

    # Provider/model overrides
    for p in (run_p, batch_p):
        p.add_argument("--provider", help="Provider name (openai|gemini)")
        p.add_argument("--model", help="Model name")
        p.add_argument("--temperature", type=float)
        p.add_argument("--parallelism", type=int)
        p.add_argument("--rps", type=float)
        p.add_argument("--json-only", action="store_true")

    args = parser.parse_args(argv)

    cfg = AIConfig()
    # Apply overrides
    for k in ("provider", "model", "temperature", "parallelism", "rps"):
        v = getattr(args, k, None)
        if v is not None:
            setattr(cfg, k, v)
    if getattr(args, "json_only", False):
        cfg.json_only = True

    if args.cmd == "run":
        inp = _parse_json_arg(args.input) or {}
        out = asyncio.run(invoke(args.task, inp, cfg))
        print(json.dumps(out, ensure_ascii=False))
        return 0

    if args.cmd == "batch":
        results = []
        with open(args.input_file, "r", encoding="utf-8") as f:
            inputs = [json.loads(line) for line in f if line.strip()]
        outs = asyncio.run(run_batch(args.task, inputs, cfg))
        if args.output_file:
            with open(args.output_file, "w", encoding="utf-8") as w:
                for o in outs:
                    if isinstance(o, Exception):
                        o = {"error": str(o)}
                    w.write(json.dumps(o, ensure_ascii=False) + "\n")
        else:
            for o in outs:
                if isinstance(o, Exception):
                    o = {"error": str(o)}
                print(json.dumps(o, ensure_ascii=False))
        return 0

    return 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

