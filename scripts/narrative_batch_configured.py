"""Compose the finite batch CLI with the project's existing LLM config loader."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Sequence

from config import Config
from company_wiki.automation.narrative_batch_cli import main as batch_main
from company_wiki.automation.narrative_http_model import model_options_from_config
from company_wiki.automation.models import canonical_json


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, add_help=False, allow_abbrev=False,
    )
    parser.add_argument("--llm-config", type=Path)
    parser.add_argument("--llm-provider", choices=("minimax", "mimo", "deepseek", "openai"))
    parser.add_argument("--allow-local-model-http", action="store_true")
    args, batch_args = parser.parse_known_args(argv)
    if "--help" in batch_args or "-h" in batch_args:
        parser.print_help()
        return batch_main(["--help"])
    try:
        options = model_options_from_config(
            Config.load(args.llm_config, llm_provider=args.llm_provider).llm)
        if args.allow_local_model_http:
            options["allow_local_http"] = True  # HTTP adapter still requires a loopback IP.
    except (OSError, TypeError, ValueError):
        print(canonical_json({"schema_version": "narrative-batch-result/1", "status": "failed",
                              "error": "NARRATIVE_MODEL_CONFIG_INVALID"}))
        return 1
    return batch_main(batch_args, loaded_model_options=options)


if __name__ == "__main__":
    raise SystemExit(main())
