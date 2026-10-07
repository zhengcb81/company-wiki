"""Public retirement returns before configuration or filesystem access."""
import json

import pytest
from company_wiki.source_catalog import cli

RETIRED = ('focus-cleanup', 'archive-retired-evidence', 'prune-retired-evidence',
           'duplicate-preview', 'duplicate-recycle')

@pytest.mark.parametrize('command', RETIRED)
@pytest.mark.parametrize('legacy_args', ([], ['--apply', '--confirmation-token', 'old',
                                            '--receipt-path', 'never.json']))
def test_retired_command_needs_neither_config_nor_legacy_permits(command, legacy_args, tmp_path, monkeypatch, capsys):
    def forbidden(*args, **kwargs):
        raise AssertionError('retired command reached production configuration')
    monkeypatch.setattr(cli, 'load_catalog_config', forbidden)
    missing = tmp_path / 'absent' / 'config.yaml'
    assert cli.main(['--config', str(missing), command, *legacy_args]) == 1
    output = capsys.readouterr()
    assert output.out == ''
    error = json.loads(output.err)
    assert error['error_code'] == 'MAINTENANCE_OPERATION_RETIRED'
    assert error['error_type'] == 'maintenance_operation_retired'
    assert error['operation'] == command
    assert error['retryable'] is False
    assert not list(tmp_path.iterdir())

def test_help_lists_current_readonly_inventory_without_retired_writers(capsys):
    with pytest.raises(SystemExit) as caught:
        cli.main(['--help'])
    assert caught.value.code == 0
    help_text = capsys.readouterr().out
    assert 'duplicates' in help_text
    assert all(name not in help_text for name in RETIRED)
    assert 'confirmation-token' not in help_text

def test_current_command_still_rejects_unknown_flags(tmp_path):
    with pytest.raises(SystemExit) as caught:
        cli.main(['--config', str(tmp_path / 'absent'), 'status', '--typo'])
    assert caught.value.code == 2
