"""Read-only plan or individual finite host tick from explicit diagnostic sidecars."""

import json
from pathlib import Path

from company_wiki import runtime_feedback

from .coordinator import settle
from .host import process_host, read_hosts
from .observations import read_batch


@runtime_feedback.entry("feedback-control", local_only=True, quiet_success=True)
def main(argv=None):
    parser = runtime_feedback.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="mode", required=True)
    for mode in ("plan", "tick"):
        command = commands.add_parser(mode)
        command.add_argument("inputs", type=Path, nargs="+")
        if mode == "tick":
            command.add_argument("--hosts", type=Path, required=True)
            command.add_argument("--rpc-timeout", type=int, default=30, help="host control RPC timeout in seconds")
            command.add_argument("--wait-seconds", type=int, default=0, help="poll pending actions within this window, in addition to RPC time")
    args = parser.parse_args(argv)
    batch = read_batch(args.inputs)
    if args.mode == "plan":
        result = batch.plan()
    else:
        if args.rpc_timeout <= 0:
            parser.error("--rpc-timeout must be positive")
        if args.wait_seconds < 0:
            parser.error("--wait-seconds must be nonnegative")
        try:
            config = read_hosts(args.hosts)
        except (ValueError, OSError, RecursionError) as exc:
            runtime_feedback.record_optional_failure("host_config_unavailable", exc)
            parser.error(f"unreadable host configuration ({type(exc).__name__})")
        result = settle(batch, process_host(config, args.rpc_timeout), args.wait_seconds)
    print(json.dumps(result, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(runtime_feedback.run_cli(main))
