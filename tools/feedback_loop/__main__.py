"""Read-only plan or individual finite host tick from explicit diagnostic sidecars."""

import argparse
import json
from pathlib import Path
import sys

from .coordinator import advance
from .host import process_host, read_hosts
from .observations import read_batch


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="mode", required=True)
    for mode in ("plan", "tick"):
        command = commands.add_parser(mode)
        command.add_argument("inputs", type=Path, nargs="+")
        if mode == "tick":
            command.add_argument("--hosts", type=Path, required=True)
            command.add_argument("--rpc-timeout", type=int, default=30, help="host control RPC timeout in seconds")
    args = parser.parse_args(argv)
    batch = read_batch(args.inputs)
    if args.mode == "plan":
        result = batch.plan()
    else:
        if args.rpc_timeout <= 0:
            parser.error("--rpc-timeout must be positive")
        try:
            config = read_hosts(args.hosts)
        except (ValueError, OSError, RecursionError) as exc:
            parser.error(f"unreadable host configuration ({type(exc).__name__})")
        result = advance(batch, process_host(config, args.rpc_timeout))
    print(json.dumps(result, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
