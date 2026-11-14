"""Deploy one real historical source component, never relabel a current result."""
from hashlib import sha1, sha256
import gzip
import json
from pathlib import Path


FIXTURE = Path(__file__).with_name("historical_reading_v3")
BASE_COMMIT = "5002e8c3c40ca14a29f3ed8a08f6fcab2ec14b9c"
SOURCE_BLOB = "8a06bfa7b92808db448fa8dee1eb2ba016cfc140"
OPERATING_COMMIT = "a6a2a8be54e628e68569caea245a48888744d607"
OPERATING_BLOB = "7a01204d5dff7970fee4b30fc3dfa3418d1d2f9e"


def _frozen_source(manifest, expected_name, expected_blob):
    if manifest["git_path"] != f"src/company_wiki/source_catalog/{expected_name}":
        raise ValueError("unexpected historical producer path")
    compressed = (FIXTURE / f"{expected_name}.gz").read_bytes()
    source = gzip.decompress(compressed)
    if (manifest["git_blob_sha1"] != expected_blob
            or sha256(compressed).hexdigest() != manifest["gzip_sha256"]
            or len(compressed) != manifest["gzip_bytes"]
            or sha256(source).hexdigest() != manifest["source_sha256"]
            or len(source) != manifest["source_bytes"]
            or sha1(b"blob " + str(len(source)).encode() + b"\0" + source).hexdigest() != expected_blob):
        raise ValueError("historical producer fixture does not match its actual Git blob")
    return source


def deploy_historical_reading_producer(root: Path) -> tuple[Path, Path, Path]:
    """Deploy exact old producer bytes and the matching operating-session owner.

    The rest of the application uses current code. Observation records the
    actual output without editing its schema, IDs or hashes.
    """
    manifest = json.loads((FIXTURE / "manifest.json").read_text(encoding="utf-8"))
    if manifest["commit"] != BASE_COMMIT:
        raise ValueError("unexpected historical producer commit")
    source = _frozen_source(manifest, "narrative_reading.py", SOURCE_BLOB)
    operating = manifest["producer_dependency"]
    if operating["commit"] != OPERATING_COMMIT:
        raise ValueError("unexpected historical operating-session commit")
    operating_source = _frozen_source(operating, "narrative_operating_relations.py", OPERATING_BLOB)
    deployed = root / "historical-v3-source/source_catalog"
    deployed.mkdir(parents=True)
    producer = deployed / "narrative_reading.py"
    producer.write_bytes(source)
    (deployed / "narrative_operating_relations.py").write_bytes(operating_source)
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
from company_wiki.document_understanding import summary_input
deployed = Path(DEPLOYED)
if any('company_wiki.source_catalog.' + name in sys.modules
       for name in ('narrative_reading', 'narrative_operating_relations')):
    raise SystemExit('historical producer must load before the current module')
# Expose the old import spellings only inside this historical subprocess.
summary_input._sent_policies = summary_input.sent_policies
summary_input._unread = summary_input.unread_units
summary_input._SHARED_CONSTRAINTS = summary_input.SHARED_CONSTRAINTS
catalog.__path__.insert(0, str(deployed))
from company_wiki.source_catalog import narrative_reading as reading
from company_wiki.source_catalog import narrative_operating_relations as operating
for module, filename, expected in (
    (reading, 'narrative_reading.py', READER_SHA),
    (operating, 'narrative_operating_relations.py', SESSION_SHA),
):
    physical = Path(module.__file__).resolve()
    if physical != (deployed / filename).resolve() or sha256(physical.read_bytes()).hexdigest() != expected:
        raise SystemExit('historical producer physical identity mismatch')
observations = Path(OBSERVATIONS)
def record(value):
    with observations.open('a', encoding='utf-8') as stream:
        stream.write(json.dumps(dict(value, pid=os.getpid(), producer=reading.__file__, source_sha256=READER_SHA,
                                     operating_sha256=SESSION_SHA)) + '\\n')
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
    code = code.replace("DEPLOYED", ascii(str(deployed))).replace("READER_SHA", ascii(manifest["source_sha256"]))
    code = code.replace("SESSION_SHA", ascii(operating["source_sha256"]))
    code = code.replace("OBSERVATIONS", ascii(str(observations)))
    (bootstrap / "sitecustomize.py").write_text(code, encoding="utf-8")
    return bootstrap, observations, producer
