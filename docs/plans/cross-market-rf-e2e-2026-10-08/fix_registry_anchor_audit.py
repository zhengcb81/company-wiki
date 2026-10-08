"""Repair anchor membership without changing conflict or chain validation."""
from pathlib import Path

path = Path("C:/Users/郑曾波/Projects/revenue-forecast/scripts/publication_registry.py")
source = path.read_text(encoding="utf-8")
old = '    for path in result_files or []:\n'
assert source.count(old) == 1
source = source.replace(old, '    registered_anchors = {entry["input_sha256"] for entry in entries}\n' + old)
old = 'not isinstance(claimed, str) or claimed not in by_generation'
assert source.count(old) == 1
source = source.replace(old, 'not isinstance(claimed, str) or claimed not in registered_anchors')
path.write_text(source, encoding="utf-8")
print("Fixed anchor membership; generation conflict detection unchanged")
