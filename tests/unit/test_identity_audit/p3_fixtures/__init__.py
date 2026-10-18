"""Lane-owned synthetic fixtures for the P3 read-only identity audit.

This package is intentionally independent: the catalog construction pattern was
copied from ``tests/unit/du11_identity_projection`` and no other test module or
card is imported.  Everything is written under ``tmp_path``; the production
catalog, production config and any real original stay untouched.
"""
