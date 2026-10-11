"""Repeat only the isolated import probe after the proven fd0 lock correction."""

from pathlib import Path

source = Path(__file__).with_name("probe_import_stack.py")
script = source.read_text(encoding="utf-8").replace(
    '"probe-import-stack', '"probe-import-stack-after-fix'
)
exec(compile(script, str(source), "exec"))
