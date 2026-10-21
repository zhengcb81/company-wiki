from dataclasses import replace
from unit.test_local_source_boundaries import cn_lake, cn_request, original_with_text, NAME
from company_wiki.source_catalog.local_reconcile import prepare_local_source
from company_wiki.source_catalog.source_reader import SourceRef, SourceVersionReader


def test_latest_discovery_does_not_stop_at_first_valid_old_period(tmp_path):
    cat, root = cn_lake(tmp_path)
    try:
        folder = root / NAME
        folder.mkdir()
        expected = None
        for year in (2024, 2026):
            original = original_with_text(NAME + "\n" + str(year) + "\u5e74\u534a\u5e74\u5ea6\u62a5\u544a\n\u8bc1\u5238\u4ee3\u7801\uff1a600999")
            (folder / f"{year}.pdf").write_bytes(original.data)
            if year == 2026:
                expected = original.ref.content_sha256
        request = replace(cn_request(), fiscal_year=None, fiscal_period=None, mode="latest_as_of")
        result = prepare_local_source(cat, request)
        assert result["status"] == "ready", result
        ref = SourceRef(**result["source_ref"])
        assert ref.content_sha256 == expected, SourceVersionReader(cat).describe_version(ref)
    finally:
        cat.close()



def test_latest_prepare_existing_old_catalog_still_discovers_new_original(tmp_path):
    cat, root = cn_lake(tmp_path)
    try:
        folder = root / NAME
        folder.mkdir()
        old = original_with_text(NAME + "\n2024\u5e74\u534a\u5e74\u5ea6\u62a5\u544a\n\u8bc1\u5238\u4ee3\u7801\uff1a600999")
        (folder / "2024.pdf").write_bytes(old.data)
        prepared = prepare_local_source(cat, replace(cn_request(), fiscal_year=2024))
        assert prepared["status"] == "ready", prepared
        new = original_with_text(NAME + "\n2026\u5e74\u534a\u5e74\u5ea6\u62a5\u544a\n\u8bc1\u5238\u4ee3\u7801\uff1a600999")
        (folder / "2026.pdf").write_bytes(new.data)
        result = prepare_local_source(cat, replace(cn_request(), fiscal_year=None, fiscal_period=None, mode="latest_as_of"))
        assert result["status"] == "ready", result
        assert result["source_ref"]["content_sha256"] == new.ref.content_sha256
    finally:
        cat.close()


def test_latest_does_not_pick_registered_revision_before_unregistered_same_period(tmp_path):
    cat, root = cn_lake(tmp_path)
    try:
        folder = root / NAME
        folder.mkdir()
        body = NAME + "\n2026\u5e74\u534a\u5e74\u5ea6\u62a5\u544a\n\u8bc1\u5238\u4ee3\u7801\uff1a600999"
        old = original_with_text(body)
        (folder / "a.pdf").write_bytes(old.data)
        assert prepare_local_source(cat, cn_request())["status"] == "ready"
        revised = original_with_text(body + "\nRevised data")
        (folder / "b.pdf").write_bytes(revised.data)
        result = prepare_local_source(cat, replace(cn_request(), mode="latest_as_of"))
        # Both publication times are unknown; same-day verified opens cannot
        # resolve original chronology. Do not treat a lexical name as a version.
        assert result["status"] == "ambiguous", result
        assert result["blocks_download"] is True and result["source_ref"] is None
    finally:
        cat.close()



def test_latest_bounded_retries_advance_beyond_twenty_old_originals(tmp_path):
    from company_wiki.source_catalog.local_inventory import LocalPrepareLimits
    cat, root = cn_lake(tmp_path)
    try:
        folder = root / NAME
        folder.mkdir()
        expected = None
        for year in [*range(2001, 2021), 2026]:
            original = original_with_text(NAME + "\n" + str(year) + "\u5e74\u534a\u5e74\u5ea6\u62a5\u544a\n\u8bc1\u5238\u4ee3\u7801\uff1a600999")
            (folder / f"{year}.pdf").write_bytes(original.data)
            if year == 2026:
                expected = original.ref.content_sha256
        request = replace(cn_request(), fiscal_year=None, fiscal_period=None, mode="latest_as_of")
        counts = []
        for _attempt in range(24):
            result = prepare_local_source(cat, request, limits=LocalPrepareLimits(max_candidates=4))
            counts.append(cat.reader.fetchone("SELECT COUNT(*) FROM documents")[0])
            if result["status"] == "ready":
                assert result["source_ref"]["content_sha256"] == expected
                break
            assert result["status"] in {"unavailable", "blocked"} and result["blocks_download"], result
            assert result["download_events"] == 0
        assert result["status"] == "ready", (result, counts)
        assert counts[-1] == 21 and max(counts) > min(counts)
    finally:
        cat.close()


def test_latest_existing_proved_source_does_not_hide_new_unknown_original(tmp_path):
    cat, root = cn_lake(tmp_path)
    try:
        folder = root / NAME
        folder.mkdir()
        original = original_with_text(NAME + "\n2024\u5e74\u534a\u5e74\u5ea6\u62a5\u544a\n\u8bc1\u5238\u4ee3\u7801\uff1a600999")
        (folder / "2024.pdf").write_bytes(original.data)
        assert prepare_local_source(cat, replace(cn_request(), fiscal_year=2024))["status"] == "ready"
        (folder / "unknown.pdf").write_bytes(original_with_text(NAME + "\nUnresolved content").data)
        result = prepare_local_source(cat, replace(cn_request(), fiscal_year=None, fiscal_period=None, mode="latest_as_of"))
        assert result["status"] != "ready", result
        assert result["blocks_download"] is True
    finally:
        cat.close()

