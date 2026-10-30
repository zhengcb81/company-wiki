"""Cold, local-only public preparation control using a neutral synthetic PDF."""
from datetime import UTC, datetime
from hashlib import sha256
import json
from pathlib import Path
import sys

import pymupdf

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from company_wiki.source_catalog.security_identity import SecurityMasterStore, SecurityRecord
from company_wiki.source_catalog.service import SourceCatalog
from company_wiki.source_catalog.config import load_catalog_config
from tools.document_understanding_benchmark.phase_c_readonly_source import prepare_registered_source


def test_cold_public_prepare_preserves_unknown_date_and_single_registration(tmp_path, monkeypatch):
    raw = tmp_path / 'input/companies/云岭科技/record.pdf'
    raw.parent.mkdir(parents=True)
    with pymupdf.open() as pdf:
        page = pdf.new_page()
        page.insert_text((40, 50), '证券代码：600997\n证券简称：云岭科技\n云岭科技股份有限公司投资者关系\n活动记录表',
                         fontname='china-s', fontsize=12)
        raw.write_bytes(pdf.tobytes())
    config = tmp_path / 'input/config.json'
    config.write_text(json.dumps({'schema_version': '1.0', 'catalog_dir': str(tmp_path / 'production'),
        'roots': [{'root_id': 'input', 'path': str(tmp_path / 'input/companies'), 'kind': 'company_raw'}]}), encoding='utf-8')
    owned = tmp_path / 'owned'
    master = SecurityMasterStore(owned / 'catalog/security_master')
    master.write_market('CN', (SecurityRecord('云岭科技', 'CN', 'SSE', '600997', '600997', (), True,
        'fixture', 'https://fixture.test/issuer', '600997', {}),),
        retrieved_at='2026-10-01T00:00:00Z', sources=('fixture',))
    before = {p: p.read_bytes() for p in (raw, config)}
    register = SourceCatalog.register_sources
    calls = []
    def observed(self, **kwargs):
        calls.append(kwargs)
        return register(self, **kwargs)
    monkeypatch.setattr(SourceCatalog, 'register_sources', observed)
    result = prepare_registered_source(source_config=config, owned_root=owned, original=raw,
        expected_sha256=sha256(raw.read_bytes()).hexdigest(),
        descriptor={'entity': '云岭科技', 'security_id': '600997', 'market': 'CN', 'document_kind': 'investor_relations'},
        as_of_date=datetime.now(UTC).date().isoformat())
    assert len(calls) == 1 and result['registration']['files_seen'] == 1
    assert result['local_preparation']['status'] == 'ready'
    assert result['manifest']['published_date'] is None
    assert result['manifest']['security_id'] == '600997'
    assert result['selection']['mode'] == 'qualified_source_request'
    assert result['raw_copies'] == result['download_events'] == 0
    assert before == {p: p.read_bytes() for p in before}
    assert not (tmp_path / 'production').exists()
    catalog = SourceCatalog(load_catalog_config(Path(result['catalog_config']), project_root=owned))
    try:
        assert catalog.reader.status()['documents'] == 1
    finally:
        catalog.close()
