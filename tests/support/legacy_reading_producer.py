"""Deploy one real historical source component, never relabel a current result."""
from hashlib import sha1, sha256
import gzip
import json
from pathlib import Path


FIXTURE = Path(__file__).with_name("historical_reading_v3")
BASE_COMMIT = "5002e8c3c40ca14a29f3ed8a08f6fcab2ec14b9c"
SOURCE_BLOB = "8a06bfa7b92808db448fa8dee1eb2ba016cfc140"


def deploy_historical_reading_producer(root: Path) -> tuple[Path, Path, Path]:
    """Current runtime falls through around exact old physical producer bytes.

    Only the source producer is old. The original typed-v3 codec is explicitly
    selected by the launcher; this does not reproduce a whole historical release.
    The wrapper observes actual output without editing its schema, IDs or hashes.
    """
    manifest = json.loads((FIXTURE / "manifest.json").read_text(encoding="utf-8"))
    compressed = (FIXTURE / manifest["artifact"]).read_bytes()
    source = gzip.decompress(compressed)
    if (manifest["commit"] != BASE_COMMIT or manifest["git_blob_sha1"] != SOURCE_BLOB
            or sha256(compressed).hexdigest() != manifest["gzip_sha256"]
            or sha256(source).hexdigest() != manifest["source_sha256"]
            or len(source) != manifest["source_bytes"]
            or sha1(b"blob " + str(len(source)).encode() + b"\0" + source).hexdigest() != SOURCE_BLOB):
        raise ValueError("historical producer fixture does not match its actual Git blob")
    deployed = root / "historical-v3-source/source_catalog"
    deployed.mkdir(parents=True)
    producer = deployed / "narrative_reading.py"
    producer.write_bytes(source)
    bootstrap = root / "historical-v3-bootstrap"
    bootstrap.mkdir()
    observations = root / "historical-v3-producer.jsonl"
    code = '''"""Owned physical source deployment, not a source-output transformer."""
from hashlib import sha256
import json
import os
from pathlib import Path
import sys
import company_wiki.source_catalog as catalog
deployed = Path(DEPLOYED)
expected = EXPECTED
if 'company_wiki.source_catalog.narrative_reading' in sys.modules:
    raise SystemExit('historical producer must load before the current module')
catalog.__path__.insert(0, str(deployed))
from company_wiki.source_catalog import narrative_reading as reading
physical = Path(reading.__file__).resolve()
if physical != (deployed / 'narrative_reading.py').resolve() or sha256(physical.read_bytes()).hexdigest() != expected:
    raise SystemExit('historical producer physical identity mismatch')
observations = Path(OBSERVATIONS)
def record(value):
    with observations.open('a', encoding='utf-8') as stream:
        stream.write(json.dumps(dict(value, pid=os.getpid(), producer=str(physical), source_sha256=expected)) + '\\n')
record({'phase': 'loaded'})
original = reading.select_reading_evidence
def observe(*args, **kwargs):
    result = original(*args, **kwargs)
    context = result.reading_context
    record({'phase': 'selected', 'reading_schema': context['schema_version'],
            'views': sum(len(group.get('citation_views', ())) for group in context['groups']),
            'has_support_use': any('reading_support_use' in view for group in context['groups']
                                   for view in group.get('citation_views', ()))})
    return result
reading.select_reading_evidence = observe
'''
    code = code.replace("DEPLOYED", ascii(str(deployed))).replace("EXPECTED", ascii(manifest["source_sha256"]))
    code = code.replace("OBSERVATIONS", ascii(str(observations)))
    (bootstrap / "sitecustomize.py").write_text(code, encoding="utf-8")
    return bootstrap, observations, producer
