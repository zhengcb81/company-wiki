"""Scratch probe: print the swallowed exception via the _refusal spy."""
import io
import sys
import traceback
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, r'C:\Users\郑曾波\Projects\mb11-cwp\src')
from company_wiki.automation import narrative_transport_cli as cli

REQUEST = Path(
    r'C:\Users\郑曾波\Projects\mb11-cwp\tests\fixtures\narrative_transport_v1\read_request.json'
).read_bytes()
input_stream = io.TextIOWrapper(io.BytesIO(REQUEST), encoding='utf-8')
output_bytes, receipt_bytes = io.BytesIO(), io.BytesIO()
output_stream = io.TextIOWrapper(output_bytes, encoding='utf-8')
receipt_stream = io.TextIOWrapper(receipt_bytes, encoding='utf-8')
sys.stdin = input_stream
sys.stdout = output_stream
sys.stderr = receipt_stream
config = SimpleNamespace(project_root=Path(r'C:\Users\郑曾波\Projects\mb11-cwp'))
artifacts = SimpleNamespace(close=lambda: None)
catalog = SimpleNamespace(
    open_narrative_artifact_reader=lambda: artifacts, close=lambda: None,
)
cli.load_catalog_config = lambda _: config
cli.SourceCatalog = lambda _: catalog
cli.SourceVersionReader = lambda _: object()


class NoisyReader:
    def __init__(self, *_):
        pass

    def read(self, _):
        return SimpleNamespace(data=b'{"bundle":"exact bytes"}', receipt={'status': 'ok'})


cli.NarrativeTransportReader = NoisyReader

original_refusal = cli._refusal


def refusal_spy(status, reason):
    sys.__stdout__.write('REFUSAL %s/%s — active exception:\n' % (status, reason))
    traceback.print_exc(file=sys.__stdout__)
    return original_refusal(status, reason)


cli._refusal = refusal_spy
code = cli.main(['--config', 'unused.yaml'])
receipt_stream.seek(0)
sys.__stdout__.write('exit %s\n' % code)
